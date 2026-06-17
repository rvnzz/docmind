# DocMind

Система для анализа документов с использованием RAG (Retrieval-Augmented Generation). Загружаешь документы, задаёшь вопросы на естественном языке - получаешь ответы на основе содержимого.

## Стек

- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **База данных**: PostgreSQL + PGVector (векторное расширение)
- **LLM**: Anthropic Claude через LiteLLM для чата, LiteLLM для эмбеддингов
- **Парсинг**: markitdown (PDF, DOCX, TXT, XLSX, PPTX, HTML и т.д.)
- **Чанкинг**: LangChain RecursiveCharacterTextSplitter
- **UI**: Streamlit
- **Хранение файлов**: локальная файловая система (DOCUMENTS_DIR)

## Установка и запуск

```bash
# Запускаем PostgreSQL с PGVector
docker-compose up -d

# Устанавливаем зависимости
uv sync

# Копируем пример .env и заполняем своими ключами
cp .env.example .env

# Запускаем API
uv run app/main.py

# В отдельном терминале запускаем UI
streamlit run ui/app.py
```

API: http://localhost:8000  
Swagger: http://localhost:8000/docs  
UI: http://localhost:8501

## Переменные окружения

| Переменная | Описание | Пример |
|---|---|---|
| `PGVECTOR_CONNECTION` | Строка подключения к PostgreSQL | `postgresql+psycopg://postgres:password@localhost:5432/docmind` |
| `DATABASE_URL` | URL для SQLAlchemy (если не указан, используется PGVECTOR_CONNECTION) | |
| `DOCUMENTS_DIR` | Папка для хранения загруженных файлов | `./documents` |
| `MODEL_NAME` | Модель Anthropic для чата | `claude-sonnet-4-20250514` |
| `BASE_URL` | Base URL для Anthropic API | `https://api.anthropic.com` |
| `API_KEY` | API ключ Anthropic | `sk-ant-...` |
| `EMBEDDING_MODEL_NAME` | Модель для эмбеддингов | `text-embedding-3-small` |
| `EMBEDDING_BASE_URL` | Base URL для embedding API | |
| `EMBEDDING_API_KEY` | API ключ для embedding API | |

## Архитектура

```mermaid
graph TB
    subgraph "Клиенты"
        UI[Streamlit UI]
        API_Client[API Client]
    end
    
    subgraph "FastAPI Backend"
        Router_Doc[Documents Router]
        Router_QA[QA Router]
        RAG[RAG Service]
    end
    
    subgraph "Сервисы"
        Parser[Document Parser<br/>markitdown]
        Chunker[Document Chunker<br/>LangChain]
        Embedder[Embedding Service<br/>LiteLLM]
        Storage[Local Storage<br/>FileSystem]
    end
    
    subgraph "База данных"
        PG[(PostgreSQL)]
        PGVec[(PGVector)]
        Tables[documents<br/>document_chunks<br/>answers]
    end
    
    subgraph "Внешние API"
        Anthropic[Anthropic Claude]
        EmbedAPI[Embedding API]
    end
    
    UI --> Router_Doc
    UI --> Router_QA
    API_Client --> Router_Doc
    API_Client --> Router_QA
    
    Router_Doc --> RAG
    Router_QA --> RAG
    
    RAG --> Parser
    RAG --> Chunker
    RAG --> Embedder
    RAG --> Storage
    RAG --> PG
    RAG --> PGVec
    
    Parser --> Storage
    Chunker --> Embedder
    Embedder --> EmbedAPI
    RAG --> Anthropic
    
    PG --> Tables
    PGVec --> Vectors[(Векторы)]
```

## Компоненты системы

### 1. Routers (app/routers/)

**documents.py** - endpoints для работы с документами:
- Загрузка одного или нескольких файлов
- Получение списка документов с фильтрацией и пагинацией
- Получение информации о конкретном документе
- Удаление документов (файл + метаданные + векторы)
- Поиск документов по имени/автору

**qa.py** - endpoints для вопрос-ответа:
- Отправка вопроса и получение ответа с источниками
- Получение истории вопросов и ответов
- Получение конкретного ответа по ID

### 2. Services (app/services/)

**parser.py** - парсинг документов:
- Использует markitdown для извлечения текста из PDF, DOCX, XLSX, PPTX и т.д.
- Извлекает метаданные (автор, заголовок, размер файла)
- Постобработка для PDF (удаление лишних пробелов) и DOCX (нормализация переносов строк)

**chunker.py** - разбивка на чанки:
- LangChain RecursiveCharacterTextSplitter
- Дефолтные параметры: chunk_size=500, chunk_overlap=100
- Каждый чанк получает метаданные: filename, chunk_index, total_chunks

