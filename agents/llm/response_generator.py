"""
Response generator using LLM.

LLM Agent is responsible for this module.
Generates responses based on orchestrated context.
"""

from typing import Optional, AsyncGenerator
from pydantic import BaseModel, Field
import logging

from orchestrator import (
    OrchestrationResult,
    QueryIntent,
)
from orchestrator.flow.flow_analyzer import FlowAnalysis
from agents.llm.llm_client import get_llm_client, LLMRequest, LLMProvider
from agents.prompts.templates import get_prompt_for_intent

logger = logging.getLogger(__name__)


class ResponseRequest(BaseModel):
    """Request for response generation."""

    orchestration_result: OrchestrationResult = Field(
        ..., description="Result from orchestration"
    )
    stream: bool = Field(default=False, description="Stream response")
    provider: Optional[LLMProvider] = Field(None, description="LLM provider")
    temperature: float = Field(default=0.2, description="Generation temperature")
    max_tokens: int = Field(default=2000, description="Max tokens to generate")


class GeneratedResponse(BaseModel):
    """Generated response."""

    content: str = Field(..., description="Response content")
    query: str = Field(..., description="Original query")
    intent: QueryIntent = Field(..., description="Detected intent")
    sources_count: int = Field(default=0, description="Number of sources used")
    tokens_used: Optional[int] = Field(None, description="Tokens used")
    model: str = Field(..., description="Model used")


class ResponseGenerator:
    """
    Generates responses using LLM based on orchestrated context.

    Combines:
    - Intent classification
    - Retrieved context (graph + vector)
    - Flow analysis (if applicable)
    - Intent-specific prompts
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize response generator.

        Args:
            provider: LLM provider
            model: Model name
        """
        self.llm_client = get_llm_client(provider=provider, model=model)

    def generate(self, request: ResponseRequest) -> GeneratedResponse:
        """
        Generate response synchronously.

        Args:
            request: Response request

        Returns:
            GeneratedResponse with content
        """
        orchestration = request.orchestration_result

        # Create intent-specific prompt
        prompt_dict = self._create_prompt(orchestration)

        # Generate using LLM
        llm_request = LLMRequest(
            system_prompt=prompt_dict["system"],
            user_prompt=prompt_dict["user"],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False,
        )

        llm_response = self.llm_client.generate(llm_request)

        return GeneratedResponse(
            content=llm_response.content,
            query=orchestration.query,
            intent=orchestration.intent,
            sources_count=orchestration.context.total_items if orchestration.context else 0,
            tokens_used=llm_response.tokens_used,
            model=llm_response.model,
        )

    async def generate_async(
        self,
        request: ResponseRequest
    ) -> GeneratedResponse:
        """
        Generate response asynchronously.

        Args:
            request: Response request

        Returns:
            GeneratedResponse with content
        """
        orchestration = request.orchestration_result

        # Create intent-specific prompt
        prompt_dict = self._create_prompt(orchestration)

        # Generate using LLM
        llm_request = LLMRequest(
            system_prompt=prompt_dict["system"],
            user_prompt=prompt_dict["user"],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False,
        )

        llm_response = await self.llm_client.generate_async(llm_request)

        return GeneratedResponse(
            content=llm_response.content,
            query=orchestration.query,
            intent=orchestration.intent,
            sources_count=orchestration.context.total_items if orchestration.context else 0,
            tokens_used=llm_response.tokens_used,
            model=llm_response.model,
        )

    async def generate_stream(
        self,
        request: ResponseRequest
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response.

        Args:
            request: Response request

        Yields:
            Content chunks
        """
        orchestration = request.orchestration_result

        # Create intent-specific prompt
        prompt_dict = self._create_prompt(orchestration)

        # Generate using LLM
        llm_request = LLMRequest(
            system_prompt=prompt_dict["system"],
            user_prompt=prompt_dict["user"],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
        )

        async for chunk in self.llm_client.generate_stream(llm_request):
            yield chunk

    def _create_prompt(
        self,
        orchestration: OrchestrationResult
    ) -> dict[str, str]:
        """Create prompt from orchestration result."""
        # Extract components
        intent = orchestration.intent
        query = orchestration.query
        context = orchestration.context
        flow_analysis = orchestration.flow_analysis

        # Create prompt using template factory
        prompt_dict = get_prompt_for_intent(
            intent=intent,
            query=query,
            context=context,
            flow_analysis=flow_analysis,
        )

        return prompt_dict


def get_response_generator(
    provider: Optional[LLMProvider] = None,
    model: Optional[str] = None,
) -> ResponseGenerator:
    """
    Get response generator instance.

    Args:
        provider: LLM provider
        model: Model name

    Returns:
        ResponseGenerator instance
    """
    return ResponseGenerator(provider=provider, model=model)
