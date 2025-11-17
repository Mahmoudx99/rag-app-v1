"""
LLM Service - FastAPI Application
A microservice for LLM interactions with model-agnostic architecture
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routes import chat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.SERVICE_VERSION,
    description="Model-agnostic LLM service for RAG applications"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for internal service
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    chat.router,
    prefix="/api/v1",
    tags=["chat"]
)


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"LLM Model: {settings.LLM_MODEL}")


@app.get("/")
async def root():
    """Root endpoint - service info"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "status": "running"
    }


@app.get("/health")
async def health():
    """Basic health check endpoint"""
    return {"status": "healthy", "service": settings.SERVICE_NAME}
