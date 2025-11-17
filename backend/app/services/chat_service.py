"""
Chat orchestration service - coordinates between LLM service and search
"""
import logging
import httpx
from typing import List, Dict, Any, Optional
import uuid

logger = logging.getLogger(__name__)


class ChatService:
    """
    Orchestrates chat interactions between the LLM service and search functionality.
    Manages conversation history and context injection.
    """

    def __init__(self, llm_service_url: str, hybrid_search_service=None):
        """
        Initialize chat service

        Args:
            llm_service_url: URL of the LLM microservice
            hybrid_search_service: Optional HybridSearchService for tool-based search
        """
        self.llm_service_url = llm_service_url.rstrip('/')
        self.search_service = hybrid_search_service
        self.conversations: Dict[str, List[Dict[str, str]]] = {}

        logger.info(f"Chat service initialized with LLM service at: {self.llm_service_url}")

    def _get_or_create_conversation(self, conversation_id: Optional[str] = None) -> str:
        """Get existing or create new conversation"""
        if conversation_id and conversation_id in self.conversations:
            return conversation_id

        new_id = str(uuid.uuid4())
        self.conversations[new_id] = []
        return new_id

    def _add_to_history(self, conversation_id: str, role: str, content: str):
        """Add message to conversation history"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id].append({
                "role": role,
                "content": content
            })

    def get_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """Get conversation history"""
        return self.conversations.get(conversation_id, [])

    def clear_history(self, conversation_id: str) -> bool:
        """Clear conversation history"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False

    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        context_chunks: Optional[List[Dict[str, Any]]] = None,
        use_search_tool: bool = False,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a chat message and get response

        Args:
            message: User's message
            conversation_id: Optional conversation ID for history
            context_chunks: Optional pre-selected context chunks
            use_search_tool: Whether to allow LLM to use search as a tool
            system_prompt: Optional custom system prompt

        Returns:
            Dictionary with response, sources, and conversation_id
        """
        try:
            conv_id = self._get_or_create_conversation(conversation_id)
            history = self.get_history(conv_id)
            sources = []

            # Format context chunks
            formatted_context = None
            if context_chunks:
                formatted_context = [
                    {
                        "content": chunk.get("content", ""),
                        "metadata": chunk.get("metadata", {})
                    }
                    for chunk in context_chunks
                ]
                sources = context_chunks

            # If use_search_tool is enabled, use tool calling
            if use_search_tool and self.search_service:
                response_data = await self._chat_with_tools(
                    message=message,
                    history=history,
                    context=formatted_context,
                    system_prompt=system_prompt
                )
                sources.extend(response_data.get("sources", []))
                response_text = response_data["response"]
            else:
                # Direct LLM call
                response_data = await self._call_llm_generate(
                    prompt=message,
                    context=formatted_context,
                    history=history,
                    system_prompt=system_prompt
                )
                response_text = response_data["response"]

            # Update conversation history
            self._add_to_history(conv_id, "user", message)
            self._add_to_history(conv_id, "assistant", response_text)

            return {
                "response": response_text,
                "conversation_id": conv_id,
                "sources": sources,
                "usage": response_data.get("usage", {}),
                "model": response_data.get("model", "")
            }

        except Exception as e:
            logger.error(f"Error in chat: {e}")
            raise

    async def _call_llm_generate(
        self,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Call the LLM service generate endpoint"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "prompt": prompt,
                "context": context,
                "history": history,
                "system_prompt": system_prompt
            }

            response = await client.post(
                f"{self.llm_service_url}/api/v1/generate",
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def _chat_with_tools(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        context: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Chat with LLM using search as a tool.
        The LLM can decide to search the knowledge base.
        """
        # Define the search tool
        search_tool = {
            "type": "function",
            "function": {
                "name": "search_knowledge_base",
                "description": "Search the knowledge base for relevant information. Use this when you need to find specific information from the documents.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to find relevant information"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return (default: 5)"
                        }
                    },
                    "required": ["query"]
                }
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            # First call with tools
            payload = {
                "prompt": message,
                "tools": [search_tool],
                "context": context,
                "history": history,
                "system_prompt": system_prompt
            }

            response = await client.post(
                f"{self.llm_service_url}/api/v1/generate/with-tools",
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            # Check if the LLM wants to use the search tool
            sources = []
            if result.get("tool_calls"):
                for tool_call in result["tool_calls"]:
                    if tool_call["name"] == "search_knowledge_base":
                        # Execute the search
                        search_query = tool_call["arguments"].get("query", message)
                        top_k = int(tool_call["arguments"].get("top_k", 5))

                        search_results = self.search_service.hybrid_search(
                            query=search_query,
                            n_results=top_k
                        )

                        # Format search results as context
                        search_context = []
                        for i in range(len(search_results["ids"])):
                            chunk = {
                                "content": search_results["documents"][i],
                                "metadata": search_results["metadatas"][i]
                            }
                            search_context.append(chunk)
                            sources.append(chunk)

                        # Now call LLM again with the search results
                        final_payload = {
                            "prompt": message,
                            "context": search_context,
                            "history": history,
                            "system_prompt": system_prompt
                        }

                        final_response = await client.post(
                            f"{self.llm_service_url}/api/v1/generate",
                            json=final_payload
                        )
                        final_response.raise_for_status()
                        final_result = final_response.json()

                        return {
                            "response": final_result["response"],
                            "sources": sources,
                            "usage": final_result.get("usage", {}),
                            "model": final_result.get("model", "")
                        }

            # No tool calls, return the direct response
            return {
                "response": result.get("response", ""),
                "sources": sources,
                "usage": result.get("usage", {}),
                "model": result.get("model", "")
            }

    async def health_check(self) -> Dict[str, Any]:
        """Check if LLM service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.llm_service_url}/api/v1/health")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"LLM service health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
