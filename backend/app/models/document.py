"""
Document database models
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
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
    chunk_ids = Column(JSON, default=list)  # List of vector store chunk IDs

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


class Chunk(Base):
    """Chunk model for storing document chunks for retrieval"""

    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(String(255), unique=True, index=True, nullable=False)  # Vector store ID
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, default=dict)
    page_number = Column(Integer, nullable=True)
    chunk_index = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to document
    document = relationship("Document", backref="chunks")

    def __repr__(self):
        return f"<Chunk(id={self.id}, chunk_id='{self.chunk_id}', document_id={self.document_id})>"
