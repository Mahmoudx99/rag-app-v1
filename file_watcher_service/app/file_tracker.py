"""
File Tracker - Tracks which files have been processed to ensure idempotency.

Design Note: This is a simple JSON-based tracker for demo purposes.
In production/GCP, this would be replaced with:
- GCS object metadata
- Firestore document
- Cloud Storage notification deduplication

GCP Migration: Cloud Storage triggers are inherently idempotent at the
notification level, but you may still need application-level deduplication.
"""
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Set, Optional
from dataclasses import dataclass, asdict

from .config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ProcessedFileRecord:
    """Record of a processed file."""
    file_path: str
    file_name: str
    file_size: int
    processed_at: str
    status: str  # "success", "failed", "pending"
    event_id: str
    error_message: Optional[str] = None


class FileTracker:
    """
    Tracks processed files to avoid duplicate processing.

    GCP Migration Options:
    1. Firestore:
       ```python
       from google.cloud import firestore
       db = firestore.Client()
       doc_ref = db.collection('processed_files').document(file_hash)
       doc_ref.set({'processed_at': datetime.now(), ...})
       ```

    2. GCS Metadata:
       ```python
       from google.cloud import storage
       bucket.blob(file_name).metadata = {'processed': 'true', 'timestamp': '...'}
       ```

    3. Cloud Storage Notification Deduplication (built-in):
       - Each notification has unique ID
       - Can track notification IDs instead
    """

    def __init__(self, tracker_path: Optional[str] = None):
        settings = get_settings()
        self.tracker_path = Path(tracker_path or settings.PROCESSED_TRACKER_PATH)
        self.tracker_path.parent.mkdir(parents=True, exist_ok=True)
        self._processed_files: dict = {}
        self._load()

    def _load(self):
        """Load tracking data from disk."""
        if self.tracker_path.exists():
            try:
                with open(self.tracker_path, 'r') as f:
                    data = json.load(f)
                    self._processed_files = data.get('files', {})
                    logger.info(f"Loaded {len(self._processed_files)} processed file records")
            except Exception as e:
                logger.error(f"Error loading tracker: {e}")
                self._processed_files = {}
        else:
            self._processed_files = {}

    def _save(self):
        """Save tracking data to disk."""
        try:
            with open(self.tracker_path, 'w') as f:
                json.dump({
                    'files': self._processed_files,
                    'last_updated': datetime.utcnow().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving tracker: {e}")

    def _get_file_key(self, file_path: str, file_size: int) -> str:
        """
        Generate unique key for a file.

        Uses path + size as a simple fingerprint.
        GCP: Could use GCS object generation number or etag.
        """
        return f"{file_path}:{file_size}"

    def is_processed(self, file_path: str, file_size: int) -> bool:
        """Check if a file has already been successfully processed."""
        key = self._get_file_key(file_path, file_size)
        if key in self._processed_files:
            record = self._processed_files[key]
            # Only skip if successfully processed
            # Pending or failed files should be retried
            return record.get('status') == 'success'
        return False

    def is_deleted(self, file_path: str, file_size: int) -> bool:
        """Check if a file was deleted and should not be reprocessed."""
        key = self._get_file_key(file_path, file_size)
        if key in self._processed_files:
            record = self._processed_files[key]
            return record.get('status') == 'deleted'
        return False

    def is_pending(self, file_path: str, file_size: int) -> bool:
        """Check if a file is currently pending processing."""
        key = self._get_file_key(file_path, file_size)
        if key in self._processed_files:
            record = self._processed_files[key]
            return record.get('status') == 'pending'
        return False

    def mark_deleted(self, original_filename: str, file_size: int):
        """
        Mark a file as deleted so it won't be reprocessed.
        This is called when a document is deleted from the UI.
        """
        # Find the file in watch folder by original filename and size
        for key, record in self._processed_files.items():
            if (record.get('file_name') == original_filename and
                record.get('file_size') == file_size):
                record['status'] = 'deleted'
                record['processed_at'] = datetime.utcnow().isoformat()
                self._save()
                logger.info(f"Marked {original_filename} as deleted (won't reprocess)")
                return True

        # If not found in tracker, add it as deleted
        # This handles files that might have been processed before tracker existed
        key = f"deleted:{original_filename}:{file_size}"
        self._processed_files[key] = {
            'file_path': f'unknown:{original_filename}',
            'file_name': original_filename,
            'file_size': file_size,
            'processed_at': datetime.utcnow().isoformat(),
            'status': 'deleted',
            'event_id': 'manual_deletion',
            'error_message': None
        }
        self._save()
        logger.info(f"Added {original_filename} as deleted (won't reprocess)")
        return True

    def is_file_blocked(self, file_name: str, file_size: int) -> bool:
        """
        Check if a file should be blocked from processing.
        Checks by filename and size (not full path) to handle watch folder files.
        """
        for key, record in self._processed_files.items():
            if (record.get('file_name') == file_name and
                record.get('file_size') == file_size):
                status = record.get('status')
                if status in ['success', 'deleted']:
                    return True
        return False

    def clear_stale_pending(self, max_age_seconds: int = 300):
        """Clear pending records that are older than max_age_seconds."""
        cutoff = datetime.utcnow().timestamp() - max_age_seconds
        to_remove = []

        for key, record in self._processed_files.items():
            if record.get('status') == 'pending':
                processed_at = record.get('processed_at')
                if processed_at:
                    try:
                        record_time = datetime.fromisoformat(processed_at).timestamp()
                        if record_time < cutoff:
                            to_remove.append(key)
                    except Exception:
                        pass

        for key in to_remove:
            del self._processed_files[key]
            logger.info(f"Cleared stale pending record: {key}")

        if to_remove:
            self._save()

    def mark_pending(self, record: ProcessedFileRecord):
        """Mark a file as pending processing."""
        key = self._get_file_key(record.file_path, record.file_size)
        self._processed_files[key] = asdict(record)
        self._save()
        logger.debug(f"Marked {record.file_name} as pending")

    def mark_success(self, file_path: str, file_size: int):
        """Mark a file as successfully processed."""
        key = self._get_file_key(file_path, file_size)
        if key in self._processed_files:
            self._processed_files[key]['status'] = 'success'
            self._processed_files[key]['processed_at'] = datetime.utcnow().isoformat()
            self._save()
            logger.info(f"Marked {file_path} as successfully processed")

    def mark_failed(self, file_path: str, file_size: int, error_message: str):
        """Mark a file as failed processing."""
        key = self._get_file_key(file_path, file_size)
        if key in self._processed_files:
            self._processed_files[key]['status'] = 'failed'
            self._processed_files[key]['error_message'] = error_message
            self._processed_files[key]['processed_at'] = datetime.utcnow().isoformat()
            self._save()
            logger.error(f"Marked {file_path} as failed: {error_message}")

    def get_pending_files(self) -> list:
        """Get list of files that are pending processing."""
        pending = []
        for key, record in self._processed_files.items():
            if record.get('status') == 'pending':
                pending.append(record)
        return pending

    def clear_old_records(self, days: int = 30):
        """Remove records older than specified days."""
        cutoff = datetime.utcnow().timestamp() - (days * 86400)
        to_remove = []

        for key, record in self._processed_files.items():
            processed_at = record.get('processed_at')
            if processed_at:
                try:
                    record_time = datetime.fromisoformat(processed_at).timestamp()
                    if record_time < cutoff:
                        to_remove.append(key)
                except Exception:
                    pass

        for key in to_remove:
            del self._processed_files[key]

        if to_remove:
            self._save()
            logger.info(f"Removed {len(to_remove)} old records")
