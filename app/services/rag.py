from typing import Dict, Any, List, Optional
import os
import time
from langchain_anthropic import ChatAnthropic
from app.db.vector_store import VectorStoreManager
from app.db.database import get_db
from app.db.repository import DocumentRepository
from app.db.models import DocumentStatus, DocumentType
from app.services.embedder import EmbeddingService
from app.services.storage import LocalStorageManager

class RAGService:
    def __init__(self):
        self.model = ChatAnthropic(
            model_name=os.getenv("MODEL_NAME"),
            base_url=os.getenv("BASE_URL"),
            api_key=os.getenv("API_KEY"),
        )
        self.embedder = EmbeddingService()
        self.vector_store = VectorStoreManager(self.embedder.embedding_model)
        self.storage = LocalStorageManager()

    def process_document(self, document, chunks, file_path):
        with get_db() as db:
            repo = DocumentRepository(db)

            doc_data = {
                "filename": document["filename"],
                "file_type": document["file_type"],
                "file_path": file_path,
                "content": document["content"],
                "title": document.get("metadata", {}).get("title"),
                "author": document.get("metadata", {}).get("author"),
                "metadata": document.get("metadata", {}),
                "chunks_count": len(chunks),
            }

            doc = repo.create_document(doc_data)
            doc_id = doc.id

            try:
                vec_ids = self.vector_store.add_chunks(chunks, doc_id, document["filename"])

                chunk_records = []
                for i, (chunk, vid) in enumerate(zip(chunks, vec_ids)):
                    chunk_records.append({
                        "chunk_index": i,
                        "content": chunk["content"],
                        "vector_id": vid,
                        "metadata": chunk.get("metadata", {}),
                    })

                repo.create_chunks(doc_id, chunk_records)
                repo.update_document_status(doc_id, DocumentStatus.COMPLETED)

            except Exception as e:
                repo.update_document_status(doc_id, DocumentStatus.FAILED, str(e))
                raise

            return doc_id

    def answer_question(self, question, top_k=5, document_ids=None, include_sources=True):
        start = time.time()

        filter_dict = None
        if document_ids:
            filter_dict = {"document_id": {"$in": document_ids}}

        results = self.vector_store.similarity_search(question, k=top_k, filter=filter_dict)

        ctx_parts = []
        sources = []

        for doc, score in results:
            ctx_parts.append(doc.page_content)
            sources.append({
                "document_id": doc.metadata.get("document_id", "unknown"),
                "filename": doc.metadata.get("filename", "unknown"),
                "chunk_index": doc.metadata.get("chunk_index", 0),
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "similarity_score": score
            })

        context = "\n\n---\n\n".join(ctx_parts)

        # TODO: move this to a template file
        prompt = f"""Вы - ассистент, который отвечает на вопросы, используя только предоставленный контекст.

Контекст:
{context}

Вопрос: {question}

Ответьте на вопрос, используя только информацию из контекста. Если в контексте нет информации для ответа, скажите, что не знаете ответа.

Ответ:"""

        resp = self.model.invoke(prompt)
        answer_text = resp.text

        proc_time = (time.time() - start) * 1000

        with get_db() as db:
            repo = DocumentRepository(db)
            answer = repo.create_answer({
                "question": question,
                "answer": answer_text,
                "sources": sources if include_sources else [],
                "processing_time_ms": proc_time,
            })

            return {
                "id": answer.id,
                "question": question,
                "answer": answer_text,
                "sources": sources if include_sources else [],
                "confidence": None,
                "processing_time_ms": proc_time,
                "created_at": answer.created_at
            }

    def get_document_info(self, doc_id):
        with get_db() as db:
            repo = DocumentRepository(db)
            doc = repo.get_document(doc_id)
            if not doc:
                return None
            return self._doc_to_dict(doc)

    def get_all_documents(self, limit=100, offset=0, status=None, file_type=None):
        with get_db() as db:
            repo = DocumentRepository(db)
            status_enum = DocumentStatus(status) if status else None
            type_enum = DocumentType(file_type) if file_type else None
            docs, total = repo.get_all_documents(
                skip=offset,
                limit=limit,
                status=status_enum,
                file_type=type_enum
            )
            return [self._doc_to_dict(d) for d in docs], total

    def get_documents_count(self):
        with get_db() as db:
            from app.db.models import Document
            return db.query(Document).count()

    def get_chunks_count(self):
        with get_db() as db:
            from app.db.models import DocumentChunk
            return db.query(DocumentChunk).count()

    def delete_document(self, doc_id):
        with get_db() as db:
            repo = DocumentRepository(db)
            doc = repo.get_document(doc_id)
            if not doc:
                return False

            if doc.file_path:
                self.storage.delete_file(doc.file_path)

            self.vector_store.delete_chunks_by_document_id(doc_id)
            return repo.delete_document(doc_id)

    def search_documents(self, query, **filters):
        with get_db() as db:
            repo = DocumentRepository(db)
            status_enum = DocumentStatus(filters["status"]) if filters.get("status") else None
            type_enum = DocumentType(filters["file_type"]) if filters.get("file_type") else None
            docs, total = repo.get_all_documents(
                search_query=query if query else None,
                status=status_enum,
                file_type=type_enum
            )
            return [self._doc_to_dict(d) for d in docs], total

    def get_answer_history(self, limit=20, offset=0):
        with get_db() as db:
            repo = DocumentRepository(db)
            answers, total = repo.get_answers(skip=offset, limit=limit)
            return {
                "total": total,
                "history": [self._ans_to_dict(a) for a in answers]
            }

    def get_answer(self, answer_id):
        with get_db() as db:
            repo = DocumentRepository(db)
            ans = repo.get_answer(answer_id)
            if not ans:
                return None
            return self._ans_to_dict(ans)

    def _doc_to_dict(self, doc):
        return {
            "id": doc.id,
            "filename": doc.filename,
            "file_type": doc.file_type.value if doc.file_type else "unknown",
            "file_path": doc.file_path,
            "content_length": doc.content_length,
            "chunks_count": doc.chunks_count,
            "metadata": doc.doc_metadata or {},
            "status": doc.status.value if doc.status else "pending",
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
            "processed_at": doc.processed_at,
            "title": doc.title,
            "author": doc.author,
        }

    def _ans_to_dict(self, ans):
        return {
            "id": ans.id,
            "question": ans.question,
            "answer": ans.answer,
            "sources": ans.sources or [],
            "confidence": ans.confidence,
            "processing_time_ms": ans.processing_time_ms,
            "created_at": ans.created_at,
        }
