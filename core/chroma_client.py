import chromadb
from django.conf import settings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# Initialize persistent client
chroma_client = chromadb.PersistentClient(path=str(settings.BASE_DIR / 'chroma_db'))

# Fallback openAI embedding function using LMStudio server locally, as requested
emb_fn = OpenAIEmbeddingFunction(
    api_key="lm-studio",
    api_base="http://127.0.0.1:1234/v1",
    model_name="text-embedding-nomic-embed-text-v1.5"
)

# Get or create collection
collection = chroma_client.get_or_create_collection(
    name="research_tracker",
    embedding_function=emb_fn
)
