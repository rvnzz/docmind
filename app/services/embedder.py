from typing import List, Dict, Any
import os
from langchain_litellm.embeddings import LiteLLMEmbeddings


class EmbeddingService:
    def __init__(self):
        self.embedding_model = LiteLLMEmbeddings(
            model=os.getenv("EMBEDDING_MODEL_NAME"),
            api_base=os.getenv("EMBEDDING_BASE_URL"),
            api_key=os.getenv("EMBEDDING_API_KEY"),
        )

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Получает эмбеддинги для списка текстов"""
        return self.embedding_model.embed_documents(texts)

    def get_embedding(self, text: str) -> List[float]:
        """Получает эмбеддинг для одного текста"""
        return self.embedding_model.embed_query(text)

    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Создает эмбеддинги для чанков"""
        texts = [chunk["content"] for chunk in chunks]
        embeddings = self.get_embeddings(texts)

        for i, chunk in enumerate(chunks):
            chunk["embedding"] = embeddings[i]

        return chunks