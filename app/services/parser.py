import os
from typing import Dict, Any, List
from markitdown import MarkItDown


class DocumentParser:
    def __init__(self):
        self.markitdown = MarkItDown()

    def parse_document(self, file_path: str) -> Dict[str, Any]:
        """Парсит документ из файловой системы и возвращает содержимое с метаданными"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_extension = os.path.splitext(file_path)[1].lower()

        try:
            # Используем markitdown для парсинга
            result = self.markitdown.convert(file_path)
            content = result.text_content

            # Дополнительная обработка для разных форматов
            if file_extension == '.pdf':
                content = self._post_process_pdf(content)
            elif file_extension == '.docx':
                content = self._post_process_docx(content)

            return {
                "content": content,
                "filename": os.path.basename(file_path),
                "file_type": file_extension[1:] if file_extension else "unknown",
                "metadata": {
                    "source": file_path,
                    "file_size": os.path.getsize(file_path),
                    "title": result.metadata.get("title") if hasattr(result, "metadata") else None,
                    "author": result.metadata.get("author") if hasattr(result, "metadata") else None,
                }
            }
        except Exception as e:
            raise ValueError(f"Error parsing document {file_path}: {str(e)}")

    def _post_process_pdf(self, content: str) -> str:
        """Постобработка PDF контента"""
        # Удаляем лишние пробелы и нормализуем
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.isspace():
                cleaned_lines.append(line)
        return '\n'.join(cleaned_lines)

    def _post_process_docx(self, content: str) -> str:
        """Постобработка DOCX контента"""
        # Нормализуем пробелы и разрывы строк
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        return content

    def parse_batch(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Парсит несколько документов"""
        results = []
        for file_path in file_paths:
            try:
                result = self.parse_document(file_path)
                results.append(result)
            except Exception as e:
                results.append({
                    "error": str(e),
                    "filename": os.path.basename(file_path),
                    "content": None
                })
        return results

    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Извлекает метаданные из документа"""
        try:
            result = self.markitdown.convert(file_path)
            metadata = {
                "filename": os.path.basename(file_path),
                "file_size": os.path.getsize(file_path),
                "file_type": os.path.splitext(file_path)[1].lower(),
            }

            # Добавляем метаданные из markitdown если доступны
            if hasattr(result, "metadata"):
                for key, value in result.metadata.items():
                    if value:
                        metadata[key] = value

            return metadata
        except Exception as e:
            return {
                "filename": os.path.basename(file_path),
                "error": str(e)
            }

    def get_supported_formats(self) -> List[str]:
        """Возвращает список поддерживаемых форматов"""
        return [
            '.pdf', '.docx', '.txt', '.md',
            '.html', '.htm', '.xlsx', '.xls',
            '.pptx', '.ppt', '.csv', '.json',
            '.xml', '.zip'
        ]