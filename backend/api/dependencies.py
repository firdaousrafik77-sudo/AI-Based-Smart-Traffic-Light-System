"""
Layer 5 - API: Shared instances + shared helpers
All components are created once here and imported by the route files.
This is the only place where all layers are wired together.

Dependency order:
    config → data/ml/models → core → simulation → api
"""

import random
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

from .. import config

logger = logging.getLogger(__name__)
from ..data.database           import TrafficDatabase
from ..ml.predict              import TrafficPredictor       # inference only
from ..ml.optimizers           import ReinforcementLearningOptimizer, GeneticAlgorithmOptimizer
from ..core.intersection       import TrafficIntersection
from ..core.emergency_detector import EmergencyDetector
from ..core.simulation         import SimulationManager

# ---- Layer 2: Database -----------------------------------------------
db = TrafficDatabase(Path(config.DB_PATH))

# ---- Layer 3: ML components ------------------------------------------
# TrafficPredictor loads saved .joblib files from MODELS_DIR.
# If they don't exist yet (first run), main.py startup calls ModelTrainer
# to train and save them, then calls ml_predictor.load_models() to reload.
ml_predictor = TrafficPredictor(
    models_dir=Path(config.MODELS_DIR),
    history_window=config.ML_HISTORY_WINDOW,
)

rl_optimizer = ReinforcementLearningOptimizer(
    learning_rate=config.RL_LEARNING_RATE,
    discount_factor=config.RL_DISCOUNT_FACTOR,
)

ga_optimizer = GeneticAlgorithmOptimizer(
    population_size=config.GA_POPULATION_SIZE,
)

# ---- Layer 4: Core ---------------------------------------------------
emergency_detector = EmergencyDetector(config)

intersection = TrafficIntersection(
    name="Main Intersection",
    ml_predictor=ml_predictor,
    rl_optimizer=rl_optimizer,
    ga_optimizer=ga_optimizer,
    emergency_detector=emergency_detector,
)

simulation_manager = SimulationManager(
    intersection=intersection,
    db=db,
    config=config,
)


# ---- Shared helper ---------------------------------------------------

async def build_state_snapshot(save_to_db: bool = False) -> Dict:
    """
    Build the full state dict that both GET /api/state and the WebSocket send.
    Extracted here so the logic lives in exactly one place.

    Parameters
    ----------
    save_to_db : if True, persist the prediction and (occasionally) metrics.
                 The REST endpoint sets this True; the WebSocket sets it False
                 because it fires every second and we don't want to flood the DB.
    """
    status      = intersection.get_status()
    predictions = None

    if ml_predictor.is_trained:
        try:
            now         = datetime.now()
            predictions = await ml_predictor.predict_traffic(
                status['traffic'], now.hour, now.weekday()
            )
            if save_to_db:
                db.save_prediction(predictions)
        except Exception as exc:
            logger.error(f"Prediction error: {exc}")

    if save_to_db and random.random() < 0.1:
        db.save_metrics(intersection.metrics)

    return {
        **status,
        "predictions": predictions,
        "timestamp":   datetime.now().isoformat(),
    }
