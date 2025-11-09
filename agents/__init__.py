"""Agents module for FlowRAG - SLM and LLM agents."""

from .slm import (
    get_gemma_client,
    GemmaClient,
    get_slm_intent_classifier,
    SLMIntentClassifier,
)
from .llm import (
    get_llm_client,
    LLMClient,
    LLMProvider,
    get_response_generator,
    ResponseGenerator,
    ResponseRequest,
    GeneratedResponse,
)
from .prompts import (
    get_prompt_for_intent,
    TemplateFactory,
)

__all__ = [
    # SLM
    "get_gemma_client",
    "GemmaClient",
    "get_slm_intent_classifier",
    "SLMIntentClassifier",
    # LLM
    "get_llm_client",
    "LLMClient",
    "LLMProvider",
    "get_response_generator",
    "ResponseGenerator",
    "ResponseRequest",
    "GeneratedResponse",
    # Prompts
    "get_prompt_for_intent",
    "TemplateFactory",
]
