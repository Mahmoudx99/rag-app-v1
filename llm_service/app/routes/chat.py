"""
Chat API routes for LLM Service
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from ..config import get_settings
from ..providers.factory import get_llm_provider

router = APIRouter()
logger = logging.getLogger(__name__)

# LLM provider will be initialized on first use
llm_provider = None


def get_provider():
    """Get or create LLM provider instance"""
    global llm_provider
    if llm_provider is None:
        settings = get_settings()
        llm_provider = get_llm_provider(settings)
    return llm_provider


# Request/Response models
class ContextChunk(BaseModel):
    content: str
    metadata: Dict[str, Any] = {}


class ChatMessage(BaseModel):
    role: str  # user, assistant, system
    content: str


class GenerateRequest(BaseModel):
    prompt: str
    context: Optional[List[ContextChunk]] = None
    history: Optional[List[ChatMessage]] = None
    system_prompt: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


class GenerateResponse(BaseModel):
    response: str
    usage: Dict[str, int] = {}
    model: str
    finish_reason: str = "STOP"


class ToolDefinition(BaseModel):
    type: str = "function"
    function: Dict[str, Any]


class GenerateWithToolsRequest(BaseModel):
    prompt: str
    tools: List[ToolDefinition]
    context: Optional[List[ContextChunk]] = None
    history: Optional[List[ChatMessage]] = None
    system_prompt: Optional[str] = None


class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]


class GenerateWithToolsResponse(BaseModel):
    response: str
    tool_calls: List[ToolCall] = []
    usage: Dict[str, int] = {}
    model: str


class HealthResponse(BaseModel):
    status: str
    provider: str
    model: str = ""
    available_models: List[str] = []
    error: str = ""


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    Generate a response from the LLM

    - Takes a prompt and optional context/history
    - Returns the generated response with usage statistics
    """
    try:
        provider = get_provider()

        # Convert context to dict format
        context_dicts = None
        if request.context:
            context_dicts = [
                {"content": c.content, "metadata": c.metadata}
                for c in request.context
            ]

        # Convert history to dict format
        history_dicts = None
        if request.history:
            history_dicts = [
                {"role": m.role, "content": m.content}
                for m in request.history
            ]

        # Generate response
        result = provider.generate(
            prompt=request.prompt,
            context=context_dicts,
            history=history_dicts,
            system_prompt=request.system_prompt
        )

        return GenerateResponse(
            response=result["response"],
            usage=result.get("usage", {}),
            model=result.get("model", ""),
            finish_reason=result.get("finish_reason", "STOP")
        )

    except Exception as e:
        logger.error(f"Error generating response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}"
        )


@router.post("/generate/stream")
async def generate_stream(request: GenerateRequest):
    """
    Generate a streaming response from the LLM

    - Returns Server-Sent Events (SSE) stream
    - Each event contains a chunk of the response
    """
    try:
        provider = get_provider()

        # Convert context to dict format
        context_dicts = None
        if request.context:
            context_dicts = [
                {"content": c.content, "metadata": c.metadata}
                for c in request.context
            ]

        # Convert history to dict format
        history_dicts = None
        if request.history:
            history_dicts = [
                {"role": m.role, "content": m.content}
                for m in request.history
            ]

        async def event_generator():
            """Generate SSE events"""
            try:
                for chunk in provider.generate_stream(
                    prompt=request.prompt,
                    context=context_dicts,
                    history=history_dicts,
                    system_prompt=request.system_prompt
                ):
                    # Send each chunk as an SSE event
                    data = json.dumps({"chunk": chunk})
                    yield f"data: {data}\n\n"

                # Send done event
                yield f"data: {json.dumps({'done': True})}\n\n"

            except Exception as e:
                logger.error(f"Error in stream: {e}")
                error_data = json.dumps({"error": str(e)})
                yield f"data: {error_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    except Exception as e:
        logger.error(f"Error setting up stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start stream: {str(e)}"
        )


@router.post("/generate/with-tools", response_model=GenerateWithToolsResponse)
async def generate_with_tools(request: GenerateWithToolsRequest):
    """
    Generate response with tool/function calling support

    - The LLM can decide to call provided tools
    - Returns tool calls and/or text response
    """
    try:
        provider = get_provider()

        # Convert context to dict format
        context_dicts = None
        if request.context:
            context_dicts = [
                {"content": c.content, "metadata": c.metadata}
                for c in request.context
            ]

        # Convert history to dict format
        history_dicts = None
        if request.history:
            history_dicts = [
                {"role": m.role, "content": m.content}
                for m in request.history
            ]

        # Convert tools to dict format
        tools_dicts = [
            {"type": t.type, "function": t.function}
            for t in request.tools
        ]

        # Generate response with tools
        result = provider.generate_with_tools(
            prompt=request.prompt,
            tools=tools_dicts,
            context=context_dicts,
            history=history_dicts,
            system_prompt=request.system_prompt
        )

        # Convert tool calls to response model
        tool_calls = [
            ToolCall(name=tc["name"], arguments=tc["arguments"])
            for tc in result.get("tool_calls", [])
        ]

        return GenerateWithToolsResponse(
            response=result.get("response", ""),
            tool_calls=tool_calls,
            usage=result.get("usage", {}),
            model=result.get("model", "")
        )

    except Exception as e:
        logger.error(f"Error generating with tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate with tools: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check the health of the LLM service

    - Verifies API connectivity
    - Returns available models
    """
    try:
        provider = get_provider()
        health_info = provider.health_check()

        return HealthResponse(
            status=health_info.get("status", "unknown"),
            provider=health_info.get("provider", ""),
            model=health_info.get("model", ""),
            available_models=health_info.get("available_models", []),
            error=health_info.get("error", "")
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            provider="unknown",
            error=str(e)
        )
