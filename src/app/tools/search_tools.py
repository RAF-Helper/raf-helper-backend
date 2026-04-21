"""Search tools for agents using Elasticsearch with embeddings."""

import logging
from typing import Optional
from datetime import datetime

from ..repositories.elasticsearch_repository import ElasticsearchRepository
from ..services.embedding_service import EmbeddingService
from ..services.tavily_service import get_tavily_service

logger = logging.getLogger(__name__)

# Singleton instances
_es_repo: ElasticsearchRepository | None = None
_embedder: EmbeddingService | None = None


def _get_repo() -> ElasticsearchRepository:
    global _es_repo
    if _es_repo is None:
        _es_repo = ElasticsearchRepository()
    return _es_repo


def _get_embedder() -> EmbeddingService:
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingService()
    return _embedder


# ============ Tool Functions ============

async def get_staff_documents(
    query: str,
    position: Optional[str] = None,
    room: Optional[int] = None,
    department: Optional[str] = None,
    name: Optional[str] = None,
    k: int = 3,
) -> str:
    """
    Search for university staff members by name, position, department, or competences.

    Returns formatted list of staff members with their details.
    """
    repo = _get_repo()
    embedder = _get_embedder()

    # Generate embedding for semantic search
    vector = await embedder.embed_text(query)

    # Perform search with filters
    results = await repo.search_staff(
        query=query,
        position=position,
        room=room,
        department=department,
        limit=k,
        query_vector=vector,
    )

    if not results:
        return "No staff members found matching the criteria."

    lines = []
    for s in results:
        full_name = " ".join([s["surname"], s["name"], s.get("fathers_name") or ""]).strip()
        lines.append(
            f"- {full_name}, {s['position']} ({s['department']}), каб. {s['room']}"
        )
    return "\n".join(lines)


async def get_events_documents(
    query: str,
    bonus_amount: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    k: int = 3,
) -> str:
    """
    Search for university events by name, description, or requirements.

    Optional filters: bonus_amount (minimum), date range.
    Returns formatted list of events.
    """
    repo = _get_repo()
    embedder = _get_embedder()

    vector = await embedder.embed_text(query)

    results = await repo.search_events(
        query=query,
        bonus_amount=bonus_amount,
        date_from=date_from,
        date_to=date_to,
        limit=k,
        query_vector=vector,
    )

    if not results:
        return "No events found matching the criteria."

    lines = []
    for e in results:
        # Format date range
        date_str = f"{e.get('date_from', 'N/A')} to {e.get('date_to', 'N/A')}"
        lines.append(
            f"- {e['name']} ({date_str})\n  {e.get('description', 'No description')}\n  Bonus: {e.get('bonus_amount', 'N/A')}, Participants: {e.get('participant_amount', 'N/A')}"
        )
    return "\n".join(lines)


