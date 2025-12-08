"""
Data Flow Extractor - Extracts data flow relationships from code.

This module analyzes code to detect variable assignments and their usage
in subsequent function calls, creating DATA_FLOWS_TO relationships.

Feature Flags Required:
- enable_data_flow_relationships: Enable DATA_FLOWS_TO relationship creation
- enable_parallelization_waves: Enable wave-based parallelization detection
- enable_typescript_ast: Use tree-sitter AST for more accurate parsing

Ingestion Agent is responsible for this module.
"""

import re
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from config.feature_flags import get_feature_flags

# Lazy import for AST parser to avoid import errors if tree-sitter not installed
_ast_parser = None

def _get_ast_parser():
    """Lazily get the AST parser if available."""
    global _ast_parser
    if _ast_parser is None:
        try:
            from ingestion.parsers.typescript_ast_parser import get_typescript_ast_parser
            _ast_parser = get_typescript_ast_parser()
        except ImportError:
            _ast_parser = False  # Mark as unavailable
    return _ast_parser if _ast_parser else None

logger = logging.getLogger(__name__)


class DependencyType(str, Enum):
    """Type of data dependency."""
    DIRECT = "direct"           # Variable passed directly
    FIELD_ACCESS = "field_access"  # Field of variable used (e.g., customerData.ssn)
    CONDITIONAL = "conditional"    # Variable used in conditional check
    OPTIONAL = "optional"          # Optional chaining (e.g., customerData?.ssn)


@dataclass
class VariableAssignment:
    """Represents a variable assignment from a function call."""
    variable_name: str
    source_call: str          # The function/method call (e.g., "customerClient.getCustomerData")
    line_number: int
    return_type: Optional[str] = None
    is_async: bool = False
    known_fields: List[str] = field(default_factory=list)


@dataclass
class DataFlowEdge:
    """Represents a data flow between two operations."""
    source_call: str           # Source function call
    target_call: str           # Target function call
    variable_name: str         # Variable being passed
    field: str                 # Specific field (e.g., "ssn") or "self" for whole object
    source_line: int
    target_line: int
    dependency_type: DependencyType = DependencyType.DIRECT
    is_conditional: bool = False
    condition: Optional[str] = None


@dataclass
class ParallelizationWave:
    """A group of operations that can run in parallel."""
    wave_number: int
    operations: List[str]      # List of operation names
    depends_on_waves: List[int]  # Previous waves that must complete


