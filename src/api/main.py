"""
FastAPI application entry point.
Configures the app with CORS, exception handlers, and routes.
"""

import logging
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import router
from src.api.schemas import HealthResponse
from src.api.jobs import job_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# App version
VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting Quant Backtester API v{VERSION}")
    yield
    # Shutdown
    logger.info("Shutting down API...")
    job_manager.shutdown(wait=True)
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Quant Backtester API",
    description="""
    A professional-grade backtesting engine exposed as a REST API.
    
    ## Features
    - **Event-driven architecture** for realistic simulation
    - **Async backtest execution** with job tracking
    - **Multiple strategies** with configurable parameters
    - **Performance metrics** including Sharpe ratio, drawdown, and more
    
    ## Workflow
    1. Start a backtest with `POST /backtest/run`
    2. Poll status with `GET /backtest/{job_id}`
    3. Retrieve results with `GET /results/{job_id}`
    """,
    version=VERSION,
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Exception Handlers
# ============================================================


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ============================================================
# Health & Info Endpoints
# ============================================================


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint.

    Returns the current status of the API service.
    """
    return HealthResponse(status="healthy", version=VERSION, timestamp=datetime.now())


@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": "Quant Backtester API",
        "version": VERSION,
        "docs": "/docs",
        "health": "/health",
    }


# Include routes
app.include_router(router)
