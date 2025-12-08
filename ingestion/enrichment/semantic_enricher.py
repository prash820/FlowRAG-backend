"""
Semantic Enrichment Service for Code Units.

Uses LLM to generate natural language summaries and metadata
for code units, improving semantic search relevance.

Ingestion Agent is responsible for this module.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from agents.llm import get_llm_client, LLMRequest
from ingestion.parsers.base import CodeUnit

logger = logging.getLogger(__name__)


class EnrichedCodeUnit(BaseModel):
    """Code unit with semantic enrichment."""

    # Original code unit fields
    id: str
    name: str
    code_unit_type: str
    file_path: str
    language: str
    code: str
    signature: Optional[str] = None
    docstring: Optional[str] = None
    line_start: int
    line_end: int
    namespace: str

    # Enrichment fields
    semantic_summary: str = Field(
        ...,
        description="Natural language description of what this code does"
    )
    purpose: str = Field(
        ...,
        description="High-level purpose category (e.g., 'authentication', 'data fetching')"
    )
    domain_concepts: List[str] = Field(
        default_factory=list,
        description="Domain concepts and keywords for this code"
    )
    related_features: List[str] = Field(
        default_factory=list,
        description="Related features and functionality"
    )

    # Combined embedding text (what we'll actually embed)
    embedding_text: str = Field(
        ...,
        description="Combined text optimized for embedding"
    )


class ServiceDocumentation(BaseModel):
    """Service-level documentation for a namespace."""

    namespace: str
    service_name: str
    description: str = Field(..., description="What this service does")
    purpose: str = Field(..., description="Why this service exists")
    key_features: List[str] = Field(default_factory=list)
    main_components: List[str] = Field(default_factory=list)
    external_dependencies: List[str] = Field(default_factory=list)
    api_patterns: List[str] = Field(default_factory=list)

    # Full documentation text for embedding
    full_documentation: str = Field(..., description="Complete documentation text")


class GlossaryTerm(BaseModel):
    """Domain term or acronym."""

    term: str
    full_name: Optional[str] = None
    description: str
    related_services: List[str] = Field(default_factory=list)
    related_code_ids: List[str] = Field(default_factory=list)
    usage_context: str = Field(default="", description="How this term is used")


class SemanticEnricher:
    """
    Enriches code units with semantic metadata using LLM.

    Features:
    - Generate natural language summaries for code
    - Extract domain concepts and keywords
    - Create service-level documentation
    - Build glossary of domain terms
    """

    def __init__(
        self,
        batch_size: int = 10,
        max_concurrent: int = 5,
    ):
        """
        Initialize semantic enricher.

        Args:
            batch_size: Number of code units to process in one LLM call
            max_concurrent: Maximum concurrent LLM requests
        """
        self.llm_client = get_llm_client()
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)

    def enrich_code_unit(self, code_unit: CodeUnit) -> EnrichedCodeUnit:
        """
        Enrich a single code unit with semantic metadata.

        Args:
            code_unit: Code unit to enrich

        Returns:
            EnrichedCodeUnit with semantic metadata
        """
        # Build prompt for LLM
        prompt = self._build_enrichment_prompt(code_unit)

        try:
            llm_request = LLMRequest(
                system_prompt=self._get_system_prompt(),
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=500,
                stream=False,
            )

            response = self.llm_client.generate(llm_request)

            # Parse LLM response
            enrichment = self._parse_enrichment_response(response.content, code_unit)

            return enrichment

        except Exception as e:
            logger.warning(f"Failed to enrich {code_unit.name}: {e}")
            # Return basic enrichment on failure
            return self._create_basic_enrichment(code_unit)

    async def enrich_code_unit_async(self, code_unit: CodeUnit) -> EnrichedCodeUnit:
        """Async version of enrich_code_unit."""
        prompt = self._build_enrichment_prompt(code_unit)

        try:
            llm_request = LLMRequest(
                system_prompt=self._get_system_prompt(),
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=500,
                stream=False,
            )

            response = await self.llm_client.generate_async(llm_request)
            return self._parse_enrichment_response(response.content, code_unit)

        except Exception as e:
            logger.warning(f"Failed to enrich {code_unit.name}: {e}")
            return self._create_basic_enrichment(code_unit)

    def enrich_batch(
        self,
        code_units: List[CodeUnit],
        progress_callback: Optional[callable] = None,
    ) -> List[EnrichedCodeUnit]:
        """
        Enrich multiple code units efficiently.

        Args:
            code_units: List of code units to enrich
            progress_callback: Optional callback for progress updates

        Returns:
            List of enriched code units
        """
        enriched = []
        total = len(code_units)

        for i, unit in enumerate(code_units):
            enriched_unit = self.enrich_code_unit(unit)
            enriched.append(enriched_unit)

            if progress_callback:
                progress_callback(i + 1, total, unit.name)

            if (i + 1) % 10 == 0:
                logger.info(f"Enriched {i + 1}/{total} code units")

        return enriched

    async def enrich_batch_async(
        self,
        code_units: List[CodeUnit],
        progress_callback: Optional[callable] = None,
    ) -> List[EnrichedCodeUnit]:
        """
        Enrich multiple code units asynchronously.

        Args:
            code_units: List of code units to enrich
            progress_callback: Optional callback for progress updates

        Returns:
            List of enriched code units
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def enrich_with_semaphore(unit: CodeUnit) -> EnrichedCodeUnit:
            async with semaphore:
                return await self.enrich_code_unit_async(unit)

        tasks = [enrich_with_semaphore(unit) for unit in code_units]
        enriched = await asyncio.gather(*tasks)

        logger.info(f"Enriched {len(enriched)} code units")
        return list(enriched)

    def generate_service_documentation(
        self,
        namespace: str,
        code_units: List[CodeUnit],
    ) -> ServiceDocumentation:
        """
        Generate service-level documentation from code units.

        Args:
            namespace: Service namespace
            code_units: All code units in the service

        Returns:
            ServiceDocumentation for the namespace
        """
        # Summarize the service based on its code
        prompt = self._build_service_doc_prompt(namespace, code_units)

        try:
            llm_request = LLMRequest(
                system_prompt=self._get_service_doc_system_prompt(),
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=1000,
                stream=False,
            )

            response = self.llm_client.generate(llm_request)
            return self._parse_service_doc_response(response.content, namespace)

        except Exception as e:
            logger.error(f"Failed to generate service documentation: {e}")
            return self._create_basic_service_doc(namespace, code_units)

    def extract_glossary_terms(
        self,
        namespace: str,
        code_units: List[CodeUnit],
    ) -> List[GlossaryTerm]:
        """
        Extract domain terms and acronyms from code.

        Args:
            namespace: Service namespace
            code_units: Code units to analyze

        Returns:
            List of glossary terms
        """
        prompt = self._build_glossary_prompt(namespace, code_units)

        try:
            llm_request = LLMRequest(
                system_prompt=self._get_glossary_system_prompt(),
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=800,
                stream=False,
            )

            response = self.llm_client.generate(llm_request)
            return self._parse_glossary_response(response.content, namespace)

        except Exception as e:
            logger.error(f"Failed to extract glossary: {e}")
            return []

    def _get_system_prompt(self) -> str:
        """Get system prompt for code enrichment."""
        return """You are a code documentation expert. Your task is to analyze code and provide:
1. A clear, concise summary of what the code does (1-2 sentences)
2. The high-level purpose category
3. Key domain concepts and keywords
4. Related features and functionality

Respond in this exact format:
SUMMARY: <1-2 sentence description of what this code does>
PURPOSE: <single category like: authentication, data fetching, UI rendering, API endpoint, database operation, validation, etc.>
CONCEPTS: <comma-separated domain concepts and keywords>
FEATURES: <comma-separated related features>

Be specific and technical. Focus on WHAT the code does, not HOW it's implemented."""

    def _get_service_doc_system_prompt(self) -> str:
        """Get system prompt for service documentation."""
        return """You are a technical documentation expert. Analyze the provided code units and create comprehensive service documentation.

Respond in this exact format:
SERVICE_NAME: <human-readable service name>
DESCRIPTION: <2-3 sentence description of what this service does>
PURPOSE: <why this service exists and what problem it solves>
KEY_FEATURES: <comma-separated list of main features>
MAIN_COMPONENTS: <comma-separated list of main components/modules>
EXTERNAL_DEPS: <comma-separated external services/APIs this depends on>
API_PATTERNS: <comma-separated API patterns used, e.g., REST, GraphQL, OAuth>

Be concise but comprehensive. Focus on the service's role in the larger system."""

    def _get_glossary_system_prompt(self) -> str:
        """Get system prompt for glossary extraction."""
        return """You are a domain expert. Extract important terms, acronyms, and domain-specific vocabulary from the code.

For each term, provide:
TERM: <the term or acronym>
FULL_NAME: <full name if it's an acronym, otherwise leave blank>
DESCRIPTION: <brief description of what it means in this context>
CONTEXT: <how it's used in the codebase>

List up to 10 important terms, one per block, separated by ---"""

    def _build_enrichment_prompt(self, code_unit: CodeUnit) -> str:
        """Build prompt for enriching a code unit."""
        parts = [
            f"Language: {code_unit.language}",
            f"Type: {code_unit.type.value}",
            f"Name: {code_unit.name}",
        ]

        if code_unit.signature:
            parts.append(f"Signature: {code_unit.signature}")

        if code_unit.docstring:
            parts.append(f"Docstring: {code_unit.docstring}")

        # Include code (truncated if too long)
        code = code_unit.code[:1500] if len(code_unit.code) > 1500 else code_unit.code
        parts.append(f"Code:\n```{code_unit.language}\n{code}\n```")

        return "\n".join(parts)

    def _build_service_doc_prompt(
        self,
        namespace: str,
        code_units: List[CodeUnit]
    ) -> str:
        """Build prompt for service documentation."""
        # Summarize the code units
        unit_summaries = []
        for unit in code_units[:30]:  # Limit to first 30 units
            summary = f"- {unit.type.value}: {unit.name}"
            if unit.signature:
                summary += f" ({unit.signature})"
            unit_summaries.append(summary)

        return f"""Service Namespace: {namespace}

Code Units ({len(code_units)} total):
{chr(10).join(unit_summaries)}

Based on these code units, generate comprehensive service documentation."""

    def _build_glossary_prompt(
        self,
        namespace: str,
        code_units: List[CodeUnit],
    ) -> str:
        """Build prompt for glossary extraction."""
        # Extract all names and identify potential terms
        names = set()
        for unit in code_units:
            names.add(unit.name)
            # Extract potential acronyms (all caps words)
            words = unit.name.replace("_", " ").split()
            for word in words:
                if word.isupper() and len(word) >= 2:
                    names.add(word)

        return f"""Service: {namespace}

Code element names:
{', '.join(sorted(names)[:50])}

Extract important domain terms, acronyms, and vocabulary from these names."""

    def _parse_enrichment_response(
        self,
        response: str,
        code_unit: CodeUnit
    ) -> EnrichedCodeUnit:
        """Parse LLM response into EnrichedCodeUnit."""
        # Parse the structured response
        summary = ""
        purpose = ""
        concepts = []
        features = []

        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("SUMMARY:"):
                summary = line[8:].strip()
            elif line.startswith("PURPOSE:"):
                purpose = line[8:].strip()
            elif line.startswith("CONCEPTS:"):
                concepts = [c.strip() for c in line[9:].split(",") if c.strip()]
            elif line.startswith("FEATURES:"):
                features = [f.strip() for f in line[9:].split(",") if f.strip()]

        # Fallback if parsing failed
        if not summary:
            summary = f"{code_unit.type.value} {code_unit.name}"
        if not purpose:
            purpose = "general"

        # Build optimized embedding text
        embedding_text = self._build_embedding_text(
            code_unit, summary, purpose, concepts
        )

        return EnrichedCodeUnit(
            id=code_unit.id,
            name=code_unit.name,
            code_unit_type=code_unit.type.value,
            file_path=code_unit.file_path,
            language=code_unit.language,
            code=code_unit.code,
            signature=code_unit.signature,
            docstring=code_unit.docstring,
            line_start=code_unit.line_start,
            line_end=code_unit.line_end,
            namespace=code_unit.namespace,
            semantic_summary=summary,
            purpose=purpose,
            domain_concepts=concepts,
            related_features=features,
            embedding_text=embedding_text,
        )

    def _create_basic_enrichment(self, code_unit: CodeUnit) -> EnrichedCodeUnit:
        """Create basic enrichment when LLM fails."""
        # Generate basic summary from available info
        summary = f"{code_unit.type.value} named {code_unit.name}"
        if code_unit.docstring:
            summary = code_unit.docstring[:200]

        embedding_text = self._build_embedding_text(
            code_unit, summary, "general", []
        )

        return EnrichedCodeUnit(
            id=code_unit.id,
            name=code_unit.name,
            code_unit_type=code_unit.type.value,
            file_path=code_unit.file_path,
            language=code_unit.language,
            code=code_unit.code,
            signature=code_unit.signature,
            docstring=code_unit.docstring,
            line_start=code_unit.line_start,
            line_end=code_unit.line_end,
            namespace=code_unit.namespace,
            semantic_summary=summary,
            purpose="general",
            domain_concepts=[],
            related_features=[],
            embedding_text=embedding_text,
        )

    def _build_embedding_text(
        self,
        code_unit: CodeUnit,
        summary: str,
        purpose: str,
        concepts: List[str],
    ) -> str:
        """
        Build optimized text for embedding.

        This combines semantic summary with code structure
        to create embeddings that match both natural language
        queries and code-specific searches.
        """
        parts = [
            f"Function: {code_unit.name}",
            f"Purpose: {summary}",
            f"Category: {purpose}",
        ]

        if concepts:
            parts.append(f"Keywords: {', '.join(concepts)}")

        if code_unit.signature:
            parts.append(f"Signature: {code_unit.signature}")

        if code_unit.docstring:
            parts.append(f"Documentation: {code_unit.docstring[:300]}")

        # Include a snippet of code for code-specific searches
        code_snippet = code_unit.code[:300] if len(code_unit.code) > 300 else code_unit.code
        parts.append(f"Code: {code_snippet}")

        return "\n".join(parts)

    def _parse_service_doc_response(
        self,
        response: str,
        namespace: str,
    ) -> ServiceDocumentation:
        """Parse service documentation response."""
        service_name = namespace
        description = ""
        purpose = ""
        key_features = []
        main_components = []
        external_deps = []
        api_patterns = []

        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("SERVICE_NAME:"):
                service_name = line[13:].strip()
            elif line.startswith("DESCRIPTION:"):
                description = line[12:].strip()
            elif line.startswith("PURPOSE:"):
                purpose = line[8:].strip()
            elif line.startswith("KEY_FEATURES:"):
                key_features = [f.strip() for f in line[13:].split(",") if f.strip()]
            elif line.startswith("MAIN_COMPONENTS:"):
                main_components = [c.strip() for c in line[16:].split(",") if c.strip()]
            elif line.startswith("EXTERNAL_DEPS:"):
                external_deps = [d.strip() for d in line[14:].split(",") if d.strip()]
            elif line.startswith("API_PATTERNS:"):
                api_patterns = [p.strip() for p in line[13:].split(",") if p.strip()]

        # Build full documentation text
        full_doc = f"""# {service_name}

## Description
{description}

## Purpose
{purpose}

## Key Features
{chr(10).join(f'- {f}' for f in key_features)}

## Main Components
{chr(10).join(f'- {c}' for c in main_components)}

## External Dependencies
{chr(10).join(f'- {d}' for d in external_deps)}

## API Patterns
{chr(10).join(f'- {p}' for p in api_patterns)}
"""

        return ServiceDocumentation(
            namespace=namespace,
            service_name=service_name,
            description=description or f"Service in namespace {namespace}",
            purpose=purpose or "Unknown",
            key_features=key_features,
            main_components=main_components,
            external_dependencies=external_deps,
            api_patterns=api_patterns,
            full_documentation=full_doc,
        )

    def _create_basic_service_doc(
        self,
        namespace: str,
        code_units: List[CodeUnit],
    ) -> ServiceDocumentation:
        """Create basic service documentation when LLM fails."""
        component_names = list(set(u.name for u in code_units[:10]))

        return ServiceDocumentation(
            namespace=namespace,
            service_name=namespace,
            description=f"Service containing {len(code_units)} code units",
            purpose="Unknown",
            key_features=[],
            main_components=component_names,
            external_dependencies=[],
            api_patterns=[],
            full_documentation=f"# {namespace}\n\nService with {len(code_units)} code units.",
        )

    def _parse_glossary_response(
        self,
        response: str,
        namespace: str,
    ) -> List[GlossaryTerm]:
        """Parse glossary terms from response."""
        terms = []
        current_term = {}

        for line in response.split("\n"):
            line = line.strip()

            if line == "---":
                if current_term.get("term"):
                    terms.append(GlossaryTerm(
                        term=current_term.get("term", ""),
                        full_name=current_term.get("full_name"),
                        description=current_term.get("description", ""),
                        related_services=[namespace],
                        usage_context=current_term.get("context", ""),
                    ))
                current_term = {}
            elif line.startswith("TERM:"):
                current_term["term"] = line[5:].strip()
            elif line.startswith("FULL_NAME:"):
                full_name = line[10:].strip()
                if full_name:
                    current_term["full_name"] = full_name
            elif line.startswith("DESCRIPTION:"):
                current_term["description"] = line[12:].strip()
            elif line.startswith("CONTEXT:"):
                current_term["context"] = line[8:].strip()

        # Don't forget the last term
        if current_term.get("term"):
            terms.append(GlossaryTerm(
                term=current_term.get("term", ""),
                full_name=current_term.get("full_name"),
                description=current_term.get("description", ""),
                related_services=[namespace],
                usage_context=current_term.get("context", ""),
            ))

        return terms


# Singleton instance
_enricher: Optional[SemanticEnricher] = None


def get_semantic_enricher() -> SemanticEnricher:
    """Get semantic enricher singleton."""
    global _enricher
    if _enricher is None:
        _enricher = SemanticEnricher()
    return _enricher
