"""
TypeScript AST Parser using tree-sitter.

This module provides accurate TypeScript/JavaScript parsing using tree-sitter,
replacing the regex-based approach for more reliable code analysis.

Feature Flag: enable_typescript_ast

Ingestion Agent is responsible for this module.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tree_sitter_typescript as ts_typescript
    from tree_sitter import Language, Parser, Node
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    ts_typescript = None
    Language = None
    Parser = None
    Node = None

from config.feature_flags import get_feature_flags

logger = logging.getLogger(__name__)


@dataclass
class TSFunction:
    """Parsed TypeScript function/method."""
    name: str
    signature: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    return_type: Optional[str] = None
    is_async: bool = False
    is_arrow: bool = False
    is_method: bool = False
    line_start: int = 0
    line_end: int = 0
    body_start: int = 0
    body_end: int = 0


@dataclass
class TSClass:
    """Parsed TypeScript class."""
    name: str
    extends: Optional[str] = None
    implements: List[str] = field(default_factory=list)
    methods: List[TSFunction] = field(default_factory=list)
    properties: List[Dict[str, Any]] = field(default_factory=list)
    is_abstract: bool = False
    line_start: int = 0
    line_end: int = 0


@dataclass
class TSAwaitCall:
    """Parsed await expression with assignment."""
    variable_name: str
    call_chain: str           # e.g., "this.customerClient.getCustomerData"
    arguments: List[str]      # Argument expressions
    line_number: int
    column: int
    return_type: Optional[str] = None


@dataclass
class TSFieldAccess:
    """Parsed field access expression."""
    object_name: str          # e.g., "customerData"
    field_name: str           # e.g., "ssn"
    full_expression: str      # e.g., "customerData.ssn"
    line_number: int
    is_optional: bool = False  # customerData?.ssn


class TypeScriptASTParser:
    """
    Tree-sitter based TypeScript/JavaScript parser.

    Provides accurate AST-based parsing for:
    - Function/method declarations
    - Class declarations
    - Await expressions and assignments
    - Field access expressions
    - Call expressions with arguments
    """

    def __init__(self):
        """Initialize the parser."""
        if not TREE_SITTER_AVAILABLE:
            raise ImportError(
                "tree-sitter and tree-sitter-typescript are required. "
                "Install with: pip install tree-sitter tree-sitter-typescript"
            )

        self.parser = Parser()
        # Use TypeScript language - API changed in newer versions
        # tree_sitter_typescript.language_typescript() returns the language pointer
        self.ts_language = Language(ts_typescript.language_typescript())
        self.parser.language = self.ts_language

    def parse_code(self, code: str) -> Any:
        """
        Parse TypeScript/JavaScript code into AST.

        Args:
            code: Source code string

        Returns:
            Tree-sitter tree object
        """
        return self.parser.parse(bytes(code, "utf8"))

    def extract_await_assignments(self, code: str) -> List[TSAwaitCall]:
        """
        Extract all await expressions that are assigned to variables.

        Examples:
        - const data = await this.client.getData()
        - customerData = await this.customerClient.getCustomerData(id)

        Args:
            code: TypeScript source code

        Returns:
            List of TSAwaitCall objects
        """
        tree = self.parse_code(code)
        await_calls = []

        def visit_node(node: Node):
            # Pattern 1: Variable declaration with await
            # const/let variable = await ...
            if node.type == "lexical_declaration":
                for child in node.children:
                    if child.type == "variable_declarator":
                        name_node = child.child_by_field_name("name")
                        value_node = child.child_by_field_name("value")

                        if name_node and value_node and value_node.type == "await_expression":
                            await_call = self._extract_await_call(
                                name_node, value_node, code
                            )
                            if await_call:
                                await_calls.append(await_call)

            # Pattern 2: Assignment expression with await
            # variable = await ...
            elif node.type == "expression_statement":
                expr = node.children[0] if node.children else None
                if expr and expr.type == "assignment_expression":
                    left = expr.child_by_field_name("left")
                    right = expr.child_by_field_name("right")

                    if left and right and right.type == "await_expression":
                        await_call = self._extract_await_call(left, right, code)
                        if await_call:
                            await_calls.append(await_call)

            # Recurse into children
            for child in node.children:
                visit_node(child)

        visit_node(tree.root_node)
        return await_calls

    def _extract_await_call(
        self,
        name_node: Node,
        await_node: Node,
        code: str
    ) -> Optional[TSAwaitCall]:
        """Extract details from an await expression."""
        # Get variable name
        var_name = code[name_node.start_byte:name_node.end_byte]

        # Get the call expression inside await
        call_expr = None
        for child in await_node.children:
            if child.type == "call_expression":
                call_expr = child
                break

        if not call_expr:
            return None

        # Extract the call chain (e.g., this.customerClient.getCustomerData)
        func_node = call_expr.child_by_field_name("function")
        if not func_node:
            return None

        call_chain = code[func_node.start_byte:func_node.end_byte]

        # Extract arguments
        args_node = call_expr.child_by_field_name("arguments")
        arguments = []
        if args_node:
            for child in args_node.children:
                if child.type not in ["(", ")", ","]:
                    arg_text = code[child.start_byte:child.end_byte]
                    arguments.append(arg_text)

        return TSAwaitCall(
            variable_name=var_name,
            call_chain=call_chain,
            arguments=arguments,
            line_number=name_node.start_point[0] + 1,
            column=name_node.start_point[1],
        )

    def extract_field_accesses(self, code: str) -> List[TSFieldAccess]:
        """
        Extract all field access expressions (member expressions).

        Examples:
        - customerData.ssn
        - customerData?.ssn (optional chaining)
        - creditScore.reportId

        Args:
            code: TypeScript source code

        Returns:
            List of TSFieldAccess objects
        """
        tree = self.parse_code(code)
        accesses = []

        def visit_node(node: Node):
            # Member expression: object.property
            if node.type == "member_expression":
                obj_node = node.child_by_field_name("object")
                prop_node = node.child_by_field_name("property")

                if obj_node and prop_node:
                    # Check if it's optional chaining
                    is_optional = False
                    for child in node.children:
                        if child.type == "optional_chain":
                            is_optional = True
                            break

                    obj_name = code[obj_node.start_byte:obj_node.end_byte]
                    prop_name = code[prop_node.start_byte:prop_node.end_byte]
                    full_expr = code[node.start_byte:node.end_byte]

                    accesses.append(TSFieldAccess(
                        object_name=obj_name,
                        field_name=prop_name,
                        full_expression=full_expr,
                        line_number=node.start_point[0] + 1,
                        is_optional=is_optional,
                    ))

            for child in node.children:
                visit_node(child)

        visit_node(tree.root_node)
        return accesses

    def extract_classes(self, code: str) -> List[TSClass]:
        """
        Extract all class declarations.

        Args:
            code: TypeScript source code

        Returns:
            List of TSClass objects
        """
        tree = self.parse_code(code)
        classes = []

        def visit_node(node: Node):
            if node.type == "class_declaration":
                ts_class = self._extract_class(node, code)
                if ts_class:
                    classes.append(ts_class)

            for child in node.children:
                visit_node(child)

        visit_node(tree.root_node)
        return classes

    def _extract_class(self, node: Node, code: str) -> Optional[TSClass]:
        """Extract details from a class declaration."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        class_name = code[name_node.start_byte:name_node.end_byte]

        # Check for extends
        extends = None
        heritage = node.child_by_field_name("heritage")
        if heritage:
            for child in heritage.children:
                if child.type == "extends_clause":
                    for subchild in child.children:
                        if subchild.type == "identifier":
                            extends = code[subchild.start_byte:subchild.end_byte]
                            break

        # Extract methods
        methods = []
        body = node.child_by_field_name("body")
        if body:
            for child in body.children:
                if child.type == "method_definition":
                    method = self._extract_method(child, code)
                    if method:
                        methods.append(method)

        return TSClass(
            name=class_name,
            extends=extends,
            methods=methods,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

    def _extract_method(self, node: Node, code: str) -> Optional[TSFunction]:
        """Extract details from a method definition."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        method_name = code[name_node.start_byte:name_node.end_byte]

        # Check if async
        is_async = False
        for child in node.children:
            if child.type == "async":
                is_async = True
                break

        # Extract parameters
        params_node = node.child_by_field_name("parameters")
        parameters = []
        if params_node:
            parameters = self._extract_parameters(params_node, code)

        # Extract return type
        return_type = None
        ret_type_node = node.child_by_field_name("return_type")
        if ret_type_node:
            return_type = code[ret_type_node.start_byte:ret_type_node.end_byte].lstrip(": ")

        return TSFunction(
            name=method_name,
            signature=code[node.start_byte:node.end_byte].split("{")[0].strip(),
            parameters=parameters,
            return_type=return_type,
            is_async=is_async,
            is_method=True,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

    def _extract_parameters(self, params_node: Node, code: str) -> List[Dict[str, Any]]:
        """Extract parameters from a formal parameters node."""
        parameters = []

        for child in params_node.children:
            if child.type in ["required_parameter", "optional_parameter"]:
                param_name = None
                param_type = None
                is_optional = child.type == "optional_parameter"

                pattern_node = child.child_by_field_name("pattern")
                if pattern_node:
                    param_name = code[pattern_node.start_byte:pattern_node.end_byte]

                type_node = child.child_by_field_name("type")
                if type_node:
                    param_type = code[type_node.start_byte:type_node.end_byte].lstrip(": ")

                if param_name:
                    parameters.append({
                        "name": param_name,
                        "type": param_type,
                        "is_optional": is_optional,
                    })

        return parameters

    def extract_call_arguments(
        self,
        code: str,
        call_line: int
    ) -> List[Tuple[str, int]]:
        """
        Extract arguments from a call expression on a specific line.

        Returns list of (argument_expression, line_number) tuples.
        """
        tree = self.parse_code(code)
        arguments = []

        def visit_node(node: Node):
            if node.type == "call_expression":
                if node.start_point[0] + 1 == call_line:
                    args_node = node.child_by_field_name("arguments")
                    if args_node:
                        for child in args_node.children:
                            if child.type not in ["(", ")", ","]:
                                arg_text = code[child.start_byte:child.end_byte]
                                arguments.append((arg_text, child.start_point[0] + 1))

            for child in node.children:
                visit_node(child)

        visit_node(tree.root_node)
        return arguments


def get_typescript_ast_parser() -> Optional[TypeScriptASTParser]:
    """
    Get TypeScript AST parser instance if available and enabled.

    Returns None if:
    - tree-sitter is not installed
    - Feature flag enable_typescript_ast is False
    """
    flags = get_feature_flags()

    if not flags.enable_typescript_ast:
        logger.debug("TypeScript AST parsing disabled by feature flag")
        return None

    if not TREE_SITTER_AVAILABLE:
        logger.warning("tree-sitter not available, falling back to regex parsing")
        return None

    try:
        return TypeScriptASTParser()
    except Exception as e:
        logger.error(f"Failed to initialize TypeScript AST parser: {e}")
        return None


def is_ast_available() -> bool:
    """Check if AST parsing is available."""
    return TREE_SITTER_AVAILABLE
