from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.database import get_db, get_meal_log_history, get_or_create_user

router = APIRouter()


@router.get("/user/{user_id}/logs")
async def get_user_logs(user_id: str, include_superseded: bool = False, db: Any = Depends(get_db)) -> dict:
    user = get_or_create_user(db, user_id)
    logs = get_meal_log_history(db, user, limit=10, include_superseded=include_superseded)

    return {
        "user_id": user_id,
        "logs": [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "status": log.status,
                "parent_log_id": log.parent_log_id,
                "meal_title": log.meal_title,
                "kcal": log.kcal,
                "protein": log.protein_g,
                "carb": log.carb_g,
                "fat": log.fat_g,
                "components": log.components_json,
                "pending_question": log.pending_question,
            }
            for log in logs
        ],
    }


@router.post("/user/{user_id}/context/reset")
async def reset_user_context(user_id: str, db: Any = Depends(get_db)) -> dict:
    user = get_or_create_user(db, user_id)
    from app.models import MealLog

    drafts = db.query(MealLog).filter(MealLog.user_id == user.id, MealLog.status == "draft").all()
    for draft in drafts:
        draft.status = "superseded"
    db.commit()
    return {"status": "ok", "message": "Draft logs cleared"}
