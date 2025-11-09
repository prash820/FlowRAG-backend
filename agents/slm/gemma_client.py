"""
Gemma 3 270M client for intent classification and entity extraction.

SLM Agent is responsible for this module.
Uses HuggingFace transformers for local inference.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import json

from config import get_settings

logger = logging.getLogger(__name__)


class IntentClassificationRequest(BaseModel):
    """Request for intent classification."""
    query: str = Field(..., description="User query to classify")


class IntentClassificationResponse(BaseModel):
    """Response from intent classification."""
    intent: str = Field(..., description="Classified intent")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    reasoning: Optional[str] = Field(None, description="Model reasoning")


class GemmaClient:
    """
    Client for Gemma 3 270M model.

    Used for:
    - Intent classification
    - Entity extraction
    - Query understanding
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
    ):
        """
        Initialize Gemma client.

        Args:
            model_name: HuggingFace model name
            device: Device to run on (cpu/cuda/mps)
        """
        settings = get_settings()

        self.model_name = model_name or settings.slm_model_name
        self.device = device or settings.slm_device
        self.max_length = settings.slm_max_length
        self.temperature = settings.slm_temperature

        # Auto-detect device if not specified
        if self.device == "auto":
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"

        logger.info(f"Initializing Gemma client: {self.model_name} on {self.device}")

        # Load model and tokenizer
        self._load_model()

    def _load_model(self):
        """Load model and tokenizer from HuggingFace."""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
            )

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                device_map=self.device if self.device != "cpu" else None,
                trust_remote_code=True,
            )

            if self.device == "cpu":
                self.model = self.model.to(self.device)

            self.model.eval()

            logger.info(f"Successfully loaded {self.model_name}")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def classify_intent(
        self,
        query: str,
        available_intents: Optional[List[str]] = None,
    ) -> IntentClassificationResponse:
        """
        Classify query intent using Gemma.

        Args:
            query: User query
            available_intents: List of possible intents

        Returns:
            IntentClassificationResponse with intent and entities
        """
        # Default intents from our system
        if available_intents is None:
            available_intents = [
                "find_function",
                "find_class",
                "explain_code",
                "find_usage",
                "trace_calls",
                "find_flow",
                "find_dependencies",
                "optimize_flow",
                "parallel_steps",
                "find_docs",
                "general_question",
                "explore_module",
            ]

        # Create prompt for intent classification
        prompt = self._create_intent_prompt(query, available_intents)

        # Generate response
        response = self._generate(prompt, max_new_tokens=200)

        # Parse response
        return self._parse_intent_response(response, available_intents)

    def extract_entities(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract entities from query.

        Args:
            query: User query
            entity_types: Types of entities to extract

        Returns:
            Dictionary of extracted entities
        """
        if entity_types is None:
            entity_types = ["function_name", "class_name", "file_path", "number"]

        prompt = self._create_entity_prompt(query, entity_types)

        response = self._generate(prompt, max_new_tokens=150)

        return self._parse_entity_response(response)

    def _create_intent_prompt(
        self,
        query: str,
        available_intents: List[str]
    ) -> str:
        """Create prompt for intent classification."""
        intents_str = "\n".join(f"- {intent}" for intent in available_intents)

        prompt = f"""<start_of_turn>user
You are a code query classifier. Classify the user's query into one of the following intents:

{intents_str}

User Query: "{query}"

Respond in JSON format:
{{
    "intent": "the_intent_name",
    "confidence": 0.95,
    "reasoning": "brief explanation"
}}
<end_of_turn>
<start_of_turn>model
"""
        return prompt

    def _create_entity_prompt(
        self,
        query: str,
        entity_types: List[str]
    ) -> str:
        """Create prompt for entity extraction."""
        entities_str = "\n".join(f"- {entity}" for entity in entity_types)

        prompt = f"""<start_of_turn>user
Extract entities from the following query. Look for these entity types:

{entities_str}

User Query: "{query}"

Respond in JSON format:
{{
    "function_name": "extracted_function_name or null",
    "class_name": "extracted_class_name or null",
    "file_path": "extracted/file/path or null",
    "number": 123 or null
}}
<end_of_turn>
<start_of_turn>model
"""
        return prompt

    def _generate(
        self,
        prompt: str,
        max_new_tokens: int = 200,
    ) -> str:
        """
        Generate text using Gemma.

        Args:
            prompt: Input prompt
            max_new_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        try:
            # Tokenize input
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=self.max_length,
            ).to(self.device)

            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=self.temperature,
                    do_sample=True if self.temperature > 0 else False,
                    pad_token_id=self.tokenizer.eos_token_id,
                )

            # Decode
            generated_text = self.tokenizer.decode(
                outputs[0],
                skip_special_tokens=True,
            )

            # Extract only the model's response (after the prompt)
            response = generated_text[len(prompt):].strip()

            return response

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return "{}"

    def _parse_intent_response(
        self,
        response: str,
        available_intents: List[str]
    ) -> IntentClassificationResponse:
        """Parse intent classification response."""
        try:
            # Try to extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                intent = data.get("intent", "general_question")
                confidence = float(data.get("confidence", 0.5))
                reasoning = data.get("reasoning")

                # Validate intent
                if intent not in available_intents:
                    intent = "general_question"
                    confidence = 0.5

                return IntentClassificationResponse(
                    intent=intent,
                    confidence=confidence,
                    entities={},
                    reasoning=reasoning,
                )

        except Exception as e:
            logger.warning(f"Failed to parse intent response: {e}")

        # Fallback
        return IntentClassificationResponse(
            intent="general_question",
            confidence=0.5,
            entities={},
        )

    def _parse_entity_response(self, response: str) -> Dict[str, Any]:
        """Parse entity extraction response."""
        try:
            # Try to extract JSON
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                # Filter out null values
                entities = {
                    k: v for k, v in data.items()
                    if v is not None and v != "null"
                }

                return entities

        except Exception as e:
            logger.warning(f"Failed to parse entity response: {e}")

        return {}


# Singleton instance
_gemma_client: Optional[GemmaClient] = None


def get_gemma_client() -> GemmaClient:
    """Get Gemma client singleton."""
    global _gemma_client
    if _gemma_client is None:
        _gemma_client = GemmaClient()
    return _gemma_client
