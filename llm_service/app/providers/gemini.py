"""
Google Gemini LLM Provider implementation
"""
import logging
from typing import List, Dict, Any, Optional, Generator
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .base import BaseLLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider"""

    def __init__(self, settings):
        """Initialize Gemini provider"""
        super().__init__(settings)

        if not settings.LLM_API_KEY:
            raise ValueError("LLM_API_KEY is required for Gemini provider")

        # Configure the Gemini API
        genai.configure(api_key=settings.LLM_API_KEY)

        # Store generation config for reuse
        self.generation_config = genai.GenerationConfig(
            max_output_tokens=self.max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
        )

        # Store safety settings for reuse
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        # Initialize the model
        self.model_instance = genai.GenerativeModel(
            model_name=self.model,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings
        )

        logger.info(f"Gemini provider initialized with model: {self.model}")

    def _convert_messages_to_gemini_format(
        self,
        messages: List[Dict[str, str]]
    ) -> tuple:
        """
        Convert standard message format to Gemini's format

        Returns:
            Tuple of (system_instruction, history, current_message)
        """
        system_instruction = None
        history = []
        current_message = ""

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                if system_instruction is None:
                    system_instruction = content
                else:
                    system_instruction += f"\n\n{content}"
            elif role == "user":
                if msg == messages[-1]:
                    current_message = content
                else:
                    history.append({"role": "user", "parts": [content]})
            elif role == "assistant" or role == "model":
                history.append({"role": "model", "parts": [content]})

        return system_instruction, history, current_message

    def generate(
        self,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a response using Gemini"""
        try:
            messages = self.build_messages(prompt, context, history, system_prompt)
            system_instruction, chat_history, current_message = self._convert_messages_to_gemini_format(messages)

            # Create a chat session with history
            if system_instruction:
                model_with_system = genai.GenerativeModel(
                    model_name=self.model,
                    generation_config=self.generation_config,
                    safety_settings=self.safety_settings,
                    system_instruction=system_instruction
                )
                chat = model_with_system.start_chat(history=chat_history)
            else:
                chat = self.model_instance.start_chat(history=chat_history)

            # Send message and get response
            response = chat.send_message(current_message)

            # Extract usage information
            usage = {}
            if hasattr(response, 'usage_metadata'):
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count
                }

            return {
                "response": response.text,
                "usage": usage,
                "model": self.model,
                "finish_reason": response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN"
            }

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    def generate_stream(
        self,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """Generate a streaming response using Gemini"""
        try:
            messages = self.build_messages(prompt, context, history, system_prompt)
            system_instruction, chat_history, current_message = self._convert_messages_to_gemini_format(messages)

            # Create a chat session with history
            if system_instruction:
                model_with_system = genai.GenerativeModel(
                    model_name=self.model,
                    generation_config=self.generation_config,
                    safety_settings=self.safety_settings,
                    system_instruction=system_instruction
                )
                chat = model_with_system.start_chat(history=chat_history)
            else:
                chat = self.model_instance.start_chat(history=chat_history)

            # Stream the response
            response = chat.send_message(current_message, stream=True)

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            raise

    def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        context: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response with function calling support"""
        try:
            messages = self.build_messages(prompt, context, history, system_prompt)
            system_instruction, chat_history, current_message = self._convert_messages_to_gemini_format(messages)

            # Convert tools to Gemini function declarations
            gemini_tools = self._convert_tools_to_gemini_format(tools)

            # Create model with tools
            if system_instruction:
                model_with_tools = genai.GenerativeModel(
                    model_name=self.model,
                    generation_config=self.generation_config,
                    safety_settings=self.safety_settings,
                    system_instruction=system_instruction,
                    tools=gemini_tools
                )
            else:
                model_with_tools = genai.GenerativeModel(
                    model_name=self.model,
                    generation_config=self.generation_config,
                    safety_settings=self.safety_settings,
                    tools=gemini_tools
                )

            chat = model_with_tools.start_chat(history=chat_history)
            response = chat.send_message(current_message)

            # Extract tool calls if any
            tool_calls = []
            response_text = ""

            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        tool_calls.append({
                            "name": part.function_call.name,
                            "arguments": dict(part.function_call.args)
                        })
                    elif hasattr(part, 'text') and part.text:
                        response_text += part.text

            # Extract usage
            usage = {}
            if hasattr(response, 'usage_metadata'):
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count
                }

            return {
                "response": response_text,
                "tool_calls": tool_calls,
                "usage": usage,
                "model": self.model
            }

        except Exception as e:
            logger.error(f"Error generating with tools: {e}")
            raise

    def _convert_tools_to_gemini_format(
        self,
        tools: List[Dict[str, Any]]
    ) -> List[Any]:
        """Convert OpenAI-style tool definitions to Gemini format"""
        gemini_tools = []

        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                gemini_tools.append(
                    genai.protos.Tool(
                        function_declarations=[
                            genai.protos.FunctionDeclaration(
                                name=func["name"],
                                description=func.get("description", ""),
                                parameters=genai.protos.Schema(
                                    type=genai.protos.Type.OBJECT,
                                    properties={
                                        k: genai.protos.Schema(
                                            type=self._get_gemini_type(v.get("type", "string")),
                                            description=v.get("description", "")
                                        )
                                        for k, v in func.get("parameters", {}).get("properties", {}).items()
                                    },
                                    required=func.get("parameters", {}).get("required", [])
                                )
                            )
                        ]
                    )
                )

        return gemini_tools

    def _get_gemini_type(self, type_str: str):
        """Convert string type to Gemini proto type"""
        type_map = {
            "string": genai.protos.Type.STRING,
            "number": genai.protos.Type.NUMBER,
            "integer": genai.protos.Type.INTEGER,
            "boolean": genai.protos.Type.BOOLEAN,
            "array": genai.protos.Type.ARRAY,
            "object": genai.protos.Type.OBJECT,
        }
        return type_map.get(type_str, genai.protos.Type.STRING)

    def health_check(self) -> Dict[str, Any]:
        """Check if Gemini API is accessible"""
        try:
            # Try to list models as a health check
            models = genai.list_models()
            model_names = [m.name for m in models if "gemini" in m.name.lower()]

            return {
                "status": "healthy",
                "provider": "gemini",
                "model": self.model,
                "available_models": model_names[:5]  # First 5 models
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "provider": "gemini",
                "error": str(e)
            }
