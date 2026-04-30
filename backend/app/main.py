"""FastAPI main entry point — Academic OS Backend."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db

# Import ALL models here so SQLAlchemy's mapper resolves every
# string-based relationship (e.g. relationship("SyllabusTopic"))
# before the first request hits the database.
from app.models import subject, syllabus, upload, quiz, flashcard, study_plan as sp_model  # noqa: F401

from app.routers import subjects, uploads, syllabus, analytics, quizzes, flashcards, pyq, study_plan, viva


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    settings.ensure_dirs()
    await init_db()
    print("[OK] Academic OS backend started")
    print(f"  Database: {settings.DATABASE_URL}")
    print(f"  Uploads:  {settings.UPLOAD_DIR}")
    yield
    # Shutdown
    print("[STOP] Academic OS backend shutting down")


app = FastAPI(
    title="Academic OS",
    description="AI-powered Academic Operating System — Full academic co-pilot for students",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(subjects.router)
app.include_router(uploads.router)
app.include_router(syllabus.router)
app.include_router(analytics.router)
app.include_router(quizzes.router)
app.include_router(flashcards.router)
app.include_router(pyq.router)
app.include_router(study_plan.router)
app.include_router(viva.router)


@app.get("/")
async def root():
    return {
        "name": "Academic OS",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
