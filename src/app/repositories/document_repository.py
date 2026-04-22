"""Document repository for parsing pipeline."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Optional
from uuid import UUID

from ..elastic.index_manager import CONTEXT_MATERIALS_INDEX
from ..repositories.elasticsearch_repository import ElasticsearchRepository
from ..repositories.postgres_repository import FileMetadataRepository
from ..schemas.document import Document, DocumentChunk
from ..services.embedding_service import get_embedding_service


class DocumentRepository:
    """Repository for document ingestion and search with full pipeline."""

    def __init__(self, session):
        self._es_repo = ElasticsearchRepository()
        self._fm_repo = FileMetadataRepository(session)
        self._embedder = get_embedding_service()

    async def ingest_document(self, document: Document) -> int:
        """Ingest a document by indexing all its chunks with embeddings.

        Args:
            document: Parsed Document with chunks

        Returns:
            Number of chunks indexed
        """
        if not document.document_chunks:
            return 0

        # Prepare data for bulk indexing
        chunks_data = []
        chunk_texts = [chunk.content for chunk in document.document_chunks]

        # Generate embeddings for chunk content
        content_vectors = await self._embedder.embed_batch(chunk_texts)

        # Generate embeddings for level1, level2, level3 titles
        level1_texts = [chunk.level1 for chunk in document.document_chunks if chunk.level1]
        level2_texts = [chunk.level2 for chunk in document.document_chunks if chunk.level2]
        level3_texts = [chunk.level3 for chunk in document.document_chunks if chunk.level3]


        level1_vectors = await self._embedder.embed_batch(level1_texts) if level1_texts else []
        level2_vectors = await self._embedder.embed_batch(level2_texts) if level2_texts else []
        level3_vectors = await self._embedder.embed_batch(level3_texts) if level3_texts else []

        # Build index vectors
        level1_vec_map = {chunk.level1: level1_vectors[i] for i, chunk in enumerate(document.document_chunks) if chunk.level1 and i < len(level1_vectors)}
        level2_vec_map = {chunk.level2: level2_vectors[i] for i, chunk in enumerate(document.document_chunks) if chunk.level2 and i < len(level2_vectors)}
        level3_vec_map = {chunk.level3: level3_vectors[i] for i, chunk in enumerate(document.document_chunks) if chunk.level3 and i < len(level3_vectors)}


        # Build documents for indexing
        docs = []
        for i, chunk in enumerate(document.document_chunks):
            doc = {
                "document_id": str(document.id),
                "chunk_index": i,
                "chunk_text": chunk.content,
                "chunk_vector": content_vectors[i] if i < len(content_vectors) else None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # Add level 1
            if chunk.level1:
                doc["chunk_reference_level_1"] = chunk.level1
                vec = level1_vec_map.get(chunk.level1)
                if vec:
                    doc["chunk_reference_level_1_vector"] = vec

            # Add level 2
            if chunk.level2:
                doc["chunk_reference_level_2"] = chunk.level2
                vec = level2_vec_map.get(chunk.level2)
                if vec:
                    doc["chunk_reference_level_2_vector"] = vec

            # Add level 3
            if chunk.level3:
                doc["chunk_reference_level_3"] = chunk.level3
                vec = level3_vec_map.get(chunk.level3)
                if vec:
                    doc["chunk_reference_level_3_vector"] = vec

            # Add metadata
            if chunk.metadata:
                doc["chunk_reference_metadata"] = chunk.metadata

            docs.append(doc)

        return await self._es_repo.bulk_index(CONTEXT_MATERIALS_INDEX, docs)


    async def search(
        self,
        query: str,
        document_ids: list[int],
        return_chunks: bool,
        k: int = 5,
    ) -> list[dict[str, Any]]:
        """Full search pipeline: vector similarity + fuzzy text match.

        Args:
            query: Search query
            document_ids: Filter to these document UUIDs
            k: Number of results
            return_chunks: If True, return chunk texts; if False, aggregate by document

        Returns:
            List of matching chunks or document summaries
        """
        # Generate query embedding
        embed_task = self._embedder.embed_text(query)
        uuid_task = self._fm_repo.get_uuids(document_ids)

        query_vector, document_uuids = await asyncio.gather(embed_task, uuid_task)

        # Build ES query with:
        # - should: knn on chunk_vector (cosine similarity)
        # - must: fuzzy match on chunk_text
        # - filter: document_ids
        # - should: fuzzy match on reference levels and metadata

        must: list[dict] = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["chunk_text^2", "chunk_reference_level_1", "chunk_reference_level_2", "chunk_reference_level_3"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            }
        ]

        filter_: list[dict] = []
        if document_uuids:
            filter_.append({"terms": {"document_id": [str(u) for u in document_uuids]}})

        # Build should clauses for vector similarity
        should: list[dict] = [
            {
                "knn": {
                    "field": "chunk_vector",
                    "query_vector": query_vector,
                    "k": min(50, k * 2),
                    "num_candidates": min(100, k * 4),
                }
            }
        ]

        es_query: dict = {
            "bool": {
                "must": must,
                "filter": filter_,
                "should": should,
                "minimum_should_match": 0,
            }
        }

        results = await self._es_repo.search(
            index=CONTEXT_MATERIALS_INDEX,
            query=es_query,
            size=k,
        )

        for result in results:
            doc = await self._fm_repo.get_by_uuid(result["document_id"])
            result['name'] = doc.name or doc.original_name

        if not results:
            return []

        if return_chunks:
            return results

        # Aggregate by document
        docs: dict[str, list[str]] = {}
        for r in results:
            doc_id = r["document_id"]
            if doc_id not in docs:
                docs[doc_id] = []
            docs[doc_id].append(r["chunk_text"])

        return [{"document_id": doc_id, "chunks": chunks} for doc_id, chunks in docs.items()]

    async def get_document_chunks(self, document_id: str) -> list[dict[str, Any]]:
        """Retrieve all chunks for a document."""
        return await self._es_repo.search(
            index=CONTEXT_MATERIALS_INDEX,
            query={"term": {"document_id": document_id}},
            size=1000,  # large limit to get all chunks
        )

    async def delete_document(self, document_id: str) -> int:
        """Delete all chunks for a document."""
        return await self._es_repo.delete_by_query(
            index=CONTEXT_MATERIALS_INDEX,
            query={"term": {"document_id": document_id}},
        )