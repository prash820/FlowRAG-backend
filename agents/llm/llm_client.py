"""
LLM client for code explanation and reasoning.

LLM Agent is responsible for this module.
Supports OpenAI, Anthropic, or local models.
"""

from typing import Optional, Dict, Any, AsyncGenerator, List
from pydantic import BaseModel, Field
from enum import Enum
import logging
from openai import OpenAI, AsyncOpenAI
from anthropic import Anthropic, AsyncAnthropic

from config import get_settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMRequest(BaseModel):
    """Request for LLM generation."""
    system_prompt: str = Field(..., description="System prompt")
    user_prompt: str = Field(..., description="User prompt")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, gt=0)
    stream: bool = Field(default=False, description="Stream response")


class LLMResponse(BaseModel):
    """Response from LLM."""
    content: str = Field(..., description="Generated content")
    model: str = Field(..., description="Model used")
    tokens_used: Optional[int] = Field(None, description="Tokens used")
    finish_reason: Optional[str] = Field(None, description="Finish reason")


class LLMClient:
    """
    Multi-provider LLM client.

    Supports:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude 3)
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize LLM client.

        Args:
            provider: LLM provider (openai/anthropic)
            model: Model name
        """
        settings = get_settings()

        # Default to OpenAI
        self.provider = provider or LLMProvider.OPENAI

        if self.provider == LLMProvider.OPENAI:
            self.model = model or settings.openai_model
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.async_client = AsyncOpenAI(api_key=settings.openai_api_key)
        elif self.provider == LLMProvider.ANTHROPIC:
            self.model = model or settings.anthropic_model
            if not settings.anthropic_api_key:
                raise ValueError("Anthropic API key not configured")
            self.client = Anthropic(api_key=settings.anthropic_api_key)
            self.async_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        logger.info(f"Initialized LLM client: {self.provider.value} / {self.model}")

    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response from LLM.

        Args:
            request: LLM request

        Returns:
            LLMResponse with generated content
        """
        if self.provider == LLMProvider.OPENAI:
            return self._generate_openai(request)
        elif self.provider == LLMProvider.ANTHROPIC:
            return self._generate_anthropic(request)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def generate_async(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response asynchronously.

        Args:
            request: LLM request

        Returns:
            LLMResponse with generated content
        """
        if self.provider == LLMProvider.OPENAI:
            return await self._generate_openai_async(request)
        elif self.provider == LLMProvider.ANTHROPIC:
            return await self._generate_anthropic_async(request)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def generate_stream(
        self,
        request: LLMRequest
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response.

        Args:
            request: LLM request

        Yields:
            Content chunks
        """
        if self.provider == LLMProvider.OPENAI:
            async for chunk in self._generate_openai_stream(request):
                yield chunk
        elif self.provider == LLMProvider.ANTHROPIC:
            async for chunk in self._generate_anthropic_stream(request):
                yield chunk

    def _generate_openai(self, request: LLMRequest) -> LLMResponse:
        """Generate using OpenAI."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_prompt},
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None
            finish_reason = response.choices[0].finish_reason

            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
            )

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise

    async def _generate_openai_async(self, request: LLMRequest) -> LLMResponse:
        """Generate using OpenAI (async)."""
        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_prompt},
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None
            finish_reason = response.choices[0].finish_reason

            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
            )

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise

    async def _generate_openai_stream(
        self,
        request: LLMRequest
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response from OpenAI."""
        try:
            stream = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_prompt},
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming failed: {e}")
            raise

    def _generate_anthropic(self, request: LLMRequest) -> LLMResponse:
        """Generate using Anthropic."""
        try:
            response = self.client.messages.create(
                model=self.model,
                system=request.system_prompt,
                messages=[
                    {"role": "user", "content": request.user_prompt},
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            content = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            finish_reason = response.stop_reason

            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
            )

        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise

    async def _generate_anthropic_async(self, request: LLMRequest) -> LLMResponse:
        """Generate using Anthropic (async)."""
        try:
            response = await self.async_client.messages.create(
                model=self.model,
                system=request.system_prompt,
                messages=[
                    {"role": "user", "content": request.user_prompt},
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            content = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            finish_reason = response.stop_reason

            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
            )

        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise

    async def _generate_anthropic_stream(
        self,
        request: LLMRequest
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response from Anthropic."""
        try:
            async with self.async_client.messages.stream(
                model=self.model,
                system=request.system_prompt,
                messages=[
                    {"role": "user", "content": request.user_prompt},
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Anthropic streaming failed: {e}")
            raise


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client(
    provider: Optional[LLMProvider] = None,
    model: Optional[str] = None,
) -> LLMClient:
    """
    Get LLM client singleton.

    Args:
        provider: LLM provider
        model: Model name

    Returns:
        LLMClient instance
    """
    global _llm_client
    if _llm_client is None or (provider and _llm_client.provider != provider):
        _llm_client = LLMClient(provider=provider, model=model)
    return _llm_client
