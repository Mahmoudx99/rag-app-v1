"""
Configuration for File Watcher Service

Design Note: Configuration is externalized via environment variables to support
easy migration to GCP Cloud Functions where config comes from environment or
Secret Manager.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Service configuration - maps directly to GCP environment variables.

    GCP Migration:
    - WATCH_FOLDER -> GCS bucket name
    - BACKEND_URL -> Cloud Run service URL
    - POLLING_INTERVAL -> Cloud Scheduler cron (for polling) or event-driven (Cloud Storage triggers)
    - PROCESSED_TRACKER_PATH -> Could be Firestore or Cloud Storage metadata
    """

    # Folder to watch for new PDF files
    # GCP: This becomes the GCS bucket path
    WATCH_FOLDER: str = "/data/watch"

    # Backend API URL for triggering processing
    # GCP: This becomes the Cloud Run backend URL or Pub/Sub topic
    BACKEND_URL: str = "http://backend:8000"

    # API endpoint for processing files
    BACKEND_PROCESS_ENDPOINT: str = "/api/v1/documents/process-file"

    # How often to check for stable files (seconds)
    # GCP: Not needed with event-driven Cloud Storage triggers
    FILE_STABILITY_CHECK_INTERVAL: float = 2.0

    # Time to wait after last modification before processing (seconds)
    # Ensures file upload is complete
    FILE_STABILITY_THRESHOLD: float = 5.0

    # Debounce time for file system events (seconds)
    EVENT_DEBOUNCE_TIME: float = 1.0

    # Path to store processed file tracking
    # GCP: Could be Firestore document or GCS object metadata
    PROCESSED_TRACKER_PATH: str = "/data/processed/tracker.json"

    # Maximum retries for backend API calls
    MAX_RETRIES: int = 3

    # Retry delay in seconds
    RETRY_DELAY: float = 5.0

    # File patterns to watch
    WATCH_PATTERNS: list = ["*.pdf", "*.PDF"]

    # Whether to process existing files on startup
    PROCESS_EXISTING_ON_STARTUP: bool = True

    # Log level
    LOG_LEVEL: str = "INFO"

    class Config:
        env_prefix = "WATCHER_"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
