"""
Query intent classification.

Determines the type of query and appropriate retrieval strategy.
Orchestrator Agent is responsible for this module.
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import re


class QueryIntent(str, Enum):
    """Types of user query intents."""

    # Code search intents
    FIND_FUNCTION = "find_function"
    FIND_CLASS = "find_class"
    EXPLAIN_CODE = "explain_code"
    FIND_USAGE = "find_usage"
    TRACE_CALLS = "trace_calls"

    # Flow analysis intents
    FIND_FLOW = "find_flow"
    FIND_DEPENDENCIES = "find_dependencies"
    OPTIMIZE_FLOW = "optimize_flow"
    PARALLEL_STEPS = "parallel_steps"

    # Documentation intents
    FIND_DOCS = "find_docs"
    GENERAL_QUESTION = "general_question"

    # Exploration intents
    EXPLORE_MODULE = "explore_module"
    OVERVIEW = "overview"


class IntentResult(BaseModel):
    """Result of intent classification."""

    intent: QueryIntent = Field(..., description="Detected intent")
    confidence: float = Field(..., description="Confidence score (0-1)")
    entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted entities (function names, file paths, etc.)"
    )
    requires_graph: bool = Field(..., description="Whether graph traversal is needed")
    requires_vector: bool = Field(..., description="Whether vector search is needed")


class IntentClassifier:
    """
    Classify user query intent using pattern matching.

    TODO: Replace with fine-tuned SLM (Gemma 270M) in Model Agent.
    """

    def __init__(self):
        """Initialize classifier with patterns."""
        self.patterns = self._build_patterns()

    def classify(self, query: str) -> IntentResult:
        """
        Classify query intent.

        Args:
            query: User query string

        Returns:
            IntentResult with detected intent and metadata
        """
        query_lower = query.lower()

        # Check patterns in priority order
        for intent, pattern_info in self.patterns.items():
            for pattern in pattern_info["patterns"]:
                if re.search(pattern, query_lower):
                    # Extract entities
                    entities = self._extract_entities(query, intent)

                    return IntentResult(
                        intent=intent,
                        confidence=pattern_info["confidence"],
                        entities=entities,
                        requires_graph=pattern_info["requires_graph"],
                        requires_vector=pattern_info["requires_vector"],
                    )

        # Default to general question
        return IntentResult(
            intent=QueryIntent.GENERAL_QUESTION,
            confidence=0.5,
            entities={},
            requires_graph=False,
            requires_vector=True,
        )

    def _build_patterns(self) -> Dict[QueryIntent, Dict[str, Any]]:
        """Build pattern matching rules for each intent."""
        return {
            QueryIntent.FIND_FUNCTION: {
                "patterns": [
                    r"(find|show|locate|where is).*function",
                    r"function.*called",
                    r"function.*named",
                ],
                "confidence": 0.9,
                "requires_graph": True,
                "requires_vector": True,
            },
            QueryIntent.FIND_CLASS: {
                "patterns": [
                    r"(find|show|locate).*class",
                    r"class.*called",
                    r"class.*named",
                ],
                "confidence": 0.9,
                "requires_graph": True,
                "requires_vector": True,
            },
            QueryIntent.EXPLAIN_CODE: {
                "patterns": [
                    r"what does.*do",
                    r"how does.*work",
                    r"explain",
                    r"understand",
                ],
                "confidence": 0.85,
                "requires_graph": True,
                "requires_vector": True,
            },
            QueryIntent.FIND_USAGE: {
                "patterns": [
                    r"where.*used",
                    r"who calls",
                    r"called by",
                    r"usage of",
                    r"references to",
                ],
                "confidence": 0.9,
                "requires_graph": True,
                "requires_vector": False,
            },
            QueryIntent.TRACE_CALLS: {
                "patterns": [
                    r"call chain",
                    r"call stack",
                    r"call graph",
                    r"execution path",
                    r"trace.*call",
                ],
                "confidence": 0.9,
                "requires_graph": True,
                "requires_vector": False,
            },
            QueryIntent.FIND_FLOW: {
                "patterns": [
                    r"(deployment|execution|process) flow",
                    r"steps.*process",
                    r"workflow",
                    r"sequence.*steps",
                ],
                "confidence": 0.95,
                "requires_graph": True,
                "requires_vector": True,
            },
            QueryIntent.FIND_DEPENDENCIES: {
                "patterns": [
                    r"depend(s|encies)",
                    r"what.*need",
                    r"prerequisite",
                    r"must.*before",
                    r"required.*run",
                ],
                "confidence": 0.9,
                "requires_graph": True,
                "requires_vector": True,
            },
            QueryIntent.PARALLEL_STEPS: {
                "patterns": [
                    r"(run|execute).*parallel",
                    r"parallel.*step",
                    r"can.*same time",
                    r"concurrent",
                    r"simultaneously",
                ],
                "confidence": 0.95,
                "requires_graph": True,
                "requires_vector": True,
            },
            QueryIntent.OPTIMIZE_FLOW: {
                "patterns": [
                    r"optimi[zs]e",
                    r"improve.*performance",
                    r"faster",
                    r"reduce.*time",
                    r"speed up",
                ],
                "confidence": 0.85,
                "requires_graph": True,
                "requires_vector": True,
            },
            QueryIntent.FIND_DOCS: {
                "patterns": [
                    r"documentation",
                    r"readme",
                    r"guide",
                    r"tutorial",
                ],
                "confidence": 0.9,
                "requires_graph": False,
                "requires_vector": True,
            },
            QueryIntent.EXPLORE_MODULE: {
                "patterns": [
                    r"what.*in.*module",
                    r"show me.*file",
                    r"list.*function",
                    r"overview.*module",
                ],
                "confidence": 0.85,
                "requires_graph": True,
                "requires_vector": False,
            },
        }

    def _extract_entities(self, query: str, intent: QueryIntent) -> Dict[str, Any]:
        """Extract entities from query based on intent."""
        entities = {}

        # Extract function/class names (capitalized words or snake_case)
        if intent in (QueryIntent.FIND_FUNCTION, QueryIntent.FIND_CLASS):
            # Look for quoted strings
            quoted = re.findall(r'["\']([^"\']+)["\']', query)
            if quoted:
                entities["name"] = quoted[0]
            else:
                # Look for camelCase or snake_case
                names = re.findall(r'\b[a-z_][a-z0-9_]*\b', query.lower())
                if names:
                    # Filter out common words
                    common = {"the", "a", "an", "is", "are", "function", "class", "called", "named"}
                    names = [n for n in names if n not in common]
                    if names:
                        entities["name"] = names[-1]  # Take last one

        # Extract file paths
        file_patterns = [
            r'[\w/]+\.py',
            r'[\w/]+\.js',
            r'[\w/]+\.ts',
        ]
        for pattern in file_patterns:
            matches = re.findall(pattern, query)
            if matches:
                entities["file_path"] = matches[0]
                break

        # Extract numbers (for steps, counts, etc.)
        numbers = re.findall(r'\b\d+\b', query)
        if numbers:
            entities["numbers"] = [int(n) for n in numbers]

        return entities


def get_intent_classifier() -> IntentClassifier:
    """Get intent classifier instance."""
    return IntentClassifier()
