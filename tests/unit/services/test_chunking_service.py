"""Unit tests for the ChunkingService."""

import pytest
from uuid import uuid4
from src.app.services.chunking_service import ChunkingService
from src.app.schemas.document import Document, DocumentChunk, DocumentFormat
from src.app.config import settings

@pytest.fixture
def chunking_service():
    return ChunkingService()

def test_chunking_service_basic_split(chunking_service):
    """Verify that a long block of text is split into multiple chunks with overlap."""
    # Set a small chunk size for testing
    original_chunk_size = settings.chunk_size
    original_overlap = settings.chunk_overlap
    settings.chunk_size = 100
    settings.chunk_overlap = 20

    try:
        # Create a document with one large block of text
        content = (
            "This is a long piece of text that should definitely be split into multiple chunks "
            "because it exceeds the small max_size we just set for this test case. "
            "We want to verify that the recursive splitting logic works and that the overlap "
            "is correctly applied between the resulting chunks."
        )

        doc = Document(
            id=uuid4(),
            name="Test Doc",
            filename="test.txt",
            format=DocumentFormat.TXT,
            document_chunks=[
                DocumentChunk(content=content, level1="Chapter 1", metadata={"page_number": 1})
            ]
        )

        refined_doc = chunking_service.chunk(doc)

        assert len(refined_doc.document_chunks) > 1
        # Check that structural metadata is preserved
        for chunk in refined_doc.document_chunks:
            assert chunk.level1 == "Chapter 1"
            assert chunk.metadata["page_number"] == 1
            assert len(chunk.content) <= settings.chunk_size

    finally:
        # Restore settings
        settings.chunk_size = original_chunk_size
        settings.chunk_overlap = original_overlap

def test_chunking_service_structural_preservation(chunking_service):
    """Verify that chunks already within size limits are preserved exactly."""
    doc = Document(
        id=uuid4(),
        name="Short Doc",
        filename="short.txt",
        format=DocumentFormat.TXT,
        document_chunks=[
            DocumentChunk(content="Short block 1", level1="L1", level2="L2", metadata={"page_number": 1}),
            DocumentChunk(content="Short block 2", level1="L1", level2="L2", metadata={"page_number": 2}),
        ]
    )

    refined_doc = chunking_service.chunk(doc)

    assert len(refined_doc.document_chunks) == 2
    assert refined_doc.document_chunks[0].content == "Short block 1"
    assert refined_doc.document_chunks[1].content == "Short block 2"
    assert refined_doc.document_chunks[1].metadata["page_number"] == 2

def test_chunking_service_slides_override(chunking_service):
    """Verify that PPTX format uses the slides-specific chunk size."""
    original_chunk_size = settings.chunk_size
    original_slides_size = settings.slides_chunk_size

    # Set slides size to be very small, and general size to be large
    settings.chunk_size = 1000
    settings.slides_chunk_size = 50
    settings.slides_chunk_overlap = 10

    try:
        content = "This is a slide content that is longer than 50 characters to trigger splitting."
        doc = Document(
            id=uuid4(),
            name="Slides",
            filename="pres.pptx",
            format=DocumentFormat.PPTX,
            document_chunks=[
                DocumentChunk(content=content, level1="Slide 1", metadata={"page_number": 1})
            ]
        )

        refined_doc = chunking_service.chunk(doc)

        # Should be split because it uses slides_chunk_size (50), not chunk_size (1000)
        assert len(refined_doc.document_chunks) > 1
        assert len(refined_doc.document_chunks[0].content) <= settings.slides_chunk_size

    finally:
        settings.chunk_size = original_chunk_size
        settings.slides_chunk_size = original_slides_size
