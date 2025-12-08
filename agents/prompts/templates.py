"""
Prompt templates for LLM agents.

LLM Agent is responsible for this module.
Templates are organized by query intent.
"""

from typing import Dict, Any, List
from orchestrator.router.intent_classifier import QueryIntent
from orchestrator.context.context_assembler import AssembledContext, ContextItem


class PromptTemplate:
    """Base class for prompt templates."""

    @staticmethod
    def format_context_items(items: List[ContextItem]) -> str:
        """Format context items for inclusion in prompt."""
        if not items:
            return "No relevant context found."

        formatted = []
        for item in items:
            formatted.append(f"\n{item.content}\n")
            if item.citation:
                formatted.append(f"Source: {item.citation}\n")

        return "\n---\n".join(formatted)


class CodeExplanationTemplate(PromptTemplate):
    """Template for code explanation queries."""

    SYSTEM_PROMPT = """You are an expert code analyst helping developers understand codebases.

CRITICAL RULES:
1. ONLY explain what is explicitly shown in the provided context. Do NOT assume or invent functionality.
2. If you cannot see the full implementation in the context, say so clearly.
3. Keep explanations concise and grounded in the actual code snippets provided.
4. Cite specific file paths and function names from the context.
5. Do NOT speculate about design decisions unless they are obvious from comments in the code.

Focus on:
- What the code does (based on what you can see)
- How it works (actual implementation visible)
- Cite sources when referencing specific code"""

    @staticmethod
    def create_prompt(query: str, context: AssembledContext, **kwargs: Any) -> Dict[str, str]:
        """Create prompt for code explanation."""
        context_str = PromptTemplate.format_context_items(context.items)

        user_prompt = f"""Based on the following code context, please answer this question:

**Question:** {query}

**Relevant Code Context:**
{context_str}

Please provide a clear explanation that helps the developer understand the code."""

        return {
            "system": CodeExplanationTemplate.SYSTEM_PROMPT,
            "user": user_prompt,
        }


class FunctionFindingTemplate(PromptTemplate):
    """Template for finding functions."""

    SYSTEM_PROMPT = """You are a code search assistant helping developers find specific functions.

Provide concise information about the function including:
- Function signature
- Purpose and functionality
- Parameters and return value
- Where it's used (callers)
- What it calls (dependencies)

Always cite the source file and line number."""

    @staticmethod
    def create_prompt(query: str, context: AssembledContext, **kwargs: Any) -> Dict[str, str]:
        """Create prompt for function finding."""
        context_str = PromptTemplate.format_context_items(context.items)

        user_prompt = f"""Find and explain the function requested:

**Query:** {query}

**Found Functions:**
{context_str}

Please provide key information about the function(s) found."""

        return {
            "system": FunctionFindingTemplate.SYSTEM_PROMPT,
            "user": user_prompt,
        }


class CallTraceTemplate(PromptTemplate):
    """Template for call chain tracing."""

    SYSTEM_PROMPT = """You are a code flow analyst helping developers understand execution paths.

When showing call chains:
- Display the chain clearly (A → B → C)
- Explain what each function does
- Highlight any important transformations or state changes
- Note any async operations or potential bottlenecks"""

    @staticmethod
    def create_prompt(query: str, context: AssembledContext, **kwargs: Any) -> Dict[str, str]:
        """Create prompt for call tracing."""
        context_str = PromptTemplate.format_context_items(context.items)

        user_prompt = f"""Trace and explain the call chain:

**Query:** {query}

**Call Chain Analysis:**
{context_str}

Please explain the execution flow and any important details."""

        return {
            "system": CallTraceTemplate.SYSTEM_PROMPT,
            "user": user_prompt,
        }


class FlowAnalysisTemplate(PromptTemplate):
    """Template for execution flow analysis."""

    SYSTEM_PROMPT = """You are a performance optimization expert analyzing execution flows.

When analyzing flows:
- Identify sequential vs parallel steps
- Highlight the critical path
- Suggest optimization opportunities
- Estimate potential performance improvements
- Consider trade-offs and risks"""

    @staticmethod
    def create_prompt(
        query: str,
        context: AssembledContext,
        flow_analysis: Any = None
    ) -> Dict[str, str]:
        """Create prompt for flow analysis."""
        context_str = PromptTemplate.format_context_items(context.items)

        # Add flow analysis if available
        flow_info = ""
        if flow_analysis:
            flow_info = f"""

**Flow Analysis Results:**
- Total Steps: {flow_analysis.total_steps}
- Parallel Groups: {len(flow_analysis.parallel_groups)}
- Critical Path: {len(flow_analysis.critical_path)} steps
- Sequential Time: {flow_analysis.sequential_time:.2f}s
- Parallel Time: {flow_analysis.parallel_time:.2f}s
- Potential Speedup: {flow_analysis.speedup_potential:.2f}x

**Recommendations:**
{chr(10).join(f'- {rec}' for rec in flow_analysis.recommendations)}
"""

        user_prompt = f"""Analyze the execution flow and provide optimization recommendations:

**Query:** {query}

**Flow Context:**
{context_str}
{flow_info}

Please provide detailed analysis and actionable optimization suggestions."""

        return {
            "system": FlowAnalysisTemplate.SYSTEM_PROMPT,
            "user": user_prompt,
        }


