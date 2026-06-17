from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib

from .models import Document, DocumentChunk, Answer, DocumentStatus, DocumentType

class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_document(self, data) -> Document:
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
            doc_metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            processed_at=datetime.now()
        )

        self.db.add(doc)
        self.db.flush()
        return doc

    def get_document(self, doc_id) -> Optional[Document]:
        return self.db.query(Document).filter(Document.id == doc_id).first()

    def get_document_by_hash(self, content_hash) -> Optional[Document]:
        return self.db.query(Document).filter(Document.content_hash == content_hash).first()

    def get_all_documents(
        self,
        skip=0,
        limit=100,
        status=None,
        file_type=None,
        search_query=None
    ):
        q = self.db.query(Document)

        if status:
            q = q.filter(Document.status == status)
        if file_type:
            q = q.filter(Document.file_type == file_type)
        if search_query:
            s = f"%{search_query}%"
            q = q.filter(or_(
                Document.filename.ilike(s),
                Document.title.ilike(s),
                Document.author.ilike(s)
            ))

        total = q.count()
        docs = q.order_by(desc(Document.created_at)).offset(skip).limit(limit).all()

        return docs, total

    def update_document(self, doc_id, data) -> Optional[Document]:
        doc = self.get_document(doc_id)
        if not doc:
            return None

        for k, v in data.items():
            if hasattr(doc, k):
                setattr(doc, k, v)

        doc.updated_at = datetime.now()
        self.db.flush()
        return doc

    def delete_document(self, doc_id) -> bool:
        doc = self.get_document(doc_id)
        if not doc:
            return False

        self.db.delete(doc)
        self.db.flush()
        return True

    def update_document_status(self, doc_id, status, error_message=None):
        doc = self.get_document(doc_id)
        if doc:
            doc.status = status
            if error_message:
                doc.error_message = error_message
            if status == DocumentStatus.COMPLETED:
                doc.processed_at = datetime.now()
            self.db.flush()

    def create_chunk(self, doc_id, data) -> DocumentChunk:
        chunk = DocumentChunk(
            document_id=doc_id,
            chunk_index=data["chunk_index"],
            content=data["content"],
            content_length=len(data["content"]),
            vector_id=data.get("vector_id"),
            chunk_metadata=data.get("metadata", {})
        )

        self.db.add(chunk)
        self.db.flush()
        return chunk

    def create_chunks(self, doc_id, chunks) -> List[DocumentChunk]:
        objs = []
        for c in chunks:
            obj = self.create_chunk(doc_id, c)
            objs.append(obj)

        self.update_document(doc_id, {"chunks_count": len(objs)})
        return objs

    def get_chunks(self, doc_id) -> List[DocumentChunk]:
        return self.db.query(DocumentChunk).filter(
            DocumentChunk.document_id == doc_id
        ).order_by(DocumentChunk.chunk_index).all()

    def get_chunk_by_vector_id(self, vector_id) -> Optional[DocumentChunk]:
        return self.db.query(DocumentChunk).filter(DocumentChunk.vector_id == vector_id).first()

    def create_answer(self, data) -> Answer:
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

    def get_answers(self, skip=0, limit=20, document_id=None):
        q = self.db.query(Answer)

        if document_id:
            q = q.filter(Answer.document_id == document_id)

        total = q.count()
        answers = q.order_by(desc(Answer.created_at)).offset(skip).limit(limit).all()

        return answers, total

    def get_answer(self, answer_id) -> Optional[Answer]:
        return self.db.query(Answer).filter(Answer.id == answer_id).first()

    def get_statistics(self):
        total_docs = self.db.query(Document).count()
        total_chunks = self.db.query(DocumentChunk).count()
        total_answers = self.db.query(Answer).count()

        status_stats = {}
        for s in DocumentStatus:
            cnt = self.db.query(Document).filter(Document.status == s).count()
            status_stats[s.value] = cnt

        type_stats = {}
        for t in DocumentType:
            cnt = self.db.query(Document).filter(Document.file_type == t).count()
            type_stats[t.value] = cnt

        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "total_answers": total_answers,
            "by_status": status_stats,
            "by_type": type_stats
        }
