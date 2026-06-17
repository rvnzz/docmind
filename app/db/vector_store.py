import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from langchain_postgres import PGVector
from langchain_litellm.embeddings import LiteLLMEmbeddings


class VectorStoreManager:
    def __init__(self, embedding_model, collection_name="docmind"):
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        self.vector_store = PGVector(
            embeddings=embedding_model,
            collection_name=collection_name,
            connection=os.getenv("PGVECTOR_CONNECTION"),
        )
        self._documents_cache = {}  # Простой кэш для демонстрации

    def add_document(self, document: Dict[str, Any], chunks: List[Dict[str, Any]]) -> str:
        """Добавляет документ и его чанки в векторное хранилище"""
        doc_id = str(uuid.uuid4())

        # Сохраняем метаданные документа
        self._documents_cache[doc_id] = {
            "id": doc_id,
            "filename": document["filename"],
            "file_type": document["file_type"],
            "content_length": len(document["content"]),
            "chunks_count": len(chunks),
            "metadata": document.get("metadata", {}),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "status": "completed"
        }

        # Добавляем чанки с ID документа
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                **chunk.get("metadata", {}),
                "document_id": doc_id,
                "filename": document["filename"],
                "chunk_index": i
            }
            self.vector_store.add_texts(
                texts=[chunk["content"]],
                metadatas=[chunk_metadata]
            )

        return doc_id

    def add_documents(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Добавляет чанки документов в векторное хранилище (совместимость)"""
        texts = [chunk["content"] for chunk in chunks]
        metadatas = [chunk.get("metadata", {}) for chunk in chunks]
        return self.vector_store.add_texts(
            texts=texts,
            metadatas=metadatas
        )

    def similarity_search(self, query: str, k: int = 5, filter: Optional[Dict] = None):
        """Поиск похожих документов с фильтром"""
        if filter:
            results = self.vector_store.similarity_search_with_score(
                query, k=k, filter=filter
            )
        else:
            results = self.vector_store.similarity_search_with_score(query, k=k)
        return results

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о документе"""
        return self._documents_cache.get(document_id)

    def get_all_documents(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получает список всех документов"""
        docs = list(self._documents_cache.values())
        return docs[offset:offset + limit]

    def get_documents_count(self) -> int:
        """Получает количество документов"""
        return len(self._documents_cache)

    def get_chunks_count(self) -> int:
        """Получает количество чанков"""
        # В реальном приложении нужно делать запрос к БД
        return sum([doc.get("chunks_count", 0) for doc in self._documents_cache.values()])

    def delete_document(self, document_id: str) -> bool:
        """Удаляет документ и его чанки"""
        if document_id in self._documents_cache:
            # В реальном приложении нужно удалять чанки из векторной БД
            del self._documents_cache[document_id]
            return True
        return False

    def delete_collection(self):
        """Удаляет коллекцию"""
        self.vector_store.delete_collection()
        self._documents_cache.clear()

    def search_documents(self, query: str, **filters) -> List[Dict[str, Any]]:
        """Поиск документов с фильтрацией"""
        # Реализация поиска с фильтрацией
        results = []
        for doc_id, doc in self._documents_cache.items():
            # Применяем фильтры
            if "file_type" in filters and doc.get("file_type") != filters["file_type"]:
                continue
            if "status" in filters and doc.get("status") != filters["status"]:
                continue
            results.append(doc)
        return results