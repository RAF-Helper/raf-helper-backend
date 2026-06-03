"""Document service for upload, parsing, chunking and ES indexing."""

from pathlib import Path
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import FileMetadata
from app.repositories.postgres_repository import FileMetadataRepository, ChatContextRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.elasticsearch_repository import ElasticsearchRepository
from app.services.embedding_service import get_embedding_service
from app.services.chunking_service import ChunkingService
from app.parsers import PDFParser, DocxParser, PptxParser, TextParser, MdParser

_PARSERS = {
    "application/pdf": PDFParser(),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxParser(),
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": PptxParser(),
    "text/plain": TextParser(),
    "text/markdown": MdParser(),
}

_CHUNK_SERVICE = ChunkingService()

_ALLOWED_MIME_TYPES = set(_PARSERS.keys())

# Mapping from file extensions to MIME types for fallback
_EXTENSION_MIME_MAP = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".rtf": "application/rtf",
}


class UnsupportedFileTypeError(Exception):
    pass


class DocumentService:
    def __init__(self, session: AsyncSession, es_repo: Optional[ElasticsearchRepository] = None):
        self.session = session
        self.file_repo = FileMetadataRepository(session)
        self.ctx_repo = ChatContextRepository(session)
        self.doc_repo = DocumentRepository(session)
        self.es_repo = es_repo or ElasticsearchRepository()

    def _storage_path(self, user_id: int, file_id: int, original_name: str) -> Path:
        base = Path(settings.storage_path) / str(user_id)
        base.mkdir(parents=True, exist_ok=True)
        ext = Path(original_name).suffix
        return base / f"{file_id}{ext}"

    def _resolve_mime_type(self, mime_type: str, original_name: str) -> str:
        """Resolve the correct MIME type, using extension as fallback."""
        if mime_type in _ALLOWED_MIME_TYPES:
            return mime_type
        # Fallback: check extension
        ext = Path(original_name).suffix.lower()
        return _EXTENSION_MIME_MAP.get(ext, mime_type)

    async def upload(
        self,
        user_id: int,
        data: bytes,
        original_name: str,
        mime_type: str,
    ) -> FileMetadata:
        """Save file to disk, persist metadata, parse and index chunks."""
        mime_type = self._resolve_mime_type(mime_type, original_name)
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

        # 4. Parse + chunk + index
        chunk_count = await self._index_file(file_record.id, str(file_record.document_id), mime_type, data, original_name)

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
        await self.es_repo.delete_document_chunks(str(file.document_id))

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

    async def get_full_document_text(self, document_id: str) -> str:
        """Retrieve full text of a document by re-parsing it from storage."""
        file_record = await self.file_repo.get_by_uuid(document_id)
        if not file_record:
            return ""

        parser = _PARSERS.get(file_record.mime_type, _PARSERS["text/plain"])

        try:
            # Load and parse from the stored path
            artifact = parser.load(file_record.path)
            document = parser.parse(artifact, file_record.original_name)

            # Concatenate all chunk contents
            full_text = "\n".join([chunk.content for chunk in document.document_chunks])
            return full_text
        except Exception as e:
            logging.error(f"Error re-parsing document {document_id} from {file_record.path}: {e}")
            return ""

    async def search_materials(
        self,
        query: str,
        document_ids: list[int],
        k: int = 5,
        return_chunks: bool = True,
    ) -> list[dict]:
        """Search materials via the DocumentRepository pipeline."""
        results = await self.doc_repo.search(
            query=query,
            document_ids=document_ids,
            k=k,
            return_chunks=return_chunks
        )

        if return_chunks or not results:
            return results

        # return_chunks=False: aggregate by document and retrieve full text
        full_docs = []
        for res in results:
            doc_id = res["document_id"]
            # TODO: Implement summarization for full text of documents that overwhelm the model's context
            full_text = await self.get_full_document_text(doc_id)

            # We can get the name from the repository's search result if available,
            # or fetch it from file_repo.
            file_record = await self.file_repo.get_by_uuid(doc_id)
            name = file_record.original_name if file_record else "Unknown Document"

            full_docs.append({
                "document_id": doc_id,
                "name": name,
                "content": full_text
            })

        return full_docs

    async def _index_file(
        self, file_id: int, document_id: str, mime_type: str, data: bytes, filename: str
    ) -> int:
        parser = _PARSERS.get(mime_type, _PARSERS["text/plain"])

        temp_path = Path(settings.storage_path) / f"temp_{file_id}_{filename}"
        temp_path.write_bytes(data)

        try:
            artifact = parser.load(str(temp_path))
            document = parser.parse(artifact, filename)
            document.id = document_id

            # Refine chunks using the ChunkingService
            refined_document = _CHUNK_SERVICE.chunk(document)

            # Use the specialized DocumentRepository for ingestion
            # which handles embeddings for content and all 3 levels of headings
            count = await self.doc_repo.ingest_document(refined_document)
            return count
        finally:
            if temp_path.exists():
                temp_path.unlink()
