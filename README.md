# 🧠 RAG Knowledge Base

A modern, production-ready **Retrieval-Augmented Generation (RAG)** web application with semantic search and AI chat capabilities. Upload PDF documents, build an incremental knowledge base, search through your documents using natural language queries, and chat with an AI that can access your knowledge base.

![Architecture](https://img.shields.io/badge/Architecture-Microservices-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
![Gemini](https://img.shields.io/badge/Gemini-4285F4?logo=google&logoColor=white)

## ✨ Features

- **📄 PDF Upload & Processing** - Drag & drop PDF files for automatic text extraction
- **🔍 Hybrid Search** - Combine semantic + keyword search with advanced filters
- **🤖 AI Chat Integration** - Chat with Gemini 2.0 Flash using your documents as context
- **🧠 Autonomous AI Search** - AI can autonomously search your knowledge base
- **📊 Incremental Knowledge Base** - Knowledge base grows with each document
- **🎯 Context Selection** - Select specific chunks as context for AI responses
- **👁️ Context Viewer** - See exactly what context the AI uses to answer
- **🗑️ Document Management** - Easy deletion of documents and their embeddings
- **💾 Persistent Storage** - PostgreSQL + ChromaDB for reliable data storage
- **🐳 Docker-ized** - Complete containerized microservices architecture
- **🎨 Modern UI** - Clean, responsive React interface with tabs
- **⚡ Fast** - Optimized paragraph chunking and batch embedding generation

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│            Modern UI with Search, Chat & Documents           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    Backend API (FastAPI)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │   PDF    │ │ Embedding│ │  Hybrid  │ │   Chat   │      │
│  │ Processor│ │  Service │ │  Search  │ │ Service  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└────────┬──────────┬─────────────┬───────────┬──────────────┘
         │          │             │           │
         ↓          ↓             ↓           ↓
┌──────────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐
│  PostgreSQL  │ │  File   │ │ ChromaDB│ │   LLM Service   │
│  (Metadata)  │ │ Storage │ │(Vectors)│ │ (Gemini 2.0)    │
└──────────────┘ └─────────┘ └─────────┘ └─────────────────┘
```

### Services

1. **Frontend (React + Nginx)**
   - Modern, responsive UI with tabs (Search/Chat/Documents)
   - File upload with progress tracking
   - Hybrid search interface with mode selection
   - Advanced search filters (date, document, boolean)
   - AI chat interface with context viewer
   - Chunk selection for RAG context

2. **Backend (FastAPI)**
   - RESTful API
   - PDF text extraction (plain mode only)
   - Paragraph-based chunking
   - Embedding generation (sentence-transformers)
   - Hybrid search (semantic + keyword with BM25)
   - Chat orchestration with LLM service
   - Vector storage management

3. **LLM Service (Gemini)**
   - Separate Docker container
   - Model-agnostic architecture
   - Gemini 2.0 Flash integration
   - Tool/function calling for autonomous search
   - Conversation history support

4. **PostgreSQL**
   - Document metadata storage
   - Tracking upload history
   - Status management

5. **ChromaDB**
   - Vector embeddings storage
   - Efficient similarity search
   - Persistent storage

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- 4GB RAM minimum (8GB recommended)
- 10GB free disk space

### Installation

1. **Clone and Navigate**
   ```bash
   cd rag_app
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your Gemini API key:
   # LLM_API_KEY=your_gemini_api_key_here
   ```

3. **Start All Services**
   ```bash
   docker-compose up --build
   ```

4. **Access the Application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - LLM Service: http://localhost:8002
   - API Docs: http://localhost:8000/docs

### First Use

1. Open http://localhost:3000
2. Go to **Documents** tab and upload a PDF (drag & drop)
3. Wait for processing to complete
4. Switch to **Search** tab
5. Select search mode (Hybrid/Semantic/Keyword)
6. Enter a natural language query
7. View ranked results with scores
8. **Select chunks** by clicking checkboxes
9. Click **"Chat with Selected"** to use them as AI context
10. Or go to **Chat** tab and enable "Allow AI to search" for autonomous search!

## 📖 Usage

### Uploading Documents

1. Go to the **Documents** tab
2. Drag & drop a PDF or click to browse
3. System will:
   - Extract text using plain mode
   - Chunk text into paragraphs
   - Generate embeddings (384 dimensions)
   - Store in ChromaDB

### Searching

1. Go to the **Search** tab
2. Select search mode:
   - **Hybrid**: Combines semantic + keyword (recommended)
   - **Semantic**: Pure vector similarity
   - **Keyword**: BM25 text matching
3. Adjust semantic weight slider (for hybrid mode)
4. Use **Advanced Search** for filters:
   - Filter by specific documents
   - Date range filtering
   - Boolean operators (AND/NOT/OR terms)
5. Enter your query in natural language
6. View ranked results with:
   - Combined scores
   - Semantic and keyword score breakdown
   - Source documents and page numbers
7. **Select chunks** for AI context by clicking checkboxes
8. Click **"Chat with Selected"** button to start chatting

### AI Chat

1. Go to the **Chat** tab
2. Choose your interaction mode:
   - **Direct chat**: Talk directly to the AI
   - **With context**: Use selected chunks as context
   - **Autonomous search**: Enable "Allow AI to search knowledge base"
3. Type your question
4. View AI response with:
   - Source citations (when using context)
   - **"View Context"** button to see retrieved chunks
   - Token usage statistics
5. Click **"New Chat"** to start fresh conversation

### Managing Documents

1. Go to the **Documents** tab
2. View all uploaded documents with:
   - Metadata (title, author, pages)
   - Processing status
   - Chunk count
3. Delete documents easily
   - Removes from database
   - Deletes file
   - Removes all embeddings

## 🔧 Configuration

### Environment Variables

See `.env.example` for all available configurations.

Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `CHUNK_SIZE` | 1000 | Characters per chunk |
| `CHUNK_OVERLAP` | 200 | Overlap between chunks |
| `EMBEDDING_MODEL` | all-MiniLM-L6-v2 | Sentence transformer model |
| `MAX_UPLOAD_SIZE` | 52428800 | Max file size (50MB) |
| `LLM_API_KEY` | - | Your Gemini API key (required for chat) |
| `LLM_MODEL` | gemini-2.0-flash | LLM model to use |

### Setting Up Gemini API Key

1. Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Add to `.env` file:
   ```bash
   LLM_API_KEY=your_actual_api_key_here
   ```
3. Restart services: `docker-compose restart`

### Customizing Models

To use a different embedding model, edit `.env`:

```bash
# Faster, smaller (384 dims)
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Better quality (768 dims)
EMBEDDING_MODEL=all-mpnet-base-v2

# Multilingual support
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
```

## 📂 Project Structure

```
rag_app/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── documents.py      # Upload, list, delete
│   │   │   ├── search.py         # Hybrid search
│   │   │   └── chat.py           # AI chat orchestration
│   │   ├── core/
│   │   │   ├── config.py         # Configuration
│   │   │   └── database.py       # DB connection
│   │   ├── models/
│   │   │   └── document.py       # SQLAlchemy models
│   │   ├── services/
│   │   │   ├── pdf_processor.py  # PDF extraction
│   │   │   ├── embedding_service.py  # Embeddings
│   │   │   ├── vector_store.py   # ChromaDB interface
│   │   │   ├── hybrid_search.py  # BM25 + Semantic
│   │   │   └── chat_service.py   # LLM orchestration
│   │   └── main.py               # FastAPI app
│   ├── Dockerfile
│   ├── requirements.txt
│   └── requirements-chat.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SearchBar.js      # Search with mode selector
│   │   │   ├── SearchResults.js  # Results with chunk selection
│   │   │   ├── AdvancedSearch.js # Filter panel
│   │   │   ├── ChatInterface.js  # AI chat UI
│   │   │   └── ...
│   │   ├── services/
│   │   │   └── api.js            # API client (search, chat, docs)
│   │   ├── App.js
│   │   └── index.js
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── llm_service/                  # LLM microservice
│   ├── app/
│   │   ├── providers/
│   │   │   ├── base.py           # Abstract provider
│   │   │   ├── gemini.py         # Gemini implementation
│   │   │   └── factory.py        # Provider factory
│   │   ├── routes/chat.py        # LLM API endpoints
│   │   ├── config.py
│   │   └── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── data/                         # Persistent data
│   ├── uploads/                  # PDF files
│   ├── chromadb/                 # Vector embeddings
│   └── postgres/                 # Database data
├── docker-compose.yml
├── .env                          # Environment config (API keys)
├── ARCHITECTURE.md               # Detailed architecture docs
└── README.md
```

## 🔌 API Endpoints

### Documents

- `POST /api/v1/documents/upload` - Upload PDF
- `GET /api/v1/documents/` - List all documents
- `GET /api/v1/documents/{id}` - Get document details
- `DELETE /api/v1/documents/{id}` - Delete document
- `GET /api/v1/documents/stats/overview` - Get statistics

### Search

- `POST /api/v1/search/` - Hybrid search with filters

Example:
```bash
curl -X POST http://localhost:8000/api/v1/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is artificial intelligence?",
    "top_k": 5,
    "search_mode": "hybrid",
    "semantic_weight": 0.7
  }'
```

### Chat

- `POST /api/v1/chat/` - Send chat message
- `GET /api/v1/chat/history/{id}` - Get conversation history
- `DELETE /api/v1/chat/history/{id}` - Clear conversation
- `GET /api/v1/chat/health` - Check LLM service health

Example:
```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the key findings in the documents?",
    "use_search_tool": true
  }'
