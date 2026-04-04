"""Elasticsearch repository implementation - skeleton."""

from typing import Any, Optional
from datetime import datetime, timezone

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk

from ..elastic.client import ElasticsearchClient
from ..elastic.index_manager import STAFF_INDEX, EVENTS_INDEX, CONTEXT_MATERIALS_INDEX


class ElasticsearchRepository:
    """Repository for all Elasticsearch index operations."""

    def __init__(self, client: Optional[AsyncElasticsearch] = None):
        self.client = client or ElasticsearchClient.get()

    # ------------------------------------------------------------------ #
    # Generic low-level helpers                                            #
    # ------------------------------------------------------------------ #

    async def index_document(
        self,
        index: str,
        document: dict[str, Any],
        doc_id: Optional[str] = None,
    ) -> str:
        """Index a single document; returns the assigned document ID."""
        resp = await self.client.index(index=index, id=doc_id, document=document)
        return resp["_id"]

    async def get_document(self, index: str, doc_id: str) -> Optional[dict[str, Any]]:
        """Fetch a document by ID; returns None if not found."""
        try:
            resp = await self.client.get(index=index, id=doc_id)
            return {"id": resp["_id"], **resp["_source"]}
        except NotFoundError:
            return None

    async def delete_document(self, index: str, doc_id: str) -> bool:
        """Delete a document by ID; returns True if deleted."""
        try:
            await self.client.delete(index=index, id=doc_id)
            return True
        except NotFoundError:
            return False

    async def update_document(
        self, index: str, doc_id: str, partial_doc: dict[str, Any]
    ) -> bool:
        """Partially update a document."""
        try:
            await self.client.update(index=index, id=doc_id, doc=partial_doc)
            return True
        except NotFoundError:
            return False

    async def search(
        self,
        index: str,
        query: dict[str, Any],
        size: int = 10,
        from_: int = 0,
    ) -> list[dict[str, Any]]:
        """Execute a raw ES query and return hits as dicts."""
        resp = await self.client.search(index=index, query=query, size=size, from_=from_)
        return [
            {"id": h["_id"], "score": h["_score"], **h["_source"]}
            for h in resp["hits"]["hits"]
        ]

    async def bulk_index(self, index: str, documents: list[dict[str, Any]]) -> int:
        """Bulk-index documents. Each dict may include '_id' for explicit IDs.
        Returns the number of successfully indexed docs."""
        actions = [
            {
                "_index": index,
                "_id": doc.pop("_id", None),
                "_source": doc,
            }
            for doc in documents
        ]
        success, _ = await async_bulk(self.client, actions, raise_on_error=False)
        return success

    async def delete_by_query(self, index: str, query: dict[str, Any]) -> int:
        """Delete documents matching a query; returns deleted count."""
        resp = await self.client.delete_by_query(index=index, query=query)
        return resp.get("deleted", 0)

    # ------------------------------------------------------------------ #
    # Staff index                                                           #
    # ------------------------------------------------------------------ #

    async def index_staff(
        self, staff_data: dict[str, Any], doc_id: Optional[str] = None
    ) -> str:
        """Index a staff member. Vector fields must be pre-populated by caller.

        Vector stubs:
            staff_data["competences_vector"]  — embed staff_data["competences"]
            staff_data["description_vector"]  — embed staff_data["description"]
        """
        return await self.index_document(STAFF_INDEX, staff_data, doc_id)

    async def get_staff(self, doc_id: str) -> Optional[dict[str, Any]]:
        return await self.get_document(STAFF_INDEX, doc_id)

    async def update_staff(self, doc_id: str, partial: dict[str, Any]) -> bool:
        return await self.update_document(STAFF_INDEX, doc_id, partial)

    async def delete_staff(self, doc_id: str) -> bool:
        return await self.delete_document(STAFF_INDEX, doc_id)

    async def search_staff(
        self,
        query: str,
        department: Optional[str] = None,
        limit: int = 10,
        query_vector: Optional[list[float]] = None,
    ) -> list[dict[str, Any]]:
        """Hybrid staff search.

        Text search is always performed (BM25 over name, surname, position,
        department, competences, description).  If *query_vector* is provided
        the results are re-ranked using kNN on description_vector.

        Args:
            query_vector: embedding of *query* — obtain from the embedding
                          service (LLM stub) before calling this method.
        """
        must: list[dict] = [
            {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "name^2", "surname^2", "fathers_name",
                        "position^1.5", "department",
                        "competences^1.5", "description",
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            }
        ]
        filter_: list[dict] = []
        if department:
            filter_.append({"term": {"department": department}})

        es_query: dict[str, Any] = {"bool": {"must": must, "filter": filter_}}

        if query_vector:
            # TODO: replace with knn-aware hybrid query when LLM embedding
            #       service is integrated (see agents/tools/embeddings.py).
            pass

        return await self.search(STAFF_INDEX, es_query, size=limit)

    async def find_staff_by_entities(
        self,
        entities: list[dict],
        limit: int = 5,
    ) -> dict[str, list[dict[str, Any]]]:
        """Find staff records matching the given PII entities.

        Args:
            entities: List of span dicts with keys: entity_type, original
            limit: Max staff hits per entity

        Returns:
            Mapping: {original_entity_value: [staff_hits]}
            Empty list means no staff match.
        """
        # Only consider entity types that likely correspond to staff records
        STAFF_ENTITY_TYPES = {"PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER"}
        result: dict[str, list[dict[str, Any]]] = {}

        # Deduplicate by original value to avoid redundant lookups
        seen = set()
        for span in entities:
            if span["entity_type"] not in STAFF_ENTITY_TYPES:
                continue
            value = span["original"].strip()
            if not value or value in seen:
                continue
            seen.add(value)

            hits = await self.search_staff(query=value, limit=limit)
            result[value] = hits

        return result

    # ------------------------------------------------------------------ #
    # Events index                                                          #
    # ------------------------------------------------------------------ #

    async def index_event(
        self, event_data: dict[str, Any], doc_id: Optional[str] = None
    ) -> str:
        """Index an event. Vector fields must be pre-populated by caller.

        Vector stubs:
            event_data["description_vector"]               — embed description
            event_data["participant_requirements_vector"]  — embed requirements
        """
        return await self.index_document(EVENTS_INDEX, event_data, doc_id)

    async def get_event(self, doc_id: str) -> Optional[dict[str, Any]]:
        return await self.get_document(EVENTS_INDEX, doc_id)

    async def update_event(self, doc_id: str, partial: dict[str, Any]) -> bool:
        return await self.update_document(EVENTS_INDEX, doc_id, partial)

    async def delete_event(self, doc_id: str) -> bool:
        return await self.delete_document(EVENTS_INDEX, doc_id)

    async def search_events(
        self,
        query: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 10,
        query_vector: Optional[list[float]] = None,
    ) -> list[dict[str, Any]]:
        """Hybrid events search with optional date range filter.

        Args:
            query_vector: embedding of *query* (LLM stub).
        """
        must: list[dict] = [
            {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "name^2", "description^1.5",
                        "participant_requirements",
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            }
        ]
        filter_: list[dict] = []
        if date_from or date_to:
            date_range: dict = {}
            if date_from:
                date_range["gte"] = date_from.isoformat()
            if date_to:
                date_range["lte"] = date_to.isoformat()
            filter_.append({"range": {"date_from": date_range}})

        es_query: dict[str, Any] = {"bool": {"must": must, "filter": filter_}}

        if query_vector:
            # TODO: hybrid kNN re-ranking (LLM embedding stub).
            pass

        return await self.search(EVENTS_INDEX, es_query, size=limit)

    # ------------------------------------------------------------------ #
    # Context Materials index                                               #
    # ------------------------------------------------------------------ #

    async def index_context_chunk(
        self,
        document_id: int,
        chunk_index: int,
        chunk_text: str,
        chunk_vector: Optional[list[float]] = None,
    ) -> str:
        """Index a single document chunk.

        Args:
            chunk_vector: dense embedding of *chunk_text* (LLM stub).
                          Pass None to skip semantic indexing.
        """
        doc: dict[str, Any] = {
            "document_id": document_id,
            "chunk_index": chunk_index,
            "chunk_text": chunk_text,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if chunk_vector is not None:
            doc["chunk_vector"] = chunk_vector
        return await self.index_document(CONTEXT_MATERIALS_INDEX, doc)

    async def bulk_index_chunks(
        self,
        document_id: int,
        chunks: list[str],
        vectors: Optional[list[list[float]]] = None,
    ) -> int:
        """Bulk-index all chunks for a document.

        Args:
            vectors: pre-computed embeddings aligned with *chunks* (LLM stub).
        """
        now = datetime.now(timezone.utc).isoformat()
        docs = []
        for i, text in enumerate(chunks):
            doc: dict[str, Any] = {
                "document_id": document_id,
                "chunk_index": i,
                "chunk_text": text,
                "created_at": now,
            }
            if vectors and i < len(vectors):
                doc["chunk_vector"] = vectors[i]
            docs.append(doc)
        return await self.bulk_index(CONTEXT_MATERIALS_INDEX, docs)

    async def delete_document_chunks(self, document_id: int) -> int:
        """Remove all chunks belonging to a document from the index."""
        return await self.delete_by_query(
            CONTEXT_MATERIALS_INDEX,
            {"term": {"document_id": document_id}},
        )

    async def search_context(
        self,
        query: str,
        document_ids: Optional[list[int]] = None,
        limit: int = 10,
        query_vector: Optional[list[float]] = None,
    ) -> list[dict[str, Any]]:
        """RAG retrieval over context material chunks.

        Args:
            document_ids: restrict search to chunks from these PG file IDs.
            query_vector:  dense embedding of *query* for semantic search (LLM stub).
        """
        must: list[dict] = [
            {
                "match": {
                    "chunk_text": {
                        "query": query,
                        "fuzziness": "AUTO",
                    }
                }
            }
        ]
        filter_: list[dict] = []
        if document_ids:
            filter_.append({"terms": {"document_id": document_ids}})

        es_query: dict[str, Any] = {"bool": {"must": must, "filter": filter_}}

        if query_vector:
            # TODO: kNN semantic + BM25 hybrid (LLM embedding stub).
            pass

        return await self.search(CONTEXT_MATERIALS_INDEX, es_query, size=limit)