**embedder.py** - создание эмбеддингов:
- LiteLLM для генерации векторных представлений
- Поддержка разных embedding моделей через конфигурацию

**rag.py** - основная логика RAG:
- Обработка документов: сохранение в БД, чанкинг, эмбеддинг, сохранение векторов
- Ответ на вопрос: поиск похожих чанков, формирование контекста, отправка в LLM
- Управление историей вопросов и ответов

**storage.py** - локальное хранилище файлов:
- Сохранение файлов в DOCUMENTS_DIR
- Удаление файлов при удалении документов
- Генерация уникальных имён файлов (UUID + original_name)

### 3. Database (app/db/)

**models.py** - ORM модели:

```mermaid
erDiagram
    Document ||--o{ DocumentChunk : has
    Document ||--o{ Answer : referenced_in
    Document ||--o{ DocumentTag : has
    
    Document {
        string id PK
        string filename
        enum file_type
        string file_path
        string content_hash
        string title
        string author
        integer page_count
        integer word_count
        integer content_length
        integer chunks_count
        enum status
        string error_message
        datetime created_at
        datetime updated_at
        datetime processed_at
        json doc_metadata
        json tags
    }
    
    DocumentChunk {
        string id PK
        string document_id FK
        integer chunk_index
        text content
        integer content_length
        string vector_id
        json chunk_metadata
        datetime created_at
    }
    
    Answer {
        string id PK
        text question
        text answer
        string document_id FK
        float confidence
        float processing_time_ms
        json sources
        datetime created_at
    }
    
    DocumentTag {
        string id PK
        string document_id FK
        string tag
    }
```

**repository.py** - операции с БД:
- CRUD для документов, чанков, ответов
- Фильтрация и поиск
- Обновление статусов документов
- Подсчёт статистики

**vector_store.py** - работа с PGVector:
- Добавление чанков с эмбеддингами
- Поиск по схожести (cosine similarity)
- Удаление чанков по document_id
- Фильтрация по метаданным (document_id, filename)

**database.py** - настройка SQLAlchemy:
- Создание engine и сессий
- Контекстный менеджер для транзакций
- Инициализация таблиц при старте

## Workflow загрузки документа

```mermaid
sequenceDiagram
    participant Client
    participant Router as Documents Router
    participant Storage as Local Storage
    participant Parser as Document Parser
    participant Chunker as Document Chunker
    participant RAG as RAG Service
    participant DB as PostgreSQL
    participant PGVec as PGVector
    participant EmbedAPI as Embedding API
    
    Client->>Router: POST /upload (file)
    Router->>Storage: save_file(uuid_filename, content)
    Storage-->>Router: file_path
    
    Router->>Parser: parse_document(file_path)
    Parser-->>Router: {content, filename, file_type, metadata}
    
    Router->>Chunker: chunk_document(document)
    Chunker-->>Router: chunks[]
    
    Router->>RAG: process_document(document, chunks, file_path)
    
    RAG->>DB: create_document(doc_data)
    DB-->>RAG: document (with id)
    
    RAG->>EmbedAPI: embed_chunks(chunks)
    EmbedAPI-->>RAG: vector_ids[]
    
    RAG->>PGVec: add_chunks(chunks, doc_id, filename)
    PGVec-->>RAG: success
    
    RAG->>DB: create_chunks(doc_id, chunk_records)
    DB-->>RAG: chunks
    
    RAG->>DB: update_document_status(COMPLETED)
    DB-->>RAG: success
    
    RAG-->>Router: doc_id
    Router-->>Client: DocumentUploadResponse
    
    Note over Storage: Файл остаётся на диске
```

### Детали процесса загрузки

1. **Приём файла**: роутер получает файл через multipart/form-data
2. **Сохранение**: файл сохраняется в DOCUMENTS_DIR с уникальным именем (UUID + original_name)
3. **Парсинг**: markitdown извлекает текст и метаданные
4. **Чанкинг**: текст разбивается на чанки по 500 токенов с перекрытием 100
5. **Создание записи в БД**: документ сохраняется в таблицу documents со статусом PENDING
6. **Эмбеддинг**: каждый чанк отправляется в embedding API для получения вектора
7. **Сохранение векторов**: чанки с векторами сохраняются в PGVector с метаданными (document_id, filename, chunk_index)
8. **Сохранение чанков в БД**: информация о чанках сохраняется в document_chunks с vector_id
9. **Обновление статуса**: документ помечается как COMPLETED
10. **Возврат ответа**: клиент получает ID документа и информацию о обработке

При ошибке на любом этапе документ помечается как FAILED с error_message.

## Workflow вопроса и ответа

