"""
Chat API routes - LLM chat with RAG capabilities
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ...services.chat_service import ChatService
from ...services.hybrid_search import HybridSearchService
from ...services.embedding_service import EmbeddingService
from ...services.vector_store import VectorStore
from ...core.config import get_settings

router = APIRouter()
settings = get_settings()

# Services will be initialized on first use
chat_service = None
hybrid_search_service = None


def get_chat_service():
    """Get or create chat service instance"""
    global chat_service, hybrid_search_service

    if hybrid_search_service is None:
        embedding_service = EmbeddingService(
            model_name=settings.EMBEDDING_MODEL,
            batch_size=settings.BATCH_SIZE
        )
        vector_store = VectorStore(
            project_id=settings.GCP_PROJECT_ID,
            region=settings.GCP_REGION,
            index_endpoint_id=settings.VERTEX_AI_INDEX_ENDPOINT_ID,
            deployed_index_id=settings.VERTEX_AI_DEPLOYED_INDEX_ID,
            index_id=settings.VERTEX_AI_INDEX_ID
        )
        hybrid_search_service = HybridSearchService(
            vector_store=vector_store,
            embedding_service=embedding_service
        )

    if chat_service is None:
        chat_service = ChatService(
            llm_service_url=settings.LLM_SERVICE_URL,
            hybrid_search_service=hybrid_search_service
        )

    return chat_service


# Request/Response models
class ContextChunk(BaseModel):
    chunk_id: str
    content: str
    metadata: Dict[str, Any] = {}


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    context_chunks: Optional[List[ContextChunk]] = None
    use_search_tool: bool = False
    system_prompt: Optional[str] = None


class SourceInfo(BaseModel):
    content: str
    metadata: Dict[str, Any] = {}


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[SourceInfo] = []
    usage: Dict[str, int] = {}
    model: str = ""


class HistoryMessage(BaseModel):
    role: str
    content: str


class ConversationHistory(BaseModel):
    conversation_id: str
    messages: List[HistoryMessage]


class HealthResponse(BaseModel):
    status: str
    llm_service: Dict[str, Any] = {}


@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    Send a message to the chat

    - Direct chat: No context, LLM responds from its knowledge
    - RAG chat: Provide context_chunks to use as reference
    - Tool-based chat: Set use_search_tool=True to let LLM search automatically
    """
    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty"
        )

    try:
        service = get_chat_service()

        # Convert context chunks to the format expected by chat service
        context = None
        if request.context_chunks:
            context = [
                {
                    "chunk_id": chunk.chunk_id,
                    "content": chunk.content,
                    "metadata": chunk.metadata
                }
                for chunk in request.context_chunks
            ]

        # Send message to chat service
        result = await service.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            context_chunks=context,
            use_search_tool=request.use_search_tool,
            system_prompt=request.system_prompt
        )

        # Format sources for response
        sources = [
            SourceInfo(
                content=src.get("content", ""),
                metadata=src.get("metadata", {})
            )
            for src in result.get("sources", [])
        ]

        return ChatResponse(
            response=result["response"],
            conversation_id=result["conversation_id"],
            sources=sources,
            usage=result.get("usage", {}),
            model=result.get("model", "")
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )


@router.get("/history/{conversation_id}", response_model=ConversationHistory)
async def get_conversation_history(conversation_id: str):
    """
    Get the conversation history for a given conversation ID
    """
    try:
        service = get_chat_service()
        history = service.get_history(conversation_id)

        if not history and conversation_id not in service.conversations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )

        messages = [
            HistoryMessage(role=msg["role"], content=msg["content"])
            for msg in history
        ]

        return ConversationHistory(
            conversation_id=conversation_id,
            messages=messages
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get history: {str(e)}"
        )


@router.delete("/history/{conversation_id}")
async def clear_conversation_history(conversation_id: str):
    """
    Clear the conversation history for a given conversation ID
    """
    try:
        service = get_chat_service()
        success = service.clear_history(conversation_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )

        return {"message": f"Conversation {conversation_id} cleared successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear history: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
async def check_health():
    """
    Check the health of the chat service and LLM service
    """
    try:
        service = get_chat_service()
        llm_health = await service.health_check()

        overall_status = "healthy" if llm_health.get("status") == "healthy" else "degraded"

        return HealthResponse(
            status=overall_status,
            llm_service=llm_health
        )

    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            llm_service={"error": str(e)}
        )
