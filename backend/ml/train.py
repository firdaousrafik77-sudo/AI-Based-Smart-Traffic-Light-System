"""
ML - Training
Trains both models from scratch and saves the artifacts to disk.

Saved files (inside MODELS_DIR):
    scaler.joblib           ← StandardScaler  (fitted on training data)
    flow_model.joblib       ← RandomForestRegressor
    congestion_model.joblib ← GradientBoostingClassifier

Run this once at startup if the files don't exist yet.
After training, TrafficPredictor (predict.py) loads these files.
"""

import logging
from pathlib import Path
from typing import Dict

import joblib
from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

from .features import FeatureBuilder

logger = logging.getLogger(__name__)

# File names — imported by predict.py so the names stay in sync
SCALER_FILE           = "scaler.joblib"
FLOW_MODEL_FILE       = "flow_model.joblib"
CONGESTION_MODEL_FILE = "congestion_model.joblib"


class ModelTrainer:
    """
    Full training pipeline:
      1. Generate synthetic traffic data  (via FeatureBuilder)
      2. Fit a StandardScaler
      3. Train a RandomForestRegressor    (predicts vehicle counts)
      4. Train a GradientBoostingClassifier (predicts congestion level)
      5. Save all three artifacts to disk with joblib
    """

    def __init__(self, models_dir: Path):
        self.models_dir      = Path(models_dir)
        self.feature_builder = FeatureBuilder()
        self.models_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    #  Public                                                              #
    # ------------------------------------------------------------------ #

    def train_and_save(self, n_samples: int = 5000) -> Dict[str, float]:
        """
        Train both models and persist them.

        Returns evaluation scores so the caller can log them.
        """
        logger.info(f"Generating {n_samples} synthetic training samples...")
        X, y_flow, y_congestion = self.feature_builder.generate_dataset(n_samples)

        # ---- 1. Fit scaler on the flow-model training split ----
        X_tr, X_te, yf_tr, yf_te = train_test_split(
            X, y_flow, test_size=0.2, random_state=42
        )
        scaler   = StandardScaler()
        X_tr_s   = scaler.fit_transform(X_tr)
        X_te_s   = scaler.transform(X_te)

        # ---- 2. Train flow model (regression) ----
        flow_model = RandomForestRegressor(n_estimators=100, random_state=42)
        flow_model.fit(X_tr_s, yf_tr)
        flow_r2 = flow_model.score(X_te_s, yf_te)
        logger.info(f"Flow model     R²       : {flow_r2:.3f}")

        # ---- 3. Train congestion model (classification) ----
        Xc_tr, Xc_te, yc_tr, yc_te = train_test_split(
            X, y_congestion, test_size=0.2, random_state=42
        )
        congestion_model = GradientBoostingClassifier(n_estimators=50, random_state=42)
        congestion_model.fit(scaler.transform(Xc_tr), yc_tr)
        cong_acc = congestion_model.score(scaler.transform(Xc_te), yc_te)
        logger.info(f"Congestion model accuracy: {cong_acc:.3f}")

        # ---- 4. Save to disk ----
        self._save_artifacts(scaler, flow_model, congestion_model)

        return {
            "flow_r2":             flow_r2,
            "congestion_accuracy": cong_acc,
            "n_samples":           n_samples,
        }

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _save_artifacts(self, scaler, flow_model, congestion_model):
        joblib.dump(scaler,           self.models_dir / SCALER_FILE)
        joblib.dump(flow_model,       self.models_dir / FLOW_MODEL_FILE)
        joblib.dump(congestion_model, self.models_dir / CONGESTION_MODEL_FILE)
        logger.info(f"Saved 3 model artifacts → {self.models_dir}")

    @staticmethod
    def models_exist(models_dir: Path) -> bool:
        """Check whether all three artifact files are already on disk."""
        d = Path(models_dir)
        return (
            (d / SCALER_FILE).exists() and
            (d / FLOW_MODEL_FILE).exists() and
            (d / CONGESTION_MODEL_FILE).exists()
        )
