"""
Application configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "RAG Knowledge Base"
    VERSION: str = "1.0.0"

    # Database (SQLite for local/testing, can be overridden for cloud)
    DATABASE_URL: str = "sqlite:////data/rag_app.db"
    # For GCP Cloud SQL PostgreSQL, set: postgresql://user:pass@/dbname?host=/cloudsql/project:region:instance

    # GCP Settings
    GCP_PROJECT_ID: str = "anb-gpt-prj"
    GCP_REGION: str = "me-central2"

    # Vertex AI Vector Search
    VERTEX_AI_INDEX_ENDPOINT_ID: str = "projects/687800931209/locations/me-central2/indexEndpoints/2982368115737755648"
    VERTEX_AI_DEPLOYED_INDEX_ID: str = "rag_embeddings_v1"
    VERTEX_AI_INDEX_ID: str = "projects/687800931209/locations/me-central2/indexes/926615623331479552"

    # File Storage (Universal location for all documents)
    WATCH_DIR: str = "/data/watch"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: set = {".pdf"}

    # PDF Processing
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    CHUNK_STRATEGY: str = "paragraph"

    # Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    BATCH_SIZE: int = 32

    # LLM Service
    LLM_SERVICE_URL: str = "http://llm:8001"

    # CORS
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost"]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
