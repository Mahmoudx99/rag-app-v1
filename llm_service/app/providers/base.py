"""
Abstract base class for LLM providers
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Generator


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers - ensures model-agnostic architecture"""

    def __init__(self, settings):
        """
        Initialize provider with settings

        Args:
            settings: Configuration settings object
        """
        self.settings = settings
        self.model = settings.LLM_MODEL
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.temperature = settings.LLM_TEMPERATURE
        self.top_p = settings.LLM_TOP_P
        self.top_k = settings.LLM_TOP_K

    @abstractmethod
    def generate(
        self,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response from the LLM

        Args:
            prompt: User's message/question
            context: Optional list of context chunks (for RAG)
            history: Optional conversation history
            system_prompt: Optional system instructions
            **kwargs: Additional provider-specific parameters

        Returns:
            Dictionary containing:
                - response: Generated text
                - usage: Token usage statistics
                - model: Model used
        """
        pass

    @abstractmethod
    def generate_stream(
        self,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Generate a streaming response from the LLM

        Args:
            prompt: User's message/question
            context: Optional list of context chunks
            history: Optional conversation history
            system_prompt: Optional system instructions
            **kwargs: Additional parameters

        Yields:
            String chunks of the response as they are generated
        """
        pass

    @abstractmethod
    def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        context: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response with tool/function calling support

        Args:
            prompt: User's message
            tools: List of tool definitions (function schemas)
            context: Optional context chunks
            history: Optional conversation history
            system_prompt: Optional system instructions
            **kwargs: Additional parameters

        Returns:
            Dictionary containing:
                - response: Generated text (may be empty if tool called)
                - tool_calls: List of tool calls requested by the model
                - usage: Token usage statistics
        """
        pass

    def build_messages(
        self,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Build message list for the LLM

        Args:
            prompt: Current user message
            context: Optional RAG context
            history: Conversation history
            system_prompt: System instructions

        Returns:
            List of message dictionaries
        """
        messages = []

        # Add system prompt
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        else:
            # Default system prompt for RAG
            default_system = (
                "You are a helpful AI assistant with access to a knowledge base. "
                "When provided with context from documents, use that information to answer questions accurately. "
                "Always cite your sources when using information from the context. "
                "If you don't have enough information to answer, say so clearly. "
                "Format your responses using Markdown for better readability: "
                "use **bold** for emphasis, bullet points for lists, and code blocks for code. "
                "For mathematical expressions, use LaTeX notation: inline math with $...$ (e.g., $E=mc^2$) "
                "and block equations with $$...$$ (e.g., $$\\int_a^b f(x)dx$$). "
                "Use tables when presenting structured data."
            )
            messages.append({
                "role": "system",
                "content": default_system
            })

        # Add context if provided
        if context:
            context_text = self._format_context(context)
            messages.append({
                "role": "system",
                "content": f"Here is relevant context from the knowledge base:\n\n{context_text}"
            })

        # Add conversation history
        if history:
            for msg in history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

        # Add current user prompt
        messages.append({
            "role": "user",
            "content": prompt
        })

        return messages

    def _format_context(self, context: List[Dict[str, Any]]) -> str:
        """
        Format context chunks into a readable string

        Args:
            context: List of context chunk dictionaries

        Returns:
            Formatted string with numbered context chunks
        """
        formatted_parts = []

        for i, chunk in enumerate(context, 1):
            source = chunk.get("metadata", {}).get("source", "Unknown")
            page = chunk.get("metadata", {}).get("page_number", "N/A")
            content = chunk.get("content", chunk.get("text", ""))

            formatted_parts.append(
                f"[Source {i}: {source}, Page {page}]\n{content}\n"
            )

        return "\n".join(formatted_parts)

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Check if the provider is healthy and can make requests

        Returns:
            Dictionary with health status information
        """
        pass