```mermaid
sequenceDiagram
    participant Client
    participant Router as QA Router
    participant RAG as RAG Service
    participant PGVec as PGVector
    participant LLM as Anthropic Claude
    participant DB as PostgreSQL
    
    Client->>Router: POST /ask {question, top_k}
    Router->>RAG: answer_question(question, top_k)
    
    RAG->>PGVec: similarity_search(question, k=top_k)
    Note over PGVec: Вопрос -> эмбеддинг -><br/>cosine similarity поиск
    PGVec-->>RAG: results[] (chunks + scores)
    
    RAG->>RAG: Формирование контекста из чанков
    RAG->>RAG: Формирование промпта
    
    RAG->>LLM: invoke(prompt)
    Note over LLM: Промпт с контекстом<br/>и вопросом
    LLM-->>RAG: answer_text
    
    RAG->>DB: create_answer(question, answer, sources, time)
    DB-->>RAG: answer
    
    RAG-->>Router: {id, question, answer, sources, time}
    Router-->>Client: AnswerResponse
```

### Детали процесса ответа

1. **Получение вопроса**: роутер принимает вопрос и параметры (top_k, document_ids, include_sources)
2. **Поиск похожих чанков**: вопрос отправляется в PGVector для поиска top-K наиболее похожих чанков
3. **Формирование контекста**: из найденных чанков собирается текст контекста
4. **Формирование источников**: для каждого чанка создаётся источник с document_id, filename, chunk_index, content, similarity_score
5. **Создание промпта**: промпт содержит контекст, вопрос и инструкцию отвечать только на основе контекста
6. **Генерация ответа**: промпт отправляется в Anthropic Claude
7. **Сохранение в БД**: вопрос, ответ, источники и время обработки сохраняются в таблицу answers
8. **Возврат ответа**: клиент получает ответ с источниками

## Workflow удаления документа

```mermaid
sequenceDiagram
    participant Client
    participant Router as Documents Router
    participant RAG as RAG Service
    participant DB as PostgreSQL
    participant Storage as Local Storage
    participant PGVec as PGVector
    
    Client->>Router: DELETE /documents/{id}
    Router->>RAG: get_document_info(id)
    RAG->>DB: get_document(id)
    DB-->>RAG: document
    RAG-->>Router: document
    
    Router->>RAG: delete_document(id)
    
    RAG->>Storage: delete_file(file_path)
    Storage-->>RAG: success
    
    RAG->>PGVec: delete_chunks_by_document_id(id)
    Note over PGVec: Удаление всех чанков<br/>с document_id = id
    PGVec-->>RAG: success
    
    RAG->>DB: delete_document(id)
    Note over DB: CASCADE удаляет<br/>document_chunks и answers
    DB-->>RAG: success
    
    RAG-->>Router: true
    Router-->>Client: DocumentDeleteResponse
```

## Workflow поиска документов

```mermaid
flowchart LR
    A[Поисковый запрос] --> B{Тип поиска}
    B -->|По тексту| C[SQL LIKE поиск<br/>по filename, title, author]
    B -->|По статусу| D[Фильтр по status]
    B -->|По типу| E[Фильтр по file_type]
    B -->|Комбинированный| F[Несколько фильтров]
    
    C --> G[Документы]
    D --> G
    E --> G
    F --> G
    
    G --> H[Пагинация]
    H --> I[Результат]
```

## API Endpoints

### Документы

**POST /api/v1/upload** - загрузка одного файла
```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@document.pdf"
```

**POST /api/v1/upload-batch** - загрузка нескольких файлов
```bash
curl -X POST http://localhost:8000/api/v1/upload-batch \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.docx"
```

**GET /api/v1/documents** - список документов
```bash
curl "http://localhost:8000/api/v1/documents?page=1&limit=20&status=completed&file_type=pdf"
```

**GET /api/v1/documents/{id}** - информация о документе
```bash
curl http://localhost:8000/api/v1/documents/{document_id}
```

**DELETE /api/v1/documents/{id}** - удаление документа
```bash
curl -X DELETE http://localhost:8000/api/v1/documents/{document_id}
```

**POST /api/v1/documents/search** - поиск документов
```bash
curl -X POST http://localhost:8000/api/v1/documents/search \
  -H "Content-Type: application/json" \
  -d '{"query": "contract", "file_type": "pdf", "page": 1, "limit": 10}'
```

### Вопрос-ответ

**POST /api/v1/ask** - задать вопрос
```bash
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Каковы условия расторжения договора?",
    "top_k": 5,
    "include_sources": true
  }'
```

**GET /api/v1/history** - история вопросов и ответов
```bash
curl "http://localhost:8000/api/v1/history?page=1&limit=20"
```