class DependencyAnalysisTemplate(PromptTemplate):
    """Template for dependency analysis."""

    SYSTEM_PROMPT = """You analyze code dependencies. Be CONCISE.

STRICT RULES:
1. ONLY list dependencies explicitly shown in code (imports, API calls, HTTP requests).
2. NO speculation. NO "hypothetical" or "potential" sections. NO inferences.
3. If no direct relationship is visible, say "No relationship found in provided code" and STOP.
4. Keep response under 150 words. Use bullet points for dependencies found.
5. NEVER use "might", "could", "likely", "probably", or "inferred".

Format: List actual dependencies with file citations. Nothing more."""

    @staticmethod
    def create_prompt(query: str, context: AssembledContext, **kwargs: Any) -> Dict[str, str]:
        """Create prompt for dependency analysis."""
        context_str = PromptTemplate.format_context_items(context.items)

        user_prompt = f"""Analyze the dependencies:

**Query:** {query}

**Dependency Context:**
{context_str}

Please explain the dependency relationships and any concerns."""

        return {
            "system": DependencyAnalysisTemplate.SYSTEM_PROMPT,
            "user": user_prompt,
        }


class GeneralQuestionTemplate(PromptTemplate):
    """Template for general questions."""

    SYSTEM_PROMPT = """You are a coding assistant answering questions about a codebase. Be CONCISE.

STRICT RULES:
1. ONLY use information explicitly shown in the context. NO speculation, NO assumptions, NO hypotheticals.
2. If context is insufficient, say "Not enough information in the provided code" and STOP. Do NOT guess.
3. NEVER use phrases like "likely", "probably", "might", "could be", "hypothetically", or "inferred".
4. NEVER write sections titled "Hypothetical", "Inferences", or "Potential" - these indicate speculation.
5. Keep answers under 200 words. If you can answer in one sentence, do so.
6. Only cite actual code/files from the context.

Format: Brief answer with file citations. No essays."""

    @staticmethod
    def create_prompt(query: str, context: AssembledContext, **kwargs: Any) -> Dict[str, str]:
        """Create prompt for general questions."""
        context_str = PromptTemplate.format_context_items(context.items)

        user_prompt = f"""Answer the following question using the provided context:

**Question:** {query}

**Context:**
{context_str}

Please provide a helpful answer."""

        return {
            "system": GeneralQuestionTemplate.SYSTEM_PROMPT,
            "user": user_prompt,
        }


class TemplateFactory:
    """Factory for creating intent-specific prompts."""

    TEMPLATE_MAP = {
        QueryIntent.EXPLAIN_CODE: CodeExplanationTemplate,
        QueryIntent.FIND_FUNCTION: FunctionFindingTemplate,
        QueryIntent.FIND_CLASS: FunctionFindingTemplate,  # Reuse
        QueryIntent.TRACE_CALLS: CallTraceTemplate,
        QueryIntent.FIND_USAGE: CallTraceTemplate,  # Reuse
        QueryIntent.FIND_FLOW: FlowAnalysisTemplate,
        QueryIntent.PARALLEL_STEPS: FlowAnalysisTemplate,
        QueryIntent.OPTIMIZE_FLOW: FlowAnalysisTemplate,
        QueryIntent.FIND_DEPENDENCIES: DependencyAnalysisTemplate,
        QueryIntent.GENERAL_QUESTION: GeneralQuestionTemplate,
        QueryIntent.FIND_DOCS: GeneralQuestionTemplate,  # Reuse
        QueryIntent.EXPLORE_MODULE: GeneralQuestionTemplate,  # Reuse
    }

    @classmethod
    def create_prompt(
        cls,
        intent: QueryIntent,
        query: str,
        context: AssembledContext,
        **kwargs: Any
    ) -> Dict[str, str]:
        """
        Create prompt for given intent.

        Args:
            intent: Query intent
            query: User query
            context: Assembled context
            **kwargs: Additional arguments (e.g., flow_analysis)

        Returns:
            Dictionary with 'system' and 'user' prompts
        """
        template_class = cls.TEMPLATE_MAP.get(intent, GeneralQuestionTemplate)

        return template_class.create_prompt(query, context, **kwargs)


def get_prompt_for_intent(
    intent: QueryIntent,
    query: str,
    context: AssembledContext,
    **kwargs: Any
) -> Dict[str, str]:
    """
    Get formatted prompt for a query intent.

    Args:
        intent: Query intent
        query: User query
        context: Assembled context
        **kwargs: Additional arguments

    Returns:
        Dictionary with system and user prompts
    """
    return TemplateFactory.create_prompt(intent, query, context, **kwargs)
