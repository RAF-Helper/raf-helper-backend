"""Search tools for agents using Elasticsearch with embeddings."""

import logging
from typing import Optional
from datetime import datetime

from app.repositories.elasticsearch_repository import ElasticsearchRepository
from app.services.embedding_service import EmbeddingService
from app.services.tavily_service import get_tavily_service
from app.services.document_service import DocumentService
from app.db.session import AsyncSessionLocal

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


async def list_context_files(
    chat_id: Optional[int] = None,
) -> str:
    """
    List all files currently present in the chat context.
    Returns a list of files with their IDs and names.
    """
    if chat_id is None:
        return "Error: Chat ID not provided. Cannot list context files."

    try:
        async with AsyncSessionLocal() as session:
            doc_service = DocumentService(session)
            file_ids = await doc_service.get_chat_file_ids(chat_id)

            if not file_ids:
                return "No files found in the current chat context."

            # Fetch metadata for these files
            # Use file_repo directly via doc_service
            files = await doc_service.file_repo.get_by_ids(file_ids)

            lines = ["Files in the current chat context:"]
            for f in files:
                lines.append(f"- ID: {f.id}, Name: {f.original_name}")

            return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing context files for chat {chat_id}: {e}", exc_info=True)
        return "Error retrieving context files."


async def get_file_content(
    file_id: int,
) -> str:
    """
    Retrieve the full text content of a specific file using its file ID.
    """
    try:
        async with AsyncSessionLocal() as session:
            doc_service = DocumentService(session)
            # Resolve file_id to document_id (UUID)
            file_record = await doc_service.file_repo.get(file_id)
            if not file_record:
                return f"Error: File with ID {file_id} not found."

            content = await doc_service.get_full_document_text(file_record.document_id)
            if not content:
                return f"Error: Could not retrieve content for file {file_record.original_name} (ID: {file_id})."

            return f"Content of {file_record.original_name} (ID: {file_id}):\n\n{content}"
    except Exception as e:
        logger.error(f"Error getting content for file {file_id}: {e}", exc_info=True)
        return f"Error retrieving file content: {str(e)}"

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
    document_ids: Optional[list[str]] = None,
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
    # 1. Internal Knowledge Base Search
    internal_content = ""
    if document_ids:
        try:
            async with AsyncSessionLocal() as session:
                doc_service = DocumentService(session)
                results = await doc_service.search_materials(
                    query=query,
                    document_ids=document_ids,
                    k=k,
                    return_chunks=return_chunks,
                )

                if results:
                    lines = ["[Internal Knowledge Base]"]
                    if return_chunks:
                        # Results are chunks: list[dict]
                        for r in results:
                            lines.append(
                                f"[Doc {r['document_id']}, Chunk {r.get('chunk_index', 'N/A')}]\n{r['chunk_text']}"
                            )
                    else:
                        # Results are full documents: list[dict] with 'name', 'content'
                        for r in results:
                            lines.append(
                                f"Document {r['name']}:\n{r['content']}"
                            )
                    internal_content = "\n\n".join(lines)
        except Exception as e:
            logger.error(f"Error during internal material search: {e}", exc_info=True)
            internal_content = "Error retrieving internal materials."

    # 2. Web Search
    web_content = ""
    if use_web_search:
        try:
            tavily = get_tavily_service()
            web_results = await tavily.search(query, include_raw_content=True)

            if web_results:
                web_lines = ["[Web Search Results]"]
                for i, r in enumerate(web_results, 1):
                    web_lines.append(
                        f"{i}. {r['title']}\n   {r['url']}\n   {r['content']}"
                    )
                web_content = "\n".join(web_lines)
        except Exception as e:
            logger.error(f"Error during web search: {e}", exc_info=True)
            web_content = "Error performing web search."

    # 3. Combine and Return
    if internal_content and web_content:
        return f"{internal_content}\n\n---\n\n{web_content}"
    elif internal_content:
        return internal_content
    elif web_content:
        return web_content
    else:
        return "No relevant document fragments found."


# ============ OpenAI Tool Definitions ============

list_context_files_def = {
    "name": "list_context_files",
    "description": "List all files currently present in the chat context. Returns a list of files with their IDs and names.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

get_file_content_def = {
    "name": "get_file_content",
    "description": "Retrieve the full text content of a specific file using its file ID.",
    "parameters": {
        "type": "object",
        "properties": {
            "file_id": {
                "type": "integer",
                "description": "The unique integer ID of the file"
            }
        },
        "required": ["file_id"]
    }
}

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
    list_context_files_def,
    get_file_content_def,
    get_staff_documents_def,
    get_events_documents_def,
    get_materials_fragments_def,
]

TOOL_FUNCTIONS = {
    "list_context_files": list_context_files,
    "get_file_content": get_file_content,
    "get_staff_documents": get_staff_documents,
    "get_events_documents": get_events_documents,
    "get_materials_fragments": get_materials_fragments,
}
