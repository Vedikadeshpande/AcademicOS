"""Adaptive study planner — distributes topics across days based on credits, priority, and time."""
import json
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.subject import Subject
from app.models.syllabus import SyllabusUnit, SyllabusTopic
from app.models.study_plan import StudyPlan


def _compute_topic_priority(topic: SyllabusTopic) -> float:
    """Priority score: higher = needs more attention."""
    coverage_gap = 1.0 if not topic.is_covered else 0.0
    return (
        coverage_gap * 0.3
        + topic.pyq_frequency * 0.3
        + (1.0 - topic.quiz_accuracy) * 0.3
        + topic.importance_score * 0.1
    )


def _analyze_topic_complexity(topic: SyllabusTopic) -> float:
    """Analyze complexity (1-10) based on content depth and relative importance."""
    base_score = 3.0
    content = topic.content_cache or ""
    # Estimate depth via text volume (approx. +1 for every 500 words, max +5)
    length_factor = min(len(content) / 2500.0, 5.0)
    # Estimate conceptual difficulty via existing syllabus weight
    importance_factor = (topic.importance_score or 0.5) * 2.0
    return min(10.0, base_score + length_factor + importance_factor)

def _estimate_topic_minutes(priority: float, complexity: float) -> int:
    """Estimate dynamic study time considering both urgency and actual content depth."""
    base_time = 20
    if priority >= 0.7:
        base_time += 15
    # Add time dynamically based on the complexity score (up to +30 extra minutes)
    extra_time = int((complexity / 10.0) * 30)
    return base_time + extra_time

async def generate_study_plan(
    subject_ids: list[str],
    daily_hours: float,
    db: AsyncSession,
) -> list[dict]:
    """
    Generate an adaptive multi-subject study plan using Complexity Analysis.
    """
    daily_minutes = int(daily_hours * 60)

    # Fetch subjects
    if subject_ids:
        result = await db.execute(
            select(Subject).where(Subject.id.in_(subject_ids))
        )
    else:
        result = await db.execute(
            select(Subject).where(Subject.exam_date.isnot(None))
        )
    subjects = result.scalars().all()

    if not subjects:
        return []

    # Total credits for proportional allocation
    total_credits = sum(s.credits for s in subjects)

    # Find the latest exam date to determine plan duration
    today = date.today()
    exam_dates = [s.exam_date for s in subjects if s.exam_date and s.exam_date > today]
    if not exam_dates:
        end_date = today + timedelta(days=30)
    else:
        end_date = max(exam_dates)

    total_days = (end_date - today).days
    if total_days <= 0:
        total_days = 7

    # Delete existing plans for these subjects
    for s in subjects:
        existing = await db.execute(
            select(StudyPlan).where(
                StudyPlan.subject_id == s.id,
                StudyPlan.plan_date >= today,
            )
        )
        for plan in existing.scalars().all():
            await db.delete(plan)

    # Build topic lists per subject with priorities AND complexity
    subject_topics = {}
    for s in subjects:
        topics_result = await db.execute(
            select(SyllabusTopic)
            .join(SyllabusUnit)
            .where(SyllabusUnit.subject_id == s.id)
        )
        topics = topics_result.scalars().all()
        
        # Structure: (Topic, Priority, Complexity)
        scored = []
        for t in topics:
            p = _compute_topic_priority(t)
            c = _analyze_topic_complexity(t)
            scored.append({"topic": t, "priority": p, "complexity": c, "scheduled_time": 0})
            
        # Sort by urgency (priority) so high priority hits the schedule first
        scored.sort(key=lambda x: x["priority"], reverse=True)
        
        subject_topics[s.id] = {
            "subject": s,
            "topics": scored,
            "daily_minutes": int((s.credits / total_credits) * daily_minutes) if total_credits > 0 else 30,
        }

    created_plans = []

    for day_offset in range(total_days):
        plan_date = today + timedelta(days=day_offset)
        day_tasks = []

        for sid, data in subject_topics.items():
            s = data["subject"]
            if s.exam_date and plan_date > s.exam_date:
                continue

            remaining = data["daily_minutes"]
            topics = data["topics"]
            
            # Keep track of daily cognitive load to avoid complex stacking
            daily_complexity_load = 0.0
            
            for t_data in topics:
                if remaining <= 0:
                    break
                    
                t = t_data["topic"]
                p = t_data["priority"]
                c = t_data["complexity"]
                
                # Calculate total needed vs already scheduled
                total_needed = _estimate_topic_minutes(p, c)
                if t_data["scheduled_time"] >= total_needed:
                    continue # Already fully scheduled
                    
                # Cognitive Load Balancing:
                # If we already scheduled a highly complex topic today (load > 8), 
                # don't schedule another highly complex one (c > 7) on the SAME DAY, unless we must.
                if daily_complexity_load > 8.0 and c > 7.0:
                    continue # Skip to a lighter topic for today's padding

                time_left_for_topic = total_needed - t_data["scheduled_time"]
                allocated = min(time_left_for_topic, remaining)

                day_tasks.append({
                    "topic_id": t.id,
                    "topic_title": t.title,
                    "subject_id": s.id,
                    "subject_name": s.name,
                    "subject_color": s.color,
                    "duration_min": allocated,
                    "priority": round(p, 2),
                    "complexity": round(c, 1),
                    "is_completed": False,
                })

                t_data["scheduled_time"] += allocated
                remaining -= allocated
                daily_complexity_load += (c * (allocated/total_needed)) # Add partial load
                
            # If we still have remaining time & skipped heavy topics, force fill them (fallback)
            if remaining > 0:
                 for t_data in topics:
                    if remaining <= 0: break
                    total_needed = _estimate_topic_minutes(t_data["priority"], t_data["complexity"])
                    if t_data["scheduled_time"] < total_needed:
                        time_left_for_topic = total_needed - t_data["scheduled_time"]
                        allocated = min(time_left_for_topic, remaining)
                        day_tasks.append({
                            "topic_id": t_data["topic"].id,
                            "topic_title": t_data["topic"].title,
                            "subject_id": s.id,
                            "subject_name": s.name,
                            "subject_color": s.color,
                            "duration_min": allocated,
                            "priority": round(t_data["priority"], 2),
                            "complexity": round(t_data["complexity"], 1),
                            "is_completed": False,
                        })
                        t_data["scheduled_time"] += allocated
                        remaining -= allocated

            # Removed legacy cycle indexing

        # Save plan to DB
        if day_tasks:
            plan = StudyPlan(
                subject_id=subjects[0].id,  # Primary subject for grouping
                plan_date=plan_date,
                daily_schedule=json.dumps(day_tasks),
                completion_pct=0.0,
            )
            db.add(plan)
            await db.flush()

            created_plans.append({
                "plan_id": plan.id,
                "plan_date": plan_date.isoformat(),
                "tasks": day_tasks,
                "completion_pct": 0.0,
            })

    await db.commit()
    return created_plans


