"""
Intent classifier using Gemma 3 270M SLM.

SLM Agent is responsible for this module.
Replaces the pattern-based classifier with ML-based classification.
"""

from typing import Dict, Any
from pydantic import BaseModel, Field
import logging

from orchestrator.router.intent_classifier import QueryIntent, IntentResult
from agents.slm.gemma_client import get_gemma_client

logger = logging.getLogger(__name__)


class SLMIntentClassifier:
    """
    Intent classifier using Gemma 3 270M.

    Provides ML-based intent classification and entity extraction
    as an alternative to pattern-based classification.
    """

    def __init__(self):
        """Initialize SLM intent classifier."""
        self.gemma_client = get_gemma_client()

    def classify(self, query: str) -> IntentResult:
        """
        Classify query intent using Gemma SLM.

        Args:
            query: User query

        Returns:
            IntentResult with intent, confidence, and entities
        """
        logger.debug(f"Classifying intent with SLM: {query}")

        # Get available intents
        available_intents = [intent.value for intent in QueryIntent]

        # Classify using Gemma
        classification = self.gemma_client.classify_intent(
            query=query,
            available_intents=available_intents,
        )

        # Extract entities
        entities = self.gemma_client.extract_entities(query)

        # Merge entities from classification
        if classification.entities:
            entities.update(classification.entities)

        # Convert intent string to QueryIntent enum
        try:
            intent_enum = QueryIntent(classification.intent)
        except ValueError:
            logger.warning(f"Unknown intent: {classification.intent}, defaulting to GENERAL_QUESTION")
            intent_enum = QueryIntent.GENERAL_QUESTION
            classification.confidence = 0.5

        # Determine data source requirements
        requires_graph, requires_vector = self._determine_requirements(intent_enum)

        return IntentResult(
            intent=intent_enum,
            confidence=classification.confidence,
            entities=entities,
            requires_graph=requires_graph,
            requires_vector=requires_vector,
        )

    def _determine_requirements(
        self,
        intent: QueryIntent
    ) -> tuple[bool, bool]:
        """Determine if graph or vector search is needed."""
        # Graph-heavy intents
        graph_intents = {
            QueryIntent.FIND_USAGE,
            QueryIntent.TRACE_CALLS,
            QueryIntent.FIND_DEPENDENCIES,
            QueryIntent.FIND_FLOW,
            QueryIntent.PARALLEL_STEPS,
        }

        # Vector-heavy intents
        vector_intents = {
            QueryIntent.FIND_FUNCTION,
            QueryIntent.FIND_CLASS,
            QueryIntent.EXPLAIN_CODE,
            QueryIntent.FIND_DOCS,
            QueryIntent.GENERAL_QUESTION,
        }

        # Some need both
        hybrid_intents = {
            QueryIntent.EXPLORE_MODULE,
            QueryIntent.OPTIMIZE_FLOW,
        }

        if intent in hybrid_intents:
            return True, True
        elif intent in graph_intents:
            return True, False
        elif intent in vector_intents:
            return False, True
        else:
            # Default: use both
            return True, True


def get_slm_intent_classifier() -> SLMIntentClassifier:
    """Get SLM intent classifier instance."""
    return SLMIntentClassifier()
