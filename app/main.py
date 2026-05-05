from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from contextlib import asynccontextmanager

from .database import init_db
from .logger import logger
from .readiness import validate_config
from .routes import router
from .runtime.interface.provider_runtime import close_provider_clients

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Canary application...")
    validate_config()
    init_db()
    yield
    await close_provider_clients()
    logger.info("Shutting down Canary application...")

app = FastAPI(title="Text Meal Canary", lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent.parent / "static"), name="static")
