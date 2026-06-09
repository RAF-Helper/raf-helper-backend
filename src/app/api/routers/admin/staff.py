"""Admin endpoints for managing the Staff Elasticsearch index."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from elasticsearch import AsyncElasticsearch

from app.elastic.client import get_elasticsearch_client
from app.repositories.elasticsearch_repository import ElasticsearchRepository
from app.schemas.staff import StaffCreate, StaffRead, StaffUpdate, StaffSearchResult
from app.api.auth.firebase import verify_firebase_token
from app.api.dependencies import get_embedding_service
from app.services.embedding_service import EmbeddingService

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
    embedder: EmbeddingService = Depends(get_embedding_service),
) -> StaffRead:
    """Add a new staff member to the index.

    Generates embeddings for competences and description fields using the
    sentence-transformers service. If these fields are empty, vector fields
    are omitted (they can be added later via re-embedding).
    """
    doc = body.model_dump()

    # Generate embeddings if text is non-empty
    if body.competences:
        doc["competences_vector"] = await embedder.embed_text(body.competences)
    if body.description:
        doc["description_vector"] = await embedder.embed_text(body.description)

    doc_id = await repo.index_staff(doc)
    return StaffRead(id=doc_id, **body.model_dump())


@router.get("/search", response_model=list[StaffSearchResult])
async def search_staff(
    q: Optional[str] = Query(None),
    department: Optional[str] = Query(default=None),
    position: Optional[str] = Query(default=None),
    room: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    repo: ElasticsearchRepository = Depends(_get_repo),
) -> list[StaffSearchResult]:
    """Full-text (BM25 + optional kNN) staff search.

    If q is provided, performs hybrid search. If q is None/empty, returns all
    staff matching the filters (department, position, room) with pagination.
    """
    hits = await repo.search_staff(q or "", department=department, position=position, room=room, limit=limit)
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
    embedder: EmbeddingService = Depends(get_embedding_service),
) -> StaffRead:
    partial = body.model_dump(exclude_none=True)
    if not partial:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update.")

    # If text fields are being updated, regenerate their embeddings
    if "competences" in partial and body.competences:
        partial["competences_vector"] = await embedder.embed_text(body.competences)
    if "description" in partial and body.description:
        partial["description_vector"] = await embedder.embed_text(body.description)

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
