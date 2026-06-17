from sqlalchemy import (
    Column, String, Integer, DateTime, Float, Text,
    JSON, ForeignKey, Enum, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

Base = declarative_base()

class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    HTML = "html"
    XLSX = "xlsx"
    PPTX = "pptx"
    UNKNOWN = "unknown"

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    file_type = Column(Enum(DocumentType), nullable=False)
    file_path = Column(String(512))
    content_hash = Column(String(64))

    title = Column(String(500))
    author = Column(String(255))
    page_count = Column(Integer)
    word_count = Column(Integer)
    content_length = Column(Integer, nullable=False)
    chunks_count = Column(Integer, default=0)

    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING)
    error_message = Column(Text)

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    processed_at = Column(DateTime)

    doc_metadata = Column("metadata", JSON, default={})
    tags = Column(JSON, default=[])

    __table_args__ = (
        Index('idx_documents_filename', 'filename'),
        Index('idx_documents_status', 'status'),
        Index('idx_documents_file_type', 'file_type'),
        Index('idx_documents_created_at', 'created_at'),
    )

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    answers = relationship("Answer", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_length = Column(Integer, nullable=False)

    vector_id = Column(String(36))
    chunk_metadata = Column("metadata", JSON, default={})

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_chunks_document_id', 'document_id'),
        Index('idx_chunks_vector_id', 'vector_id'),
        Index('idx_chunks_chunk_index', 'document_id', 'chunk_index'),
    )

    document = relationship("Document", back_populates="chunks")

class Answer(Base):
    __tablename__ = "answers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)

    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"))

    confidence = Column(Float)
    processing_time_ms = Column(Float)

    sources = Column(JSON, default=[])

    created_at = Column(DateTime, default=datetime.now, nullable=False)

    __table_args__ = (
        Index('idx_answers_created_at', 'created_at'),
        Index('idx_answers_document_id', 'document_id'),
    )

    document = relationship("Document", back_populates="answers")

class DocumentTag(Base):
    __tablename__ = "document_tags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    tag = Column(String(100), nullable=False)

    __table_args__ = (
        Index('idx_tags_document_id', 'document_id'),
        Index('idx_tags_tag', 'tag'),
        Index('idx_tags_unique', 'document_id', 'tag', unique=True),
    )
