"""Elasticsearch index creation and mapping management."""

import logging

from elasticsearch import AsyncElasticsearch

VECTOR_DIMS = 1536  # OpenAI-compatible embedding dimension (configurable)

STAFF_INDEX = "staff"
EVENTS_INDEX = "events"
CONTEXT_MATERIALS_INDEX = "context_materials"

STAFF_MAPPING = {
    "settings": {
        "analysis": {
            "analyzer": {
                "russian_standard": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "russian_stop", "russian_stemmer"],
                }
            },
            "filter": {
                "russian_stop": {"type": "stop", "stopwords": "_russian_"},
                "russian_stemmer": {"type": "stemmer", "language": "russian"},
            },
        }
    },
    "mappings": {
        "properties": {
            "name": {"type": "text", "analyzer": "russian_standard"},
            "surname": {"type": "text", "analyzer": "russian_standard"},
            "fathers_name": {"type": "text", "analyzer": "russian_standard"},
            "position": {"type": "text", "analyzer": "russian_standard"},
            "room": {"type": "integer"},
            "department": {"type": "keyword"},
            "competences": {"type": "text", "analyzer": "russian_standard"},
            "competences_vector": {
                "type": "dense_vector",
                "dims": VECTOR_DIMS,
                "index": True,
                "similarity": "cosine",
            },
            "description": {"type": "text", "analyzer": "russian_standard"},
            "description_vector": {
                "type": "dense_vector",
                "dims": VECTOR_DIMS,
                "index": True,
                "similarity": "cosine",
            },
        }
    },
}

EVENTS_MAPPING = {
    "settings": {
        "analysis": {
            "analyzer": {
                "russian_standard": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "russian_stop", "russian_stemmer"],
                }
            },
            "filter": {
                "russian_stop": {"type": "stop", "stopwords": "_russian_"},
                "russian_stemmer": {"type": "stemmer", "language": "russian"},
            },
        }
    },
    "mappings": {
        "properties": {
            "name": {"type": "text", "analyzer": "russian_standard"},
            "date_from": {"type": "date"},
            "date_to": {"type": "date"},
            "description": {"type": "text", "analyzer": "russian_standard"},
            "description_vector": {
                "type": "dense_vector",
                "dims": VECTOR_DIMS,
                "index": True,
                "similarity": "cosine",
            },
            "bonus_amount": {"type": "integer"},
            "participant_amount": {"type": "integer"},
            "participant_requirements": {"type": "text", "analyzer": "russian_standard"},
            "participant_requirements_vector": {
                "type": "dense_vector",
                "dims": VECTOR_DIMS,
                "index": True,
                "similarity": "cosine",
            },
        }
    },
}

CONTEXT_MATERIALS_MAPPING = {
    "mappings": {
        "properties": {
            "document_id": {"type": "integer"},
            "chunk_index": {"type": "integer"},
            "chunk_text": {"type": "text", "analyzer": "standard"},
            "chunk_vector": {
                "type": "dense_vector",
                "dims": VECTOR_DIMS,
                "index": True,
                "similarity": "cosine",
            },
            "created_at": {"type": "date"},
        }
    }
}


async def ensure_indexes(es: AsyncElasticsearch) -> None:
    """Create ES indexes with mappings if they don't already exist."""
    if not await es.ping():
        logging.error('ES not connected, no index created')
        return
    indexes = {
        STAFF_INDEX: STAFF_MAPPING,
        EVENTS_INDEX: EVENTS_MAPPING,
        CONTEXT_MATERIALS_INDEX: CONTEXT_MATERIALS_MAPPING,
    }
    for name, body in indexes.items():
        exists = await es.indices.exists(index=name)
        if not exists:
            await es.indices.create(index=name, body=body)
    logging.info('Successfully created ES indexes')
