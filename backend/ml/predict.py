"""
ML - Inference (prediction only)
Loads pre-trained model artifacts from disk and runs predictions.

This file has NO training code.
If models are not found on disk, it raises a clear error.
Training is handled entirely by train.py → ModelTrainer.
"""

import logging
from collections import deque
from pathlib import Path
from typing import Dict, Optional

import joblib
import numpy as np

from .features import FeatureBuilder
from .train import SCALER_FILE, FLOW_MODEL_FILE, CONGESTION_MODEL_FILE

logger = logging.getLogger(__name__)


class TrafficPredictor:
    """
    Inference-only predictor.

    Responsibilities:
        - Load the three saved artifacts (scaler, flow model, congestion model)
        - Accept live traffic data and return predictions
        - Keep a short rolling history per road (used as context)

    NOT responsible for training — see train.py for that.
    """

    def __init__(self, models_dir: Path, history_window: int = 10):
        self.models_dir      = Path(models_dir)
        self.feature_builder = FeatureBuilder()
        self.history_window  = history_window

        # Short rolling history — one deque per road
        self.history: Dict[str, deque] = {
            road: deque(maxlen=history_window)
            for road in ["North", "South", "East", "West"]
        }

        # Model objects (None until loaded)
        self.scaler           = None
        self.flow_model       = None
        self.congestion_model = None

        self.is_trained      = False
        self.last_prediction: Optional[Dict] = None

        # Try to load straight away; will succeed if train.py has already run
        self.load_models()

    # ------------------------------------------------------------------ #
    #  Model loading                                                       #
    # ------------------------------------------------------------------ #

    def load_models(self):
        """
        Load model artifacts from disk.
        Sets is_trained = True on success, False on failure.
        """
        try:
            self.scaler           = joblib.load(self.models_dir / SCALER_FILE)
            self.flow_model       = joblib.load(self.models_dir / FLOW_MODEL_FILE)
            self.congestion_model = joblib.load(self.models_dir / CONGESTION_MODEL_FILE)
            self.is_trained       = True
            logger.info(f"Models loaded from {self.models_dir}")
        except FileNotFoundError:
            logger.warning(
                f"Model files not found in {self.models_dir}. "
                "Call ModelTrainer.train_and_save() first."
            )
            self.is_trained = False

    # ------------------------------------------------------------------ #
    #  Prediction                                                          #
    # ------------------------------------------------------------------ #

    async def predict_traffic(self,
                              current_traffic: Dict[str, int],
                              time_of_day: int,
                              day_of_week: int) -> Dict:
        """
        Predict vehicle counts and congestion level for the next cycle.

        Parameters
        ----------
        current_traffic : live vehicle counts  {'North': n, 'South': n, ...}
        time_of_day     : hour 0-23
        day_of_week     : 0=Monday … 6=Sunday

        Returns
        -------
        {'North': int, 'South': int, 'East': int, 'West': int,
         'congestion_level': 0|1|2}
        """
        if not self.is_trained:
            raise RuntimeError(
                "Models are not loaded. "
                "Make sure ModelTrainer.train_and_save() has been called."
            )

        # Update rolling history
        for road, count in current_traffic.items():
            self.history[road].append(count)

        # Build feature vector
        features = self.feature_builder.build_single(
            current_traffic, time_of_day, day_of_week
        )

        try:
            scaled          = self.scaler.transform(features)
            pred_flows      = self.flow_model.predict(scaled)[0]
            pred_congestion = self.congestion_model.predict(scaled)[0]
        except Exception as exc:
            logger.warning(f"Prediction error, using current counts as fallback: {exc}")
            # Use current counts unchanged — no artificial inflation.
            pred_flows      = [current_traffic[r]
                               for r in ['North', 'South', 'East', 'West']]
            pred_congestion = 1

        result = {
            'North':            max(0, int(pred_flows[0])),
            'South':            max(0, int(pred_flows[1])),
            'East':             max(0, int(pred_flows[2])),
            'West':             max(0, int(pred_flows[3])),
            'congestion_level': int(pred_congestion),
        }
        self.last_prediction = result
        return result

    # ------------------------------------------------------------------ #
    #  Helper used by TrafficIntersection                                  #
    # ------------------------------------------------------------------ #

    def get_optimal_duration(self, traffic_volume: int,
                             congestion_level: int) -> int:
        """
        Map (traffic_volume, congestion_level) → recommended green seconds.
        Pure logic, no model call needed.
        """
        if traffic_volume > 50:   duration = 30
        elif traffic_volume > 30: duration = 25
        elif traffic_volume < 10: duration = 10
        else:                     duration = 15

        if congestion_level == 2:   duration = min(40, duration + 10)
        elif congestion_level == 0: duration = max(8,  duration - 5)

        return duration
