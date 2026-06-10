"""File upload and management endpoints."""

import logging
import os
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.document_service import DocumentService, UnsupportedFileTypeError
from app.schemas.document import DocumentSearchRequest, DocumentChunk
from app.services.user_service import UserService
from app.api.auth.firebase import verify_firebase_token
from app.schemas.file import FileRead, FileUploadResponse
from app.config import settings

router = APIRouter(prefix="/files", tags=["files"])

_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


async def _resolve_user_id(
    firebase_uid: str, session: AsyncSession
) -> int:
    svc = UserService(session)
    user = await svc.get_by_firebase_id(firebase_uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Call POST /auth/sync first.",
        )
    return user.id


@router.post("/", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
) -> FileUploadResponse:
    """Upload a document file (PDF / DOCX / PPTX).

    The file is saved to local storage, its text is extracted, chunked and
    indexed in Elasticsearch for later RAG retrieval.
    """
    user_id = await _resolve_user_id(firebase_uid, session)

    data = await file.read()
    if len(data) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {_MAX_FILE_SIZE // 1024 // 1024} MB.",
        )

    mime = file.content_type or "application/octet-stream"
    try:
        svc = DocumentService(session)
        record = await svc.upload(
            user_id=user_id,
            data=data,
            original_name=file.filename or "upload",
            mime_type=mime,
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc))

    return FileUploadResponse(file=FileRead.model_validate(record))


@router.post("/search")
async def search_files(
    request: DocumentSearchRequest,
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
):
    """Search for materials across uploaded documents."""
    user_id = await _resolve_user_id(firebase_uid, session)
    svc = DocumentService(session)
    results = await svc.search_materials(
        query=request.query,
        document_ids=request.document_ids,
        k=request.limit
    )
    return results

@router.get("/", response_model=list[FileRead])
async def list_files(
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
) -> list[FileRead]:
    """List all files uploaded by the current user."""
    user_id = await _resolve_user_id(firebase_uid, session)
    svc = DocumentService(session)
    files = await svc.list_user_files(user_id)
    return [FileRead.model_validate(f) for f in files]


@router.get("/{file_id}", response_model=FileRead)
async def get_file(
    file_id: int,
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
) -> FileRead:
    """Get metadata for a specific file."""
    user_id = await _resolve_user_id(firebase_uid, session)
    svc = DocumentService(session)
    file = await svc.get_file(file_id, user_id)
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    return FileRead.model_validate(file)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: int,
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a file and remove its chunks from the search index."""
    user_id = await _resolve_user_id(firebase_uid, session)
    svc = DocumentService(session)
    deleted = await svc.delete_file(file_id, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")


_EXPORT_STORAGE = os.path.join(settings.storage_path, "..", "exports")
_EXPORT_STORAGE = os.path.normpath(_EXPORT_STORAGE)

# Only these are allowed for download — .pptx and .tex for now
_ALLOWED_EXPORT_EXTENSIONS = (".pptx", ".tex")

# Map extension → MIME type for the Content-Disposition header
_EXTENSION_MIME = {
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".tex": "application/x-latex",
}


@router.get("/exports/{filename:path}")
async def download_export(
    filename: str,
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
):
    """Download a previously generated export file (abstract .tex or presentation .pptx).

    The filename format is ``<type>_<chat_id>.<ext>`` (e.g. ``abstract_42.tex`` or
    ``presentation_42.pptx``).  The endpoint verifies that the requesting user owns
    the chat that produced the file before serving it.
    """
    user_id = await _resolve_user_id(firebase_uid, session)

    # 1. Validate filename — avoid path traversal
    basename = os.path.basename(filename)
    if not re.match(r"^(abstract|presentation)_\d+\.(tex|pptx)$", basename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid export filename format.",
        )

    ext = os.path.splitext(basename)[1]
    if ext not in _ALLOWED_EXPORT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension: {ext}",
        )

    # 2. Check file exists
    filepath = os.path.join(_EXPORT_STORAGE, basename)
    if not os.path.isfile(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found.",
        )

    # 3. Verify ownership — parse chat_id from filename and check it belongs to user
    match = re.match(r"^(abstract|presentation)_(\d+)\.", basename)
    chat_id = int(match.group(2))

    from app.services.chat_service import ChatService
    chat = await ChatService(session).get_chat(chat_id, user_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this export file.",
        )

    mime = _EXTENSION_MIME.get(ext, "application/octet-stream")
    return FileResponse(
        path=filepath,
        media_type=mime,
        filename=basename,
        headers={"Content-Disposition": f'attachment; filename="{basename}"'},
    )
