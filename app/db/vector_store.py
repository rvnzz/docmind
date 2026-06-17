import os
from typing import List, Dict, Any, Optional
from langchain_postgres import PGVector

class VectorStoreManager:
    def __init__(self, embedding_model, collection_name="docmind"):
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        self.vector_store = PGVector(
            embeddings=embedding_model,
            collection_name=collection_name,
            connection=os.getenv("PGVECTOR_CONNECTION"),
        )

    def add_chunks(self, chunks, document_id, filename):
        texts = [c["content"] for c in chunks]
        metadatas = []
        for i, c in enumerate(chunks):
            meta = {
                **c.get("metadata", {}),
                "document_id": document_id,
                "filename": filename,
                "chunk_index": i
            }
            metadatas.append(meta)
        return self.vector_store.add_texts(texts=texts, metadatas=metadatas)

    def similarity_search(self, query, k=5, filter=None):
        if filter:
            return self.vector_store.similarity_search_with_score(query, k=k, filter=filter)
        return self.vector_store.similarity_search_with_score(query, k=k)

    def delete_chunks_by_document_id(self, document_id):
        try:
            self.vector_store.delete(filter={"document_id": document_id})
            return True
        except:
            return False

    def delete_collection(self):
        self.vector_store.delete_collection()
