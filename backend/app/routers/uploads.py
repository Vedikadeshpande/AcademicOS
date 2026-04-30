"""File upload endpoints — PDF, PPT, PYQ papers."""
import os
import uuid
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.config import settings
from app.models.subject import Subject
from app.models.upload import Upload

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".ppt"}


@router.post("/", status_code=201)
async def upload_file(
    background_tasks: BackgroundTasks,
    subject_id: str = Form(...),
    file_type: str = Form(...),  # pdf, ppt, pyq
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # Validate subject exists
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}")

    if file_type not in ("pdf", "ppt", "pyq"):
        raise HTTPException(status_code=400, detail="file_type must be one of: pdf, ppt, pyq")

    # Save file to disk
    subject_dir = os.path.join(settings.UPLOAD_DIR, subject_id)
    os.makedirs(subject_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}{ext}"
    file_path = os.path.join(subject_dir, safe_filename)

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    # Create upload record
    upload = Upload(
        id=file_id,
        subject_id=subject_id,
        filename=file.filename,
        file_type=file_type,
        file_path=file_path,
        status="processing",
    )
    db.add(upload)
    await db.commit()
    await db.refresh(upload)

    # Kick off background processing
    background_tasks.add_task(process_upload, file_id)

    return {
        "id": upload.id,
        "filename": upload.filename,
        "file_type": upload.file_type,
        "status": upload.status,
    }


@router.get("/{subject_id}")
async def list_uploads(subject_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Upload)
        .where(Upload.subject_id == subject_id)
        .order_by(Upload.uploaded_at.desc())
    )
    uploads = result.scalars().all()
    return [
        {
            "id": u.id,
            "filename": u.filename,
            "file_type": u.file_type,
            "status": u.status,
            "uploaded_at": u.uploaded_at.isoformat(),
        }
        for u in uploads
    ]


@router.get("/status/{upload_id}")
async def get_upload_status(upload_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalar_one_or_none()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return {
        "id": upload.id,
        "filename": upload.filename,
        "status": upload.status,
    }

@router.delete("/{upload_id}")
async def delete_upload(upload_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalar_one_or_none()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Delete file from disk
    if upload.file_path and os.path.exists(upload.file_path):
        try:
            os.remove(upload.file_path)
        except OSError:
            pass

    # Delete DB record (cascade deletes content_chunks)
    await db.delete(upload)
    await db.commit()
    return {"status": "deleted", "id": upload_id}


async def process_upload(upload_id: str):
    """Background task to process uploaded files (extraction, chunking, embedding)."""
    from app.services.file_processor import process_file
    try:
        await process_file(upload_id)
    except Exception as e:
        # Mark as error — log in production
        print(f"Error processing upload {upload_id}: {e}")

