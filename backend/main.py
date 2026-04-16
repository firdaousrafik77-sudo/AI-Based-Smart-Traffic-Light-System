"""
Entry point — creates the FastAPI app and wires everything together.
This file should contain as little logic as possible; it only:
  - Configures the app (middleware, static files, routers)
  - Runs the ML training once at startup
  - Serves the frontend HTML
"""

import sys
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Make sure the project root is on sys.path so "backend.*" imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend import config
from backend.api.dependencies      import ml_predictor
from backend.ml.train              import ModelTrainer
from backend.api.routes.simulation import router as simulation_router
from backend.api.routes.emergency  import router as emergency_router
from backend.api.routes.analytics  import router as analytics_router
from backend.api.websocket         import router as ws_router

# ---- Logging setup ---------------------------------------------------
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ---- App creation ----------------------------------------------------
app = FastAPI(title=config.APP_NAME, version=config.APP_VERSION)

# CORS — allow the frontend to talk to the backend from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (CSS, JS)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/styles.css")
async def serve_css():
    return FileResponse(FRONTEND_DIR / "styles.css")

@app.get("/script.js")
async def serve_js():
    return FileResponse(FRONTEND_DIR / "script.js")

# ---- Routers ---------------------------------------------------------
app.include_router(simulation_router)
app.include_router(emergency_router)
app.include_router(analytics_router)
app.include_router(ws_router)

# ---- Startup event ---------------------------------------------------
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info(f"Starting {config.APP_NAME} v{config.APP_VERSION}")

    models_dir = ml_predictor.models_dir

    if not ModelTrainer.models_exist(models_dir):
        # First run — train from scratch and save to disk
        logger.info(f"No saved models found in {models_dir}")
        logger.info(f"Training with {config.ML_TRAINING_SAMPLES} samples...")
        trainer = ModelTrainer(models_dir)
        scores  = trainer.train_and_save(config.ML_TRAINING_SAMPLES)
        logger.info(f"Training complete: {scores}")

        # Reload the predictor so it picks up the newly saved files
        ml_predictor.load_models()
    else:
        # Subsequent runs — models already on disk, just confirm they loaded
        logger.info(f"Saved models found in {models_dir} — using them")

    logger.info(f"ML ready (is_trained={ml_predictor.is_trained})")
    logger.info(f"Dashboard → http://localhost:{config.PORT}")
    logger.info(f"API docs  → http://localhost:{config.PORT}/docs")
    logger.info("=" * 60)

# ---- Frontend --------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    index = FRONTEND_DIR / "index.html"
    try:
        return index.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error(f"index.html not found at {index}")
        return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)

# ---- Run directly ----------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower(),
    )
