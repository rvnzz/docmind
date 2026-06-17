from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib

from .models import Document, DocumentChunk, Answer, DocumentStatus, DocumentType


class DocumentRepository:
    """Репозиторий для работы с документами в БД"""

    def __init__(self, db: Session):
        self.db = db

    # === DOCUMENT OPERATIONS ===

    def create_document(self, data: Dict[str, Any]) -> Document:
        """Создает новый документ"""
        # Вычисляем хеш содержимого для дедупликации
        content_hash = hashlib.sha256(data.get("content", "").encode()).hexdigest()

        doc = Document(
            filename=data["filename"],
            file_type=DocumentType(data.get("file_type", "unknown")),
            file_path=data.get("file_path"),
            content_hash=content_hash,
            title=data.get("title"),
            author=data.get("author"),
            page_count=data.get("page_count"),
            word_count=data.get("word_count"),
            content_length=len(data.get("content", "")),
            chunks_count=data.get("chunks_count", 0),
            status=DocumentStatus.COMPLETED,
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            processed_at=datetime.now()
        )

        self.db.add(doc)
        self.db.flush()
        return doc

    def get_document(self, document_id: str) -> Optional[Document]:
        """Получает документ по ID"""
        return self.db.query(Document).filter(Document.id == document_id).first()

    def get_document_by_hash(self, content_hash: str) -> Optional[Document]:
        """Получает документ по хешу содержимого"""
        return self.db.query(Document).filter(Document.content_hash == content_hash).first()

    def get_all_documents(
            self,
            skip: int = 0,
            limit: int = 100,
            status: Optional[DocumentStatus] = None,
            file_type: Optional[DocumentType] = None,
            search_query: Optional[str] = None
    ) -> tuple[List[Document], int]:
        """Получает список документов с фильтрацией"""
        query = self.db.query(Document)

        # Фильтры
        if status:
            query = query.filter(Document.status == status)
        if file_type:
            query = query.filter(Document.file_type == file_type)
        if search_query:
            search = f"%{search_query}%"
            query = query.filter(
                or_(
                    Document.filename.ilike(search),
                    Document.title.ilike(search),
                    Document.author.ilike(search)
                )
            )

        # Подсчет общего количества
        total = query.count()

        # Пагинация
        documents = query.order_by(desc(Document.created_at)).offset(skip).limit(limit).all()

        return documents, total

    def update_document(self, document_id: str, data: Dict[str, Any]) -> Optional[Document]:
        """Обновляет документ"""
        doc = self.get_document(document_id)
        if not doc:
            return None

        for key, value in data.items():
            if hasattr(doc, key):
                setattr(doc, key, value)

        doc.updated_at = datetime.now()
        self.db.flush()
        return doc

    def delete_document(self, document_id: str) -> bool:
        """Удаляет документ и все связанные записи"""
        doc = self.get_document(document_id)
        if not doc:
            return False

        self.db.delete(doc)
        self.db.flush()
        return True

    def update_document_status(self, document_id: str, status: DocumentStatus, error_message: Optional[str] = None):
        """Обновляет статус документа"""
        doc = self.get_document(document_id)
        if doc:
            doc.status = status
            if error_message:
                doc.error_message = error_message
            if status == DocumentStatus.COMPLETED:
                doc.processed_at = datetime.now()
            self.db.flush()

    # === CHUNK OPERATIONS ===

    def create_chunk(self, document_id: str, data: Dict[str, Any]) -> DocumentChunk:
        """Создает чанк документа"""
        chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=data["chunk_index"],
            content=data["content"],
            content_length=len(data["content"]),
            vector_id=data.get("vector_id"),
            metadata=data.get("metadata", {})
        )

        self.db.add(chunk)
        self.db.flush()
        return chunk

    def create_chunks(self, document_id: str, chunks: List[Dict[str, Any]]) -> List[DocumentChunk]:
        """Создает несколько чанков"""
        chunks_objs = []
        for chunk_data in chunks:
            chunk = self.create_chunk(document_id, chunk_data)
            chunks_objs.append(chunk)

        # Обновляем количество чанков в документе
        self.update_document(document_id, {"chunks_count": len(chunks_objs)})

        return chunks_objs

    def get_chunks(self, document_id: str) -> List[DocumentChunk]:
        """Получает все чанки документа"""
        return self.db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index).all()

    def get_chunk_by_vector_id(self, vector_id: str) -> Optional[DocumentChunk]:
        """Получает чанк по ID в векторной БД"""
        return self.db.query(DocumentChunk).filter(DocumentChunk.vector_id == vector_id).first()

    # === ANSWER OPERATIONS ===

    def create_answer(self, data: Dict[str, Any]) -> Answer:
        """Сохраняет ответ на вопрос"""
        answer = Answer(
            question=data["question"],
            answer=data["answer"],
            document_id=data.get("document_id"),
            confidence=data.get("confidence"),
            processing_time_ms=data.get("processing_time_ms"),
            sources=data.get("sources", [])
        )

        self.db.add(answer)
        self.db.flush()
        return answer

    def get_answers(
            self,
            skip: int = 0,
            limit: int = 20,
            document_id: Optional[str] = None
    ) -> tuple[List[Answer], int]:
        """Получает историю ответов"""
        query = self.db.query(Answer)

        if document_id:
            query = query.filter(Answer.document_id == document_id)

        total = query.count()
        answers = query.order_by(desc(Answer.created_at)).offset(skip).limit(limit).all()

        return answers, total

    def get_answer(self, answer_id: str) -> Optional[Answer]:
        """Получает ответ по ID"""
        return self.db.query(Answer).filter(Answer.id == answer_id).first()

    # === STATISTICS ===

    def get_statistics(self) -> Dict[str, Any]:
        """Получает статистику по документам"""
        total_docs = self.db.query(Document).count()
        total_chunks = self.db.query(DocumentChunk).count()
        total_answers = self.db.query(Answer).count()

        # По статусам
        status_stats = {}
        for status in DocumentStatus:
            count = self.db.query(Document).filter(Document.status == status).count()
            status_stats[status.value] = count

        # По типам
        type_stats = {}
        for doc_type in DocumentType:
            count = self.db.query(Document).filter(Document.file_type == doc_type).count()
            type_stats[doc_type.value] = count

        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "total_answers": total_answers,
            "by_status": status_stats,
            "by_type": type_stats
        }