"""
File System Watcher - Monitors folder for new PDF files.

Design Note: Uses watchdog library for file system events. This is the
component that would be completely replaced by GCP Cloud Storage triggers.

GCP Migration:
- This entire module is replaced by Cloud Storage Object Notifications
- Cloud Storage sends event to Pub/Sub when object is created
- No need for polling or file system watching
- Cloud Functions or Cloud Run receives the event
"""
import asyncio
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
from fnmatch import fnmatch

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from .config import get_settings
from .event_publisher import FileEvent
from .file_tracker import FileTracker, ProcessedFileRecord

logger = logging.getLogger(__name__)


class PDFFileHandler(FileSystemEventHandler):
    """
    Handles file system events for PDF files.

    GCP Migration:
    This handler would be replaced by a Cloud Function that receives
    Cloud Storage events:

    ```python
    from google.cloud import storage

    def process_gcs_event(event, context):
        '''Cloud Function triggered by GCS object finalize.'''
        bucket_name = event['bucket']
        file_name = event['name']

        if not file_name.endswith('.pdf'):
            return

        # Trigger processing
        ...
    ```
    """

    def __init__(
        self,
        callback: Callable[[str], None],
        patterns: list = None,
        stability_threshold: float = 5.0
    ):
        super().__init__()
        self.callback = callback
        self.patterns = patterns or ["*.pdf", "*.PDF"]
        self.stability_threshold = stability_threshold
        self._pending_files: dict = {}  # file_path -> last_modified_time
        self._lock = asyncio.Lock()

    def _matches_pattern(self, file_path: str) -> bool:
        """Check if file matches watched patterns."""
        file_name = os.path.basename(file_path)
        return any(fnmatch(file_name, pattern) for pattern in self.patterns)

    def on_created(self, event):
        """Handle file creation event."""
        if event.is_directory:
            return

        if self._matches_pattern(event.src_path):
            logger.info(f"Detected new file: {event.src_path}")
            self._pending_files[event.src_path] = datetime.now().timestamp()

    def on_modified(self, event):
        """Handle file modification event (updates stability timer)."""
        if event.is_directory:
            return

        if self._matches_pattern(event.src_path):
            # Update last modified time for stability check
            if event.src_path in self._pending_files:
                self._pending_files[event.src_path] = datetime.now().timestamp()

    def get_stable_files(self) -> list:
        """
        Get files that haven't been modified recently (stable).

        This ensures file upload is complete before processing.

        GCP Migration: Not needed because Cloud Storage sends
        OBJECT_FINALIZE event only after upload is complete.
        """
        stable = []
        current_time = datetime.now().timestamp()

        to_remove = []
        for file_path, last_modified in list(self._pending_files.items()):
            if current_time - last_modified >= self.stability_threshold:
                # File is stable (not modified for threshold duration)
                if os.path.exists(file_path):
                    stable.append(file_path)
                to_remove.append(file_path)

        # Remove stable files from pending
        for file_path in to_remove:
            del self._pending_files[file_path]

        return stable


