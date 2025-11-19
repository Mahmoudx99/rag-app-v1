"""
Documents API routes - Upload, list, and delete documents
"""
import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ...core.config import get_settings
from ...core.database import get_db
from ...models.document import Document
from ...services.pdf_processor import PDFProcessor
from ...services.embedding_service import EmbeddingService
from ...services.vector_store import VectorStore

router = APIRouter()
settings = get_settings()

# Initialize services (will be loaded on startup)
pdf_processor = None
embedding_service = None
vector_store = None


def get_services():
    """Get service instances"""
    global pdf_processor, embedding_service, vector_store

    if pdf_processor is None:
        pdf_processor = PDFProcessor(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )

    if embedding_service is None:
        embedding_service = EmbeddingService(
            model_name=settings.EMBEDDING_MODEL,
            batch_size=settings.BATCH_SIZE
        )

    if vector_store is None:
        vector_store = VectorStore(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            collection_name=settings.CHROMA_COLLECTION
        )

    return pdf_processor, embedding_service, vector_store


# Response models
class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    title: str | None
    author: str | None
    num_pages: int | None
    num_chunks: int
    status: str
    uploaded_at: datetime
    processed_at: datetime | None
    # Streaming progress fields
    chunks_processed: int = 0
    chunks_estimated: int | None = None
    processing_started_at: datetime | None = None
    last_chunk_at: datetime | None = None

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    success: bool
    document_id: int
    filename: str
    num_chunks: int
    message: str


class DeleteResponse(BaseModel):
    success: bool
    message: str


class DocumentProgressResponse(BaseModel):
    """Response model for document processing progress."""
    id: int
    filename: str
    status: str
    chunks_processed: int
    chunks_estimated: int | None
    num_chunks: int
    progress_percent: float | None
    is_searchable: bool  # True if at least some chunks are available
    processing_started_at: datetime | None
    last_chunk_at: datetime | None
    error_message: str | None = None


class ProcessFileRequest(BaseModel):
    """
    Request model for processing a file from the watcher service.

    Designed to match GCP Cloud Storage event schema for easy migration.
    GCP Migration: This becomes the Pub/Sub message payload from Cloud Storage notifications.
    """
    event_type: str  # "OBJECT_FINALIZE"
    file_path: str
    file_name: str
    file_size: int
    bucket: str  # Watch folder path (maps to GCS bucket)
    timestamp: str
    event_id: str


class ProcessFileResponse(BaseModel):
    success: bool
    document_id: int | None = None
    filename: str
    num_chunks: int = 0
    message: str
    event_id: str


class WatcherActivityItem(BaseModel):
    """Represents a single watcher activity event."""
    event_id: str
    filename: str
    file_size: int
    status: str  # "processing", "completed", "failed"
    started_at: datetime
    completed_at: datetime | None = None
    document_id: int | None = None
    num_chunks: int = 0
    error_message: str | None = None
    # Enhanced progress tracking fields
    chunks_processed: int = 0
    chunks_estimated: int | None = None
    progress_percent: float | None = None
    elapsed_seconds: float = 0.0
    processing_rate: float | None = None  # chunks per second
    estimated_remaining_seconds: float | None = None


class WatcherActivityResponse(BaseModel):
    """Response for watcher activity status."""
    recent_activities: list[WatcherActivityItem]
    total_processed: int
    total_failed: int
    is_active: bool


class ReprocessRequest(BaseModel):
    """Request to reprocess specific deleted files."""
    event_ids: list[str]  # List of event_ids to reprocess


# In-memory storage for watcher activity (last 50 events)
_watcher_activity: list[dict] = []
_MAX_ACTIVITY_HISTORY = 50
_ACTIVITY_FILE_PATH = Path("/data/processed/activity_history.json")


def _load_activity_history():
    """Load activity history from persistent storage."""
    global _watcher_activity
    try:
        if _ACTIVITY_FILE_PATH.exists():
            import json
            with open(_ACTIVITY_FILE_PATH, 'r') as f:
                data = json.load(f)
                # Convert string timestamps back to datetime
                for item in data.get('activities', []):
                    if isinstance(item.get('started_at'), str):
                        item['started_at'] = datetime.fromisoformat(item['started_at'])
                    if isinstance(item.get('completed_at'), str) and item['completed_at']:
                        item['completed_at'] = datetime.fromisoformat(item['completed_at'])
                _watcher_activity = data.get('activities', [])[:_MAX_ACTIVITY_HISTORY]
    except Exception as e:
        print(f"Warning: Could not load activity history: {e}")
        _watcher_activity = []


