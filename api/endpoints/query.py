"""
Query API endpoints.

API Layer is responsible for this module.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
import logging
import time
import json
from typing import AsyncGenerator

from api.schemas import (
    QueryRequest,
    QueryResponse,
    ContextItemResponse,
    StreamChunk,
)
from orchestrator import (
    get_orchestrator,
    OrchestrationRequest,
)
from agents.llm import (
    get_response_generator,
    ResponseRequest,
    LLMProvider,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
async def query_codebase(request: QueryRequest) -> QueryResponse:
    """
    Query the codebase and get an AI-generated response.

    Non-streaming endpoint that returns complete response.
    """
    logger.info(f"Query: '{request.query}' in namespace: {request.namespace}")
    start_time = time.time()

    try:
        # Step 1: Orchestrate (classify intent, retrieve, assemble context)
        orchestrator = get_orchestrator(
            max_context_tokens=request.max_context_tokens
        )

        orchestration_request = OrchestrationRequest(
            query=request.query,
            namespace=request.namespace,
            max_results=request.max_results,
            max_context_tokens=request.max_context_tokens,
            include_flow_analysis=request.include_flow_analysis,
        )

        orchestration_result = orchestrator.orchestrate(orchestration_request)

        # Step 2: Generate response using LLM
        provider = None
        if request.provider:
            provider = LLMProvider(request.provider)

        response_generator = get_response_generator(provider=provider)

        response_request = ResponseRequest(
            orchestration_result=orchestration_result,
            stream=False,
            temperature=request.temperature,
        )

        generated_response = await response_generator.generate_async(response_request)

        # Step 3: Format response
        context_items = []
        if orchestration_result.context:
            for item in orchestration_result.context.items:
                context_items.append(ContextItemResponse(
                    content=item.content,
                    source_type=item.source_type,
                    relevance_score=item.relevance_score,
                    citation=item.citation,
                    metadata=item.metadata,
                ))

        # Format flow analysis if present
        flow_analysis = None
        if orchestration_result.flow_analysis:
            flow_analysis = {
                "flow_id": orchestration_result.flow_analysis.flow_id,
                "total_steps": orchestration_result.flow_analysis.total_steps,
                "parallel_groups": orchestration_result.flow_analysis.parallel_groups,
                "critical_path": orchestration_result.flow_analysis.critical_path,
                "speedup_potential": orchestration_result.flow_analysis.speedup_potential,
                "recommendations": orchestration_result.flow_analysis.recommendations,
            }

        total_time = time.time() - start_time

        return QueryResponse(
            answer=generated_response.content,
            query=request.query,
            intent=orchestration_result.intent.value,
            intent_confidence=orchestration_result.intent_confidence,
            context_items=context_items,
            sources_count=len(context_items),
            flow_analysis=flow_analysis,
            model=generated_response.model,
            tokens_used=generated_response.tokens_used,
            retrieval_time=orchestration_result.total_retrieval_time,
            total_time=total_time,
        )

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )


@router.post("/stream")
async def query_codebase_stream(request: QueryRequest):
    """
    Query the codebase and stream the AI-generated response.

    Streaming endpoint that returns response chunks in real-time.
    """
    logger.info(f"Streaming query: '{request.query}' in namespace: {request.namespace}")

    async def generate_stream() -> AsyncGenerator[str, None]:
        """Generate streaming response."""
        try:
            # Step 1: Orchestrate
            orchestrator = get_orchestrator(
                max_context_tokens=request.max_context_tokens
            )

            orchestration_request = OrchestrationRequest(
                query=request.query,
                namespace=request.namespace,
                max_results=request.max_results,
                max_context_tokens=request.max_context_tokens,
                include_flow_analysis=request.include_flow_analysis,
            )

            orchestration_result = orchestrator.orchestrate(orchestration_request)

            # Send metadata chunk first
            metadata = {
                "type": "metadata",
                "intent": orchestration_result.intent.value,
                "intent_confidence": orchestration_result.intent_confidence,
                "sources_count": orchestration_result.context.total_items if orchestration_result.context else 0,
            }
            yield f"data: {json.dumps(metadata)}\n\n"

            # Step 2: Stream response from LLM
            provider = None
            if request.provider:
                provider = LLMProvider(request.provider)

            response_generator = get_response_generator(provider=provider)

            response_request = ResponseRequest(
                orchestration_result=orchestration_result,
                stream=True,
                temperature=request.temperature,
            )

            # Stream content chunks
            async for chunk in response_generator.generate_stream(response_request):
                chunk_data = StreamChunk(chunk=chunk, done=False)
                yield f"data: {chunk_data.model_dump_json()}\n\n"

            # Send final chunk
            final_chunk = StreamChunk(chunk="", done=True)
            yield f"data: {final_chunk.model_dump_json()}\n\n"

        except Exception as e:
            logger.error(f"Streaming query failed: {e}", exc_info=True)
            error_chunk = {
                "type": "error",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
