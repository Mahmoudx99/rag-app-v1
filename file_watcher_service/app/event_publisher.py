"""
Event Publisher - Abstraction layer for event publishing.

Design Note: This module provides an abstraction that can be easily swapped
for GCP Pub/Sub. Currently implements direct HTTP calls to backend, but
the interface is designed to match Pub/Sub patterns.

GCP Migration:
- Replace DirectEventPublisher with PubSubEventPublisher
- Events become Pub/Sub messages
- Backend subscribes to topic via push subscription
"""
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class FileEvent:
    """
    Event payload for file operations.

    Designed to match GCP Cloud Storage event schema for easy migration.
    https://cloud.google.com/storage/docs/json_api/v1/objects
    """
    event_type: str  # "OBJECT_FINALIZE" maps to GCS events
    file_path: str
    file_name: str
    file_size: int
    bucket: str  # Watch folder path (maps to GCS bucket)
    timestamp: str
    event_id: str

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class EventPublisher(ABC):
    """
    Abstract base class for event publishing.

    GCP Migration: Implement PubSubEventPublisher that:
    - Creates Pub/Sub client
    - Publishes to configured topic
    - Backend has push subscription to receive events
    """

    @abstractmethod
    async def publish(self, event: FileEvent) -> bool:
        """Publish an event. Returns True if successful."""
        pass

    @abstractmethod
    async def close(self):
        """Clean up resources."""
        pass


class DirectHTTPPublisher(EventPublisher):
    """
    Direct HTTP publisher - calls backend API immediately.

    This is the simplest implementation for demo purposes.
    In GCP, this would be replaced by Pub/Sub which provides:
    - Guaranteed delivery
    - Retry logic
    - Dead letter queues
    - Event ordering
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_connections=10)
        )
        self.base_url = self.settings.BACKEND_URL
        self.endpoint = self.settings.BACKEND_PROCESS_ENDPOINT

    async def publish(self, event: FileEvent) -> bool:
        """
        Publish event by calling backend API directly.

        GCP Migration:
        ```python
        from google.cloud import pubsub_v1

        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(project_id, topic_id)

        data = event.to_json().encode("utf-8")
        future = publisher.publish(topic_path, data)
        future.result()  # Wait for publish to complete
        ```
        """
        url = f"{self.base_url}{self.endpoint}"

        for attempt in range(self.settings.MAX_RETRIES):
            try:
                logger.info(f"Publishing event for file: {event.file_name} (attempt {attempt + 1})")

                response = await self.client.post(
                    url,
                    json=event.to_dict(),
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code in [200, 201, 202]:
                    logger.info(f"Successfully published event for {event.file_name}")
                    return True
                else:
                    logger.warning(
                        f"Backend returned {response.status_code}: {response.text}"
                    )

            except httpx.TimeoutException:
                logger.error(f"Timeout calling backend for {event.file_name}")
            except httpx.ConnectError as e:
                logger.error(f"Connection error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error publishing event: {e}")

            if attempt < self.settings.MAX_RETRIES - 1:
                logger.info(f"Retrying in {self.settings.RETRY_DELAY} seconds...")
                import asyncio
                await asyncio.sleep(self.settings.RETRY_DELAY)

        logger.error(f"Failed to publish event for {event.file_name} after {self.settings.MAX_RETRIES} attempts")
        return False

    async def close(self):
        await self.client.aclose()


# Factory function for easy swapping in GCP
def create_event_publisher() -> EventPublisher:
    """
    Factory to create the appropriate event publisher.

    GCP Migration:
    ```python
    import os

    if os.getenv("USE_PUBSUB", "false").lower() == "true":
        return PubSubEventPublisher(
            project_id=os.getenv("GCP_PROJECT_ID"),
            topic_id=os.getenv("PUBSUB_TOPIC_ID")
        )
    else:
        return DirectHTTPPublisher()
    ```
    """
    return DirectHTTPPublisher()
