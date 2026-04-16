"""Configuration module for Smart Traffic System"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(ENV_PATH)

# Application settings
APP_NAME = "Smart Traffic Control System"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "3000"))
WORKERS = int(os.getenv("WORKERS", "1"))

# ML Model settings
ML_TRAINING_SAMPLES = int(os.getenv("ML_TRAINING_SAMPLES", "5000"))
ML_HISTORY_WINDOW = int(os.getenv("ML_HISTORY_WINDOW", "10"))

# Traffic simulation settings
TRAFFIC_UPDATE_INTERVAL = int(os.getenv("TRAFFIC_UPDATE_INTERVAL", "1"))  # seconds
SPAWN_RATE_RUSH_HOUR = int(os.getenv("SPAWN_RATE_RUSH_HOUR", "2"))  # seconds
SPAWN_RATE_NORMAL = int(os.getenv("SPAWN_RATE_NORMAL", "3"))  # seconds
SPAWN_RATE_NIGHT = int(os.getenv("SPAWN_RATE_NIGHT", "5"))  # seconds

# Traffic light timings (seconds)
YELLOW_DURATION = float(os.getenv("YELLOW_DURATION", "4.5"))  # Real-world: 4-6 seconds
ALL_RED_DURATION = float(os.getenv("ALL_RED_DURATION", "2"))   # Safety clearance between phases
MIN_GREEN_DURATION = int(os.getenv("MIN_GREEN_DURATION", "10"))
MAX_GREEN_DURATION = int(os.getenv("MAX_GREEN_DURATION", "40"))

# Speed-based yellow light durations (seconds) - configurable per zone
YELLOW_DURATION_BY_SPEED = {
    25: 3.5,    # 25 mph zones
    35: 4.0,    # 35 mph zones
    45: 4.5,    # 45 mph zones
    55: 5.5,    # 55 mph zones
}

# Thresholds
CONGESTION_THRESHOLD = int(os.getenv("CONGESTION_THRESHOLD", "60"))
EMERGENCY_TRAFFIC_THRESHOLD = int(os.getenv("EMERGENCY_TRAFFIC_THRESHOLD", "100"))
EMERGENCY_SINGLE_ROAD_THRESHOLD = int(os.getenv("EMERGENCY_SINGLE_ROAD_THRESHOLD", "50"))

# Emergency detection
EMERGENCY_PROBABILITY = float(os.getenv("EMERGENCY_PROBABILITY", "0.001"))
EMERGENCY_PRIORITY_DURATION = int(os.getenv("EMERGENCY_PRIORITY_DURATION", "10"))  # seconds

# Database
DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent / "traffic_system.db"))

# Saved ML model artifacts (flow_model.joblib, congestion_model.joblib, scaler.joblib)
MODELS_DIR = os.getenv("MODELS_DIR", str(Path(__file__).parent.parent / "ml_models"))

# RL Optimizer settings
RL_LEARNING_RATE = float(os.getenv("RL_LEARNING_RATE", "0.1"))
RL_DISCOUNT_FACTOR = float(os.getenv("RL_DISCOUNT_FACTOR", "0.95"))
RL_EPSILON = float(os.getenv("RL_EPSILON", "0.1"))

# GA Optimizer settings
GA_POPULATION_SIZE = int(os.getenv("GA_POPULATION_SIZE", "20"))
GA_MUTATION_RATE = float(os.getenv("GA_MUTATION_RATE", "0.1"))

# Database settings
DB_CLEANUP_DAYS = int(os.getenv("DB_CLEANUP_DAYS", "7"))
DB_CLEANUP_INTERVAL_HOURS = int(os.getenv("DB_CLEANUP_INTERVAL_HOURS", "24"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "traffic_system.log")

print(f"Configuration loaded from {ENV_PATH if ENV_PATH.exists() else 'environment'}")
