# 📄 DocMind — AI-сервис для анализа документов

> Загружай PDF и текстовые файлы — задавай вопросы на естественном языке. Powered by RAG (Retrieval-Augmented Generation).

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?logo=fastapi)
![OpenAI](https://img.shields.io/badge/OpenAI-Embeddings-412991?logo=openai)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-orange)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)

---

## 🎯 Что умеет сервис

- 📤 **Загрузка документов** — поддержка PDF, TXT, DOCX
- 🔍 **Семантический поиск** — находит релевантные фрагменты через векторные эмбеддинги
- 🤖 **AI-ответы** — GPT-4o отвечает на основе содержимого документа, а не выдумывает
- 📚 **Мультидокументность** — работа с несколькими файлами одновременно
- 🌐 **REST API** — готовый FastAPI-бэкенд с документацией Swagger
- 🖥️ **Веб-интерфейс** — простой UI на Streamlit для демонстрации

---

## 🏗️ Архитектура

```
┌─────────────────┐     ┌──────────────────────────────────────────┐
│   Streamlit UI  │────▶│              FastAPI Backend              │
└─────────────────┘     │                                          │
                        │  ┌─────────────┐   ┌──────────────────┐ │
                        │  │  /upload    │   │    /ask          │ │
                        │  │  Парсинг    │   │  Поиск чанков    │ │
                        │  │  Чанкинг    │   │  + GPT-4o ответ  │ │
                        │  └──────┬──────┘   └───────┬──────────┘ │
                        └─────────┼────────────────────┼───────────┘
                                  │                    │
                        ┌─────────▼──────────────────────────────┐
                        │           ChromaDB (Vector Store)       │
                        │   document_id │ chunk_text │ embedding  │
                        └────────────────────────────────────────┘
                                                 │
                                    ┌────────────▼─────────────┐
                                    │   OpenAI API             │
                                    │  text-embedding-3-small  │
                                    │  gpt-4o                  │
                                    └──────────────────────────┘
```

---

## 🚀 Быстрый старт

### Вариант 1 — через Docker (рекомендуется)

```bash
git clone https://github.com/yourusername/docmind.git
cd docmind

cp .env.example .env
# Добавь OPENAI_API_KEY в .env

docker-compose up --build
```

Сервис доступен по адресам:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Streamlit UI: http://localhost:8501

### Вариант 2 — локально

```bash
git clone https://github.com/yourusername/docmind.git
cd docmind

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Добавь OPENAI_API_KEY в .env

# Запуск API
uvicorn app.main:app --reload

# Запуск UI (в отдельном терминале)
streamlit run ui/app.py
```

---

## 📁 Структура проекта

```
docmind/
├── app/
│   ├── main.py              # FastAPI приложение
│   ├── routers/
│   │   ├── documents.py     # Эндпоинты загрузки
│   │   └── qa.py            # Эндпоинты вопрос-ответ
│   ├── services/
│   │   ├── parser.py        # Парсинг PDF, DOCX, TXT
│   │   ├── chunker.py       # Разбивка на чанки
│   │   ├── embedder.py      # Создание эмбеддингов
│   │   └── rag.py           # RAG-логика: поиск + генерация
│   ├── db/
│   │   └── vector_store.py  # Работа с ChromaDB
│   └── models/
│       └── schemas.py       # Pydantic-схемы
├── ui/
│   └── app.py               # Streamlit-интерфейс
├── tests/
│   ├── test_parser.py
│   ├── test_embedder.py
│   └── test_rag.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## 📡 API Reference

### Загрузка документа

```http
POST /documents/upload
Content-Type: multipart/form-data

file: <binary>
```

**Ответ:**
```json
{
  "document_id": "doc_abc123",
  "filename": "contract.pdf",
  "chunks_count": 42,
  "status": "indexed"
}
```

### Задать вопрос

```http
POST /qa/ask
Content-Type: application/json

{
  "document_id": "doc_abc123",
  "question": "Каковы условия расторжения договора?",
  "top_k": 5
}
```

**Ответ:**
```json
{
  "answer": "Согласно разделу 8.2, договор может быть расторгнут...",
  "sources": [
    {
      "chunk_id": "chunk_017",
      "text": "8.2. Стороны вправе расторгнуть настоящий договор...",
      "page": 12,
      "relevance_score": 0.94
    }
  ]
}
```

### Список документов

```http
GET /documents/
```

### Удалить документ

```http
DELETE /documents/{document_id}
```

---

## ⚙️ Переменные окружения

| Переменная | Описание | Пример |
|---|---|---|
| `OPENAI_API_KEY` | Ключ OpenAI API | `sk-...` |
| `EMBEDDING_MODEL` | Модель для эмбеддингов | `text-embedding-3-small` |
| `CHAT_MODEL` | Модель для ответов | `gpt-4o` |
| `CHUNK_SIZE` | Размер чанка в токенах | `500` |
| `CHUNK_OVERLAP` | Перекрытие чанков | `50` |
| `TOP_K_RESULTS` | Кол-во чанков для контекста | `5` |
| `CHROMA_PERSIST_DIR` | Папка для ChromaDB | `./chroma_db` |

---

## 🔧 Как работает RAG

```
1. UPLOAD
   Документ → Парсинг текста → Разбивка на чанки (500 токенов)
                                        ↓
                              OpenAI Embeddings API
                                        ↓
                              Сохранение в ChromaDB

2. ASK
   Вопрос → Эмбеддинг вопроса → Cosine Similarity поиск в ChromaDB
                                        ↓
                              Топ-5 релевантных чанков
                                        ↓
                   Промпт: "Контекст: {чанки} Вопрос: {вопрос}"
                                        ↓
                                    GPT-4o
                                        ↓
                                 Финальный ответ
```

---

## 🧪 Тесты

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=app tests/

# Конкретный модуль
pytest tests/test_rag.py -v
```

---

## 🛠️ Стек технологий

| Категория | Технология |
|---|---|
| Backend | FastAPI, Uvicorn, Pydantic |
| AI / LLM | OpenAI GPT-4o, text-embedding-3-small |
| Vector DB | ChromaDB |
| Парсинг | PyMuPDF, python-docx |
| UI | Streamlit |
| Контейнеризация | Docker, Docker Compose |
| Тесты | Pytest |

---

## 📈 Планы по развитию

- [ ] Поддержка веб-страниц (URL → индексация)
- [ ] Стриминг ответов через WebSocket
- [ ] Аутентификация через JWT
- [ ] История диалогов по документу
- [ ] Поддержка локальных моделей (Ollama)
- [ ] Экспорт ответов в PDF

---

## 👨‍💻 Автор

**Твоё Имя** — [@yourusername](https://github.com/yourusername)

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?logo=linkedin)](https://linkedin.com/in/yourprofile)

---

## 📄 Лицензия

MIT License — см. [LICENSE](LICENSE)