"""
Document database models
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from ..core.database import Base


class Document(Base):
    """Document model for tracking uploaded PDFs"""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)

    # PDF metadata
    title = Column(String(512), nullable=True)
    author = Column(String(255), nullable=True)
    num_pages = Column(Integer, nullable=True)

    # Processing info
    num_chunks = Column(Integer, default=0)
    chunk_ids = Column(JSON, default=list)  # List of ChromaDB chunk IDs

    # Streaming progress tracking
    chunks_processed = Column(Integer, default=0)  # Chunks embedded and stored so far
    chunks_estimated = Column(Integer, nullable=True)  # Estimated total chunks (based on pages)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    last_chunk_at = Column(DateTime(timezone=True), nullable=True)  # Last chunk processed timestamp

    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status}')>"
