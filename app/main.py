from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routes import router

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="Text Meal Canary")
app.include_router(router)
app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent.parent / "static"), name="static")
