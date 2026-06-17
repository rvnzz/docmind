from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import List, Optional
import os
import uuid

from app.services.parser import DocumentParser
from app.services.chunker import DocumentChunker
from app.services.rag import RAGService
from app.services.storage import LocalStorageManager
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
    SupportedFormatsResponse,
    DocumentMetadata,
)

router = APIRouter()
rag = RAGService()
chunker = DocumentChunker()
parser = DocumentParser()
storage = LocalStorageManager()

@router.post("/upload", response_model=DocumentUploadResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def upload_document(file: UploadFile = File(...)):
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in parser.get_supported_formats():
            raise HTTPException(400, f"Unsupported: {ext}")

        content = await file.read()
        fname = f"{uuid.uuid4()}_{file.filename}"
        fpath = storage.save_file(fname, content)

        try:
            doc = parser.parse_document(fpath)
            if not doc.get("content"):
                raise HTTPException(400, "Failed to extract content")

            chunks = chunker.chunk_document(doc)
            doc_id = rag.process_document(doc, chunks, fpath)

            return DocumentUploadResponse(
                id=doc_id,
                filename=file.filename,
                status=DocumentStatus.COMPLETED,
                chunks_created=len(chunks),
                content_length=len(doc["content"]),
                file_type=DocumentType(doc["file_type"]),
                message="OK",
                metadata=DocumentMetadata(**{
                    "source": fpath,
                    "file_size": len(content),
                    "title": doc.get("metadata", {}).get("title"),
                    "author": doc.get("metadata", {}).get("author"),
                })
            )
        except HTTPException:
            storage.delete_file(fpath)
            raise
        except:
            storage.delete_file(fpath)
            raise

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/upload-batch", response_model=BatchUploadResponse, responses={500: {"model": ErrorResponse}})
async def upload_batch(files: List[UploadFile] = File(...)):
    results = []
    errors = []

    for f in files:
        fpath = None
        try:
            content = await f.read()
            fname = f"{uuid.uuid4()}_{f.filename}"
            fpath = storage.save_file(fname, content)

            doc = parser.parse_document(fpath)
            chunks = chunker.chunk_document(doc)
            doc_id = rag.process_document(doc, chunks, fpath)

            results.append(UploadFileResponse(
                id=doc_id,
                filename=f.filename,
                status=DocumentStatus.COMPLETED,
                chunks_created=len(chunks),
                message="OK"
            ))
        except Exception as e:
            if fpath:
                storage.delete_file(fpath)
            errors.append({"filename": f.filename, "error": str(e)})

    return BatchUploadResponse(
        total=len(files),
        success=len(results),
        errors=len(errors),
        results=results,
        error_details=errors
    )

@router.get("/documents", response_model=DocumentListResponse, responses={500: {"model": ErrorResponse}})
async def list_documents(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), status: Optional[DocumentStatus] = None, file_type: Optional[DocumentType] = None):
    try:
        offset = (page - 1) * limit
        docs, total = rag.get_all_documents(
            limit=limit,
            offset=offset,
            status=status.value if status else None,
            file_type=file_type.value if file_type else None,
        )

        items = []
        for d in docs:
            items.append(DocumentResponse(
                id=d["id"],
                filename=d["filename"],
                file_type=DocumentType(d["file_type"]),
                content_length=d["content_length"],
                chunks_count=d["chunks_count"],
                metadata=d.get("metadata", {}),
                status=DocumentStatus(d["status"]),
                created_at=d["created_at"],
                updated_at=d.get("updated_at") or d["created_at"],
                processed_at=d.get("processed_at")
            ))

        return DocumentListResponse(total=total, documents=items, page=page, limit=limit)
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/documents/{doc_id}", response_model=DocumentResponse, responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def get_document(doc_id: str):
    try:
        d = rag.get_document_info(doc_id)
        if not d:
            raise HTTPException(404, "Not found")

        return DocumentResponse(
            id=d["id"],
            filename=d["filename"],
            file_type=DocumentType(d["file_type"]),
            content_length=d["content_length"],
            chunks_count=d["chunks_count"],
            metadata=d.get("metadata", {}),
            status=DocumentStatus(d["status"]),
            created_at=d["created_at"],
            updated_at=d.get("updated_at") or d["created_at"],
            processed_at=d.get("processed_at")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.delete("/documents/{doc_id}", response_model=DocumentDeleteResponse, responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def delete_document(doc_id: str):
    try:
        d = rag.get_document_info(doc_id)
        if not d:
            raise HTTPException(404, "Not found")

        ok = rag.delete_document(doc_id)
        if not ok:
            raise HTTPException(500, "Delete failed")

        return DocumentDeleteResponse(id=doc_id, filename=d["filename"], status="deleted", message="OK")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/supported-formats", response_model=SupportedFormatsResponse)
async def get_supported_formats():
    fmts = parser.get_supported_formats()
    return SupportedFormatsResponse(formats=fmts, total=len(fmts))

@router.post("/documents/search", response_model=DocumentListResponse, responses={500: {"model": ErrorResponse}})
async def search_documents(req: DocumentSearchRequest):
    try:
        offset = (req.page - 1) * req.limit
        docs, total = rag.search_documents(
            req.query or "",
            status=req.status.value if req.status else None,
            file_type=req.file_type.value if req.file_type else None,
        )

        paginated = docs[offset:offset + req.limit]

        items = []
        for d in paginated:
            items.append(DocumentResponse(
                id=d["id"],
                filename=d["filename"],
                file_type=DocumentType(d["file_type"]),
                content_length=d["content_length"],
                chunks_count=d["chunks_count"],
                metadata=d.get("metadata", {}),
                status=DocumentStatus(d["status"]),
                created_at=d["created_at"],
                updated_at=d.get("updated_at") or d["created_at"],
                processed_at=d.get("processed_at")
            ))

        return DocumentListResponse(total=total, documents=items, page=req.page, limit=req.limit)
    except Exception as e:
        raise HTTPException(500, str(e))
