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

    def get_embeddings(self, texts):
        return self.embedding_model.embed_documents(texts)

    def get_embedding(self, text):
        return self.embedding_model.embed_query(text)

    def embed_chunks(self, chunks):
        texts = [c["content"] for c in chunks]
        embeddings = self.get_embeddings(texts)

        for i, c in enumerate(chunks):
            c["embedding"] = embeddings[i]

        return chunks
