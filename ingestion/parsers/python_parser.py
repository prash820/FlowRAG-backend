"""
Python code parser using AST.

Extracts functions, classes, imports, and relationships from Python code.
Ingestion Agent is responsible for this module.
"""

import ast
import time
from typing import List, Optional, Dict, Any
from pathlib import Path

from databases.neo4j import NodeLabel
from .base import BaseParser, CodeUnit, ParseResult


class PythonParser(BaseParser):
    """Parser for Python source code."""

    def __init__(self):
        """Initialize Python parser."""
        super().__init__("python")

    def parse_file(
        self,
        file_path: str,
        namespace: str,
        content: Optional[str] = None,
    ) -> ParseResult:
        """Parse a Python file."""
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
        """Parse Python code string."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            # Return empty result for files with syntax errors
            return ParseResult(
                file_path=file_path,
                language=self.language,
                namespace=namespace,
            )

        # Extract code units
        modules = self._extract_module(tree, code, file_path, namespace)
        classes = self.extract_classes(tree, code, file_path, namespace)
        functions, methods = self._extract_functions_and_methods(
            tree, code, file_path, namespace, classes
        )

        # Extract relationships
        imports = self._extract_imports(tree, file_path)
        calls = self._extract_calls(tree, file_path)

        # Count lines
        total_lines, code_lines = self.count_lines(code)

        return ParseResult(
            file_path=file_path,
            language=self.language,
            namespace=namespace,
            modules=modules,
            classes=classes,
            functions=functions,
            methods=methods,
            imports=imports,
            calls=calls,
            total_lines=total_lines,
            code_lines=code_lines,
        )

    def _extract_module(
        self,
        tree: ast.Module,
        code: str,
        file_path: str,
        namespace: str,
    ) -> List[CodeUnit]:
        """Extract module-level information."""
        docstring = ast.get_docstring(tree)

        module_id = self.generate_id(
            Path(file_path).stem,
            file_path,
            1
        )

        module = CodeUnit(
            id=module_id,
            name=Path(file_path).stem,
            type=NodeLabel.MODULE,
            file_path=file_path,
            language=self.language,
            code=code[:500],  # First 500 chars
            docstring=docstring,
            line_start=1,
            line_end=len(code.split("\n")),
            namespace=namespace,
        )

        return [module]

    def extract_classes(
        self,
        tree: ast.Module,
        code: str,
        file_path: str,
        namespace: str,
    ) -> List[CodeUnit]:
        """Extract class definitions."""
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_unit = self._parse_class(node, code, file_path, namespace)
                if class_unit:
                    classes.append(class_unit)

        return classes

    def _parse_class(
        self,
        node: ast.ClassDef,
        code: str,
        file_path: str,
        namespace: str,
    ) -> Optional[CodeUnit]:
        """Parse a class definition."""
        try:
            # Get code snippet
            lines = code.split("\n")
            class_code = "\n".join(
                lines[node.lineno - 1:node.end_lineno]
            )

            # Extract base classes
            base_classes = [
                self._get_name(base)
                for base in node.bases
            ]

            # Extract methods
            method_names = [
                item.name
                for item in node.body
                if isinstance(item, ast.FunctionDef)
            ]

            # Get docstring
            docstring = ast.get_docstring(node)

            class_id = self.generate_id(node.name, file_path, node.lineno)

            return CodeUnit(
                id=class_id,
                name=node.name,
                type=NodeLabel.CLASS,
                file_path=file_path,
                language=self.language,
                code=class_code,
                docstring=docstring,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                namespace=namespace,
                decorators=[self._get_name(d) for d in node.decorator_list],
                imports=base_classes,  # Store base classes in imports for now
            )
        except Exception:
            return None

    def extract_functions(self, tree: ast.Module) -> List[CodeUnit]:
        """Extract standalone functions (not methods)."""
        # This is implemented in _extract_functions_and_methods
        return []

    def _extract_functions_and_methods(
        self,
        tree: ast.Module,
        code: str,
        file_path: str,
        namespace: str,
        classes: List[CodeUnit],
    ) -> tuple[List[CodeUnit], List[CodeUnit]]:
        """Extract functions and methods separately."""
        functions = []
        methods = []

        # Get class node mapping
        class_nodes = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if it's a method
                is_method = any(
                    node in class_node.body
                    for class_node in class_nodes.values()
                )

                func_unit = self._parse_function(
                    node, code, file_path, namespace, is_method
                )

                if func_unit:
                    if is_method:
                        methods.append(func_unit)
                    else:
                        functions.append(func_unit)

        return functions, methods

    def _parse_function(
        self,
        node: ast.FunctionDef,
        code: str,
        file_path: str,
        namespace: str,
        is_method: bool = False,
    ) -> Optional[CodeUnit]:
        """Parse a function or method definition."""
        try:
            # Get code snippet
            lines = code.split("\n")
            func_code = "\n".join(
                lines[node.lineno - 1:node.end_lineno]
            )

            # Extract parameters
            parameters = [arg.arg for arg in node.args.args]

            # Get return type
            return_type = None
            if node.returns:
                return_type = self._get_name(node.returns)

            # Get docstring
            docstring = ast.get_docstring(node)

            # Extract function calls
            calls = self._extract_function_calls(node)

            func_id = self.generate_id(node.name, file_path, node.lineno)

            return CodeUnit(
                id=func_id,
                name=node.name,
                type=NodeLabel.METHOD if is_method else NodeLabel.FUNCTION,
                file_path=file_path,
                language=self.language,
                code=func_code,
                signature=self._get_signature(node),
                docstring=docstring,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                parameters=parameters,
                return_type=return_type,
                decorators=[self._get_name(d) for d in node.decorator_list],
                calls=calls,
                namespace=namespace,
            )
        except Exception:
            return None

    def _get_signature(self, node: ast.FunctionDef) -> str:
        """Generate function signature."""
        params = []
        for arg in node.args.args:
            param = arg.arg
            if arg.annotation:
                param += f": {self._get_name(arg.annotation)}"
            params.append(param)

        signature = f"{node.name}({', '.join(params)})"

        if node.returns:
            signature += f" -> {self._get_name(node.returns)}"

        return signature

    def _extract_function_calls(self, node: ast.FunctionDef) -> List[str]:
        """Extract function calls within a function."""
        calls = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._get_name(child.func)
                if call_name:
                    calls.append(call_name)

        return list(set(calls))  # Remove duplicates

    def _extract_imports(
        self,
        tree: ast.Module,
        file_path: str,
    ) -> List[Dict[str, str]]:
        """Extract import statements."""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "from_file": file_path,
                        "module": alias.name,
                        "alias": alias.asname or "",
                        "type": "import",
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append({
                        "from_file": file_path,
                        "module": f"{module}.{alias.name}" if module else alias.name,
                        "alias": alias.asname or "",
                        "type": "from_import",
                    })

        return imports

    def _extract_calls(
        self,
        tree: ast.Module,
        file_path: str,
    ) -> List[Dict[str, str]]:
        """Extract function call relationships."""
        # This would need more sophisticated analysis
        # For now, return empty list
        return []

    def _get_name(self, node: ast.AST) -> str:
        """Get name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        elif isinstance(node, ast.Subscript):
            return self._get_name(node.value)
        elif isinstance(node, ast.Constant):
            return str(node.value)
        else:
            return ""
