"""File upload, parsing, chunking and ES indexing service."""

import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db.models import FileMetadata
from ..repositories.postgres_repository import FileMetadataRepository, ChatContextRepository
from ..repositories.elasticsearch_repository import ElasticsearchRepository
from ..services.embedding_service import get_embedding_service
from ..elastic.parsers import PDFParser, DocxParser, PptxParser
from ..elastic.chunker import TextChunker

_PARSERS = {
    "application/pdf": PDFParser(),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxParser(),
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": PptxParser(),
}

_CHUNKER = TextChunker(max_size=1000, overlap=200)

_ALLOWED_MIME_TYPES = set(_PARSERS.keys())


class UnsupportedFileTypeError(Exception):
    pass


class FileService:
    def __init__(self, session: AsyncSession, es_repo: Optional[ElasticsearchRepository] = None):
        self.session = session
        self.file_repo = FileMetadataRepository(session)
        self.ctx_repo = ChatContextRepository(session)
        self.es_repo = es_repo or ElasticsearchRepository()

    # ------------------------------------------------------------------ #
    # Storage helpers                                                       #
    # ------------------------------------------------------------------ #

    def _storage_path(self, user_id: int, file_id: int, original_name: str) -> Path:
        base = Path(settings.storage_path) / str(user_id)
        base.mkdir(parents=True, exist_ok=True)
        ext = Path(original_name).suffix
        return base / f"{file_id}{ext}"

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    async def upload(
        self,
        user_id: int,
        data: bytes,
        original_name: str,
        mime_type: str,
    ) -> FileMetadata:
        """Save file to disk, persist metadata, parse and index chunks."""
        if mime_type not in _ALLOWED_MIME_TYPES:
            raise UnsupportedFileTypeError(
                f"Unsupported file type: {mime_type}. "
                f"Allowed: {', '.join(_ALLOWED_MIME_TYPES)}"
            )

        # 1. Create DB record to obtain the auto-generated ID.
        file_record = await self.file_repo.create(
            user_id=user_id,
            path="",  # filled after we know the ID
            original_name=original_name,
            mime_type=mime_type,
            size=len(data),
        )

        # 2. Persist bytes to disk.
        dest = self._storage_path(user_id, file_record.id, original_name)
        dest.write_bytes(data)

        # 3. Update path in DB.
        file_record = await self.file_repo.update(file_record.id, path=str(dest))

        # 4. Parse + chunk + index (synchronously for now; move to bg task if slow).
        chunk_count = await self._index_file(file_record.id, mime_type, data, original_name)

        file_record = await self.file_repo.update(
            file_record.id, is_indexed=True, chunk_count=chunk_count
        )
        return file_record

    async def get_file(self, file_id: int, user_id: int) -> Optional[FileMetadata]:
        file = await self.file_repo.get(file_id)
        if file and file.user_id == user_id:
            return file
        return None

    async def list_user_files(self, user_id: int) -> list[FileMetadata]:
        return await self.file_repo.get_by_user(user_id)

    async def delete_file(self, file_id: int, user_id: int) -> bool:
        file = await self.get_file(file_id, user_id)
        if not file:
            return False

        # Remove from ES
        await self.es_repo.delete_document_chunks(file_id)

        # Remove from disk
        path = Path(file.path)
        if path.exists():
            path.unlink(missing_ok=True)

        # Remove from DB (cascade removes chat_context rows)
        return await self.file_repo.delete(file_id)

    async def link_to_chat(self, file_id: int, chat_id: int, user_id: int) -> bool:
        file = await self.get_file(file_id, user_id)
        if not file:
            return False
        return await self.ctx_repo.link_file_to_chat(chat_id, file_id)

    async def unlink_from_chat(self, file_id: int, chat_id: int) -> bool:
        return await self.ctx_repo.unlink_file_from_chat(chat_id, file_id)

    async def get_chat_file_ids(self, chat_id: int) -> list[int]:
        files = await self.ctx_repo.get_files_for_chat(chat_id)
        return [f.id for f in files]

    # ------------------------------------------------------------------ #
    # Internal                                                              #
    # ------------------------------------------------------------------ #

    async def _index_file(
        self, file_id: int, mime_type: str, data: bytes, filename: str
    ) -> int:
        parser = _PARSERS[mime_type]
        parsed = parser.parse_bytes(data, filename)
        text: str = parsed.get("text", "")
        if not text.strip():
            return 0

        chunks = _CHUNKER.split(text)
        if not chunks:
            return 0

        # Generate embeddings for all chunks in parallel (using thread pool)
        embedder = get_embedding_service()
        vectors = await embedder.embed_batch(chunks)

        # Index chunks with their embeddings
        await self.es_repo.bulk_index_chunks(file_id, chunks, vectors)
        return len(chunks)
