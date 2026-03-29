"""Admin endpoints for managing the Events Elasticsearch index."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from elasticsearch import AsyncElasticsearch

from ....elastic.client import get_elasticsearch_client
from ....repositories.elasticsearch_repository import ElasticsearchRepository
from ....schemas.events import EventCreate, EventRead, EventUpdate, EventSearchResult

router = APIRouter(prefix="/admin/events", tags=["admin", "events"])


def _get_repo(es: AsyncElasticsearch = Depends(get_elasticsearch_client)) -> ElasticsearchRepository:
    return ElasticsearchRepository(es)


@router.post("/", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    body: EventCreate,
    repo: ElasticsearchRepository = Depends(_get_repo),
) -> EventRead:
    """Add a new event to the index.

    Vector fields (description_vector, participant_requirements_vector) are
    populated by the embedding pipeline once the LLM integration is complete.
    """
    doc = body.model_dump()
    # Serialize datetime objects for ES
    doc["date_from"] = body.date_from.isoformat()
    doc["date_to"] = body.date_to.isoformat()
    # TODO:
    #   doc["description_vector"] = await embed(body.description)
    #   doc["participant_requirements_vector"] = await embed(body.participant_requirements)
    doc_id = await repo.index_event(doc)
    return EventRead(id=doc_id, **body.model_dump())


@router.get("/search", response_model=list[EventSearchResult])
async def search_events(
    q: str = Query(..., min_length=1),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    repo: ElasticsearchRepository = Depends(_get_repo),
) -> list[EventSearchResult]:
    """Full-text (BM25) events search with optional date filter."""
    hits = await repo.search_events(q, date_from=date_from, date_to=date_to, limit=limit)
    return [EventSearchResult(**h) for h in hits]


@router.get("/{doc_id}", response_model=EventRead)
async def get_event(
    doc_id: str,
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
    repo: ElasticsearchRepository = Depends(_get_repo),
) -> EventRead:
    partial = body.model_dump(exclude_none=True)
    if not partial:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update.")

    # Serialize datetimes
    for key in ("date_from", "date_to"):
        if key in partial and isinstance(partial[key], datetime):
            partial[key] = partial[key].isoformat()

    # TODO: re-embed changed text fields.
    updated = await repo.update_event(doc_id, partial)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")

    doc = await repo.get_event(doc_id)
    return EventRead(**doc)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    doc_id: str,
    repo: ElasticsearchRepository = Depends(_get_repo),
) -> None:
    deleted = await repo.delete_event(doc_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