def _save_activity_history():
    """Save activity history to persistent storage."""
    try:
        import json
        _ACTIVITY_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Convert datetime to string for JSON serialization
        serializable = []
        for item in _watcher_activity:
            item_copy = item.copy()
            if isinstance(item_copy.get('started_at'), datetime):
                item_copy['started_at'] = item_copy['started_at'].isoformat()
            if isinstance(item_copy.get('completed_at'), datetime):
                item_copy['completed_at'] = item_copy['completed_at'].isoformat()
            serializable.append(item_copy)

        with open(_ACTIVITY_FILE_PATH, 'w') as f:
            json.dump({
                'activities': serializable,
                'last_updated': datetime.utcnow().isoformat()
            }, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save activity history: {e}")


# Load history on module import
_load_activity_history()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and process a PDF document

    - Saves the file
    - Extracts text and chunks
    - Generates embeddings
    - Stores in vector database
    """
    # Validate file
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )

    if file.size and file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )

    # Generate unique filename
    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{file.filename}"
    file_path = os.path.join(settings.WATCH_DIR, filename)

    # Ensure watch directory exists
    os.makedirs(settings.WATCH_DIR, exist_ok=True)

    try:
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(file_path)

        # Create database record
        doc = Document(
            filename=filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            status="processing",
            processing_started_at=datetime.utcnow(),
            chunks_processed=0
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Get services
        pdf_proc, embed_svc, vec_store = get_services()

        # Extract metadata first to estimate chunks
        metadata = pdf_proc.extract_metadata(file_path)
        doc.title = metadata.get("title")
        doc.author = metadata.get("author")
        doc.num_pages = metadata.get("num_pages")
        # Estimate ~2-5 chunks per page (conservative estimate)
        doc.chunks_estimated = (metadata.get("num_pages") or 1) * 3
        db.commit()

        # Use streaming pipeline: chunks -> embeddings -> storage (progressively)
        chunk_generator = pdf_proc.process_pdf_streaming(file_path)
        all_chunk_ids = []
        total_chunks = 0

        try:
            # Stream chunks through embedding service, which batches them
            for batch_chunks, batch_embeddings in embed_svc.generate_embeddings_streaming(chunk_generator):
                # Add document metadata to each chunk
                for chunk in batch_chunks:
                    chunk["metadata"]["document_id"] = doc.id
                    chunk["metadata"]["document_filename"] = doc.filename

                # Store this batch immediately in vector database
                vec_store.add_documents_batch(batch_chunks, batch_embeddings, doc.id)

                # Track chunk IDs
                batch_ids = [chunk["id"] for chunk in batch_chunks]
                all_chunk_ids.extend(batch_ids)
                total_chunks += len(batch_chunks)

                # Update progress in database
                doc.chunks_processed = total_chunks
                doc.last_chunk_at = datetime.utcnow()
                db.commit()

        except Exception as e:
            # Processing error - partial success
            doc.status = "failed"
            doc.error_message = f"Error during streaming processing: {str(e)}"
            doc.num_chunks = total_chunks
            doc.chunk_ids = all_chunk_ids
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process PDF: {str(e)}"
            )

        # Update final document record
        doc.num_chunks = total_chunks
        doc.chunk_ids = all_chunk_ids
        doc.chunks_processed = total_chunks
        doc.status = "completed"
        doc.processed_at = datetime.utcnow()
        db.commit()

        return UploadResponse(
            success=True,
            document_id=doc.id,
            filename=doc.original_filename,
            num_chunks=total_chunks,
            message="Document uploaded and processed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        if os.path.exists(file_path):
            os.remove(file_path)

        if 'doc' in locals():
            db.delete(doc)
            db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )


@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get list of all documents
    """
    documents = db.query(Document).order_by(Document.uploaded_at.desc()).offset(skip).limit(limit).all()
    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific document by ID
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return doc


@router.get("/{document_id}/progress", response_model=DocumentProgressResponse)
def get_document_progress(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get processing progress for a specific document.

    This endpoint is designed for polling during document processing to show
    real-time progress as chunks are processed through the streaming pipeline.

    Returns:
        - chunks_processed: Number of chunks embedded and stored so far
        - chunks_estimated: Estimated total chunks (based on page count)
        - progress_percent: Percentage complete (0-100)
        - is_searchable: True if document has at least some chunks available for search
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Calculate progress percentage
    progress_percent = None
    if doc.chunks_estimated and doc.chunks_estimated > 0:
        progress_percent = min(100.0, (doc.chunks_processed / doc.chunks_estimated) * 100)
    elif doc.status == "completed" and doc.num_chunks > 0:
        progress_percent = 100.0

    # Document is searchable if it has any chunks processed
    is_searchable = doc.chunks_processed > 0 or doc.num_chunks > 0

    return DocumentProgressResponse(
        id=doc.id,
        filename=doc.original_filename,
        status=doc.status,
        chunks_processed=doc.chunks_processed or 0,
        chunks_estimated=doc.chunks_estimated,
        num_chunks=doc.num_chunks or 0,
        progress_percent=progress_percent,
        is_searchable=is_searchable,
        processing_started_at=doc.processing_started_at,
        last_chunk_at=doc.last_chunk_at,
        error_message=doc.error_message
    )


@router.get("/{document_id}/pdf")
def get_document_pdf(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the PDF file for a document
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if not os.path.exists(doc.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found on server"
        )

    return FileResponse(
        path=doc.file_path,
        media_type="application/pdf",
        filename=doc.original_filename
    )


def _mark_file_as_deleted_in_tracker(original_filename: str, file_size: int):
    """
    Mark a file as deleted in the watcher's tracker file.
    This prevents the file from being reprocessed if it's still in the watch folder.
    """
    import json
    tracker_path = Path("/data/processed/tracker.json")

    try:
        # Load existing tracker
        if tracker_path.exists():
            with open(tracker_path, 'r') as f:
                data = json.load(f)
                files = data.get('files', {})
        else:
            files = {}

        # Find and mark as deleted, or add new entry
        found = False
        for key, record in files.items():
            if (record.get('file_name') == original_filename and
                record.get('file_size') == file_size):
                record['status'] = 'deleted'
                record['processed_at'] = datetime.utcnow().isoformat()
                found = True
                break

        # If not found, add as deleted
        if not found:
            key = f"deleted:{original_filename}:{file_size}"
            files[key] = {
                'file_path': f'unknown:{original_filename}',
                'file_name': original_filename,
                'file_size': file_size,
                'processed_at': datetime.utcnow().isoformat(),
                'status': 'deleted',
                'event_id': 'manual_deletion',
                'error_message': None
            }

        # Save tracker
        tracker_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tracker_path, 'w') as f:
            json.dump({
                'files': files,
                'last_updated': datetime.utcnow().isoformat()
            }, f, indent=2)

    except Exception as e:
        # Log but don't fail the delete operation
        print(f"Warning: Could not update watcher tracker: {e}")


@router.delete("/{document_id}", response_model=DeleteResponse)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a document and all its chunks from the vector store
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    try:
        # Get vector store
        _, _, vec_store = get_services()

        # Delete from vector store
        if doc.chunk_ids:
            vec_store.delete_by_ids(doc.chunk_ids)

        # Delete file from watch directory
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)

        # Mark as deleted in watcher tracker (prevents reprocessing from watch folder)
        _mark_file_as_deleted_in_tracker(doc.original_filename, doc.file_size)

        # Track deletion in watcher activity UI
        deletion_record = {
            "event_id": f"delete_{doc.id}_{datetime.utcnow().timestamp()}",
            "filename": doc.original_filename,
            "file_size": doc.file_size,
            "status": "deleted",
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
            "document_id": doc.id,
            "num_chunks": doc.num_chunks or 0,
            "error_message": None
        }
        _watcher_activity.insert(0, deletion_record)
        if len(_watcher_activity) > _MAX_ACTIVITY_HISTORY:
            _watcher_activity.pop()
        _save_activity_history()

        # Delete from database
        db.delete(doc)
        db.commit()

        return DeleteResponse(
            success=True,
            message=f"Document '{doc.original_filename}' deleted successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document: {str(e)}"
        )


@router.get("/stats/overview")
def get_stats(db: Session = Depends(get_db)):
    """
    Get system statistics
    """
    try:
        total_docs = db.query(Document).count()
        total_chunks = db.query(Document).filter(Document.status == "completed").with_entities(
            func.sum(Document.num_chunks)
        ).scalar() or 0

        _, _, vec_store = get_services()
        vector_stats = vec_store.get_collection_stats()

        return {
            "total_documents": total_docs,
            "total_chunks": int(total_chunks),
            "vector_store": vector_stats
        }
    except Exception as e:
        # Return cached/default stats if there's an issue (e.g., during processing)
        return {
            "total_documents": 0,
            "total_chunks": 0,
            "vector_store": {"count": 0, "collection": "documents"}
        }


def _process_file_background(
    event_id: str,
    file_name: str,
    file_path: str,
    file_size: int,
    activity_record: dict
):
    """
    Background task to process PDF file using streaming pipeline.
    Chunks are embedded and stored progressively as they are created.
    This runs in a separate thread so it doesn't block the API.
    """
    from ...core.database import SessionLocal

    db = SessionLocal()
    try:
        # Process file directly from watch directory (no copying needed)
        # Extract just the filename from the full path
        import os.path as osp
        actual_filename = osp.basename(file_path)

        # Create database record using the file in watch directory
        doc = Document(
            filename=actual_filename,
            original_filename=file_name,
            file_path=file_path,  # Use the original path in watch directory
            file_size=file_size,
            status="processing",
            processing_started_at=datetime.utcnow(),
            chunks_processed=0
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Get services
        pdf_proc, embed_svc, vec_store = get_services()

        # Extract metadata first to estimate chunks
        metadata = pdf_proc.extract_metadata(file_path)
        doc.title = metadata.get("title")
        doc.author = metadata.get("author")
        doc.num_pages = metadata.get("num_pages")
        # Estimate ~2-5 chunks per page (conservative estimate)
        doc.chunks_estimated = (metadata.get("num_pages") or 1) * 3
        db.commit()

        # Update activity record with chunks estimated
        activity_record["chunks_estimated"] = doc.chunks_estimated

        # Use streaming pipeline: chunks -> embeddings -> storage (progressively)
        chunk_generator = pdf_proc.process_pdf_streaming(file_path)
        all_chunk_ids = []
        total_chunks = 0
        processing_start_time = datetime.utcnow()

        try:
            # Stream chunks through embedding service, which batches them
            for batch_chunks, batch_embeddings in embed_svc.generate_embeddings_streaming(chunk_generator):
                # Add document metadata to each chunk
                for chunk in batch_chunks:
                    chunk["metadata"]["document_id"] = doc.id
                    chunk["metadata"]["document_filename"] = doc.filename

                # Store this batch immediately in vector database
                vec_store.add_documents_batch(batch_chunks, batch_embeddings, doc.id)

                # Track chunk IDs
                batch_ids = [chunk["id"] for chunk in batch_chunks]
                all_chunk_ids.extend(batch_ids)
                total_chunks += len(batch_chunks)

                # Update progress in database
                doc.chunks_processed = total_chunks
                doc.last_chunk_at = datetime.utcnow()
                db.commit()

                # Calculate progress metrics for UI
                elapsed_seconds = (datetime.utcnow() - processing_start_time).total_seconds()
                processing_rate = total_chunks / elapsed_seconds if elapsed_seconds > 0 else 0
                progress_percent = None
                estimated_remaining = None

                if doc.chunks_estimated and doc.chunks_estimated > 0:
                    progress_percent = min(100.0, (total_chunks / doc.chunks_estimated) * 100)
                    remaining_chunks = max(0, doc.chunks_estimated - total_chunks)
                    if processing_rate > 0:
                        estimated_remaining = remaining_chunks / processing_rate

                # Update activity record for UI visibility with enhanced metrics
                activity_record["num_chunks"] = total_chunks
                activity_record["chunks_processed"] = total_chunks
                activity_record["chunks_estimated"] = doc.chunks_estimated
                activity_record["progress_percent"] = progress_percent
                activity_record["elapsed_seconds"] = elapsed_seconds
                activity_record["processing_rate"] = round(processing_rate, 2)
                activity_record["estimated_remaining_seconds"] = round(estimated_remaining, 1) if estimated_remaining else None

        except Exception as e:
            # Processing error - document is partially processed
            doc.status = "failed"
            doc.error_message = f"Error during streaming processing: {str(e)}"
            doc.num_chunks = total_chunks
            doc.chunk_ids = all_chunk_ids
            db.commit()
            activity_record["status"] = "failed"
            activity_record["completed_at"] = datetime.utcnow()
            activity_record["error_message"] = str(e)
            activity_record["num_chunks"] = total_chunks
            _save_activity_history()
            return

        # Update final document record
        doc.num_chunks = total_chunks
        doc.chunk_ids = all_chunk_ids
        doc.chunks_processed = total_chunks
        doc.status = "completed"
        doc.processed_at = datetime.utcnow()
        db.commit()

        # Update activity record
        activity_record["status"] = "completed"
        activity_record["completed_at"] = datetime.utcnow()
        activity_record["document_id"] = doc.id
        activity_record["num_chunks"] = total_chunks
        _save_activity_history()

    except Exception as e:
        # Clean up on error - Don't delete the original file from watch directory
        # as the watcher tracker will handle retry logic

        if 'doc' in locals():
            doc.status = "failed"
            doc.error_message = str(e)
            db.commit()

        activity_record["status"] = "failed"
        activity_record["completed_at"] = datetime.utcnow()
        activity_record["error_message"] = str(e)
        _save_activity_history()
    finally:
        db.close()


@router.post("/process-file", response_model=ProcessFileResponse, status_code=status.HTTP_202_ACCEPTED)
async def process_file_from_watcher(
    request: ProcessFileRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Process a PDF file triggered by the file watcher service.

    This endpoint is called when the watcher detects a new PDF file.
    Files are processed directly from the watch directory without copying.

    GCP Migration:
    - This endpoint would receive events from Pub/Sub (push subscription)
    - Or be deployed as a Cloud Function triggered by Cloud Storage
    - File would be downloaded from GCS instead of local filesystem

    ```python
    # GCP version
    from google.cloud import storage

    def process_gcs_file(event_data):
        storage_client = storage.Client()
        bucket = storage_client.bucket(event_data['bucket'])
        blob = bucket.blob(event_data['file_name'])

        # Download to temp location
        temp_path = f"/tmp/{event_data['file_name']}"
        blob.download_to_filename(temp_path)

        # Process the file
        ...
    ```
    """
    # Validate event type
    if request.event_type != "OBJECT_FINALIZE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported event type: {request.event_type}"
        )

    # Validate file exists and is PDF
    if not request.file_name.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )

    if not os.path.exists(request.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {request.file_path}"
        )

    # Check if file was already processed by checking original filename + size
    # This handles idempotency even after file is moved
    actual_size = os.path.getsize(request.file_path)
    existing = db.query(Document).filter(
        Document.original_filename == request.file_name,
        Document.file_size == actual_size
    ).first()

    if existing:
        return ProcessFileResponse(
            success=True,
            document_id=existing.id,
            filename=existing.original_filename,
            num_chunks=existing.num_chunks,
            message="File already processed",
            event_id=request.event_id
        )

    # Validate file size
    if actual_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )

    # Track activity for UI
    activity_record = {
        "event_id": request.event_id,
        "filename": request.file_name,
        "file_size": actual_size,
        "status": "processing",
        "started_at": datetime.utcnow(),
        "completed_at": None,
        "document_id": None,
        "num_chunks": 0,
        "error_message": None,
        # Enhanced progress tracking fields
        "chunks_processed": 0,
        "chunks_estimated": None,
        "progress_percent": None,
        "elapsed_seconds": 0.0,
        "processing_rate": None,
        "estimated_remaining_seconds": None
    }
    _watcher_activity.insert(0, activity_record)
    if len(_watcher_activity) > _MAX_ACTIVITY_HISTORY:
        _watcher_activity.pop()
    _save_activity_history()

    # Schedule processing in background (non-blocking)
    background_tasks.add_task(
        _process_file_background,
        request.event_id,
        request.file_name,
        request.file_path,
        actual_size,
        activity_record
    )

    # Return immediately - processing happens in background
    return ProcessFileResponse(
        success=True,
        document_id=None,  # Not yet assigned
        filename=request.file_name,
        num_chunks=0,  # Not yet processed
        message="File queued for processing",
        event_id=request.event_id
    )


@router.get("/watcher/activity", response_model=WatcherActivityResponse)
def get_watcher_activity():
    """
    Get recent file watcher activity.

    Returns the last 50 processing events from the file watcher,
    including their status (processing, completed, failed).
    """
    # Count totals
    total_processed = sum(1 for a in _watcher_activity if a["status"] == "completed")
    total_failed = sum(1 for a in _watcher_activity if a["status"] == "failed")

    # Check if any files are currently processing
    is_active = any(a["status"] == "processing" for a in _watcher_activity)

    # Convert to response model with enhanced progress fields
    activities = []
    for a in _watcher_activity:
        # Calculate elapsed time for processing items
        elapsed_seconds = a.get("elapsed_seconds", 0.0)
        if a["status"] == "processing" and isinstance(a["started_at"], datetime):
            elapsed_seconds = (datetime.utcnow() - a["started_at"]).total_seconds()

        activities.append(WatcherActivityItem(
            event_id=a["event_id"],
            filename=a["filename"],
            file_size=a["file_size"],
            status=a["status"],
            started_at=a["started_at"],
            completed_at=a["completed_at"],
            document_id=a["document_id"],
            num_chunks=a["num_chunks"],
            error_message=a["error_message"],
            # Enhanced progress tracking
            chunks_processed=a.get("chunks_processed", 0),
            chunks_estimated=a.get("chunks_estimated"),
            progress_percent=a.get("progress_percent"),
            elapsed_seconds=elapsed_seconds,
            processing_rate=a.get("processing_rate"),
            estimated_remaining_seconds=a.get("estimated_remaining_seconds")
        ))

    return WatcherActivityResponse(
        recent_activities=activities,
        total_processed=total_processed,
        total_failed=total_failed,
        is_active=is_active
    )


@router.delete("/watcher/activity")
def clear_watcher_activity():
    """Clear the watcher activity history."""
    global _watcher_activity
    _watcher_activity = []
    _save_activity_history()
    return {"message": "Watcher activity cleared"}


@router.post("/watcher/reprocess-deleted")
def reprocess_deleted_files(
    background_tasks: BackgroundTasks,
    request: ReprocessRequest = None
):
    """
    Reprocess files that were previously deleted.
    If event_ids provided, only reprocess those specific files.
    Marks reprocessed files as 'reprocessed' status (not deleted anymore).
    """
    import json
    watch_folder = Path("/data/watch")

    try:
        # Get the specific event_ids to reprocess (if provided)
        selected_event_ids = set(request.event_ids) if request and request.event_ids else None

        # Find deleted activity records to reprocess
        files_to_reprocess = []
        for activity in _watcher_activity:
            if activity.get('status') == 'deleted':
                # If specific IDs provided, check if this one is selected
                if selected_event_ids is None or activity.get('event_id') in selected_event_ids:
                    files_to_reprocess.append(activity)

        if not files_to_reprocess:
            return {"message": "No deleted files to reprocess", "reactivated": 0}

        # Process each file
        reprocessed = 0
        for deleted_activity in files_to_reprocess:
            file_name = deleted_activity['filename']
            expected_size = deleted_activity['file_size']

            # Check if file exists in watch folder
            watch_file_path = watch_folder / file_name
            if watch_file_path.exists() and watch_file_path.is_file():
                actual_size = watch_file_path.stat().st_size

                # Verify size matches (same file)
                if actual_size == expected_size:
                    # Mark the old deleted record as 'reprocessed'
                    deleted_activity['status'] = 'reprocessed'
                    deleted_activity['completed_at'] = datetime.utcnow()

                    # Create new activity record for processing
                    new_activity_record = {
                        "event_id": f"reprocess_{uuid.uuid4()}",
                        "filename": file_name,
                        "file_size": actual_size,
                        "status": "processing",
                        "started_at": datetime.utcnow(),
                        "completed_at": None,
                        "document_id": None,
                        "num_chunks": 0,
                        "error_message": None,
                        # Enhanced progress tracking fields
                        "chunks_processed": 0,
                        "chunks_estimated": None,
                        "progress_percent": None,
                        "elapsed_seconds": 0.0,
                        "processing_rate": None,
                        "estimated_remaining_seconds": None
                    }
                    _watcher_activity.insert(0, new_activity_record)
                    if len(_watcher_activity) > _MAX_ACTIVITY_HISTORY:
                        _watcher_activity.pop()

                    # Schedule processing in background
                    background_tasks.add_task(
                        _process_file_background,
                        new_activity_record["event_id"],
                        file_name,
                        str(watch_file_path),
                        actual_size,
                        new_activity_record
                    )
                    reprocessed += 1
                else:
                    # File size changed, mark as reprocessed but note the issue
                    deleted_activity['status'] = 'reprocessed'
                    deleted_activity['error_message'] = 'File size changed, skipped'
            else:
                # File not found in watch folder
                deleted_activity['status'] = 'reprocessed'
                deleted_activity['error_message'] = 'File not found in watch folder'

        _save_activity_history()

        return {
            "message": f"Reprocessing {reprocessed} files",
            "reactivated": reprocessed
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reprocessing deleted files: {str(e)}"
        )


# Import func for SQL functions
from sqlalchemy import func
