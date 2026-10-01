import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/upload", tags=["📁 Upload"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {
    ".pdf", ".zip", ".doc", ".docx", ".txt",
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".mp4", ".webm", ".mov",
}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a file. Returns a URL to download it."""
    # Validate extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type '{ext}' not allowed")

    # Read content + size check
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large (max 20MB)")

    # Generate unique filename
    unique_name = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, unique_name)

    # Save to disk
    with open(filepath, "wb") as f:
        f.write(content)

    return {
        "file_url": f"http://localhost:8000/api/upload/{unique_name}",
        "file_name": file.filename,
        "size": len(content),
    }


@router.get("/{filename}")
async def serve_file(filename: str):
    """Download or view an uploaded file."""
    # Security: prevent path traversal
    filename = os.path.basename(filename)
    filepath = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(filepath):
        raise HTTPException(404, "File not found")

    # Determine media type
    ext = os.path.splitext(filename)[1].lower()
    media_types = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".zip": "application/zip",
        ".txt": "text/plain",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        filepath,
        media_type=media_type,
        filename=filename,   # Forces Content-Disposition: attachment
    )