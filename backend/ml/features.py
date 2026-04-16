"""
ML - Feature engineering
Converts raw traffic data into the feature vectors that the models expect.

Why a separate file?
  Both training and prediction must build features in exactly the same way.
  Putting the logic here means there is one source of truth — you change
  the features in one place and both training and inference update together.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple


class FeatureBuilder:
    """
    Knows how to turn raw inputs into ML-ready arrays.

    Feature vector (one row):
        [hour, day_of_week, weather, event,
         north_count, south_count, east_count, west_count]

    Targets:
        y_flow       → [north, south, east, west]  (regression)
        y_congestion → 0 / 1 / 2                   (classification)
    """

    FEATURE_NAMES = [
        'hour', 'day', 'weather', 'event',
        'north', 'south', 'east', 'west',
    ]
    FLOW_TARGET_NAMES       = ['north', 'south', 'east', 'west']
    CONGESTION_TARGET_NAME  = 'congestion'

    # ------------------------------------------------------------------ #
    #  Used at prediction time                                            #
    # ------------------------------------------------------------------ #

    def build_single(self,
                     current_traffic: Dict[str, int],
                     time_of_day: int,
                     day_of_week: int,
                     weather: float = 0.8,
                     event: int = 0) -> np.ndarray:
        """
        Build one feature vector (shape: 1 × 8) for a live prediction.

        Parameters
        ----------
        current_traffic : vehicle counts per road right now
        time_of_day     : hour 0-23
        day_of_week     : 0=Monday … 6=Sunday
        weather         : 0.0 (bad) → 1.0 (clear)  — default 0.8
        event           : 0=normal, 1=moderate, 2=heavy event
        """
        return np.array([[
            time_of_day,
            day_of_week,
            weather,
            event,
            current_traffic['North'],
            current_traffic['South'],
            current_traffic['East'],
            current_traffic['West'],
        ]])

    # ------------------------------------------------------------------ #
    #  Used at training time                                               #
    # ------------------------------------------------------------------ #

    def generate_dataset(self, n_samples: int = 5000
                         ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Create a synthetic dataset that mimics realistic traffic patterns.

        Returns
        -------
        X             : feature matrix  (n_samples × 8)
        y_flow        : flow targets    (n_samples × 4)  — one column per road
        y_congestion  : congestion labels (n_samples,)   — 0 / 1 / 2
        """
        rows = []

        for _ in range(n_samples):
            hour    = np.random.randint(0, 24)
            day     = np.random.randint(0, 7)
            weather = np.random.uniform(0.0, 1.0)
            event   = np.random.choice([0, 1, 2], p=[0.80, 0.15, 0.05])

            # Base flow: sine wave over the day — peaks at noon and midnight
            base = 20 + 30 * np.sin(np.pi * hour / 12)
            if 7 <= hour <= 9 or 17 <= hour <= 19:
                base *= 1.5                       # rush-hour boost

            north = base * (1.2 if event == 2 else 1.0) + np.random.normal(0, 5)
            south = base * (1.2 if event >= 1 else 1.0) + np.random.normal(0, 5)
            east  = base * 0.7 + np.random.normal(0, 4)
            west  = base * 0.7 + np.random.normal(0, 4)

            avg        = np.mean([north, south, east, west])
            congestion = 0 if avg < 25 else (1 if avg < 50 else 2)

            rows.append([
                hour, day, weather, event,
                north, south, east, west,
                congestion,
            ])

        df = pd.DataFrame(
            rows,
            columns=self.FEATURE_NAMES + [self.CONGESTION_TARGET_NAME],
        )

        X            = df[self.FEATURE_NAMES].values
        y_flow       = df[self.FLOW_TARGET_NAMES].values
        y_congestion = df[self.CONGESTION_TARGET_NAME].values

        return X, y_flow, y_congestion
