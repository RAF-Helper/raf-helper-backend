"""Elasticsearch repository implementation - skeleton."""

from typing import Any, Optional
from datetime import datetime, timezone

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk

from app.elastic.client import ElasticsearchClient
from app.elastic.index_manager import STAFF_INDEX, EVENTS_INDEX, CONTEXT_MATERIALS_INDEX


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
        position: Optional[str] = None,
        room: Optional[str] = None,
        limit: int = 10,
        query_vector: Optional[list[float]] = None,
    ) -> list[dict[str, Any]]:
        """Hybrid staff search.

        Text search is always performed (BM25 over name, surname, position,
        department, competences, description).  If *query_vector* is provided,
        results are re-ranked using kNN on description_vector.

        Args:
            query_vector: embedding of *query* — obtain from the embedding
                          service before calling this method.
            position: Optional filter by exact position match
            room: Optional filter by room number
        """
        should: list[dict] = []
        if query:
            should.append({
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
            })
        filter_: list[dict] = []
        if department:
            filter_.append({"term": {"department": department}})
        if position:
            filter_.append({"term": {"position": position}})
        if room is not None:
            filter_.append({"term": {"room": room}})

        # Build hybrid query: bool with optional knn in should clause
        es_query: dict[str, Any] = {"bool": {"should": should, "filter": filter_}}

        if query_vector:
            # Add kNN as a boosting clause
            if "should" not in es_query["bool"]:
                es_query["bool"]["should"] = []
            es_query["bool"]["should"].append({
                "knn": {
                    "field": "description_vector",
                    "query_vector": query_vector,
                    "k": min(50, limit * 2),  # kNN candidates
                    "num_candidates": min(100, limit * 4),
                }
            })

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
        query: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        bonus_amount: Optional[int] = None,
        limit: int = 10,
        query_vector: Optional[list[float]] = None,
    ) -> list[dict[str, Any]]:
        """Hybrid events search with optional date range and bonus filters.

        Args:
            query_vector: embedding of *query* for semantic re-ranking.
            bonus_amount: Minimum bonus amount filter (inclusive).
        """
        should: list[dict] = []
        if query:
            should.append({
                "multi_match": {
                    "query": query,
                    "fields": [
                        "name^2", "description^1.5",
                        "participant_requirements",
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            })
        filter_: list[dict] = []
        if date_from or date_to:
            date_range: dict = {}
            if date_from:
                date_range["gte"] = date_from.isoformat()
            if date_to:
                date_range["lte"] = date_to.isoformat()
            filter_.append({"range": {"date_from": date_range}})
        if bonus_amount is not None:
            filter_.append({"range": {"bonus_amount": {"gte": bonus_amount}}})

        # Build hybrid query: bool with optional knn
        es_query: dict[str, Any] = {"bool": {"should": should, "filter": filter_}}

        if query_vector:
            # Add kNN as a boosting clause
            if "should" not in es_query["bool"]:
                es_query["bool"]["should"] = []
            es_query["bool"]["should"].append({
                "knn": {
                    "field": "description_vector",
                    "query_vector": query_vector,
                    "k": min(50, limit * 2),
                    "num_candidates": min(100, limit * 4),
                }
            })

        return await self.search(EVENTS_INDEX, es_query, size=limit)

    # ------------------------------------------------------------------ #
    # Context Materials index                                               #
    # ------------------------------------------------------------------ #

    async def index_context_chunk(
        self,
        document_id: str,
        chunk_index: int,
        chunk_text: str,
        chunk_vector: Optional[list[float]] = None,
        chunk_reference_level_1: Optional[str] = None,
        chunk_reference_level_1_vector: Optional[list[float]] = None,
        chunk_reference_level_2: Optional[str] = None,
        chunk_reference_level_2_vector: Optional[list[float]] = None,
        chunk_reference_level_3: Optional[str] = None,
        chunk_reference_level_3_vector: Optional[list[float]] = None,
        chunk_reference_metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Index a single document chunk.

        Args:
            document_id: UUID of the document (as string)
            chunk_index: position of chunk in document
            chunk_text: text content of the chunk
            chunk_vector: dense embedding of chunk_text
            chunk_reference_level_1: reference level 1 (e.g., chapter/slide number)
            chunk_reference_level_1_vector: embedding of level 1 reference
            chunk_reference_level_2: reference level 2 (e.g., section title)
            chunk_reference_level_2_vector: embedding of level 2 reference
            chunk_reference_level_3: reference level 3 (e.g., subsection title)
            chunk_reference_level_3_vector: embedding of level 3 reference
            chunk_reference_metadata: additional metadata about the chunk
        """
        doc: dict[str, Any] = {
            "document_id": document_id,
            "chunk_index": chunk_index,
            "chunk_text": chunk_text,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if chunk_vector is not None:
            doc["chunk_vector"] = chunk_vector
        if chunk_reference_level_1 is not None:
            doc["chunk_reference_level_1"] = chunk_reference_level_1
        if chunk_reference_level_1_vector is not None:
            doc["chunk_reference_level_1_vector"] = chunk_reference_level_1_vector
        if chunk_reference_level_2 is not None:
            doc["chunk_reference_level_2"] = chunk_reference_level_2
        if chunk_reference_level_2_vector is not None:
            doc["chunk_reference_level_2_vector"] = chunk_reference_level_2_vector
        if chunk_reference_level_3 is not None:
            doc["chunk_reference_level_3"] = chunk_reference_level_3
        if chunk_reference_level_3_vector is not None:
            doc["chunk_reference_level_3_vector"] = chunk_reference_level_3_vector
        if chunk_reference_metadata is not None:
            doc["chunk_reference_metadata"] = chunk_reference_metadata
        return await self.index_document(CONTEXT_MATERIALS_INDEX, doc)

    async def bulk_index_chunks(
        self,
        document_id: str,
        chunks: list[str],
        vectors: Optional[list[list[float]]] = None,
        reference_levels: Optional[list[dict[str, Any]]] = None,
    ) -> int:
        """Bulk-index all chunks for a document.

        Args:
            document_id: UUID of the document (as string)
            chunks: list of text chunks
            vectors: pre-computed embeddings for chunk_text
            reference_levels: list of dicts with optional keys:
                - level_1, level_1_vector
                - level_2, level_2_vector
                - level_3, level_3_vector
                - metadata
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
            if reference_levels and i < len(reference_levels):
                ref = reference_levels[i]
                if ref.get("level_1"):
                    doc["chunk_reference_level_1"] = ref["level_1"]
                if ref.get("level_1_vector"):
                    doc["chunk_reference_level_1_vector"] = ref["level_1_vector"]
                if ref.get("level_2"):
                    doc["chunk_reference_level_2"] = ref["level_2"]
                if ref.get("level_2_vector"):
                    doc["chunk_reference_level_2_vector"] = ref["level_2_vector"]
                if ref.get("level_3"):
                    doc["chunk_reference_level_3"] = ref["level_3"]
                if ref.get("level_3_vector"):
                    doc["chunk_reference_level_3_vector"] = ref["level_3_vector"]
                if ref.get("metadata"):
                    doc["chunk_reference_metadata"] = ref["metadata"]
            docs.append(doc)
        return await self.bulk_index(CONTEXT_MATERIALS_INDEX, docs)

    async def delete_document_chunks(self, document_id: str) -> int:
        """Remove all chunks belonging to a document from the index."""
        return await self.delete_by_query(
            CONTEXT_MATERIALS_INDEX,
            {"term": {"document_id": document_id}},
        )

    async def search_context(
        self,
        query: str,
        document_ids: Optional[list[str]] = None,
        limit: int = 10,
        query_vector: Optional[list[float]] = None,
    ) -> list[dict[str, Any]]:
        """RAG retrieval over context material chunks.

        Args:
            document_ids: restrict search to chunks from these document UUIDs (as strings).
            query_vector: dense embedding of *query* for semantic search.
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
            es_query["bool"]["should"] = [
                {
                    "knn": {
                        "field": "chunk_vector",
                        "query_vector": query_vector,
                        "k": min(50, limit * 2),
                        "num_candidates": min(100, limit * 4),
                    }
                }
            ]

        return await self.search(CONTEXT_MATERIALS_INDEX, es_query, size=limit)
