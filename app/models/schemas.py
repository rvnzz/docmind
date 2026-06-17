from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    HTML = "html"
    XLSX = "xlsx"
    PPTX = "pptx"
    UNKNOWN = "unknown"

class DocumentMetadata(BaseModel):
    source: Optional[str] = None
    file_size: Optional[int] = None
    title: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    custom: Dict[str, Any] = Field(default_factory=dict)

class DocumentBase(BaseModel):
    filename: str
    file_type: DocumentType
    content_length: int
    chunks_count: int = 0
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)

class DocumentCreate(DocumentBase):
    content: str
    chunks: List[Dict[str, Any]] = Field(default_factory=list)

class DocumentResponse(DocumentBase):
    id: str
    status: DocumentStatus = DocumentStatus.PENDING
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentResponse]
    page: Optional[int] = 1
    limit: Optional[int] = 20

class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    status: DocumentStatus
    chunks_created: int
    content_length: int
    file_type: DocumentType
    message: str
    metadata: DocumentMetadata

class DocumentDeleteResponse(BaseModel):
    id: str
    filename: str
    status: str
    message: str

class UploadFileResponse(BaseModel):
    id: str
    filename: str
    status: DocumentStatus
    chunks_created: int
    message: str

class BatchUploadResponse(BaseModel):
    total: int
    success: int
    errors: int
    results: List[UploadFileResponse]
    error_details: List[Dict[str, Any]]

class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: Optional[int] = Field(5, ge=1, le=20)
    document_ids: Optional[List[str]] = None
    include_sources: Optional[bool] = True

class SourceInfo(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    content: str
    similarity_score: Optional[float] = None

class AnswerResponse(BaseModel):
    id: str
    question: str
    answer: str
    sources: List[SourceInfo] = Field(default_factory=list)
    confidence: Optional[float] = None
    processing_time_ms: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)

class ChatHistoryResponse(BaseModel):
    total: int
    history: List[AnswerResponse]
    page: Optional[int] = 1
    limit: Optional[int] = 20

class DocumentSearchRequest(BaseModel):
    query: Optional[str] = None
    file_type: Optional[DocumentType] = None
    status: Optional[DocumentStatus] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: Optional[int] = 1
    limit: Optional[int] = 20

class ChunkResponse(BaseModel):
    id: str
    document_id: str
    content: str
    chunk_index: int
    total_chunks: int
    metadata: Dict[str, Any]

class DocumentChunksResponse(BaseModel):
    document_id: str
    total_chunks: int
    chunks: List[ChunkResponse]

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    vector_store: str
    documents_count: int
    chunks_count: int

class SupportedFormatsResponse(BaseModel):
    formats: List[str]
    total: int

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
