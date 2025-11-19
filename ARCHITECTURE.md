# 🏗️ RAG Knowledge Base - Architecture Documentation

## System Overview

The RAG Knowledge Base is a microservices-based application designed for semantic search and AI-powered chat across PDF documents. It uses modern containerization, vector databases, machine learning for efficient document retrieval, and LLM integration for intelligent question answering.

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                           User Browser                             │
└───────────────────────────┬────────────────────────────────────────┘
                            │ HTTP
                            ↓
┌───────────────────────────────────────────────────────────────────┐
│                    Frontend Container (Nginx + React)             │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │  • React 18 SPA                                          │     │
│  │  • Drag & Drop Upload                                    │     │
│  │  • Hybrid Search Interface (Semantic + Keyword)          │     │
│  │  • AI Chat Interface with Context Viewer                 │     │
│  │  • Document Management UI                                │     │
│  │  • Advanced Search Filters                               │     │
│  └──────────────────────────────────────────────────────────┘     │
└───────────────────────────┬───────────────────────────────────────┘
                            │ REST API (Port 8000)
                            ↓
┌───────────────────────────────────────────────────────────────────┐
│              Backend Container (FastAPI + Python)                 │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐   │
│  │ PDF          │ Embedding    │ Hybrid       │ Chat         │   │
│  │ Processor    │ Service      │ Search Svc   │ Service      │   │
│  │              │              │              │              │   │
│  │ • Plain Mode │ • Sentence   │ • BM25       │ • LLM        │   │
│  │ • Paragraph  │   Transform  │ • Semantic   │   Orchestr.  │   │
│  │   Chunking   │ • Batch      │ • RRF Fusion │ • Context    │   │
│  │ • Metadata
   │   Embed
   |could be saved 
   |in redis      │ • Boolean    │   Injection  │   │
│  └──────────────┴──────────────┴──────────────┴──────────────┘   │
│                                                                   │
│  API Routes:                                                      │
│  • POST   /api/v1/documents/upload                                │
│  • POST   /api/v1/documents/process-file  ← File Watcher Events  │
│  • GET    /api/v1/documents/                                      │
│  • DELETE /api/v1/documents/{id}                                  │
│  • POST   /api/v1/search/                                         │
│  • POST   /api/v1/chat/                                           │
└──────┬────────────────┬─────────────┬───────────────┬─────────────┘
       │                │             │               │        ↑
       │ SQLAlchemy     │ File System │ ChromaDB      │        │ HTTP Event
       ↓                ↓             ↓               ↓        │
┌──────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐
│ PostgreSQL   │ │ File Storage│ │  ChromaDB   │ │ LLM Service     │
│              │ │             │ │             │ │ Container       │
│ • Documents  │ │ • /data/    │ │ • Vectors   │ │                 │
│   Metadata   │ │   uploads/  │ │ • Embeddings│ │ • Gemini 2.0    │
│ • Status     │ │ • /data/    │ │ • Cosine Sim│ │ • Tool Calling  │
│ • Chunk IDs  │ │   watch/    │ │ • Persistence│ │ • Model Agnostic│
└──────────────┘ └──────┬──────┘ └─────────────┘ └─────────────────┘
                        │
                        │ File System Events
                        ↓
               ┌─────────────────────────────────────┐
               │   File Watcher Service (Python)    │
               │                                     │
               │  • Watchdog (filesystem monitor)   │
               │  • Event-driven architecture       │
               │  • GCP-ready design (Pub/Sub)      │
               │  • Idempotent processing           │
               │  • Automatic retry logic           │
               │                                     │
               │  GCP Migration Path:               │
               │  → Cloud Storage Triggers          │
               │  → Cloud Functions                 │
               │  → Pub/Sub messaging               │
               └─────────────────────────────────────┘
```

## Component Details

### 1. Frontend (React + Nginx)

**Technology Stack:**
- React 18
- Axios for API calls
- React Dropzone for file uploads
- React Toastify for notifications
- Nginx for production serving

**Key Features:**
- Responsive, modern UI
- Tab-based navigation (Search/Chat/Documents)
- Real-time upload progress
- Drag & drop file upload
- Hybrid search with mode selection (Semantic/Keyword/Hybrid)
- Advanced search filters (date, document, boolean operators)
- AI Chat interface with context viewer
- Chunk selection for RAG context
- Document management (view/delete)
- Statistics dashboard

**Files:**
```
frontend/
├── src/
│   ├── components/
│   │   ├── DocumentList.js       # Document grid view
│   │   ├── SearchBar.js          # Search input with mode selector
│   │   ├── SearchResults.js      # Results with chunk selection
│   │   ├── AdvancedSearch.js     # Filter panel
│   │   ├── ChatInterface.js      # AI chat UI
│   │   ├── UploadArea.js         # Drag & drop upload
│   │   └── PDFViewer.js          # PDF preview modal
│   ├── services/
│   │   └── api.js                # API client (documents, search, chat)
│   └── App.js                    # Main component
└── Dockerfile                    # Multi-stage build
```

### 2. Backend (FastAPI)

**Technology Stack:**
- FastAPI (async Python web framework)
- SQLAlchemy (ORM)
- Pydantic (data validation)
- pdfminer.six (PDF processing)
- sentence-transformers (embeddings)
- ChromaDB (vector storage)
- rank-bm25 (keyword search)
- httpx (async HTTP client for LLM service)

**Architecture Pattern:**
- **Layered Architecture**
  - API Layer (routes)
  - Service Layer (business logic)
  - Data Layer (models, database)

**Key Services:**

#### PDF Processor Service
```python
class PDFProcessor:
    - extract_metadata()  # Extract PDF info
    - extract_text()      # Plain text extraction
    - chunk_text()        # Paragraph-based chunking
    - process_pdf()       # Complete workflow
```

**Chunking Algorithm:**
1. Extract paragraphs (split on `\n\n`)
2. Check paragraph length
3. If < chunk_size: Keep as single chunk
4. If > chunk_size: Split by sentences
5. Apply overlap between chunks
6. Generate unique chunk IDs (hash-based)

#### Embedding Service
```python
class EmbeddingService:
    - load_model()           # Load sentence-transformers
    - generate_embeddings()  # Batch processing
    - generate_embedding()   # Single text
```

**Model Details:**
- Default: all-MiniLM-L6-v2 (downloaded at build time)
- Dimensions: 384
- Normalized embeddings (unit length)
- Batch size: 32 (configurable)
- Offline mode enabled (no runtime downloads)

#### Hybrid Search Service
```python
class HybridSearchService:
    - hybrid_search()        # Combined search
    - _semantic_search()     # Vector similarity
    - _keyword_search()      # BM25 ranking
    - _reciprocal_rank_fusion()  # Score combination
```

**Search Modes:**
- **Hybrid**: Combines semantic + keyword with RRF
- **Semantic**: Pure vector similarity search
- **Keyword**: BM25 text matching

**Advanced Filters:**
- Date range filtering
- Document ID filtering
- Boolean operators (AND/NOT/OR)

#### Chat Service
```python
class ChatService:
    - chat()                 # Main orchestration
    - _call_llm_generate()   # Direct LLM call
    - _chat_with_tools()     # Tool-based search
    - get_history()          # Conversation history
    - clear_history()        # Reset conversation
```

**Features:**
- Conversation history management
- Context injection from selected chunks
- Tool calling for AI-driven search
- Async HTTP communication with LLM service

#### Vector Store Service
```python
class VectorStore:
    - add_documents()     # Bulk insert
    - search()            # Similarity search
    - delete_by_ids()     # Remove chunks
    - delete_by_source()  # Remove by document
```

**ChromaDB Configuration:**
- Distance metric: Cosine similarity
- Index: HNSW (approximate nearest neighbors)
- Persistent storage: DuckDB + Parquet

**Files:**
```
backend/
├── app/
│   ├── api/routes/
│   │   ├── documents.py      # Document CRUD
│   │   ├── search.py         # Hybrid search endpoint
│   │   └── chat.py           # Chat orchestration
│   ├── core/
│   │   ├── config.py         # Settings
│   │   └── database.py       # DB connection
│   ├── models/
│   │   └── document.py       # SQLAlchemy models
│   ├── services/
│   │   ├── pdf_processor.py
│   │   ├── embedding_service.py
│   │   ├── vector_store.py
│   │   ├── hybrid_search.py   # BM25 + Semantic
│   │   └── chat_service.py    # LLM orchestration
│   └── main.py              # FastAPI app
├── Dockerfile
├── requirements.txt          # Core dependencies
└── requirements-chat.txt     # LLM integration deps
```

### 3. File Watcher Service (Event-Driven Processing)

**Purpose:** Automatic PDF processing by monitoring a folder

**Technology Stack:**
- Python 3.11
- watchdog (filesystem monitoring)
- httpx (async HTTP client)
- pydantic-settings (configuration)
- python-json-logger (structured logging)

**Architecture Pattern:**
- **Event-Driven** - Decoupled file detection from processing
- **GCP-Ready** - Designed to map directly to Cloud Storage + Pub/Sub

**Key Components:**

#### Watcher Service
```python
class FolderWatcher:
    - start()                    # Begin monitoring
    - _process_existing_files()  # Handle files on startup
    - _stability_check_loop()    # Ensure uploads complete
    - _create_file_event()       # Generate event payload
```

#### Event Publisher (Abstraction for Pub/Sub)
```python
class EventPublisher(ABC):
    - publish()                  # Send event to backend
    - close()                    # Cleanup

class DirectHTTPPublisher(EventPublisher):
    - publish()                  # HTTP POST to backend
    # GCP: Replace with PubSubEventPublisher
```

#### File Tracker (Idempotency)
```python
class FileTracker:
    - is_processed()     # Check if already processed
    - mark_pending()     # Start tracking
    - mark_success()     # Completed successfully
    - mark_failed()      # Track failures
```

**Event Schema (GCS-Compatible):**
```python
@dataclass
class FileEvent:
    event_type: str      # "OBJECT_FINALIZE" (GCS standard)
    file_path: str       # Full path to file
    file_name: str       # Filename only
    file_size: int       # File size in bytes
    bucket: str          # Watch folder (maps to GCS bucket)
    timestamp: str       # ISO timestamp
    event_id: str        # Unique event ID
```

**Features:**
- Automatic folder monitoring
- File stability detection (ensures upload complete)
- Idempotent processing (no duplicates)
- Retry logic for failed processing
- Structured JSON logging (Cloud Logging ready)
- Graceful shutdown handling

**Files:**
```
file_watcher_service/
├── app/
│   ├── main.py              # Service entry point
│   ├── config.py            # Configuration (env vars)
│   ├── watcher.py           # Filesystem monitoring
│   ├── event_publisher.py   # Event publishing abstraction
│   └── file_tracker.py      # Deduplication tracker
├── Dockerfile
└── requirements.txt
```

**Configuration (Environment Variables):**
```bash
WATCHER_WATCH_FOLDER=/data/watch
WATCHER_BACKEND_URL=http://backend:8000
WATCHER_FILE_STABILITY_THRESHOLD=5.0
WATCHER_MAX_RETRIES=3
WATCHER_PROCESS_EXISTING_ON_STARTUP=true
```

### 4. LLM Service (Gemini)

**Purpose:** Model-agnostic LLM integration for AI chat

**Technology Stack:**
- FastAPI
- Google Generative AI (Gemini)
- Abstract provider pattern

**Architecture:**
```python
# Factory pattern for model swapping
class BaseLLMProvider:
    - generate()              # Standard generation
    - generate_stream()       # Streaming response
    - generate_with_tools()   # Function calling
    - health_check()          # Service health

class GeminiProvider(BaseLLMProvider):
    - Gemini 2.0 Flash model
    - Safety settings configured
    - Tool/function calling support
```

**Features:**
- Model-agnostic design (easy to swap providers)
- Function/tool calling for autonomous search
- Streaming support
- Conversation history handling
- Context injection

**Files:**
```
llm_service/
├── app/
│   ├── providers/
│   │   ├── base.py           # Abstract base class
│   │   ├── gemini.py         # Gemini implementation
│   │   └── factory.py        # Provider factory
│   ├── routes/
│   │   └── chat.py           # API endpoints
│   ├── config.py             # Settings
│   └── main.py               # FastAPI app
├── Dockerfile
└── requirements.txt
```

**API Endpoints:**
- `POST /api/v1/generate` - Standard generation
- `POST /api/v1/generate/stream` - Streaming
- `POST /api/v1/generate/with-tools` - Tool calling
- `GET /api/v1/health` - Service health

### 4. PostgreSQL

**Purpose:** Metadata storage and document tracking

**Schema:**
```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_size INTEGER NOT NULL,
    title VARCHAR(512),
    author VARCHAR(255),
    num_pages INTEGER,
    num_chunks INTEGER DEFAULT 0,
    chunk_ids JSON,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT
);
```

**Why PostgreSQL?**
- ACID compliance
- JSON support for chunk_ids
- Reliable metadata storage
- Easy backups
- Well-supported

### 5. ChromaDB

**Purpose:** Vector embeddings storage and similarity search

**Data Structure:**
```python
{
    "id": "chunk_abc123_0001_xyz789",
    "embedding": [0.123, -0.456, ...],  # 384 dims
    "document": "text content",
    "metadata": {
        "document_id": 1,
        "document_filename": "file.pdf",
        "source": "file.pdf",
        "chunk_index": 0,
        "char_count": 876,
        "word_count": 120
    }
}
```

**Why ChromaDB?**
- Simple Python API
- Built-in persistence
- Fast similarity search
- Low resource requirements
- Perfect for RAG applications

## Data Flow

### Upload Workflow

```
1. User uploads PDF
   ↓
2. Frontend → POST /api/v1/documents/upload
   ↓
3. Backend saves file to /data/uploads/
   ↓
4. Create database record (status: processing)
   ↓
5. PDFProcessor.process_pdf()
   ├─→ extract_metadata() → Get title, author, pages
   ├─→ extract_text() → Extract plain text
   └─→ chunk_text() → Create paragraphs
   ↓
6. EmbeddingService.generate_embeddings()
   └─→ Batch process all chunks
   ↓
7. VectorStore.add_documents()
   └─→ Store in ChromaDB
   ↓
8. Update database record
   ├─→ status: completed
   ├─→ num_chunks: X
   └─→ chunk_ids: [...]
   ↓
9. Return success to frontend
```

### Search Workflow

```
1. User enters query + selects mode (hybrid/semantic/keyword)
   ↓
2. Frontend → POST /api/v1/search/
   ↓
3. Backend receives query + filters
   ↓
4. HybridSearchService.hybrid_search()
   ├─→ If hybrid: Run both searches
   │   ├─→ Semantic: Generate embedding, ChromaDB search
   │   └─→ Keyword: BM25 ranking
   ├─→ If semantic: Only vector search
   └─→ If keyword: Only BM25 search
   ↓
5. Apply advanced filters
   ├─→ Document ID filter
   ├─→ Date range filter
   └─→ Boolean operators (AND/NOT/OR)
   ↓
6. Reciprocal Rank Fusion (for hybrid)
   └─→ Combine scores with weighted RRF
   ↓
7. Format results with metadata
   ↓
8. Return to frontend
   ↓
9. Display ranked results with scores
```

### Chat Workflow

```
1. User sends message (with optional context chunks)
   ↓
2. Frontend → POST /api/v1/chat/
   ↓
3. Backend ChatService orchestrates
   ↓
4. If "Allow AI to search" enabled:
   ├─→ Send to LLM with search tool definition
   ├─→ LLM decides to search (or not)
   ├─→ If search requested:
   │   ├─→ Execute HybridSearchService.hybrid_search()
   │   ├─→ Get relevant chunks
   │   └─→ Re-send to LLM with context
   └─→ LLM generates final response
   ↓
5. If context chunks provided:
   ├─→ Inject chunks as context
   └─→ LLM generates response
   ↓
6. Update conversation history
   ↓
7. Return response with sources
   ↓
8. Frontend displays message + context viewer
```

### Delete Workflow

```
1. User clicks delete
   ↓
2. Frontend → DELETE /api/v1/documents/{id}
   ↓
3. Backend retrieves document record
   ↓
4. VectorStore.delete_by_ids(chunk_ids)
   └─→ Remove from ChromaDB
   ↓
5. Delete PDF file from /data/uploads/
   ↓
6. Delete database record
   ↓
7. Return success
```

### File Watcher Workflow (Automated Processing)

```
1. User/System drops PDF into /data/watch/ folder
   ↓
2. Watchdog detects file creation event
   ↓
3. Wait for file stability (no modifications for 5s)
   └─→ Ensures upload is complete
   ↓
4. Check if file already processed (idempotency)
   ↓
5. Create FileEvent with GCS-compatible schema:
   {
     event_type: "OBJECT_FINALIZE",
     file_path: "/data/watch/document.pdf",
     file_name: "document.pdf",
     bucket: "/data/watch",
     event_id: "uuid-here"
   }
   ↓
6. Publish event → Backend API
   POST /api/v1/documents/process-file
   ↓
7. Backend processes PDF (same as upload):
   ├─→ Extract text & metadata
   ├─→ Chunk document
   ├─→ Generate embeddings
   └─→ Store in ChromaDB
   ↓
8. File tracker marks as processed
   ↓
9. Document available in search & chat
```

**GCP Migration of This Workflow:**
```
1. User uploads PDF to GCS bucket
   ↓
2. Cloud Storage sends OBJECT_FINALIZE event to Pub/Sub
   ↓
3. Cloud Function receives Pub/Sub message
   ↓
4. Cloud Function calls Cloud Run backend
   POST /api/v1/documents/process-file
   ↓
5. Backend downloads from GCS, processes, stores
   ↓
6. Document available in search & chat
```

## Network Communication

```
Docker Network: rag-network
Type: Bridge

Container Communication:
- frontend:80 → backend:8000 (HTTP API)
- backend → postgres:5432 (PostgreSQL)
- backend → chromadb (Python client, local)
- backend → llm:8001 (HTTP API for LLM service)
- file_watcher → backend:8000 (Event notifications)

External Access:
- localhost:3000 → frontend:80
- localhost:8000 → backend:8000
- localhost:8002 → llm:8001 (LLM service)
- localhost:5432 → postgres:5432 (optional)
```

## Storage Strategy

### Volumes

```yaml
volumes:
  - ./data/uploads:/data/uploads       # PDF files (UI uploads)
  - ./data/watch:/data/watch           # PDF files (auto-processing)
  - ./data/processed:/data/processed   # File tracking data
  - ./data/chromadb:/data/chromadb     # Vector DB
  - ./data/postgres:/var/lib/postgresql/data