class DataFlowExtractor:
    """
    Extracts data flow relationships from TypeScript/JavaScript code.

    This uses regex-based analysis initially. When enable_typescript_ast
    is enabled, it will use the AST-based parser for more accurate results.
    """

    def __init__(self, use_ast: bool = False):
        """
        Initialize the extractor.

        Args:
            use_ast: Whether to use AST-based parsing (requires tree-sitter)
        """
        self.use_ast = use_ast
        self.assignments: Dict[str, VariableAssignment] = {}
        self.data_flows: List[DataFlowEdge] = []
        self.operation_dependencies: Dict[str, Set[str]] = {}

    def extract_from_code(
        self,
        code: str,
        file_path: str,
        namespace: str,
        language: str = "typescript"
    ) -> Dict[str, Any]:
        """
        Extract data flow relationships from code.

        Args:
            code: Source code content
            file_path: Path to source file
            namespace: Namespace for the code
            language: Programming language

        Returns:
            Dictionary containing:
            - data_flows: List of DataFlowEdge objects
            - waves: List of ParallelizationWave objects
            - dependency_graph: Dict mapping operations to their dependencies
        """
        self.assignments = {}
        self.data_flows = []
        self.operation_dependencies = {}

        if language in ['typescript', 'javascript', 'ts', 'js']:
            self._extract_typescript_flows(code)
        else:
            logger.warning(f"Data flow extraction not supported for {language}")
            return {"data_flows": [], "waves": [], "dependency_graph": {}}

        # Build parallelization waves
        waves = self._compute_parallelization_waves()

        return {
            "data_flows": self.data_flows,
            "waves": waves,
            "dependency_graph": {k: list(v) for k, v in self.operation_dependencies.items()},
        }

    def _extract_typescript_flows(self, code: str) -> None:
        """Extract data flows from TypeScript/JavaScript code."""
        flags = get_feature_flags()
        ast_parser = _get_ast_parser() if flags.enable_typescript_ast else None

        if ast_parser and self.use_ast:
            # Use AST-based extraction for more accurate results
            self._extract_assignments_with_ast(code, ast_parser)
            self._extract_call_dependencies_with_ast(code, ast_parser)
            if flags.log_feature_usage:
                logger.info("[Feature: typescript_ast] Using AST-based data flow extraction")
        else:
            # Fall back to regex-based extraction
            # Step 1: Find all variable assignments from await calls
            self._extract_assignments(code)

            # Step 2: Find all function calls and their arguments
            self._extract_call_dependencies(code)

    def _extract_assignments(self, code: str) -> None:
        """Extract variable assignments from async function calls."""
        # Pattern 1: const/let variable = await this.client.method(...)
        pattern1 = r'(?:const|let)\s+(\w+)(?:\s*:\s*[^=]+)?\s*=\s*await\s+(?:this\.)?(\w+(?:\.\w+)*)\s*\('

        for match in re.finditer(pattern1, code, re.MULTILINE):
            var_name = match.group(1)
            call_chain = match.group(2)
            line_num = code[:match.start()].count('\n') + 1

            return_type = self._find_return_type(code, match.start())

            self.assignments[var_name] = VariableAssignment(
                variable_name=var_name,
                source_call=call_chain,
                line_number=line_num,
                return_type=return_type,
                is_async=True,
            )

            self.operation_dependencies[call_chain] = set()
            logger.debug(f"Found declaration assignment: {var_name} = await {call_chain}")

        # Pattern 2: variable = await this.client.method(...) - reassignment
        # This handles cases like: customerData = await this.customerClient.getCustomerData(...)
        pattern2 = r'(\w+)\s*=\s*await\s+(?:this\.)?(\w+(?:\.\w+)*)\s*\('

        for match in re.finditer(pattern2, code, re.MULTILINE):
            var_name = match.group(1)
            call_chain = match.group(2)
            line_num = code[:match.start()].count('\n') + 1

            # Skip if it matches pattern 1 (has const/let before it)
            preceding = code[max(0, match.start() - 20):match.start()]
            if 'const ' in preceding or 'let ' in preceding:
                continue

            # Skip common false positives
            if var_name in ['const', 'let', 'var', 'return', 'throw', 'if', 'else']:
                continue

            return_type = self._find_return_type(code, match.start())

            self.assignments[var_name] = VariableAssignment(
                variable_name=var_name,
                source_call=call_chain,
                line_number=line_num,
                return_type=return_type,
                is_async=True,
            )

            self.operation_dependencies[call_chain] = set()
            logger.debug(f"Found reassignment: {var_name} = await {call_chain}")

    def _extract_call_dependencies(self, code: str) -> None:
        """Extract data dependencies between calls."""
        # For each assignment, look for usages in subsequent calls
        for var_name, assignment in self.assignments.items():
            # Find usages of this variable in later code
            assignment_end = self._find_assignment_end(code, assignment.line_number)
            remaining_code = code[assignment_end:]

            # Pattern 1: Direct field access - variable.field used as argument
            # e.g., customerData.ssn, creditScore.reportId
            field_pattern = rf'{var_name}\.(\w+)'
            for field_match in re.finditer(field_pattern, remaining_code):
                field_name = field_match.group(1)
                # Find the containing call
                target_call = self._find_containing_call(
                    remaining_code,
                    field_match.start()
                )
                if target_call and target_call != assignment.source_call:
                    target_line = (
                        code[:assignment_end].count('\n') +
                        remaining_code[:field_match.start()].count('\n') + 1
                    )

                    # Check if inside a conditional
                    is_conditional, condition = self._check_conditional(
                        code,
                        assignment_end + field_match.start()
                    )

                    edge = DataFlowEdge(
                        source_call=assignment.source_call,
                        target_call=target_call,
                        variable_name=var_name,
                        field=field_name,
                        source_line=assignment.line_number,
                        target_line=target_line,
                        dependency_type=DependencyType.FIELD_ACCESS,
                        is_conditional=is_conditional,
                        condition=condition,
                    )
                    self.data_flows.append(edge)

                    # Track dependency
                    if target_call not in self.operation_dependencies:
                        self.operation_dependencies[target_call] = set()
                    self.operation_dependencies[target_call].add(assignment.source_call)

                    logger.debug(
                        f"Found data flow: {assignment.source_call}.{field_name} -> {target_call}"
                    )

            # Pattern 2: Optional chaining - variable?.field
            optional_pattern = rf'{var_name}\?\.\s*(\w+)'
            for opt_match in re.finditer(optional_pattern, remaining_code):
                field_name = opt_match.group(1)
                target_call = self._find_containing_call(
                    remaining_code,
                    opt_match.start()
                )
                if target_call and target_call != assignment.source_call:
                    target_line = (
                        code[:assignment_end].count('\n') +
                        remaining_code[:opt_match.start()].count('\n') + 1
                    )

                    edge = DataFlowEdge(
                        source_call=assignment.source_call,
                        target_call=target_call,
                        variable_name=var_name,
                        field=field_name,
                        source_line=assignment.line_number,
                        target_line=target_line,
                        dependency_type=DependencyType.OPTIONAL,
                        is_conditional=True,  # Optional chaining is inherently conditional
                        condition=f"{var_name}?.{field_name}",
                    )
                    self.data_flows.append(edge)

                    if target_call not in self.operation_dependencies:
                        self.operation_dependencies[target_call] = set()
                    self.operation_dependencies[target_call].add(assignment.source_call)

    def _extract_assignments_with_ast(self, code: str, ast_parser: Any) -> None:
        """Extract variable assignments using AST parser."""
        await_calls = ast_parser.extract_await_assignments(code)

        for call in await_calls:
            # Normalize call chain (remove 'this.' prefix if present)
            call_chain = call.call_chain
            if call_chain.startswith('this.'):
                call_chain = call_chain[5:]

            self.assignments[call.variable_name] = VariableAssignment(
                variable_name=call.variable_name,
                source_call=call_chain,
                line_number=call.line_number,
                return_type=call.return_type,
                is_async=True,
            )

            self.operation_dependencies[call_chain] = set()
            logger.debug(f"[AST] Found assignment: {call.variable_name} = await {call_chain}")

    def _extract_call_dependencies_with_ast(self, code: str, ast_parser: Any) -> None:
        """Extract data dependencies between calls using AST parser."""
        # Get all field accesses from AST
        field_accesses = ast_parser.extract_field_accesses(code)

        # Build a mapping of variable names to their assignments
        var_to_assignment = {name: asn for name, asn in self.assignments.items()}

        for access in field_accesses:
            # Check if this field access is on one of our tracked variables
            var_name = None
            for tracked_var in var_to_assignment:
                if access.object_name == tracked_var or access.object_name.endswith(tracked_var):
                    var_name = tracked_var
                    break

            if not var_name:
                continue

            assignment = var_to_assignment[var_name]

            # Only look at accesses after the assignment
            if access.line_number <= assignment.line_number:
                continue

            # Find the containing await call for this field access
            target_call = self._find_containing_call_for_line(code, access.line_number)

            if target_call and target_call != assignment.source_call:
                # Determine dependency type
                dep_type = DependencyType.OPTIONAL if access.is_optional else DependencyType.FIELD_ACCESS

                edge = DataFlowEdge(
                    source_call=assignment.source_call,
                    target_call=target_call,
                    variable_name=var_name,
                    field=access.field_name,
                    source_line=assignment.line_number,
                    target_line=access.line_number,
                    dependency_type=dep_type,
                    is_conditional=access.is_optional,
                    condition=access.full_expression if access.is_optional else None,
                )
                self.data_flows.append(edge)

                # Track dependency
                if target_call not in self.operation_dependencies:
                    self.operation_dependencies[target_call] = set()
                self.operation_dependencies[target_call].add(assignment.source_call)

                logger.debug(
                    f"[AST] Found data flow: {assignment.source_call}.{access.field_name} -> {target_call}"
                )

    def _find_containing_call_for_line(self, code: str, line_number: int) -> Optional[str]:
        """Find the await call containing a given line number."""
        lines = code.split('\n')
        if line_number <= 0 or line_number > len(lines):
            return None

        # Look at current line and a few lines around it
        search_start = max(0, line_number - 3)
        search_end = min(len(lines), line_number + 2)
        search_region = '\n'.join(lines[search_start:search_end])

        # Find await calls in this region
        call_pattern = r'await\s+(?:this\.)?(\w+(?:\.\w+)*)\s*\('
        matches = list(re.finditer(call_pattern, search_region))

        if matches:
            # Return the closest match to our line
            return matches[-1].group(1)
        return None

    def _find_assignment_end(self, code: str, line_number: int) -> int:
        """Find the character position where an assignment line ends."""
        lines = code.split('\n')
        pos = 0
        for i in range(line_number):
            if i < len(lines):
                pos += len(lines[i]) + 1  # +1 for newline
        return pos

    def _find_containing_call(self, code: str, position: int) -> Optional[str]:
        """Find the function call containing a given position."""
        # Look backwards and forwards for the call pattern
        # Pattern: this.client.method( or client.method(
        search_start = max(0, position - 200)
        search_region = code[search_start:position + 100]

        # Find await calls in this region
        call_pattern = r'await\s+(?:this\.)?(\w+(?:\.\w+)*)\s*\('
        matches = list(re.finditer(call_pattern, search_region))

        if matches:
            # Return the last match (closest to our position)
            return matches[-1].group(1)
        return None

    def _check_conditional(self, code: str, position: int) -> Tuple[bool, Optional[str]]:
        """Check if a position is inside a conditional block."""
        # Look backwards for 'if' statement
        search_start = max(0, position - 500)
        preceding = code[search_start:position]

        # Count brace depth to see if we're inside an if block
        # This is a simplified check
        if_pattern = r'if\s*\(([^)]+)\)\s*\{'
        matches = list(re.finditer(if_pattern, preceding))

        if matches:
            last_if = matches[-1]
            condition = last_if.group(1)

            # Check if we're still inside this if block
            open_braces = preceding[last_if.end():].count('{')
            close_braces = preceding[last_if.end():].count('}')

            if open_braces > close_braces:
                return True, condition

        return False, None

    def _find_return_type(self, code: str, position: int) -> Optional[str]:
        """Find the return type annotation for a call."""
        # Look for type annotations in the preceding context
        # This is a simplified extraction
        preceding = code[max(0, position - 200):position]

        # Pattern: : TypeName = await
        type_pattern = r':\s*([A-Z]\w+(?:<[^>]+>)?)\s*(?:\|\s*null)?\s*='
        match = re.search(type_pattern, preceding)
        if match:
            return match.group(1)
        return None

    def _compute_parallelization_waves(self) -> List[ParallelizationWave]:
        """
        Compute parallelization waves based on dependencies.

        Wave 1: Operations with no dependencies
        Wave 2: Operations that depend only on Wave 1
        etc.
        """
        waves: List[ParallelizationWave] = []
        assigned_operations: Set[str] = set()
        all_operations = set(self.operation_dependencies.keys())

        wave_num = 1
        while assigned_operations != all_operations:
            # Find operations whose dependencies are all satisfied
            wave_operations = []

            for op in all_operations - assigned_operations:
                deps = self.operation_dependencies.get(op, set())
                if deps.issubset(assigned_operations):
                    wave_operations.append(op)

            if not wave_operations:
                # Circular dependency or missing operations
                # Add remaining operations to final wave
                remaining = list(all_operations - assigned_operations)
                if remaining:
                    waves.append(ParallelizationWave(
                        wave_number=wave_num,
                        operations=remaining,
                        depends_on_waves=list(range(1, wave_num)),
                    ))
                break

            waves.append(ParallelizationWave(
                wave_number=wave_num,
                operations=wave_operations,
                depends_on_waves=list(range(1, wave_num)) if wave_num > 1 else [],
            ))

            assigned_operations.update(wave_operations)
            wave_num += 1

        return waves

    def create_data_flow_id(self, edge: DataFlowEdge) -> str:
        """Generate unique ID for a data flow relationship."""
        unique_str = f"{edge.source_call}:{edge.target_call}:{edge.field}:{edge.source_line}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:16]


def get_data_flow_extractor(use_ast: bool = False) -> DataFlowExtractor:
    """
    Get data flow extractor instance.

    Args:
        use_ast: Whether to use AST-based parsing

    Returns:
        DataFlowExtractor instance
    """
    return DataFlowExtractor(use_ast=use_ast)
