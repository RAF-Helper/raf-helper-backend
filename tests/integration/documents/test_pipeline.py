"""Integration test for the document pipeline: Upload -> Parse -> Chunk -> Index -> Search."""

import pytest
import asyncio
from uuid import uuid4
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from src.app.services.document_service import DocumentService
from src.app.repositories.document_repository import DocumentRepository
from src.app.schemas.document import Document, DocumentChunk, DocumentFormat

@pytest.mark.asyncio
async def test_document_pipeline_end_to_end(mocker):
    """
    Test the 'golden path':
    1. Upload a simple text file.
    2. Verify it is parsed and chunked.
    3. Verify it is ingested into the DocumentRepository.
    4. Verify it can be retrieved via search.
    """
    # 1. Setup mocks
    mock_session = MagicMock()

    # Mock Embedding Service globally BEFORE any other instantiation
    mock_embedder = MagicMock()
    mock_embedder.embed_batch = AsyncMock(return_value=[[0.1]*10] * 5)
    mock_embedder.embed_text = AsyncMock(return_value=[0.1]*10)

    mocker.patch("src.app.services.embedding_service.get_embedding_service", return_value=mock_embedder)
    mocker.patch("src.app.repositories.document_repository.get_embedding_service", return_value=mock_embedder)
    mocker.patch("src.app.services.document_service.get_embedding_service", return_value=mock_embedder)
    mocker.patch("src.app.services.embedding_service.EmbeddingService", return_value=mock_embedder)

    # Mock ElasticsearchRepository (the low-level one)
    mock_low_es = MagicMock()
    mock_low_es.bulk_index = AsyncMock(return_value=1)
    mock_low_es.search = AsyncMock(return_value=[{
        "document_id": "mock-doc-id",
        "chunk_text": "This is the expected content",
        "score": 1.0
    }])
    mocker.patch("src.app.repositories.elasticsearch_repository.ElasticsearchRepository", return_value=mock_low_es)
    mocker.patch("src.app.repositories.document_repository.ElasticsearchRepository", return_value=mock_low_es)

    # Now create the service
    # We pass a mock es_repo to the service, but the DocumentRepository inside it
    # will instantiate its own es_repo, which we've patched above.
    mock_es_repo = MagicMock()
    mock_es_repo.delete_document_chunks = AsyncMock()
    doc_service = DocumentService(session=mock_session, es_repo=mock_es_repo)

    # Mock FileMetadataRepository
    mock_file_repo = mocker.patch.object(doc_service, 'file_repo')
    doc_id = uuid4()
    mock_file_repo.create = AsyncMock(return_value=MagicMock(id=1, document_id=doc_id))
    mock_file_repo.update = AsyncMock(return_value=MagicMock(id=1))

    # Mock Filesystem
    mocker.patch.object(doc_service, '_storage_path', return_value=Path("/tmp/test_file.txt"))
    mocker.patch("pathlib.Path.mkdir")
    mocker.patch("pathlib.Path.write_bytes")
    mocker.patch("pathlib.Path.unlink")
    mocker.patch("builtins.open", mocker.mock_open(read_data="This is the expected content. It should be indexed and searchable."))

    # 2. Execution: Upload
    result = await doc_service.upload(
        user_id=1,
        data=b"This is the expected content. It should be indexed and searchable.",
        original_name="test.txt",
        mime_type="text/plain"
    )

    # 3. Verifications: Ingestion
    assert result.id == 1
    assert mock_low_es.bulk_index.called

    # 4. Execution: Search
    search_results = await doc_service.search_materials(
        query="expected content",
        document_ids=[str(doc_id)],
        k=1
    )

    # 5. Verifications: Retrieval
    assert len(search_results) == 1
    assert search_results[0]["chunks"][0] == "This is the expected content"
    assert mock_low_es.search.called
