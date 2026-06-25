"""FastAPI application entry point for Mumbai Local Delay API."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import analysis, ask, delays, meta

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Warm up ForecastCache in background on startup
    from api.routers.analysis import start_forecast_cache
    from pipeline.store import DelayStore

    store = DelayStore()
    try:
        start_forecast_cache(store)
    except Exception as exc:
        logger.error("Failed to start forecast cache background thread: %s", exc)
    finally:
        store.close()
    yield


app = FastAPI(
    title="Mumbai Local Delay API",
    description="REST API for Mumbai local train delay analytics — backs the React frontend.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(delays.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(meta.router, prefix="/api")
app.include_router(ask.router, prefix="/api")

import os
from fastapi.staticfiles import StaticFiles

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