**GET /api/v1/history/{id}** - конкретный ответ
```bash
curl http://localhost:8000/api/v1/history/{answer_id}
```

### Системные

**GET /api/v1/supported-formats** - список поддерживаемых форматов

**GET /health** - проверка состояния сервиса

## Структура проекта

```
docmind/
├── app/
│   ├── main.py              # FastAPI приложение, настройка CORS, роутеры
│   ├── routers/
│   │   ├── documents.py     # Endpoints для работы с документами
│   │   └── qa.py            # Endpoints для вопрос-ответа
│   ├── services/
│   │   ├── parser.py        # Парсинг документов через markitdown
│   │   ├── chunker.py       # Разбивка текста на чанки
│   │   ├── embedder.py      # Генерация эмбеддингов через LiteLLM
│   │   ├── rag.py           # Основная RAG логика
│   │   └── storage.py       # Локальное хранилище файлов
│   ├── db/
│   │   ├── database.py      # SQLAlchemy engine, сессии, init_db
│   │   ├── models.py        # ORM модели (Document, DocumentChunk, Answer, DocumentTag)
│   │   ├── repository.py    # CRUD операции с БД
│   │   └── vector_store.py  # Работа с PGVector
│   └── models/
│       └── schemas.py       # Pydantic схемы для request/response
├── ui/
│   └── app.py               # Streamlit UI
├── docker-compose.yml       # PostgreSQL + PGVector
├── pyproject.toml           # Зависимости (uv)
└── README.md
```

## Как работает RAG

```mermaid
flowchart TD
    subgraph "1. Загрузка документа"
        A1[Документ] --> A2[Парсинг текста<br/>markitdown]
        A2 --> A3[Разбивка на чанки<br/>500 токенов, overlap 100]
        A3 --> A4[Генерация эмбеддингов<br/>LiteLLM]
        A4 --> A5[Сохранение в PGVector<br/>с метаданными]
        A5 --> A6[Сохранение метаданных<br/>в PostgreSQL]
    end
    
    subgraph "2. Обработка вопроса"
        B1[Вопрос пользователя] --> B2[Генерация эмбеддинга<br/>вопроса]
        B2 --> B3[Cosine similarity<br/>поиск в PGVector]
        B3 --> B4[Top-K релевантных<br/>чанков]
        B4 --> B5[Формирование контекста<br/>из чанков]
        B5 --> B6[Создание промпта<br/>для LLM]
        B6 --> B7[Anthropic Claude<br/>генерирует ответ]
        B7 --> B8[Сохранение в БД<br/>+ возврат ответа]
    end
    
    A6 -.-> B3
```

### Детали RAG процесса

**Индексация документа:**
1. Документ парсится в текст через markitdown
2. Текст разбивается на чанки по 500 токенов с перекрытием 100 токенов
3. Каждый чанк получает метаданные: filename, chunk_index, total_chunks
4. Для каждого чанка генерируется эмбеддинг (вектор)
5. Чанки с эмбеддингами сохраняются в PGVector с метаданными
6. Информация о документе и чанках сохраняется в PostgreSQL

**Поиск и генерация ответа:**
1. Вопрос пользователя преобразуется в эмбеддинг
2. В PGVector ищутся top-K наиболее похожих чанков (cosine similarity)
3. Из найденных чанков формируется контекст
4. Создаётся промпт с инструкцией отвечать только на основе контекста
5. Промпт отправляется в Anthropic Claude
6. Ответ сохраняется в БД вместе с источниками и временем обработки
7. Ответ возвращается клиенту

## Особенности реализации

### Хранение файлов
- Файлы сохраняются локально в DOCUMENTS_DIR (по умолчанию ./documents)
- Имя файла: `{uuid}_{original_filename}` для уникальности
- При удалении документа файл удаляется с диска

### Метаданные в БД
- Информация о документах хранится в PostgreSQL, а не в памяти
- Данные не теряются при перезапуске приложения
- Поддержка фильтрации и поиска по метаданным

### Векторный поиск
- PGVector для хранения эмбеддингов и поиска по схожести
- Фильтрация по document_id для поиска в рамках конкретного документа
- Cosine similarity для определения релевантности

### Обработка ошибок
- Если парсинг или обработка не удались, документ помечается как FAILED с error_message
- При удалении документа каскадно удаляются связанные чанки и ответы
- Файл удаляется только если документ успешно удалён из БД

## TODO

- Стриминг ответов через WebSocket
- Аутентификация и авторизация
- Поддержка веб-страниц (URL -> индексация)
- Экспорт ответов в PDF
- Более детальная обработка ошибок при загрузке

## Лицензия

MIT
