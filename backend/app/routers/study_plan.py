"""Study plan endpoints — generate, view, and manage adaptive study plans."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.study_plan import StudyPlanGenerateRequest, StudyPlanResponse, StudyDayPlan, StudyTaskItem
from app.services.study_planner import generate_study_plan, get_study_plans, toggle_task_completion

router = APIRouter(prefix="/api/study-plan", tags=["study-plan"])


@router.post("/generate", response_model=StudyPlanResponse)
async def generate_plan(data: StudyPlanGenerateRequest, db: AsyncSession = Depends(get_db)):
    """Generate a new adaptive study plan based on credits and daily hours."""
    plans = await generate_study_plan(data.subject_ids, data.daily_hours, db)
    days = [
        StudyDayPlan(
            plan_id=p["plan_id"],
            plan_date=p["plan_date"],
            tasks=[StudyTaskItem(**t) for t in p["tasks"]],
            completion_pct=p["completion_pct"],
        )
        for p in plans
    ]
    return StudyPlanResponse(days=days, total_days=len(days), daily_hours=data.daily_hours)


@router.get("/", response_model=StudyPlanResponse)
async def get_plan(db: AsyncSession = Depends(get_db)):
    """Get the current study plan."""
    plans = await get_study_plans(db)
    days = [
        StudyDayPlan(
            plan_id=p["plan_id"],
            plan_date=p["plan_date"],
            tasks=[StudyTaskItem(**t) for t in p["tasks"]],
            completion_pct=p["completion_pct"],
        )
        for p in plans
    ]
    return StudyPlanResponse(days=days, total_days=len(days))


@router.patch("/{plan_id}/tasks/{topic_id}/toggle")
async def toggle_task(plan_id: str, topic_id: str, db: AsyncSession = Depends(get_db)):
    """Toggle completion status of a task in a study plan."""
    result = await toggle_task_completion(plan_id, topic_id, db)
    return result
