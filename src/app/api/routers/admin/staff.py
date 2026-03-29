"""Admin endpoints for managing the Staff Elasticsearch index."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from elasticsearch import AsyncElasticsearch

from ....elastic.client import get_elasticsearch_client
from ....repositories.elasticsearch_repository import ElasticsearchRepository
from ....schemas.staff import StaffCreate, StaffRead, StaffUpdate, StaffSearchResult

router = APIRouter(prefix="/admin/staff", tags=["admin", "staff"])

# NOTE: In production, protect these endpoints with an admin role check.
#       For now they are open (Firebase token not required) so the admin UI
#       can seed data easily.  Add `Depends(verify_firebase_token)` + role
#       check when the admin role system is implemented.


def _get_repo(es: AsyncElasticsearch = Depends(get_elasticsearch_client)) -> ElasticsearchRepository:
    return ElasticsearchRepository(es)


@router.post("/", response_model=StaffRead, status_code=status.HTTP_201_CREATED)
async def create_staff(
    body: StaffCreate,
    repo: ElasticsearchRepository = Depends(_get_repo),
) -> StaffRead:
    """Add a new staff member to the index.

    Vector fields (competences_vector, description_vector) are intentionally
    omitted here — populate them via the embedding pipeline once the LLM
    integration is complete.
    """
    doc = body.model_dump()
    # TODO: generate vectors before indexing:
    #   doc["competences_vector"] = await embed(body.competences)
    #   doc["description_vector"] = await embed(body.description)
    doc_id = await repo.index_staff(doc)
    return StaffRead(id=doc_id, **body.model_dump())


@router.get("/search", response_model=list[StaffSearchResult])
async def search_staff(
    q: str = Query(..., min_length=1),
    department: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    repo: ElasticsearchRepository = Depends(_get_repo),
) -> list[StaffSearchResult]:
    """Full-text (BM25) staff search. Semantic re-ranking available once
    embedding service is wired in."""
    hits = await repo.search_staff(q, department=department, limit=limit)
    return [StaffSearchResult(**h) for h in hits]


@router.get("/{doc_id}", response_model=StaffRead)
async def get_staff(
    doc_id: str,
    repo: ElasticsearchRepository = Depends(_get_repo),
) -> StaffRead:
    doc = await repo.get_staff(doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found.")
    return StaffRead(**doc)


@router.patch("/{doc_id}", response_model=StaffRead)
async def update_staff(
    doc_id: str,
    body: StaffUpdate,
    repo: ElasticsearchRepository = Depends(_get_repo),
) -> StaffRead:
    partial = body.model_dump(exclude_none=True)
    if not partial:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update.")

    # TODO: re-embed changed text fields before updating.
    updated = await repo.update_staff(doc_id, partial)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found.")

    doc = await repo.get_staff(doc_id)
    return StaffRead(**doc)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_staff(
    doc_id: str,
    repo: ElasticsearchRepository = Depends(_get_repo),
) -> None:
    deleted = await repo.delete_staff(doc_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found.")
