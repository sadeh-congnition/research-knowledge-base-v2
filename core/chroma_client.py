from __future__ import annotations

import os
import chromadb
from django.conf import settings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# Module-level cache — populated lazily on first access.
_chroma_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None


def _get_embedding_function() -> OpenAIEmbeddingFunction:
    return OpenAIEmbeddingFunction(
        api_key="lm-studio",
        api_base="http://127.0.0.1:1234/v1",
        model_name="unsloth/embeddinggemma-300m-GGUF",
    )


def get_chroma_client() -> chromadb.PersistentClient:
    """Return the shared ChromaDB persistent client, creating it on first call."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=str(settings.BASE_DIR / "chroma_db")
        )
    return _chroma_client


def get_collection() -> chromadb.Collection:
    """Return the shared collection, creating it on first call.
    
    Collection name is controlled by CHROMA_COLLECTION_NAME environment variable,
    defaulting to 'research_tracker' for production use.
    """
    global _collection
    if _collection is None:
        client = get_chroma_client()
        collection_name = os.getenv('CHROMA_COLLECTION_NAME', 'research_tracker')
        _collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=_get_embedding_function(),
        )
    return _collection


# Backwards-compatible shim so existing callers using `from .chroma_client import collection`
# continue to work. The actual ChromaDB client is only opened when the attribute is accessed.
class _LazyCollection:
    """Proxy object that forwards every attribute access to the real collection."""

    def __getattr__(self, name: str):  # type: ignore[override]
        return getattr(get_collection(), name)


collection = _LazyCollection()
