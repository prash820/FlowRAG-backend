"""
Go parser using tree-sitter.

Extracts functions, methods, structs, interfaces, and call graphs from Go code.
Ingestion Agent is responsible for this module.
"""

from tree_sitter import Language, Parser, Node
import tree_sitter_go
import time
from typing import List, Optional, Dict, Any, Set
from pathlib import Path

from databases.neo4j import NodeLabel
from .base import BaseParser, CodeUnit, ParseResult


class GoParser(BaseParser):
    """Parser for Go source code."""

    def __init__(self):
        """Initialize Go parser."""
        super().__init__("go")
        self.ts_language = Language(tree_sitter_go.language())
        self.parser = Parser(self.ts_language)

    def parse_file(
        self,
        file_path: str,
        namespace: str,
        content: Optional[str] = None,
    ) -> ParseResult:
        """Parse a Go file."""
        start_time = time.time()

        # Read content if not provided
        if content is None:
            content = self.read_file(file_path)

        # Parse
        result = self.parse_string(content, namespace, file_path)
        result.parse_time = time.time() - start_time

        return result

    def parse_string(
        self,
        code: str,
        namespace: str,
        file_path: str = "<string>",
    ) -> ParseResult:
        """Parse Go code string."""
        try:
            # Parse with tree-sitter
            tree = self.parser.parse(bytes(code, "utf8"))
        except Exception as e:
            # Return empty result for files with syntax errors
            return ParseResult(
                file_path=file_path,
                language=self.language,
                namespace=namespace,
            )

        # Extract code units
        functions = self.extract_functions(tree.root_node, code, file_path, namespace)
        classes = self.extract_classes(tree.root_node, code, file_path, namespace)

        # Extract relationships
        imports = self._extract_imports(tree.root_node, file_path, code)
        calls = self._extract_calls(tree.root_node, file_path, code)

        # Count lines
        total_lines, code_lines = self.count_lines(code)

        return ParseResult(
            file_path=file_path,
            language=self.language,
            namespace=namespace,
            classes=classes,
            functions=functions,
            imports=imports,
            calls=calls,
            total_lines=total_lines,
            code_lines=code_lines,
        )

    def extract_functions(
        self, root_node: Node, code: str, file_path: str, namespace: str
    ) -> List[CodeUnit]:
        """Extract function and method declarations."""
        functions = []

        def visit_node(node: Node):
            if node.type == "function_declaration":
                func = self._create_function_unit(node, code, file_path, namespace)
                if func:
                    functions.append(func)

            elif node.type == "method_declaration":
                # Methods are associated with types (receivers)
                func = self._create_method_unit(node, code, file_path, namespace)
                if func:
                    functions.append(func)

            # Recursively visit children
            for child in node.children:
                visit_node(child)

        visit_node(root_node)
        return functions

    def extract_classes(
        self, root_node: Node, code: str, file_path: str, namespace: str
    ) -> List[CodeUnit]:
        """Extract struct and interface declarations."""
        classes = []

        def visit_node(node: Node):
            if node.type == "type_declaration":
                # Go has type declarations with type_spec children
                for child in node.children:
                    if child.type == "type_spec":
                        cls = self._create_type_unit(child, code, file_path, namespace)
                        if cls:
                            classes.append(cls)

            # Recursively visit children
            for child in node.children:
                visit_node(child)

        visit_node(root_node)
        return classes

    def _create_function_unit(
        self,
        node: Node,
        code: str,
        file_path: str,
        namespace: str,
    ) -> Optional[CodeUnit]:
        """Create a CodeUnit for a function."""
        # Get function name
        name_node = None
        for child in node.children:
            if child.type == "identifier":
                name_node = child
                break

        if not name_node:
            return None

        name = self._get_text(name_node, code)
        line_start = node.start_point[0] + 1
        line_end = node.end_point[0] + 1

        # Extract parameters
        params = []
        for child in node.children:
            if child.type == "parameter_list":
                params = self._extract_parameters(child, code)
                break

        # Get code snippet
        code_snippet = self._get_text(node, code)

        # Extract calls within this function
        calls = []
        self._extract_function_calls(node, calls, code)

        return CodeUnit(
            id=self.generate_id(name, file_path, line_start),
            name=name,
            type=NodeLabel.FUNCTION,
            file_path=file_path,
            language=self.language,
            code=code_snippet,
            signature=f"func {name}({', '.join(params)})",
            line_start=line_start,
            line_end=line_end,
            parameters=params,
            calls=calls,
            namespace=namespace,
        )

    def _create_method_unit(
        self,
        node: Node,
        code: str,
        file_path: str,
        namespace: str,
    ) -> Optional[CodeUnit]:
        """Create a CodeUnit for a method."""
        # Get method name
        name_node = None
        receiver_node = None
        receiver_type = None

        for child in node.children:
            if child.type == "parameter_list" and receiver_node is None:
                # First parameter_list is the receiver
                receiver_node = child
            elif child.type == "field_identifier":
                name_node = child
                break

        if not name_node:
            return None

        name = self._get_text(name_node, code)

        # Get receiver type
        if receiver_node:
            receiver_type = self._extract_receiver_type(receiver_node, code)

        line_start = node.start_point[0] + 1
        line_end = node.end_point[0] + 1

        # Extract parameters (second parameter_list)
        params = []
        param_list_count = 0
        for child in node.children:
            if child.type == "parameter_list":
                param_list_count += 1
                if param_list_count == 2:  # Second one is actual parameters
                    params = self._extract_parameters(child, code)
                    break

        # Get code snippet
        code_snippet = self._get_text(node, code)

        # Extract calls within this method
        calls = []
        self._extract_function_calls(node, calls, code)

        return CodeUnit(
            id=self.generate_id(name, file_path, line_start),
            name=name,
            type=NodeLabel.METHOD,
            file_path=file_path,
            language=self.language,
            code=code_snippet,
            signature=f"func ({receiver_type}) {name}({', '.join(params)})" if receiver_type else f"func {name}({', '.join(params)})",
            line_start=line_start,
            line_end=line_end,
            parameters=params,
            parent_id=receiver_type,
            calls=calls,
            namespace=namespace,
        )

    def _create_type_unit(
        self,
        node: Node,
        code: str,
        file_path: str,
        namespace: str,
    ) -> Optional[CodeUnit]:
        """Create a CodeUnit for a struct or interface."""
        # Get type name
        name_node = None
        type_node = None

        for child in node.children:
            if child.type == "type_identifier":
                name_node = child
            elif child.type in ("struct_type", "interface_type"):
                type_node = child

        if not name_node:
            return None

        name = self._get_text(name_node, code)
        line_start = node.start_point[0] + 1
        line_end = node.end_point[0] + 1

        # Determine if struct or interface
        node_type = NodeLabel.CLASS if type_node and type_node.type == "struct_type" else NodeLabel.CLASS

        # Get code snippet
        code_snippet = self._get_text(node, code)

        return CodeUnit(
            id=self.generate_id(name, file_path, line_start),
            name=name,
            type=node_type,
            file_path=file_path,
            language=self.language,
            code=code_snippet,
            line_start=line_start,
            line_end=line_end,
            namespace=namespace,
        )

    def _extract_parameters(self, param_list_node: Node, code: str) -> List[str]:
        """Extract parameter names from parameter_list."""
        params = []
        for child in param_list_node.children:
            if child.type == "parameter_declaration":
                # Get parameter name(s)
                for subchild in child.children:
                    if subchild.type == "identifier":
                        params.append(self._get_text(subchild, code))
        return params

    def _extract_receiver_type(self, receiver_node: Node, code: str) -> Optional[str]:
        """Extract receiver type from method receiver."""
        for child in receiver_node.children:
            if child.type == "parameter_declaration":
                for subchild in child.children:
                    if subchild.type == "pointer_type":
                        # Get type from pointer
                        for typenode in subchild.children:
                            if typenode.type == "type_identifier":
                                return self._get_text(typenode, code)
                    elif subchild.type == "type_identifier":
                        return self._get_text(subchild, code)
        return None

    def _extract_imports(self, root_node: Node, file_path: str, code: str) -> List[Dict[str, str]]:
        """Extract import statements."""
        imports = []

        def visit_node(node: Node):
            if node.type == "import_declaration":
                for child in node.children:
                    if child.type == "import_spec":
                        # Single import
                        for subchild in child.children:
                            if subchild.type == "interpreted_string_literal":
                                # Extract string content (remove quotes)
                                import_path = self._get_text(subchild, code).strip('"')
                                imports.append({
                                    "from": file_path,
                                    "to": import_path,
                                    "type": "import"
                                })
                    elif child.type == "import_spec_list":
                        # Multiple imports in a list
                        for spec in child.children:
                            if spec.type == "import_spec":
                                for subchild in spec.children:
                                    if subchild.type == "interpreted_string_literal":
                                        import_path = self._get_text(subchild, code).strip('"')
                                        imports.append({
                                            "from": file_path,
                                            "to": import_path,
                                            "type": "import"
                                        })

            # Recursively visit children
            for child in node.children:
                visit_node(child)

        visit_node(root_node)
        return imports

    def _extract_calls(self, root_node: Node, file_path: str, code: str) -> List[Dict[str, str]]:
        """Extract function/method calls."""
        calls = []

        def visit_node(node: Node):
            if node.type == "call_expression":
                callee_name = self._get_callee_name(node, code)
                if callee_name:
                    calls.append({
                        "from": file_path,
                        "to": callee_name,
                        "type": "call"
                    })

            # Recursively visit children
            for child in node.children:
                visit_node(child)

        visit_node(root_node)
        return calls

    def _extract_function_calls(self, node: Node, calls: List[str], code: str):
        """Extract function calls within a node (for CodeUnit.calls)."""
        if node.type == "call_expression":
            callee_name = self._get_callee_name(node, code)
            if callee_name and callee_name not in calls:
                calls.append(callee_name)

        # Recursively visit children
        for child in node.children:
            self._extract_function_calls(child, calls, code)

    def _get_callee_name(self, call_node: Node, code: str) -> Optional[str]:
        """Get the name of a function being called."""
        for child in call_node.children:
            if child.type == "identifier":
                return self._get_text(child, code)
            elif child.type == "selector_expression":
                # Package.Function or obj.Method
                parts = []
                for subchild in child.children:
                    if subchild.type == "identifier":
                        parts.append(self._get_text(subchild, code))
                    elif subchild.type == "field_identifier":
                        parts.append(self._get_text(subchild, code))
                return ".".join(parts) if parts else None
        return None

    def _get_text(self, node: Node, code: str) -> str:
        """Get text content of a node."""
        return node.text.decode("utf8")
