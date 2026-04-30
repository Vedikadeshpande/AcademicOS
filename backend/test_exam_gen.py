import asyncio
from app.database import async_session
from sqlalchemy import select
import app.main # to load all models and routers
from app.models.subject import Subject
from app.services.question_generator import generate_exam_paper

async def main():
    async with async_session() as db:
        subjects_res = await db.execute(select(Subject).limit(1))
        subject = subjects_res.scalar_one_or_none()
        if not subject:
            print("No subjects")
            return
        
        print(f"Testing for subject: {subject.name} ({subject.id})")
        questions = await generate_exam_paper(subject.id, db, "mid_sem")
        print(questions)

if __name__ == "__main__":
    asyncio.run(main())
