from fastapi import APIRouter, HTTPException, Query
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
rag = RAGService()

@router.post("/ask", response_model=AnswerResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def ask_question(req: QuestionRequest):
    try:
        res = rag.answer_question(
            question=req.question,
            top_k=req.top_k,
            document_ids=req.document_ids,
            include_sources=req.include_sources
        )

        sources = []
        for s in res.get("sources", []):
            sources.append(SourceInfo(
                document_id=s.get("document_id", ""),
                filename=s.get("filename", ""),
                chunk_index=s.get("chunk_index", 0),
                content=s.get("content", ""),
                similarity_score=s.get("similarity_score")
            ))

        return AnswerResponse(
            id=res.get("id", ""),
            question=req.question,
            answer=res.get("answer", ""),
            sources=sources,
            confidence=res.get("confidence"),
            processing_time_ms=res.get("processing_time_ms"),
            created_at=res.get("created_at", datetime.now())
        )
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/history", response_model=ChatHistoryResponse, responses={500: {"model": ErrorResponse}})
async def get_history(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    try:
        res = rag.get_answer_history(limit, (page - 1) * limit)

        history = []
        for item in res.get("history", []):
            sources = []
            for s in item.get("sources", []):
                sources.append(SourceInfo(
                    document_id=s.get("document_id", ""),
                    filename=s.get("filename", ""),
                    chunk_index=s.get("chunk_index", 0),
                    content=s.get("content", ""),
                    similarity_score=s.get("similarity_score")
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

        return ChatHistoryResponse(total=res.get("total", 0), history=history, page=page, limit=limit)
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/history/{answer_id}", response_model=AnswerResponse, responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def get_answer(answer_id: str):
    try:
        item = rag.get_answer(answer_id)
        if not item:
            raise HTTPException(404, "Not found")

        sources = []
        for s in item.get("sources", []):
            sources.append(SourceInfo(
                document_id=s.get("document_id", ""),
                filename=s.get("filename", ""),
                chunk_index=s.get("chunk_index", 0),
                content=s.get("content", ""),
                similarity_score=s.get("similarity_score")
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
