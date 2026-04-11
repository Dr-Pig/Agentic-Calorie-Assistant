from .admin_routes import router as admin_router
from .base_routes import router as base_router
from .intake_routes import router as intake_router
from .today_routes import router as today_router
from .user_routes import router as user_router
from .weight_routes import router as weight_router

__all__ = [
    "admin_router",
    "base_router",
    "intake_router",
    "today_router",
    "user_router",
    "weight_router",
]
