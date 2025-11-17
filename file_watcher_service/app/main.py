"""
Main entry point for File Watcher Service.

This service monitors a folder for new PDF files and triggers
the processing pipeline via the backend API.

GCP Migration:
This entire service would be replaced by:
1. Cloud Storage bucket with notifications → Pub/Sub
2. Cloud Function triggered by Pub/Sub messages
3. Cloud Function calls Cloud Run backend API

The current architecture mirrors this pattern:
- Watcher (Cloud Storage notifications)
- Event Publisher (Pub/Sub)
- Backend API (Cloud Run)
"""
import asyncio
import logging
import signal
import sys
from pythonjsonlogger import jsonlogger

from .config import get_settings
from .watcher import FolderWatcher
from .event_publisher import create_event_publisher, FileEvent

# Configure logging
def setup_logging():
    settings = get_settings()

    # JSON formatter for structured logging (GCP Cloud Logging compatible)
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger('watchdog').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


class FileWatcherService:
    """
    Main service orchestrator.

    Coordinates the watcher, event publisher, and tracks processing results.
    """

    def __init__(self):
        self.settings = get_settings()
        self.watcher = FolderWatcher()
        self.publisher = create_event_publisher()
        self._shutdown_event = asyncio.Event()

    async def handle_file_event(self, event: FileEvent):
        """
        Handle a new file event.

        This is the core processing logic that:
        1. Publishes the event (calls backend)
        2. Tracks the result
        3. Handles failures

        GCP Migration:
        This becomes the Cloud Function handler:
        ```python
        def handle_gcs_event(event, context):
            file_name = event['name']
            bucket = event['bucket']

            # Validate
            if not file_name.endswith('.pdf'):
                return

            # Call backend
            response = requests.post(
                BACKEND_URL,
                json={'file_path': f'gs://{bucket}/{file_name}', ...}
            )

            if response.status_code != 200:
                raise Exception("Processing failed")  # Triggers retry
        ```
        """
        logger.info(
            f"Handling file event",
            extra={
                'file_name': event.file_name,
                'event_id': event.event_id,
                'file_size': event.file_size
            }
        )

        # Publish event (call backend)
        success = await self.publisher.publish(event)

        # Update tracking
        self.watcher.mark_processed(
            event.file_path,
            event.file_size,
            success,
            error=None if success else "Failed to trigger processing"
        )

        if success:
            logger.info(
                f"Successfully triggered processing for {event.file_name}",
                extra={'event_id': event.event_id}
            )
        else:
            logger.error(
                f"Failed to trigger processing for {event.file_name}",
                extra={'event_id': event.event_id}
            )

    async def run(self):
        """Main service loop."""
        logger.info("=" * 50)
        logger.info("FILE WATCHER SERVICE STARTING")
        logger.info("=" * 50)
        logger.info(f"Watching folder: {self.settings.WATCH_FOLDER}")
        logger.info(f"Backend URL: {self.settings.BACKEND_URL}")
        logger.info(f"File patterns: {self.settings.WATCH_PATTERNS}")

        # Start watcher
        await self.watcher.start(self.handle_file_event)

        # Wait for shutdown signal
        await self._shutdown_event.wait()

        # Cleanup
        await self.watcher.stop()
        await self.publisher.close()

        logger.info("File watcher service stopped")

    def shutdown(self):
        """Signal the service to shut down."""
        logger.info("Shutdown signal received")
        self._shutdown_event.set()


async def main():
    """Main entry point."""
    setup_logging()

    service = FileWatcherService()

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, service.shutdown)

    try:
        await service.run()
    except Exception as e:
        logger.error(f"Service error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
