from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from dotenv import load_dotenv

from app.routers import documents, qa
from app.models.schemas import ErrorResponse, HealthResponse
from app.services.rag import RAGService
from datetime import datetime

load_dotenv(dotenv_path=".env", verbose=True)

app = FastAPI(
    title="Document RAG API",
    description="API для загрузки документов и вопрос-ответ на основе RAG с использованием MarkItDown",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрация роутеров
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(qa.router, prefix="/api/v1", tags=["qa"])

# Глобальный обработчик ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            detail=str(exc),
            error_code="INTERNAL_ERROR"
        ).model_dump()
    )

@app.get("/", response_model=dict)
async def root():
    return {
        "message": "Document RAG API with MarkItDown",
        "docs": "/docs",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/api/v1/upload",
            "documents": "/api/v1/documents",
            "ask": "/api/v1/ask",
            "history": "/api/v1/history"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка состояния сервиса"""
    rag_service = RAGService()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now(),
        vector_store="PGVector",
        documents_count=rag_service.get_documents_count(),
        chunks_count=rag_service.get_chunks_count()
    )

@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Document RAG API with MarkItDown...")
    print(f"📁 Working directory: {os.getcwd()}")
    print("✅ API ready!")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )