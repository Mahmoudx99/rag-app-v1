# RAG Knowledge Base - Architecture Documentation

## System Overview

The RAG Knowledge Base is a microservices-based application deployed on Google Cloud Platform (GCP). It provides semantic search and AI-powered chat across PDF documents using Vertex AI Vector Search for embeddings and Vertex AI Model Garden for open-source LLM inference.

## Architecture Diagram

```
                         ┌─────────────────────────────┐
                         │      User Browser           │
                         └─────────────┬───────────────┘
                                       │ HTTPS
                                       ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                        Google Cloud Platform (me-central2)               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Cloud Run Services                           │    │
│  │                                                                  │    │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐         │    │
│  │  │  Frontend    │   │   Backend    │   │ LLM Service  │         │    │
│  │  │  (React)     │   │  (FastAPI)   │   │  (FastAPI)   │         │    │
│  │  │              │   │              │   │              │         │    │
│  │  │ 512Mi, 1 CPU │   │ 4Gi, 2 CPU   │   │ 2Gi, 2 CPU   │         │    │
│  │  │ Port 80      │   │ Port 8000    │   │ Port 8001    │         │    │
│  │  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘         │    │
│  │         │                  │                   │                 │    │
│  └─────────┼──────────────────┼───────────────────┼─────────────────┘    │
│            │                  │                   │                      │
│            │ REST API         │                   │                      │
│            └─────────────────►│◄──────────────────┘                      │
│                               │                                          │
│            ┌──────────────────┼──────────────────────┐                   │
│            │                  │                      │                   │
│            ↓                  ↓                      ↓                   │
│  ┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐         │
│  │ Cloud Storage│   │  Vertex AI       │   │  Vertex AI       │         │
│  │              │   │  Vector Search   │   │  Model Garden    │         │
│  │ Bucket:      │   │                  │   │                  │         │
│  │ anb-rag-     │   │ Index Endpoint:  │   │ Llama 3.1 8B     │         │
│  │ documents    │   │ 2982368...       │   │ (or Mistral,     │         │
│  │              │   │                  │   │  Gemma)          │         │
│  │ • PDFs       │   │ • 384-dim        │   │                  │         │
│  │ • SQLite DB  │   │   embeddings     │   │ • Text generation│         │
│  │              │   │ • Cosine sim     │   │ • Streaming      │         │
│  └──────────────┘   └──────────────────┘   └──────────────────┘         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## GCP Project Details

| Resource | Value |
|----------|-------|
| Project ID | `anb-gpt-prj` |
| Region | `me-central2` (Middle East) |
| Artifact Registry | `me-central2-docker.pkg.dev/anb-gpt-prj/cloud-run-source-deploy` |

## Component Details

### 1. Frontend (Cloud Run)

**Service:** `rag-frontend`

**Technology Stack:**
- React 18
- Nginx (serving)
- Axios for API calls

**Resources:**
- Memory: 512Mi
- CPU: 1
- Min instances: 0
- Max instances: 5

**Key Features:**
- Responsive, modern UI
- Tab-based navigation (Search/Chat/Documents)
- Drag & drop file upload
- Semantic search interface
- AI Chat with context viewer
- Document management

**Environment:**
```
REACT_APP_API_URL=https://rag-backend-687800931209.me-central2.run.app/api/v1
```

### 2. Backend (Cloud Run)

**Service:** `rag-backend`

**Technology Stack:**
- FastAPI (async Python)
- SQLAlchemy (ORM)
- sentence-transformers (embeddings)
- google-cloud-aiplatform (Vertex AI SDK)

**Resources:**
- Memory: 4Gi
- CPU: 2
- Min instances: 0
- Max instances: 10
- Execution environment: gen2

**Environment Variables:**
```
GCP_PROJECT_ID=anb-gpt-prj
GCP_REGION=me-central2
DATABASE_URL=sqlite:////data/rag_app.db
WATCH_DIR=/data/watch
VERTEX_AI_INDEX_ENDPOINT_ID=projects/687800931209/locations/me-central2/indexEndpoints/2982368115737755648
VERTEX_AI_DEPLOYED_INDEX_ID=rag_embeddings_index_strea_1763631787972
VERTEX_AI_INDEX_ID=projects/687800931209/locations/me-central2/indexes/5538301641758867456
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
BATCH_SIZE=32
LLM_SERVICE_URL=https://rag-llm-687800931209.me-central2.run.app
```

**Storage Mount:**
- GCS bucket `anb-rag-documents` mounted at `/data`

**Key Services:**

#### PDF Processor
- Text extraction with pdfminer.six
- Paragraph-based chunking (1000 chars, 200 overlap)
- Streaming processing for large files
- Metadata extraction (title, author, pages)

#### Embedding Service
- Model: `all-MiniLM-L6-v2` (384 dimensions)
- Batch processing (32 texts per batch)
- Normalized embeddings

#### Vector Store (Vertex AI)
- Upserts via streaming updates
- Similarity search with `find_neighbors()`
- Metadata filtering by document ID
- Delete by chunk IDs

#### Semantic Search
- **Vector search:** Vertex AI Vector Search
- Similarity search with metadata filtering
- Fast and scalable

#### Chat Service
- Context injection from selected chunks
- Conversation history management
- Tool calling for AI-driven search

**API Routes:**
```
POST   /api/v1/documents/upload
POST   /api/v1/documents/process-file
GET    /api/v1/documents/
DELETE /api/v1/documents/{id}
POST   /api/v1/search/
POST   /api/v1/chat/
POST   /api/v1/documents/gcs-event  (Cloud Storage events via Eventarc)
GET    /health
```

### 3. LLM Service (Cloud Run)

**Service:** `rag-llm`

**Technology Stack:**
- FastAPI
- google-cloud-aiplatform (Vertex AI SDK)
- Abstract provider pattern

**Resources:**
- Memory: 2Gi
- CPU: 2
- Min instances: 0
- Max instances: 5

**Environment Variables:**
```
LLM_PROVIDER=vertex_ai
LLM_MODEL=llama-3.1-8b
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.7
VERTEX_AI_PROJECT_ID=anb-gpt-prj
VERTEX_AI_LOCATION=me-central2
VERTEX_AI_LLM_ENDPOINT_ID=<deployed-model-endpoint>
```

**Architecture:**
```python
class BaseLLMProvider:
    - generate()              # Standard generation
    - generate_stream()       # Streaming response
    - generate_with_tools()   # Function calling
    - health_check()          # Service health

class VertexAIProvider(BaseLLMProvider):
    - Deploys to Vertex AI Model Garden endpoints
    - Supports Llama 3.1, Mistral, Gemma, etc.
    - Chat-style prompt formatting
```

**API Endpoints:**
```
POST /api/v1/generate         # Standard generation
POST /api/v1/generate/stream  # Streaming
POST /api/v1/generate/with-tools  # Tool calling
GET  /api/v1/health           # Service health
```

### 4. Cloud Storage (GCS)

**Buckets:**

**Primary Bucket:** `anb-rag-documents` (mounted at `/data`)
```
anb-rag-documents/
├── uploads/            # User uploaded files (via UI)
├── rag_app.db          # SQLite database
└── processed/          # File tracking data
```

**Watch Bucket:** `gcs-rag-watch-bucket` (mounted at `/watch`)
```
gcs-rag-watch-bucket/
└── *.pdf               # Drop PDFs here for auto-processing via Eventarc
```

**Features:**
- Two separate buckets for clean separation of concerns
- `anb-rag-documents`: Application data and UI uploads
- `gcs-rag-watch-bucket`: Event-driven file ingestion
- Eventarc triggers on entire watch bucket (no path filtering needed)

### 5. Vertex AI Vector Search

**Index Configuration:**
- Dimensions: 384 (all-MiniLM-L6-v2)
- Distance metric: Cosine similarity
- Index type: Streaming updates

**Resources:**
- Index ID: `5538301641758867456`
- Endpoint ID: `2982368115737755648`
- Deployed Index ID: `rag_embeddings_index_strea_1763631787972`

**Data Structure:**
```python
{
    "id": "chunk_abc123_0001_xyz789",
    "embedding": [0.123, -0.456, ...],  # 384 dims
    "restricts": [
        {"namespace": "document_id", "allow_list": ["1"]}
    ]
}
```

**Chunk Content Storage:**
Embeddings stored in Vertex AI, content stored in SQLite:
```sql
CREATE TABLE chunks (
    chunk_id VARCHAR PRIMARY KEY,  -- Vertex AI ID
    document_id INTEGER,
    content TEXT,
    metadata JSON,
    page_number INTEGER,
    chunk_index INTEGER
);
```

### 6. Vertex AI Model Garden

**Purpose:** Host open-source LLMs for text generation

**Supported Models:**
- Llama 3.1 8B (recommended)
- Mistral 7B
- Gemma 2

**Deployment:**
1. Go to Vertex AI Model Garden in GCP Console
2. Select and deploy desired model
3. Note the endpoint ID
4. Update `VERTEX_AI_LLM_ENDPOINT_ID` in LLM service

### 7. Database (SQLite / Cloud SQL)

**Current:** SQLite on GCS mount
```
DATABASE_URL=sqlite:////data/rag_app.db
```

**Production Option:** Cloud SQL PostgreSQL
```
DATABASE_URL=postgresql://user:pass@/dbname?host=/cloudsql/project:region:instance
```

**Schema:**
```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    file_path VARCHAR(512) NOT NULL,
    file_size INTEGER NOT NULL,
    title VARCHAR(512),
    author VARCHAR(255),
    num_pages INTEGER,
    num_chunks INTEGER DEFAULT 0,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    chunks_processed INTEGER DEFAULT 0
);

CREATE TABLE chunks (
    chunk_id VARCHAR PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    content TEXT,
    metadata JSON,
    page_number INTEGER,
    chunk_index INTEGER
);
```

## Data Flow

### Upload Workflow

```
1. User uploads PDF via frontend
   ↓
2. Frontend → POST /api/v1/documents/upload
   ↓
3. Backend saves file to GCS (/data/uploads/)
   ↓
4. Create database record (status: processing)
   ↓
5. PDFProcessor.process_pdf_streaming()
   ├─→ Extract metadata
   └─→ Yield chunks progressively
   ↓
6. For each chunk batch:
   ├─→ EmbeddingService.generate_embeddings()
   └─→ VectorStore.add_documents_batch() → Vertex AI
   ↓
7. Store chunk content in SQLite
   ↓
8. Update database record (status: completed)
   ↓
9. Return success to frontend
```

### Search Workflow

```
1. User enters query
   ↓
2. Frontend → POST /api/v1/search/
   ↓
3. Backend search route:
   ├─→ Generate query embedding
   └─→ Vertex AI find_neighbors()
   ↓
4. Retrieve chunk content from SQLite
   ↓
5. Apply metadata filters (document, date)
   ↓
6. Return ranked results with scores
```

### Chat Workflow

```
1. User sends message (with optional context)
   ↓
2. Frontend → POST /api/v1/chat/
   ↓
3. Backend ChatService orchestrates
   ↓
4. If "Allow AI to search" enabled:
   ├─→ Call LLM Service with search tool
   ├─→ LLM may request search
   ├─→ Execute search, get chunks
   └─→ Re-send to LLM with context
   ↓
5. Backend → LLM Service /api/v1/generate
   ↓
6. LLM Service → Vertex AI Model Garden endpoint
   ↓
7. Return response with sources
```

### Event-Driven Processing (Eventarc)

```
1. Upload PDF to: gs://gcs-rag-watch-bucket/document.pdf
   ↓
2. Cloud Storage triggers Eventarc
   (google.cloud.storage.object.v1.finalized)
   ↓
3. Eventarc → Cloud Run backend
   POST /api/v1/documents/gcs-event
   CloudEvents format (no base64 decoding needed)
   ↓
4. Backend reads file from /watch mount
   ↓
5. Process: PDF → chunks → embeddings → Vertex AI
   ↓
6. Document available in search & chat
```

## Deployment

### Cloud Build

Each service has a `cloudbuild.yaml` for CI/CD:

```bash
# Build and deploy frontend
cd frontend && gcloud builds submit

# Build and deploy backend
cd backend && gcloud builds submit

# Build and deploy LLM service
cd llm_service && gcloud builds submit
```

### Local Development

Use `docker-compose.yml` for local development:

```bash
# Set environment variables
export VERTEX_AI_PROJECT_ID=anb-gpt-prj
export VERTEX_AI_LOCATION=me-central2
export VERTEX_AI_LLM_ENDPOINT_ID=<your-endpoint>

# Start services
docker-compose up --build
```

**Note:** Local development requires:
- GCP credentials (`credentials.json`)
- Vertex AI endpoints accessible

## Security

### Current Implementation

- Cloud Run services with IAM authentication option
- GCS bucket with IAM permissions
- Vertex AI service account roles

### Required IAM Roles

**Cloud Run Service Account:**
```
roles/aiplatform.user           # Vertex AI access
roles/storage.objectAdmin       # GCS access
```

### Production Recommendations

- Enable Cloud Run authentication
- Use Secret Manager for sensitive config
- Enable VPC connector for private networking
- Configure Cloud Armor for DDoS protection
- Enable audit logging

## Performance

### Current Configuration

| Service | Memory | CPU | Min | Max |
|---------|--------|-----|-----|-----|
| Frontend | 512Mi | 1 | 0 | 5 |
| Backend | 4Gi | 2 | 0 | 10 |
| LLM | 2Gi | 2 | 0 | 5 |

### Scaling Considerations

- **Cold starts:** Set min-instances=1 for production
- **Embedding generation:** CPU-bound, consider GPU for higher throughput
- **Vector search:** Scales with Vertex AI infrastructure

### Estimated Performance

| Operation | Time |
|-----------|------|
| Upload 10-page PDF | ~5-10s |
| Generate embeddings (100 chunks) | ~10s |
| Vector search query | <200ms |
| LLM generation | 1-5s |

## Cost Optimization

### Cloud Run
- Scale to zero when idle
- Use committed use discounts for sustained workloads

### Vertex AI Vector Search
- Pay per query and storage
- Use appropriate machine type for endpoints

### Vertex AI Model Garden
- Pay per prediction
- Consider smaller models (7B vs 70B) for cost savings

## Monitoring

### Cloud Logging
```bash
# View backend logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=rag-backend"
```

### Health Checks
- Frontend: `https://rag-frontend-xxx.run.app`
- Backend: `https://rag-backend-xxx.run.app/health`
- LLM: `https://rag-llm-xxx.run.app/api/v1/health`

### Metrics
- Cloud Run metrics in GCP Console
- Custom metrics via `/api/v1/documents/stats/overview`

## Future Enhancements

### Planned

1. **Cloud SQL Migration**
   - Move from SQLite to PostgreSQL
   - Better concurrent access

2. **GPU Support**
   - Faster embedding generation
   - Cloud Run GPU (when available in region)

3. **Authentication**
   - Cloud Identity-Aware Proxy (IAP)
   - User accounts and permissions

4. **Additional Models**
   - Support multiple LLM endpoints
   - Model selection per query

5. **Caching**
   - Memorystore (Redis) for embeddings cache
   - Query result caching

---

**Deployed on:** Google Cloud Platform
**Architecture:** Microservices on Cloud Run
**Vector DB:** Vertex AI Vector Search
**LLM:** Vertex AI Model Garden (Open Source Models)