async def get_study_plans(db: AsyncSession) -> list[dict]:
    """Get all future study plans."""
    today = date.today()
    result = await db.execute(
        select(StudyPlan)
        .where(StudyPlan.plan_date >= today)
        .order_by(StudyPlan.plan_date.asc())
    )
    plans = result.scalars().all()

    return [
        {
            "plan_id": p.id,
            "plan_date": p.plan_date.isoformat(),
            "tasks": json.loads(p.daily_schedule) if p.daily_schedule else [],
            "completion_pct": p.completion_pct,
        }
        for p in plans
    ]


async def toggle_task_completion(
    plan_id: str, topic_id: str, db: AsyncSession
) -> dict:
    """Toggle a specific task's completion in a plan."""
    result = await db.execute(select(StudyPlan).where(StudyPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        return {"error": "Plan not found"}

    tasks = json.loads(plan.daily_schedule) if plan.daily_schedule else []
    found = False
    for task in tasks:
        if task["topic_id"] == topic_id:
            task["is_completed"] = not task["is_completed"]
            found = True
            break

    if not found:
        return {"error": "Task not found in plan"}

    # Recalculate completion
    total = len(tasks)
    completed = sum(1 for t in tasks if t.get("is_completed", False))
    plan.daily_schedule = json.dumps(tasks)
    plan.completion_pct = round((completed / total * 100) if total > 0 else 0.0, 1)

    await db.commit()
    return {
        "plan_id": plan_id,
        "topic_id": topic_id,
        "completion_pct": plan.completion_pct,
        "tasks": tasks,
    }
