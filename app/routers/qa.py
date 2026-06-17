from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

from app.services.rag import RAGService
from app.models.schemas import (
    QuestionRequest,
    AnswerResponse,
    ChatHistoryResponse,
    SourceInfo,
    ErrorResponse
)

router = APIRouter()
rag_service = RAGService()


@router.post(
    "/ask",
    response_model=AnswerResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def ask_question(request: QuestionRequest) -> AnswerResponse:
    """Отвечает на вопрос используя RAG"""
    try:
        result = rag_service.answer_question(
            question=request.question,
            top_k=request.top_k,
            document_ids=request.document_ids,
            include_sources=request.include_sources
        )

        sources = []
        for src in result.get("sources", []):
            sources.append(SourceInfo(
                document_id=src.get("document_id", ""),
                filename=src.get("filename", ""),
                chunk_index=src.get("chunk_index", 0),
                content=src.get("content", ""),
                similarity_score=src.get("similarity_score")
            ))

        return AnswerResponse(
            id=result.get("id", ""),
            question=request.question,
            answer=result.get("answer", ""),
            sources=sources,
            confidence=result.get("confidence"),
            processing_time_ms=result.get("processing_time_ms"),
            created_at=result.get("created_at", datetime.now())
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/history",
    response_model=ChatHistoryResponse,
    responses={500: {"model": ErrorResponse}}
)
async def get_history(
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100)
) -> ChatHistoryResponse:
    """Получает историю вопросов и ответов"""
    try:
        result = rag_service.get_answer_history(limit, (page - 1) * limit)

        history = []
        for item in result.get("history", []):
            sources = []
            for src in item.get("sources", []):
                sources.append(SourceInfo(
                    document_id=src.get("document_id", ""),
                    filename=src.get("filename", ""),
                    chunk_index=src.get("chunk_index", 0),
                    content=src.get("content", ""),
                    similarity_score=src.get("similarity_score")
                ))

            history.append(AnswerResponse(
                id=item.get("id", ""),
                question=item.get("question", ""),
                answer=item.get("answer", ""),
                sources=sources,
                confidence=item.get("confidence"),
                processing_time_ms=item.get("processing_time_ms"),
                created_at=item.get("created_at", datetime.now())
            ))

        return ChatHistoryResponse(
            total=result.get("total", 0),
            history=history,
            page=page,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/history/{answer_id}",
    response_model=AnswerResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_answer(answer_id: str) -> AnswerResponse:
    """Получает конкретный ответ по ID"""
    try:
        # В реальном приложении нужно искать в БД
        result = rag_service.get_answer_history(100, 0)
        for item in result.get("history", []):
            if item.get("id") == answer_id:
                sources = []
                for src in item.get("sources", []):
                    sources.append(SourceInfo(
                        document_id=src.get("document_id", ""),
                        filename=src.get("filename", ""),
                        chunk_index=src.get("chunk_index", 0),
                        content=src.get("content", ""),
                        similarity_score=src.get("similarity_score")
                    ))

                return AnswerResponse(
                    id=item.get("id", ""),
                    question=item.get("question", ""),
                    answer=item.get("answer", ""),
                    sources=sources,
                    confidence=item.get("confidence"),
                    processing_time_ms=item.get("processing_time_ms"),
                    created_at=item.get("created_at", datetime.now())
                )

        raise HTTPException(status_code=404, detail="Answer not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))