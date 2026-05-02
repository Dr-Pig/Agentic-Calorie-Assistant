from __future__ import annotations

from fastapi import APIRouter

from app.database import get_db

# Import route modules from runtime and use-case composition surfaces.
from app.runtime.interface.base_routes import router as base_router
from app.composition.accurate_intake_debug_routes import router as accurate_intake_debug_router
from app.composition.body_plan_routes import router as body_plan_router
from app.composition.intake_routes import router as intake_router
from app.composition.onboarding_routes import router as onboarding_router
from app.composition.user_routes import router as user_router
from app.runtime.interface.admin_routes import router as admin_router
from app.composition.today_routes import router as today_router
from app.composition.weight_routes import router as weight_router
from app.composition.v2_routes import router as v2_router

# Runtime providers
from app.runtime.interface.provider_runtime import manager_provider, provider, search_provider

router = APIRouter()
router.include_router(base_router)
router.include_router(accurate_intake_debug_router)
router.include_router(body_plan_router)
router.include_router(intake_router)
router.include_router(onboarding_router)
router.include_router(user_router)
router.include_router(admin_router)
router.include_router(today_router)
router.include_router(weight_router)
router.include_router(v2_router)

__all__ = [
    "get_db",
    "manager_provider",
    "provider",
    "router",
    "search_provider",
]