async def get_materials_fragments(
    query: str,
    document_ids: Optional[list[int]] = None,
    return_chunks: bool = False,
    k: int = 5,
    use_web_search: bool = False,
) -> str:
    """
    Search for document fragments (context materials) by query.

    The agent only needs to specify query, return_chunks, and k.
    Document IDs and web search are automatically handled by the system based on chat context.

    Args:
        query: Search query for content within document fragments
        return_chunks: If True, return chunk texts; if False, aggregate by document
        k: Number of results to return
        use_web_search: If True, also perform web search via Tavily (internal, not passed by agent)

    Returns:
        Formatted string with matching fragments or document summaries.
    """
    repo = _get_repo()
    embedder = _get_embedder()

    vector = await embedder.embed_text(query)

    # Search in Elasticsearch
    results = await repo.search_context(
        query=query,
        document_ids=document_ids,
        limit=k,
        query_vector=vector,
    )

    # Build response from ES results
    if results:
        if return_chunks:
            # Return individual chunks
            lines = []
            for r in results:
                lines.append(
                    f"[Doc {r['document_id']}, Chunk {r['chunk_index']}]\n{r['chunk_text']}"
                )
            es_content = "\n\n".join(lines)
        else:
            # Aggregate by document
            docs: dict[int, list[str]] = {}
            for r in results:
                doc_id = r["document_id"]
                if doc_id not in docs:
                    docs[doc_id] = []
                docs[doc_id].append(r["chunk_text"])

            lines = []
            for doc_id, chunks in docs.items():
                preview = "\n".join(chunks[:2])  # First 2 chunks as preview
                lines.append(f"Document {doc_id}:\n{preview}")
            es_content = "\n\n".join(lines)
    else:
        es_content = ""

    # If web search is enabled, also search the web
    if use_web_search:
        tavily = get_tavily_service()
        web_results = await tavily.search(query, include_raw_content=True)

        if web_results:
            web_lines = ["[Web Search Results]"]
            for i, r in enumerate(web_results, 1):
                web_lines.append(
                    f"{i}. {r['title']}\n   {r['url']}\n   {r['content']}"
                )
            web_content = "\n".join(web_lines)
        else:
            web_content = ""

        # Combine ES and web results
        if es_content and web_content:
            return f"{es_content}\n\n---\n\n{web_content}"
        elif web_content:
            return web_content
        elif es_content:
            return es_content
        else:
            return "No relevant document fragments found."

    # No web search, return only ES results
    if es_content:
        return es_content
    return "No relevant document fragments found."


# ============ OpenAI Tool Definitions ============

get_staff_documents_def = {
    "name": "get_staff_documents",
    "description": "Search for university staff members by name, position, department, or competences. Returns detailed staff information including name, position, department, and room number.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g., 'math teachers', 'Ivanov', 'computer science department')"
            },
            "position": {
                "type": "string",
                "description": "Optional exact position filter (e.g., 'Professor', 'Senior Lecturer')"
            },
            "room": {
                "type": "integer",
                "description": "Optional room number filter"
            },
            "department": {
                "type": "string",
                "description": "Optional department filter (e.g., 'Кафедра информатики')"
            },
            "name": {
                "type": "string",
                "description": "Optional staff member name to search (first/last name)"
            },
            "k": {
                "type": "integer",
                "description": "Maximum number of results to return (default 3)"
            }
        },
        "required": ["query"]
    }
}

get_events_documents_def = {
    "name": "get_events_documents",
    "description": "Search for university events by name, description, or participant requirements. Supports filtering by bonus amount and date range.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g., 'hackathon', 'programming contest')"
            },
            "bonus_amount": {
                "type": "integer",
                "description": "Optional minimum bonus amount filter (inclusive)"
            },
            "date_from": {
                "type": "string",
                "format": "date-time",
                "description": "Optional start date filter (ISO 8601, e.g., '2025-01-01T00:00:00')"
            },
            "date_to": {
                "type": "string",
                "format": "date-time",
                "description": "Optional end date filter (ISO 8601)"
            },
            "k": {
                "type": "integer",
                "description": "Maximum number of results to return (default 3)"
            }
        },
        "required": ["query"]
    }
}

get_materials_fragments_def = {
    "name": "get_materials_fragments",
    "description": "Search for document fragments (context materials, learning resources) by query. The system automatically determines which documents to search based on the chat context.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for content within document fragments"
            },
            "return_chunks": {
                "type": "boolean",
                "description": "If true, return individual chunks; if false, aggregate by document (default false)"
            },
            "k": {
                "type": "integer",
                "description": "Maximum number of results to return (default 5)"
            }
        },
        "required": ["query"]
    }
}


# Export all tools and their definitions
ALL_TOOLS = [
    get_staff_documents_def,
    get_events_documents_def,
    get_materials_fragments_def,
]

TOOL_FUNCTIONS = {
    "get_staff_documents": get_staff_documents,
    "get_events_documents": get_events_documents,
    "get_materials_fragments": get_materials_fragments,
}
