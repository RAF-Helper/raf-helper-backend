"""Admin endpoints for managing the Events Elasticsearch index."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from elasticsearch import AsyncElasticsearch

from app.api.auth.firebase import verify_firebase_token

from app.elastic.client import get_elasticsearch_client
from app.repositories.elasticsearch_repository import ElasticsearchRepository
from app.schemas.events import EventCreate, EventRead, EventUpdate, EventSearchResult
from app.api.dependencies import get_embedding_service
from app.services.embedding_service import EmbeddingService

router = APIRouter(prefix="/admin/events", tags=["admin", "events"])


def _get_repo(es: AsyncElasticsearch = Depends(get_elasticsearch_client)) -> ElasticsearchRepository:
    return ElasticsearchRepository(es)


@router.post("/", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    body: EventCreate,
    firebase_uid: str = Depends(verify_firebase_token),
    repo: ElasticsearchRepository = Depends(_get_repo),
    embedder: EmbeddingService = Depends(get_embedding_service),
) -> EventRead:
    """Add a new event to the index.

    Generates embeddings for description and participant_requirements fields
    using the sentence-transformers service. If these fields are empty, vector
    fields are omitted (they can be added later via re-embedding).
    """
    doc = body.model_dump()
    # Serialize datetime objects for ES
    doc["date_from"] = body.date_from.isoformat()
    doc["date_to"] = body.date_to.isoformat()

    # Generate embeddings if text is non-empty
    if body.description:
        doc["description_vector"] = await embedder.embed_text(body.description)
    if body.participant_requirements:
        doc["participant_requirements_vector"] = await embedder.embed_text(body.participant_requirements)

    doc_id = await repo.index_event(doc)
    return EventRead(id=doc_id, **body.model_dump())


@router.get("/search", response_model=list[EventSearchResult])
async def search_events(
    q: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    bonus_amount: Optional[int] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    firebase_uid: str = Depends(verify_firebase_token),
    repo: ElasticsearchRepository = Depends(_get_repo),
) -> list[EventSearchResult]:
    """Full-text (BM25 + optional kNN) events search with optional date/bonus filters.

    If q is provided, performs hybrid search. If q is None/empty, returns all
    events matching the filters with pagination.
    """
    hits = await repo.search_events(q or "", date_from=date_from, date_to=date_to, bonus_amount=bonus_amount, limit=limit)
    return [EventSearchResult(**h) for h in hits]


@router.get("/{doc_id}", response_model=EventRead)
async def get_event(
    doc_id: str,
    firebase_uid: str = Depends(verify_firebase_token),
    repo: ElasticsearchRepository = Depends(_get_repo),
) -> EventRead:
    doc = await repo.get_event(doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    return EventRead(**doc)


@router.patch("/{doc_id}", response_model=EventRead)
async def update_event(
    doc_id: str,
    body: EventUpdate,
    firebase_uid: str = Depends(verify_firebase_token),
    repo: ElasticsearchRepository = Depends(_get_repo),
    embedder: EmbeddingService = Depends(get_embedding_service),
) -> EventRead:
    partial = body.model_dump(exclude_none=True)
    if not partial:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update.")

    # Serialize datetimes
    for key in ("date_from", "date_to"):
        if key in partial and isinstance(partial[key], datetime):
            partial[key] = partial[key].isoformat()

    # If text fields are being updated, regenerate their embeddings
    if "description" in partial and body.description:
        partial["description_vector"] = await embedder.embed_text(body.description)
    if "participant_requirements" in partial and body.participant_requirements:
        partial["participant_requirements_vector"] = await embedder.embed_text(body.participant_requirements)

    updated = await repo.update_event(doc_id, partial)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")

    doc = await repo.get_event(doc_id)
    return EventRead(**doc)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    doc_id: str,
    firebase_uid: str = Depends(verify_firebase_token),
    repo: ElasticsearchRepository = Depends(_get_repo),
) -> None:
    deleted = await repo.delete_event(doc_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
