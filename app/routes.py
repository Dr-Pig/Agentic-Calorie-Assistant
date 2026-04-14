from __future__ import annotations

from fastapi import APIRouter

from .database import get_db
from .web import admin_router, base_router, intake_router, rescue_router, today_router, user_router, weight_router
from .web.provider_runtime import planner_provider, primary_provider, provider, search_provider

router = APIRouter()
router.include_router(base_router)
router.include_router(intake_router)
router.include_router(rescue_router)
router.include_router(user_router)
router.include_router(admin_router)
router.include_router(today_router)
router.include_router(weight_router)

__all__ = [
    "get_db",
    "planner_provider",
    "primary_provider",
    "provider",
    "router",
    "search_provider",
]
