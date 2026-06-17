from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import Dict, Any, List, Optional
import os
import tempfile
from datetime import datetime

from app.services.parser import DocumentParser
from app.services.chunker import DocumentChunker
from app.services.rag import RAGService
from app.models.schemas import (
    DocumentResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    DocumentDeleteResponse,
    BatchUploadResponse,
    UploadFileResponse,
    DocumentSearchRequest,
    DocumentType,
    DocumentStatus,
    ErrorResponse,
    SupportedFormatsResponse
)

router = APIRouter()
rag_service = RAGService()
chunker = DocumentChunker()
parser = DocumentParser()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def upload_document(
        file: UploadFile = File(...)
) -> DocumentUploadResponse:
    """Загружает документ и обрабатывает его"""
    temp_file_path = None

    try:
        # Проверяем расширение файла
        file_extension = os.path.splitext(file.filename)[1].lower()
        supported_formats = parser.get_supported_formats()

        if file_extension not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {file_extension}. Supported: {', '.join(supported_formats)}"
            )

        # Сохраняем загруженный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            temp_file_path = tmp_file.name

        # Парсим документ
        document = parser.parse_document(temp_file_path)

        if not document.get("content"):
            raise HTTPException(
                status_code=400,
                detail="Failed to extract content from document"
            )

        # Разбиваем на чанки
        chunks = chunker.chunk_document(document)

        # Добавляем в RAG с сохранением
        doc_id = rag_service.process_document(document, chunks)

        return DocumentUploadResponse(
            id=doc_id,
            filename=file.filename,
            status=DocumentStatus.COMPLETED,
            chunks_created=len(chunks),
            content_length=len(document["content"]),
            file_type=DocumentType(document["file_type"]),
            message="Document processed successfully",
            metadata=document.get("metadata", {})
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass


@router.post(
    "/upload-batch",
    response_model=BatchUploadResponse,
    responses={500: {"model": ErrorResponse}}
)
async def upload_batch(
        files: List[UploadFile] = File(...)
) -> BatchUploadResponse:
    """Загружает несколько документов"""
    results = []
    errors = []

    for file in files:
        temp_file_path = None
        try:
            file_extension = os.path.splitext(file.filename)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                temp_file_path = tmp_file.name

            document = parser.parse_document(temp_file_path)
            chunks = chunker.chunk_document(document)
            doc_id = rag_service.process_document(document, chunks)

            results.append(UploadFileResponse(
                id=doc_id,
                filename=file.filename,
                status=DocumentStatus.COMPLETED,
                chunks_created=len(chunks),
                message="Document processed successfully"
            ))
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass

    return BatchUploadResponse(
        total=len(files),
        success=len(results),
        errors=len(errors),
        results=results,
        error_details=errors
    )


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    responses={500: {"model": ErrorResponse}}
)
async def list_documents(
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        status: Optional[DocumentStatus] = None,
        file_type: Optional[DocumentType] = None
) -> DocumentListResponse:
    """Список всех документов с фильтрацией"""
    try:
        # Фильтрация
        filters = {}
        if status:
            filters["status"] = status
        if file_type:
            filters["file_type"] = file_type

        offset = (page - 1) * limit
        docs = rag_service.get_all_documents(limit, offset)

        # Применяем фильтры (в реальном приложении фильтрация в БД)
        if filters:
            docs = [d for d in docs if all(d.get(k) == v for k, v in filters.items())]

        documents = []
        for doc in docs:
            documents.append(DocumentResponse(
                id=doc.get("id", ""),
                filename=doc.get("filename", ""),
                file_type=DocumentType(doc.get("file_type", "unknown")),
                content_length=doc.get("content_length", 0),
                chunks_count=doc.get("chunks_count", 0),
                metadata=doc.get("metadata", {}),
                status=DocumentStatus(doc.get("status", "pending")),
                created_at=doc.get("created_at", datetime.now()),
                updated_at=doc.get("updated_at", datetime.now()),
                processed_at=doc.get("processed_at")
            ))

        return DocumentListResponse(
            total=rag_service.get_documents_count(),
            documents=documents,
            page=page,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_document(document_id: str) -> DocumentResponse:
    """Получает информацию о документе"""
    try:
        doc = rag_service.get_document_info(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        return DocumentResponse(
            id=doc.get("id", ""),
            filename=doc.get("filename", ""),
            file_type=DocumentType(doc.get("file_type", "unknown")),
            content_length=doc.get("content_length", 0),
            chunks_count=doc.get("chunks_count", 0),
            metadata=doc.get("metadata", {}),
            status=DocumentStatus(doc.get("status", "pending")),
            created_at=doc.get("created_at", datetime.now()),
            updated_at=doc.get("updated_at", datetime.now()),
            processed_at=doc.get("processed_at")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/documents/{document_id}",
    response_model=DocumentDeleteResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def delete_document(document_id: str) -> DocumentDeleteResponse:
    """Удаляет документ"""
    try:
        doc = rag_service.get_document_info(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        success = rag_service.delete_document(document_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete document")

        return DocumentDeleteResponse(
            id=document_id,
            filename=doc.get("filename", ""),
            status="deleted",
            message=f"Document {document_id} deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/supported-formats",
    response_model=SupportedFormatsResponse
)
async def get_supported_formats() -> SupportedFormatsResponse:
    """Возвращает список поддерживаемых форматов"""
    return SupportedFormatsResponse(
        formats=parser.get_supported_formats(),
        total=len(parser.get_supported_formats())
    )


@router.post(
    "/documents/search",
    response_model=DocumentListResponse,
    responses={500: {"model": ErrorResponse}}
)
async def search_documents(request: DocumentSearchRequest) -> DocumentListResponse:
    """Поиск документов по различным критериям"""
    try:
        filters = {}
        if request.file_type:
            filters["file_type"] = request.file_type
        if request.status:
            filters["status"] = request.status

        offset = (request.page - 1) * request.limit
        docs = rag_service.search_documents(
            request.query or "",
            **filters
        )

        # Пагинация
        paginated_docs = docs[offset:offset + request.limit]

        documents = []
        for doc in paginated_docs:
            documents.append(DocumentResponse(
                id=doc.get("id", ""),
                filename=doc.get("filename", ""),
                file_type=DocumentType(doc.get("file_type", "unknown")),
                content_length=doc.get("content_length", 0),
                chunks_count=doc.get("chunks_count", 0),
                metadata=doc.get("metadata", {}),
                status=DocumentStatus(doc.get("status", "pending")),
                created_at=doc.get("created_at", datetime.now()),
                updated_at=doc.get("updated_at", datetime.now()),
                processed_at=doc.get("processed_at")
            ))

        return DocumentListResponse(
            total=len(docs),
            documents=documents,
            page=request.page,
            limit=request.limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))