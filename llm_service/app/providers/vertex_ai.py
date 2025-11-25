"""
Vertex AI Model Garden LLM Provider implementation
Supports open-source models deployed via Vertex AI endpoints
"""
import logging
from typing import List, Dict, Any, Optional, Generator
from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value

from .base import BaseLLMProvider

logger = logging.getLogger(__name__)


class VertexAIProvider(BaseLLMProvider):
    """Vertex AI Model Garden provider for open-source models"""

    def __init__(self, settings):
        """Initialize Vertex AI provider"""
        super().__init__(settings)

        # Initialize Vertex AI
        aiplatform.init(
            project=settings.VERTEX_AI_PROJECT_ID,
            location=settings.VERTEX_AI_LOCATION
        )

        self.project_id = settings.VERTEX_AI_PROJECT_ID
        self.location = settings.VERTEX_AI_LOCATION
        self.endpoint_id = settings.VERTEX_AI_LLM_ENDPOINT_ID

        # Get the endpoint
        self.endpoint = aiplatform.Endpoint(self.endpoint_id)

        logger.info(
            f"Vertex AI provider initialized - "
            f"Project: {self.project_id}, "
            f"Location: {self.location}, "
            f"Endpoint: {self.endpoint_id}, "
            f"Model: {self.model}"
        )

    def _build_prompt_text(
        self,
        messages: List[Dict[str, str]]
    ) -> str:
        """
        Build a single prompt text from messages for open-source models.
        Uses Llama-style chat format.
        """
        prompt_parts = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                prompt_parts.append(f"<|system|>\n{content}</s>")
            elif role == "user":
                prompt_parts.append(f"<|user|>\n{content}</s>")
            elif role == "assistant":
                prompt_parts.append(f"<|assistant|>\n{content}</s>")

        # Add assistant prompt for the model to complete
        prompt_parts.append("<|assistant|>\n")

        return "\n".join(prompt_parts)

    def generate(
        self,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a response using Vertex AI endpoint"""
        try:
            messages = self.build_messages(prompt, context, history, system_prompt)
            prompt_text = self._build_prompt_text(messages)

            # Prepare the request for the deployed model
            instances = [{"prompt": prompt_text}]

            parameters = {
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "top_k": self.top_k,
            }

            # Make prediction
            response = self.endpoint.predict(
                instances=instances,
                parameters=parameters
            )

            # Extract response text
            predictions = response.predictions
            if predictions and len(predictions) > 0:
                response_text = predictions[0]
                if isinstance(response_text, dict):
                    response_text = response_text.get("generated_text", str(response_text))
            else:
                response_text = ""

            # Clean up the response (remove any trailing tokens)
            response_text = response_text.strip()
            if response_text.endswith("</s>"):
                response_text = response_text[:-4].strip()

            return {
                "response": response_text,
                "usage": {
                    "prompt_tokens": len(prompt_text.split()),
                    "completion_tokens": len(response_text.split()),
                    "total_tokens": len(prompt_text.split()) + len(response_text.split())
                },
                "model": self.model,
                "finish_reason": "stop"
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
        """
        Generate a streaming response using Vertex AI endpoint.
        Note: Streaming depends on the deployed model's capabilities.
        Falls back to non-streaming if not supported.
        """
        try:
            messages = self.build_messages(prompt, context, history, system_prompt)
            prompt_text = self._build_prompt_text(messages)

            instances = [{"prompt": prompt_text}]

            parameters = {
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "top_k": self.top_k,
            }

            # Try streaming prediction if available
            try:
                for response in self.endpoint.predict_stream(
                    instances=instances,
                    parameters=parameters
                ):
                    if response.predictions:
                        for pred in response.predictions:
                            text = pred if isinstance(pred, str) else pred.get("generated_text", "")
                            if text:
                                yield text
            except AttributeError:
                # Streaming not supported, fall back to regular prediction
                logger.info("Streaming not supported, falling back to regular prediction")
                response = self.endpoint.predict(
                    instances=instances,
                    parameters=parameters
                )

                if response.predictions and len(response.predictions) > 0:
                    response_text = response.predictions[0]
                    if isinstance(response_text, dict):
                        response_text = response_text.get("generated_text", str(response_text))

                    # Clean up response
                    response_text = response_text.strip()
                    if response_text.endswith("</s>"):
                        response_text = response_text[:-4].strip()

                    # Yield in chunks to simulate streaming
                    words = response_text.split()
                    chunk_size = 5
                    for i in range(0, len(words), chunk_size):
                        chunk = " ".join(words[i:i + chunk_size])
                        if i > 0:
                            chunk = " " + chunk
                        yield chunk

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
        """
        Generate response with function calling support.
        Note: Tool calling support depends on the deployed model.
        """
        try:
            # Add tool descriptions to the system prompt
            tool_descriptions = self._format_tools_for_prompt(tools)

            enhanced_system_prompt = system_prompt or ""
            enhanced_system_prompt += f"\n\nYou have access to the following tools:\n{tool_descriptions}\n"
            enhanced_system_prompt += (
                "To use a tool, respond with a JSON object in this format:\n"
                '{"tool_call": {"name": "tool_name", "arguments": {"arg1": "value1"}}}\n'
                "If you don't need to use a tool, respond normally."
            )

            # Generate response
            result = self.generate(
                prompt=prompt,
                context=context,
                history=history,
                system_prompt=enhanced_system_prompt,
                **kwargs
            )

            # Parse tool calls from response
            tool_calls = self._extract_tool_calls(result["response"])

            if tool_calls:
                # Remove tool call JSON from response text
                response_text = result["response"]
                for tc in tool_calls:
                    import json
                    tc_json = json.dumps({"tool_call": tc})
                    response_text = response_text.replace(tc_json, "").strip()
                result["response"] = response_text

            return {
                "response": result["response"],
                "tool_calls": tool_calls,
                "usage": result["usage"],
                "model": self.model
            }

        except Exception as e:
            logger.error(f"Error generating with tools: {e}")
            raise

    def _format_tools_for_prompt(self, tools: List[Dict[str, Any]]) -> str:
        """Format tool definitions for inclusion in prompt"""
        tool_strs = []

        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                params = func.get("parameters", {}).get("properties", {})
                param_str = ", ".join([
                    f"{k}: {v.get('type', 'string')}"
                    for k, v in params.items()
                ])
                tool_strs.append(
                    f"- {func['name']}({param_str}): {func.get('description', '')}"
                )

        return "\n".join(tool_strs)

    def _extract_tool_calls(self, response_text: str) -> List[Dict[str, Any]]:
        """Extract tool calls from model response"""
        import json
        import re

        tool_calls = []

        # Look for JSON tool call patterns
        pattern = r'\{"tool_call":\s*\{[^}]+\}\}'
        matches = re.findall(pattern, response_text)

        for match in matches:
            try:
                parsed = json.loads(match)
                if "tool_call" in parsed:
                    tool_calls.append(parsed["tool_call"])
            except json.JSONDecodeError:
                continue

        return tool_calls

    def health_check(self) -> Dict[str, Any]:
        """Check if Vertex AI endpoint is accessible"""
        try:
            # Check endpoint exists and is deployed
            endpoint_info = self.endpoint.gca_resource

            deployed_models = []
            if endpoint_info.deployed_models:
                deployed_models = [
                    dm.display_name or dm.model
                    for dm in endpoint_info.deployed_models
                ]

            return {
                "status": "healthy",
                "provider": "vertex_ai",
                "project": self.project_id,
                "location": self.location,
                "endpoint": self.endpoint_id,
                "model": self.model,
                "deployed_models": deployed_models
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "provider": "vertex_ai",
                "error": str(e)
            }
