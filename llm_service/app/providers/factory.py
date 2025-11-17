"""
Factory pattern for LLM providers
"""
import logging
from .base import BaseLLMProvider
from .gemini import GeminiProvider

logger = logging.getLogger(__name__)


def get_llm_provider(settings) -> BaseLLMProvider:
    """
    Factory function to create LLM provider based on settings

    Args:
        settings: Configuration settings object

    Returns:
        Instance of the appropriate LLM provider

    Raises:
        ValueError: If provider is not supported
    """
    providers = {
        "gemini": GeminiProvider,
        # Future providers can be added here:
        # "openai": OpenAIProvider,
        # "ollama": OllamaProvider,
        # "anthropic": AnthropicProvider,
    }

    provider_name = settings.LLM_PROVIDER.lower()

    if provider_name not in providers:
        available = ", ".join(providers.keys())
        raise ValueError(
            f"Unknown LLM provider: {provider_name}. "
            f"Available providers: {available}"
        )

    logger.info(f"Creating LLM provider: {provider_name}")
    provider_class = providers[provider_name]

    return provider_class(settings)