```

### Data Persistence

| Data Type | Location | Backup Strategy |
|-----------|----------|----------------|
| PDF Files (UI) | /data/uploads | File system backup |
| PDF Files (Auto) | /data/watch | File system backup |
| File Tracker | /data/processed | JSON file backup |
| Embeddings | /data/chromadb | Directory backup |
| Metadata | /data/postgres | pg_dump |

## Security Considerations

### Current Implementation

- ✅ Non-root Docker users
- ✅ CORS configuration
- ✅ File type validation
- ✅ File size limits
- ✅ SQL injection protection (SQLAlchemy)

### Production Recommendations

- 🔒 Add authentication (JWT)
- 🔒 Enable HTTPS
- 🔒 Rate limiting
- 🔒 Input sanitization
- 🔒 Secrets management
- 🔒 Network isolation
- 🔒 Regular updates

## Performance Characteristics

### Bottlenecks

1. **PDF Processing**: I/O bound (disk read)
2. **Embedding Generation**: CPU bound
3. **Vector Search**: Memory + CPU bound

### Optimization Strategies

**Current:**
- Batch embedding generation (32 per batch)
- Persistent connections (connection pooling)
- Efficient chunking algorithm

**Future:**
- Add GPU support for embeddings
- Implement caching layer (Redis)
- Use async database queries
- Add task queue (Celery)
- Horizontal scaling

### Estimated Performance

| Operation | Time | Throughput |
|-----------|------|------------|
| Upload 10-page PDF | ~5s | - |
| Generate embeddings (100 chunks) | ~10s | 10 chunks/s |
| Search query | <100ms | 10+ QPS |
| Delete document | ~500ms | - |

## Scalability

### Horizontal Scaling Options

```
Current: Monolithic Backend
Future Options:
├── Load Balancer
├── Multiple Backend Instances
├── Separate Worker Service
├── Redis Task Queue
└── Distributed ChromaDB
```

### Resource Requirements

**Minimum:**
- 2 CPU cores
- 4GB RAM
- 10GB disk

**Recommended:**
- 4+ CPU cores
- 8GB RAM
- 50GB SSD

**For 10,000 Documents:**
- 8+ CPU cores
- 16GB RAM
- 100GB SSD

## Monitoring & Observability

### Logs

```bash
# Application logs
docker-compose logs -f backend

# Database logs
docker-compose logs -f postgres

# All logs
docker-compose logs -f
```

### Metrics

Available via API:
- `/api/v1/documents/stats/overview`
  - Total documents
  - Total chunks
  - Vector store count

### Health Checks

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000/health`
- Postgres: Built-in healthcheck

## Technology Choices

### Why These Technologies?

**FastAPI:**
- ✅ Fast (ASGI)
- ✅ Async support
- ✅ Auto-generated docs
- ✅ Type hints
- ✅ Easy to learn

**React:**
- ✅ Component-based
- ✅ Rich ecosystem
- ✅ Fast rendering
- ✅ Easy state management

**ChromaDB:**
- ✅ Purpose-built for embeddings
- ✅ Simple API
- ✅ No external dependencies
- ✅ Good performance

**PostgreSQL:**
- ✅ Reliable
- ✅ JSON support
- ✅ ACID compliant
- ✅ Well-documented

**Docker:**
- ✅ Consistent environments
- ✅ Easy deployment
- ✅ Service isolation
- ✅ Resource control

## Future Enhancements

### Planned Features

1. **Authentication & Authorization**
   - User accounts
   - Document permissions
   - API keys

2. **Additional LLM Providers**
   - OpenAI GPT-4
   - Anthropic Claude
   - Local models (Ollama)
   - Cost optimization

3. **Enhanced Chat Features**
   - Streaming responses
   - Chat history persistence
   - Custom system prompts
   - Multi-turn reasoning

4. **File Type Support**
   - DOCX, TXT, HTML
   - Image OCR
   - Audio transcription

5. **Analytics**
   - Usage statistics
   - Popular searches
   - Document insights
   - Token usage tracking

6. **Collaboration**
   - Shared knowledge bases
   - Team workspaces
   - Comments & annotations

7. **Performance**
   - GPU support for embeddings
   - Response caching
   - Async processing queue
   - Horizontal scaling

---

**Designed for**: Scalability, maintainability, and production readiness
**Built with**: Modern best practices and clean architecture principles