```

## 🛠️ Development

### Backend Development

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm start
```

### Running Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

## 🐳 Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild and restart
docker-compose up --build

# Clean everything (including data)
docker-compose down -v
```

## 📊 Performance

- **Embedding Generation**: ~500-1000 chunks/second (CPU)
- **Search Latency**: <100ms for 10k documents
- **Upload Processing**: Depends on PDF size and complexity
- **Memory Usage**: ~2-4GB total (all services)

## 🔒 Security Considerations

For production deployment:

1. Change default PostgreSQL credentials
2. Add authentication/authorization
3. Enable HTTPS
4. Set up rate limiting
5. Configure CORS properly
6. Use environment-specific configs
7. Regular backups of data volumes

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- [ ] Add user authentication
- [ ] Support more file types (DOCX, TXT, etc.)
- [ ] Add more LLM providers (OpenAI, Claude, Ollama)
- [ ] Streaming chat responses
- [ ] Chat history persistence (database)
- [ ] Batch upload support
- [ ] Export search results
- [ ] GPU support for embeddings
- [ ] Response caching

## 📄 License

MIT License - feel free to use for any purpose

## 🙏 Acknowledgments

- **pdfminer.six** - PDF text extraction
- **sentence-transformers** - Embedding generation
- **ChromaDB** - Vector database
- **FastAPI** - Backend framework
- **React** - Frontend framework
- **Google Gemini** - LLM integration
- **rank-bm25** - Keyword search

## 📞 Support

For issues, questions, or contributions:
- Check the API docs: http://localhost:8000/docs
- Review logs: `docker-compose logs -f`
- Check LLM service: `docker-compose logs llm`
- Restart services: `docker-compose restart`
- View architecture: [ARCHITECTURE.md](ARCHITECTURE.md)

---

Built with ❤️ for intelligent document management, semantic search, and AI-powered knowledge retrieval
