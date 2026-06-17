import os
from typing import Dict, Any, List
from markitdown import MarkItDown

class DocumentParser:
    def __init__(self):
        self.markitdown = MarkItDown()

    def parse_document(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        try:
            result = self.markitdown.convert(file_path)
            content = result.text_content

            if ext == '.pdf':
                content = self._clean_pdf(content)
            elif ext == '.docx':
                content = content.replace('\r\n', '\n').replace('\r', '\n')

            return {
                "content": content,
                "filename": os.path.basename(file_path),
                "file_type": ext[1:] if ext else "unknown",
                "metadata": {
                    "source": file_path,
                    "file_size": os.path.getsize(file_path),
                    "title": result.metadata.get("title") if hasattr(result, "metadata") else None,
                    "author": result.metadata.get("author") if hasattr(result, "metadata") else None,
                }
            }
        except Exception as e:
            raise ValueError(f"Error parsing {file_path}: {e}")

    def _clean_pdf(self, content):
        lines = content.split('\n')
        cleaned = []
        for line in lines:
            line = line.strip()
            if line and not line.isspace():
                cleaned.append(line)
        return '\n'.join(cleaned)

    def parse_batch(self, file_paths):
        results = []
        for fp in file_paths:
            try:
                r = self.parse_document(fp)
                results.append(r)
            except Exception as e:
                results.append({
                    "error": str(e),
                    "filename": os.path.basename(fp),
                    "content": None
                })
        return results

    def extract_metadata(self, file_path):
        try:
            result = self.markitdown.convert(file_path)
            meta = {
                "filename": os.path.basename(file_path),
                "file_size": os.path.getsize(file_path),
                "file_type": os.path.splitext(file_path)[1].lower(),
            }

            if hasattr(result, "metadata"):
                for k, v in result.metadata.items():
                    if v:
                        meta[k] = v

            return meta
        except Exception as e:
            return {"filename": os.path.basename(file_path), "error": str(e)}

    def get_supported_formats(self):
        return ['.pdf', '.docx', '.txt', '.md', '.html', '.htm', '.xlsx', '.xls', '.pptx', '.ppt', '.csv', '.json', '.xml', '.zip']
