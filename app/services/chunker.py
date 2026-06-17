from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentChunker:
    def __init__(self, chunk_size=500, chunk_overlap=100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )

    def chunk_document(self, document):
        content = document["content"]

        docs = self.splitter.create_documents(
            texts=[content],
            metadatas=[{
                "filename": document["filename"],
                "source": document["metadata"].get("source", "")
            }]
        )

        chunks = []
        for i, d in enumerate(docs):
            chunks.append({
                "content": d.page_content,
                "metadata": {
                    "filename": document["filename"],
                    "chunk_index": i,
                    "total_chunks": len(docs),
                    **d.metadata
                }
            })

        return chunks
