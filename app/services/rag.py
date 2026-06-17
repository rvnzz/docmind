from typing import Dict, Any, List, Optional, Union
import os
import uuid
from datetime import datetime
import time
from langchain_anthropic import ChatAnthropic
from app.db.vector_store import VectorStoreManager
from app.services.embedder import EmbeddingService


class RAGService:
    def __init__(self):
        self.model = ChatAnthropic(
            model_name=os.getenv("MODEL_NAME"),
            base_url=os.getenv("BASE_URL"),
            api_key=os.getenv("API_KEY"),
        )
        self.embedder = EmbeddingService()
        self.vector_store = VectorStoreManager(self.embedder.embedding_model)
        self._answer_history = []  # Простое хранилище истории


    def process_document(self, document: Dict[str, Any], chunks: List[Dict[str, Any]]) -> str:
        """Добавляет документ в векторное хранилище и возвращает ID"""
        return self.vector_store.add_document(document, chunks)

    def answer_question(self, question: str, top_k: int = 5,
                        document_ids: Optional[List[str]] = None,
                        include_sources: bool = True) -> Dict[str, Any]:
        """Отвечает на вопрос используя RAG"""
        start_time = time.time()

        # Фильтр по документам
        filter_dict = None
        if document_ids:
            filter_dict = {"document_id": {"$in": document_ids}}

        # Поиск релевантных документов
        results = self.vector_store.similarity_search(
            question, k=top_k, filter=filter_dict
        )

        # Подготовка контекста и источников
        context_parts = []
        sources = []

        for doc, score in results:
            context_parts.append(doc.page_content)
            sources.append({
                "document_id": doc.metadata.get("document_id", "unknown"),
                "filename": doc.metadata.get("filename", "unknown"),
                "chunk_index": doc.metadata.get("chunk_index", 0),
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "similarity_score": score
            })

        context = "\n\n---\n\n".join(context_parts)

        # Формирование промпта
        prompt = f"""Вы - ассистент, который отвечает на вопросы, используя только предоставленный контекст.

        Контекст:
        {context}

        Вопрос: {question}

        Ответьте на вопрос, используя только информацию из контекста. Если в контексте нет информации для ответа, скажите, что не знаете ответа.

        Ответ:"""

        # Генерация ответа
        response = self.model.invoke(prompt)
        answer_text = response.text

        # Сохраняем в историю
        answer_id = str(uuid.uuid4())
        answer_data = {
            "id": answer_id,
            "question": question,
            "answer": answer_text,
            "sources": sources if include_sources else [],
            "confidence": None,
            "processing_time_ms": (time.time() - start_time) * 1000,
            "created_at": datetime.now()
        }
        self._answer_history.append(answer_data)

        return answer_data

    def get_document_info(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о документе"""
        return self.vector_store.get_document(document_id)

    def get_all_documents(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получает список всех документов"""
        return self.vector_store.get_all_documents(limit, offset)

    def get_documents_count(self) -> int:
        """Получает количество документов"""
        return self.vector_store.get_documents_count()

    def get_chunks_count(self) -> int:
        """Получает количество чанков"""
        return self.vector_store.get_chunks_count()

    def delete_document(self, document_id: str) -> bool:
        """Удаляет документ"""
        return self.vector_store.delete_document(document_id)

    def search_documents(self, query: str, **filters) -> List[Dict[str, Any]]:
        """Поиск документов"""
        return self.vector_store.search_documents(query, **filters)

    def get_answer_history(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """Получает историю ответов"""
        history = self._answer_history[-limit - offset:offset + limit] if self._answer_history else []
        return {
            "total": len(self._answer_history),
            "history": history
        }