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

Your task is to explain code clearly and concisely, focusing on:
- What the code does (functionality)
- How it works (implementation details)
- Why it's designed this way (design decisions)
- Any important patterns or best practices used

Use the provided context to give accurate, specific answers. Always cite sources when referencing specific code."""

    @staticmethod
    def create_prompt(query: str, context: AssembledContext) -> Dict[str, str]:
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
    def create_prompt(query: str, context: AssembledContext) -> Dict[str, str]:
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
    def create_prompt(query: str, context: AssembledContext) -> Dict[str, str]:
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

    SYSTEM_PROMPT = """You are a software architecture analyst helping understand dependencies.

When analyzing dependencies:
- Show dependency relationships clearly
- Identify circular dependencies
- Highlight tightly coupled components
- Suggest ways to reduce coupling
- Note any architectural concerns"""

    @staticmethod
    def create_prompt(query: str, context: AssembledContext) -> Dict[str, str]:
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

    SYSTEM_PROMPT = """You are a helpful coding assistant with access to a codebase.

Answer questions clearly and concisely:
- Use the provided context to give specific answers
- Cite sources when referencing code
- If context is insufficient, say so honestly
- Provide examples when helpful"""

    @staticmethod
    def create_prompt(query: str, context: AssembledContext) -> Dict[str, str]:
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
