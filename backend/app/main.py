"""
RAG Knowledge Base - Main FastAPI Application
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import get_settings
from .core.database import init_db
from .api.routes import documents, search, chat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events
    """
    # Startup
    logger.info("Starting RAG Knowledge Base API...")
    logger.info(f"Project: {settings.PROJECT_NAME} v{settings.VERSION}")

    # Initialize database
    init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down RAG Knowledge Base API...")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="RAG-powered knowledge base with semantic search",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    documents.router,
    prefix=f"{settings.API_V1_PREFIX}/documents",
    tags=["documents"]
)

app.include_router(
    search.router,
    prefix=f"{settings.API_V1_PREFIX}/search",
    tags=["search"]
)

app.include_router(
    chat.router,
    prefix=f"{settings.API_V1_PREFIX}/chat",
    tags=["chat"]
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}