class FolderWatcher:
    """
    Main watcher that monitors a folder and triggers processing.

    GCP Migration:
    This entire class is replaced by:
    1. Cloud Storage bucket with Object Notifications enabled
    2. Pub/Sub topic that receives notifications
    3. Cloud Function or Cloud Run that subscribes to topic

    Setup in GCP:
    ```bash
    # Create notification
    gsutil notification create -t projects/PROJECT/topics/TOPIC \
        -f json -e OBJECT_FINALIZE gs://BUCKET

    # Deploy Cloud Function
    gcloud functions deploy process-pdf \
        --runtime python311 \
        --trigger-topic TOPIC \
        --entry-point handle_event
    ```
    """

    def __init__(self):
        self.settings = get_settings()
        self.watch_folder = Path(self.settings.WATCH_FOLDER)
        self.watch_folder.mkdir(parents=True, exist_ok=True)

        self.tracker = FileTracker()
        self.observer: Optional[Observer] = None
        self.handler: Optional[PDFFileHandler] = None
        self._event_queue: asyncio.Queue = None
        self._running = False

    async def start(self, event_callback: Callable[[FileEvent], None]):
        """
        Start watching the folder.

        Args:
            event_callback: Async function to call when a file is ready
        """
        logger.info(f"Starting folder watcher on: {self.watch_folder}")

        self._event_queue = asyncio.Queue()
        self._running = True

        # Create event handler
        self.handler = PDFFileHandler(
            callback=lambda path: None,  # Events handled via stability check
            patterns=self.settings.WATCH_PATTERNS,
            stability_threshold=self.settings.FILE_STABILITY_THRESHOLD
        )

        # Start file system observer
        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.watch_folder), recursive=False)
        self.observer.start()

        logger.info("File system observer started")

        # Process existing files if configured
        if self.settings.PROCESS_EXISTING_ON_STARTUP:
            await self._process_existing_files(event_callback)

        # Start stability check loop
        asyncio.create_task(self._stability_check_loop(event_callback))

        logger.info("Folder watcher fully initialized")

    async def _process_existing_files(self, event_callback: Callable):
        """Process any existing PDF files in the watch folder."""
        logger.info("Checking for existing PDF files...")

        for pattern in self.settings.WATCH_PATTERNS:
            for file_path in self.watch_folder.glob(pattern):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    file_name = file_path.name

                    # Skip if already processed
                    if self.tracker.is_processed(str(file_path), file_size):
                        logger.debug(f"Skipping already processed: {file_name}")
                        continue

                    # Skip if deleted (user deleted from UI)
                    if self.tracker.is_deleted(str(file_path), file_size):
                        logger.debug(f"Skipping deleted file: {file_name}")
                        continue

                    # Skip if blocked by filename + size
                    if self.tracker.is_file_blocked(file_name, file_size):
                        logger.debug(f"Skipping blocked file: {file_name}")
                        continue

                    logger.info(f"Found unprocessed file: {file_name}")
                    event = self._create_file_event(str(file_path))
                    if event:
                        await event_callback(event)

    async def _stability_check_loop(self, event_callback: Callable):
        """
        Periodically check for stable files and trigger processing.

        GCP Migration: This loop is not needed because Cloud Storage
        OBJECT_FINALIZE event is triggered only when upload is complete.
        """
        # Clear stale pending records on startup (older than 5 minutes)
        self.tracker.clear_stale_pending(max_age_seconds=300)

        while self._running:
            try:
                stable_files = self.handler.get_stable_files()

                for file_path in stable_files:
                    try:
                        file_size = os.path.getsize(file_path)
                        file_name = os.path.basename(file_path)

                        # Skip if already successfully processed
                        if self.tracker.is_processed(file_path, file_size):
                            logger.debug(f"Skipping already processed: {file_path}")
                            continue

                        # Skip if file was deleted (user deleted from UI)
                        if self.tracker.is_deleted(file_path, file_size):
                            logger.debug(f"Skipping deleted file: {file_path}")
                            continue

                        # Skip if file is blocked (by filename + size match)
                        if self.tracker.is_file_blocked(file_name, file_size):
                            logger.debug(f"Skipping blocked file: {file_path}")
                            continue

                        # Skip if currently pending (avoid duplicate processing)
                        if self.tracker.is_pending(file_path, file_size):
                            logger.debug(f"Skipping pending file: {file_path}")
                            continue

                        logger.info(f"File stable and ready: {file_path}")
                        event = self._create_file_event(file_path)
                        if event:
                            await event_callback(event)
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {e}")

            except Exception as e:
                logger.error(f"Error in stability check loop: {e}")

            await asyncio.sleep(self.settings.FILE_STABILITY_CHECK_INTERVAL)

    def _create_file_event(self, file_path: str) -> Optional[FileEvent]:
        """
        Create a FileEvent for a file.

        The event structure mimics GCP Cloud Storage events.
        """
        try:
            path = Path(file_path)
            stat = path.stat()

            event = FileEvent(
                event_type="OBJECT_FINALIZE",  # Matches GCS event type
                file_path=str(path.absolute()),
                file_name=path.name,
                file_size=stat.st_size,
                bucket=str(self.watch_folder),  # Maps to GCS bucket
                timestamp=datetime.utcnow().isoformat(),
                event_id=str(uuid.uuid4())
            )

            # Track as pending
            record = ProcessedFileRecord(
                file_path=str(path.absolute()),
                file_name=path.name,
                file_size=stat.st_size,
                processed_at=datetime.utcnow().isoformat(),
                status="pending",
                event_id=event.event_id
            )
            self.tracker.mark_pending(record)

            return event

        except Exception as e:
            logger.error(f"Error creating event for {file_path}: {e}")
            return None

    def mark_processed(self, file_path: str, file_size: int, success: bool, error: str = None):
        """Mark a file as processed."""
        if success:
            self.tracker.mark_success(file_path, file_size)
        else:
            self.tracker.mark_failed(file_path, file_size, error or "Unknown error")

    async def stop(self):
        """Stop the watcher."""
        logger.info("Stopping folder watcher...")
        self._running = False

        if self.observer:
            self.observer.stop()
            self.observer.join()

        logger.info("Folder watcher stopped")
