"""Unit tests for DocumentRepository and DocumentService."""

import pytest
from uuid import uuid4
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from src.app.services.document_service import DocumentService, UnsupportedFileTypeError
from src.app.services.chunking_service import ChunkingService
from src.app.schemas.document import Document, DocumentChunk, DocumentFormat
from src.app.repositories.document_repository import DocumentRepository

@pytest.fixture
def mock_session():
    return MagicMock()

@pytest.fixture
def mock_es_repo():
    repo = MagicMock()
    repo.delete_document_chunks = AsyncMock()
    return repo

@pytest.fixture
def doc_service(mock_session, mock_es_repo):
    return DocumentService(session=mock_session, es_repo=mock_es_repo)

def test_document_service_upload_unsupported_type(doc_service):
    """Verify that unsupported mime types raise UnsupportedFileTypeError."""
    with pytest.raises(UnsupportedFileTypeError):
        # Use a mock async session and just call upload with bad mime
        import asyncio
        asyncio.run(doc_service.upload(
            user_id=1,
            data=b"test",
            original_name="test.exe",
            mime_type="application/x-msdownload"
        ))

@pytest.mark.asyncio
async def test_document_service_upload_flow(doc_service, mocker):
    """Verify the full upload orchestration: parse -> chunk -> ingest."""
    # Mock dependencies
    mock_file_repo = mocker.patch.object(doc_service, 'file_repo')
    mock_file_repo.create = AsyncMock(return_value=MagicMock(id=1, document_id=uuid4()))
    mock_file_repo.update = AsyncMock(return_value=MagicMock(id=1))

    # Mock storage path and filesystem operations to avoid PermissionError
    mocker.patch.object(doc_service, '_storage_path', return_value=Path("/tmp/test_file.txt"))
    mocker.patch("pathlib.Path.mkdir")
    mocker.patch("pathlib.Path.write_bytes")
    mocker.patch("pathlib.Path.unlink")

    # Mock parser and chunker
    mocker.patch("src.app.services.document_service._PARSERS", {
        "text/plain": MagicMock(
            load=MagicMock(return_value="raw text"),
            parse=MagicMock(return_value=Document(
                id=uuid4(), name="Test", filename="test.txt",
                format=DocumentFormat.TXT, document_chunks=[DocumentChunk(content="raw text")]
            ))
        )
    })

    # Mock the DocumentRepository (which is inside DocumentService)
    mock_doc_repo = MagicMock(spec=DocumentRepository)
    mock_doc_repo.ingest_document = AsyncMock(return_value=1)
    doc_service.doc_repo = mock_doc_repo

    result = await doc_service.upload(
        user_id=1,
        data=b"test content",
        original_name="test.txt",
        mime_type="text/plain"
    )

    assert result.id == 1
    mock_doc_repo.ingest_document.assert_called_once()

@pytest.mark.asyncio
async def test_document_repository_ingest_logic(mocker):
    """Verify DocumentRepository generates embeddings for content and levels."""
    # Mock EmbeddingService
    mock_embedder = MagicMock()
    mock_embedder.embed_batch = AsyncMock(return_value=[[0.1] * 10])
    mocker.patch("src.app.repositories.document_repository.get_embedding_service", return_value=mock_embedder)

    # Mock ES Repo
    mock_es = MagicMock()
    mock_es.bulk_index = AsyncMock(return_value=1)
    # Mock the ElasticsearchRepository class so that DocumentRepository's __init__ uses the mock
    mocker.patch("src.app.repositories.document_repository.ElasticsearchRepository", return_value=mock_es)

    repo = DocumentRepository()
    doc = Document(
        id=uuid4(),
        name="Test",
        filename="test.txt",
        format=DocumentFormat.TXT,
        document_chunks=[
            DocumentChunk(content="Content 1", level1="Chapter 1", level2="Section 1")
        ]
    )

    count = await repo.ingest_document(doc)

    assert count == 1
    # Verify embed_batch was called for content AND levels
    assert mock_embedder.embed_batch.call_count >= 2
    assert mock_es.bulk_index.called
