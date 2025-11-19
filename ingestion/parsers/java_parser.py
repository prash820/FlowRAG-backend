"""
Java parser using tree-sitter.

Extracts classes, methods, interfaces, and call graphs from Java code.
Ingestion Agent is responsible for this module.
"""

from tree_sitter import Language, Parser, Node
import tree_sitter_java
import time
from typing import List, Optional, Dict, Any, Set
from pathlib import Path

from databases.neo4j import NodeLabel
from .base import BaseParser, CodeUnit, ParseResult


class JavaParser(BaseParser):
    """Parser for Java source code."""

    def __init__(self):
        """Initialize Java parser."""
        super().__init__("java")
        self.ts_language = Language(tree_sitter_java.language())
        self.parser = Parser(self.ts_language)

    def parse_file(
        self,
        file_path: str,
        namespace: str,
        content: Optional[str] = None,
    ) -> ParseResult:
        """Parse a Java file."""
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
        """Parse Java code string."""
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
        """Extract method declarations."""
        functions = []
        current_class = None

        def visit_node(node: Node, parent_class=None):
            nonlocal current_class

            if node.type == "class_declaration":
                # Track current class for methods
                class_name_node = None
                for child in node.children:
                    if child.type == "identifier":
                        class_name_node = child
                        break
                if class_name_node:
                    current_class = self._get_text(class_name_node, code)

            elif node.type == "method_declaration":
                func = self._create_method_unit(node, code, file_path, namespace, current_class)
                if func:
                    functions.append(func)

            elif node.type == "constructor_declaration":
                func = self._create_constructor_unit(node, code, file_path, namespace, current_class)
                if func:
                    functions.append(func)

            # Recursively visit children
            for child in node.children:
                visit_node(child, current_class)

        visit_node(root_node)
        return functions

    def extract_classes(
        self, root_node: Node, code: str, file_path: str, namespace: str
    ) -> List[CodeUnit]:
        """Extract class and interface declarations."""
        classes = []

        def visit_node(node: Node):
            if node.type in ("class_declaration", "interface_declaration", "enum_declaration"):
                cls = self._create_class_unit(node, code, file_path, namespace)
                if cls:
                    classes.append(cls)

            # Recursively visit children
            for child in node.children:
                visit_node(child)

        visit_node(root_node)
        return classes

    def _create_method_unit(
        self,
        node: Node,
        code: str,
        file_path: str,
        namespace: str,
        parent_class: Optional[str] = None,
    ) -> Optional[CodeUnit]:
        """Create a CodeUnit for a method."""
        # Get method name
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
            if child.type == "formal_parameters":
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
            signature=f"{name}({', '.join(params)})",
            line_start=line_start,
            line_end=line_end,
            parameters=params,
            parent_id=parent_class,
            calls=calls,
            namespace=namespace,
        )

    def _create_constructor_unit(
        self,
        node: Node,
        code: str,
        file_path: str,
        namespace: str,
        parent_class: Optional[str] = None,
    ) -> Optional[CodeUnit]:
        """Create a CodeUnit for a constructor."""
        # Get constructor name (same as class name)
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
            if child.type == "formal_parameters":
                params = self._extract_parameters(child, code)
                break

        # Get code snippet
        code_snippet = self._get_text(node, code)

        # Extract calls within this constructor
        calls = []
        self._extract_function_calls(node, calls, code)

        return CodeUnit(
            id=self.generate_id(name, file_path, line_start),
            name=name,
            type=NodeLabel.METHOD,  # Treat constructors as methods
            file_path=file_path,
            language=self.language,
            code=code_snippet,
            signature=f"{name}({', '.join(params)})",
            line_start=line_start,
            line_end=line_end,
            parameters=params,
            parent_id=parent_class,
            calls=calls,
            namespace=namespace,
        )

    def _create_class_unit(
        self,
        node: Node,
        code: str,
        file_path: str,
        namespace: str,
    ) -> Optional[CodeUnit]:
        """Create a CodeUnit for a class, interface, or enum."""
        # Get class name
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

        # Get code snippet
        code_snippet = self._get_text(node, code)

        return CodeUnit(
            id=self.generate_id(name, file_path, line_start),
            name=name,
            type=NodeLabel.CLASS,
            file_path=file_path,
            language=self.language,
            code=code_snippet,
            line_start=line_start,
            line_end=line_end,
            namespace=namespace,
        )

    def _extract_parameters(self, formal_params_node: Node, code: str) -> List[str]:
        """Extract parameter names from formal_parameters."""
        params = []
        for child in formal_params_node.children:
            if child.type == "formal_parameter":
                # Get parameter name (last identifier in the formal_parameter)
                identifiers = [c for c in child.children if c.type == "identifier"]
                if identifiers:
                    params.append(self._get_text(identifiers[-1], code))
        return params

    def _extract_imports(self, root_node: Node, file_path: str, code: str) -> List[Dict[str, str]]:
        """Extract import statements."""
        imports = []

        def visit_node(node: Node):
            if node.type == "import_declaration":
                # Get the imported identifier
                for child in node.children:
                    if child.type in ("scoped_identifier", "identifier"):
                        import_path = self._get_scoped_identifier(child, code)
                        if import_path:
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

    def _get_scoped_identifier(self, node: Node, code: str) -> Optional[str]:
        """Get the full scoped identifier (e.g., java.util.List)."""
        if node.type == "identifier":
            return self._get_text(node, code)
        elif node.type == "scoped_identifier":
            parts = []
            for child in node.children:
                if child.type == "identifier":
                    parts.append(self._get_text(child, code))
                elif child.type == "scoped_identifier":
                    part = self._get_scoped_identifier(child, code)
                    if part:
                        parts.append(part)
            return ".".join(parts) if parts else None
        return None

    def _extract_calls(self, root_node: Node, file_path: str, code: str) -> List[Dict[str, str]]:
        """Extract method calls."""
        calls = []

        def visit_node(node: Node):
            if node.type == "method_invocation":
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
        """Extract method calls within a node (for CodeUnit.calls)."""
        if node.type == "method_invocation":
            callee_name = self._get_callee_name(node, code)
            if callee_name and callee_name not in calls:
                calls.append(callee_name)

        # Recursively visit children
        for child in node.children:
            self._extract_function_calls(child, calls, code)

    def _get_callee_name(self, method_invocation_node: Node, code: str) -> Optional[str]:
        """Get the name of a method being called."""
        parts = []
        for child in method_invocation_node.children:
            if child.type == "identifier":
                parts.append(self._get_text(child, code))
            elif child.type == "field_access":
                # Object.method() or Class.staticMethod()
                field_parts = self._get_field_access_parts(child, code)
                parts.extend(field_parts)
        return ".".join(parts) if parts else None

    def _get_field_access_parts(self, field_access_node: Node, code: str) -> List[str]:
        """Get parts of a field access (e.g., System.out.println)."""
        parts = []
        for child in field_access_node.children:
            if child.type == "identifier":
                parts.append(self._get_text(child, code))
            elif child.type == "field_access":
                parts.extend(self._get_field_access_parts(child, code))
        return parts

    def _get_text(self, node: Node, code: str) -> str:
        """Get text content of a node."""
        return node.text.decode("utf8")
