from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )

    def chunk_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Разбивает документ на чанки с помощью LangChain"""
        content = document["content"]

        # Создаем документы с метаданными
        docs = self.text_splitter.create_documents(
            texts=[content],
            metadatas=[{
                "filename": document["filename"],
                "source": document["metadata"].get("source", "")
            }]
        )

        chunks = []
        for i, doc in enumerate(docs):
            chunks.append({
                "content": doc.page_content,
                "metadata": {
                    "filename": document["filename"],
                    "chunk_index": i,
                    "total_chunks": len(docs),
                    **doc.metadata
                }
            })

        return chunks