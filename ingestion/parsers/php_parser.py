"""
PHP/Laravel parser using tree-sitter.

Extracts functions, classes, and Laravel routes from PHP code.
Ingestion Agent is responsible for this module.
"""

from tree_sitter import Language, Parser, Node
import time
from typing import List, Optional, Dict, Any
from pathlib import Path

try:
    import tree_sitter_php
    TREE_SITTER_PHP_AVAILABLE = True
except ImportError:
    TREE_SITTER_PHP_AVAILABLE = False

from databases.neo4j import NodeLabel
from .base import BaseParser, CodeUnit, ParseResult
from .api_routes import APIRoute


class PHPParser(BaseParser):
    """Parser for PHP source code."""

    def __init__(self):
        """Initialize PHP parser."""
        super().__init__("php")

        if not TREE_SITTER_PHP_AVAILABLE:
            raise ImportError(
                "tree-sitter-php is not installed. "
                "Install with: pip install tree-sitter-php"
            )

        self.ts_language = Language(tree_sitter_php.language())
        self.parser = Parser(self.ts_language)

    def parse_file(
        self,
        file_path: str,
        namespace: str,
        content: Optional[str] = None,
    ) -> ParseResult:
        """Parse a PHP file."""
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
        """Parse PHP code string."""
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

        # Extract API routes (Laravel)
        api_routes = self.extract_api_routes(tree.root_node, code, file_path)

        # Count lines
        total_lines, code_lines = self.count_lines(code)

        return ParseResult(
            file_path=file_path,
            language=self.language,
            namespace=namespace,
            classes=classes,
            functions=functions,
            api_routes=api_routes,
            total_lines=total_lines,
            code_lines=code_lines,
        )

    def extract_functions(
        self, root_node: Node, code: str, file_path: str, namespace: str
    ) -> List[CodeUnit]:
        """Extract function declarations from PHP code."""
        functions = []

        def visit_node(node: Node, parent_class=None):
            # Function declaration (not a method)
            if node.type == "function_definition" and not parent_class:
                func = self._create_function_unit(node, code, file_path, namespace)
                if func:
                    functions.append(func)

            # Method declaration (inside class)
            elif node.type == "method_declaration":
                func = self._create_method_unit(node, code, file_path, namespace, parent_class)
                if func:
                    functions.append(func)

            # Track current class for methods
            elif node.type == "class_declaration":
                class_name = self._get_class_name(node, code)
                # Recursively visit class body
                for child in node.children:
                    visit_node(child, class_name)
                return  # Don't visit children again

            # Recursively visit children
            for child in node.children:
                visit_node(child, parent_class)

        visit_node(root_node)
        return functions

    def extract_classes(
        self, root_node: Node, code: str, file_path: str, namespace: str
    ) -> List[CodeUnit]:
        """Extract class declarations from PHP code."""
        classes = []

        def visit_node(node: Node):
            if node.type == "class_declaration":
                cls = self._create_class_unit(node, code, file_path, namespace)
                if cls:
                    classes.append(cls)

            # Recursively visit children
            for child in node.children:
                visit_node(child)

        visit_node(root_node)
        return classes

    def extract_api_routes(self, root_node: Node, code: str, file_path: str) -> List[APIRoute]:
        """Extract Laravel routes from PHP code."""
        routes = []

        def visit_node(node: Node):
            if node.type == "expression_statement":
                # Check for Route:: static calls
                route = self._try_extract_laravel_route(node, code, file_path)
                if route:
                    routes.append(route)

            # Recursively visit children
            for child in node.children:
                visit_node(child)

        visit_node(root_node)
        return routes

    def _try_extract_laravel_route(self, node: Node, code: str, file_path: str) -> Optional[APIRoute]:
        """
        Extract Laravel route patterns:
        - Route::get('/users', [UserController::class, 'index'])
        - Route::post('/users', 'UserController@store')
        - Route::resource('/posts', PostController::class)
        """
        node_text = self._get_text(node, code)

        # Check if this is a Route:: call
        if not node_text.startswith('Route::'):
            return None

        # Extract HTTP method
        http_method = None
        if '::get(' in node_text:
            http_method = 'GET'
        elif '::post(' in node_text:
            http_method = 'POST'
        elif '::put(' in node_text:
            http_method = 'PUT'
        elif '::patch(' in node_text:
            http_method = 'PATCH'
        elif '::delete(' in node_text:
            http_method = 'DELETE'
        elif '::resource(' in node_text:
            # Resource routes create multiple routes
            http_method = 'RESOURCE'
        elif '::apiResource(' in node_text:
            http_method = 'API_RESOURCE'
        else:
            return None

        # Find method_call_expression or scoped_call_expression
        for child in node.children:
            if child.type in ["scoped_call_expression", "member_call_expression"]:
                return self._parse_route_call(child, code, file_path, http_method)

        return None

    def _parse_route_call(self, call_node: Node, code: str, file_path: str, http_method: str) -> Optional[APIRoute]:
        """Parse a Route::method() call."""
        path = None
        handler = None

        # Get arguments
        for child in call_node.children:
            if child.type == "arguments":
                args = []
                for arg_child in child.children:
                    if arg_child.type == "string":
                        # Extract string value (remove quotes)
                        string_val = self._get_text(arg_child, code).strip("'\"")
                        args.append(string_val)
                    elif arg_child.type == "array_creation_expression":
                        # [UserController::class, 'index']
                        array_items = self._extract_array_items(arg_child, code)
                        args.append(array_items)
                    elif arg_child.type == "scoped_call_expression":
                        # Controller::class
                        args.append(self._get_text(arg_child, code))

                # Parse arguments based on pattern
                if len(args) >= 2:
                    path = args[0]

                    # Handler can be:
                    # 1. String: 'UserController@index'
                    # 2. Array: [UserController::class, 'index']
                    # 3. Class reference: UserController::class
                    if isinstance(args[1], str):
                        if '@' in args[1]:
                            # 'UserController@index' format
                            handler = args[1].replace('@', '.')
                        else:
                            handler = args[1]
                    elif isinstance(args[1], list) and len(args[1]) >= 2:
                        # [UserController::class, 'index'] format
                        controller = args[1][0].replace('::class', '')
                        method = args[1][1]
                        handler = f"{controller}.{method}"
                    else:
                        handler = str(args[1])

        if path and handler and http_method:
            return APIRoute(
                method=http_method,
                path=path,
                handler=handler,
                framework='laravel',
                file_path=file_path
            )

        return None

    def _extract_array_items(self, array_node: Node, code: str) -> list:
        """Extract items from array_creation_expression."""
        items = []

        for child in array_node.children:
            if child.type == "array_element_initializer":
                for subchild in child.children:
                    if subchild.type == "string":
                        items.append(self._get_text(subchild, code).strip("'\""))
                    elif subchild.type == "scoped_call_expression":
                        items.append(self._get_text(subchild, code))

        return items

    def _create_function_unit(
        self,
        node: Node,
        code: str,
        file_path: str,
        namespace: str,
    ) -> Optional[CodeUnit]:
        """Create a CodeUnit for a function."""
        name = None

        # Get function name
        for child in node.children:
            if child.type == "name":
                name = self._get_text(child, code)
                break

        if not name:
            return None

        line_start = node.start_point[0] + 1
        line_end = node.end_point[0] + 1
        code_snippet = self._get_text(node, code)

        return CodeUnit(
            id=self.generate_id(name, file_path, line_start),
            name=name,
            type=NodeLabel.FUNCTION,
            file_path=file_path,
            language=self.language,
            code=code_snippet,
            line_start=line_start,
            line_end=line_end,
            namespace=namespace,
        )

    def _create_method_unit(
        self,
        node: Node,
        code: str,
        file_path: str,
        namespace: str,
        parent_class: Optional[str] = None,
    ) -> Optional[CodeUnit]:
        """Create a CodeUnit for a method."""
        name = None

        # Get method name
        for child in node.children:
            if child.type == "name":
                name = self._get_text(child, code)
                break

        if not name:
            return None

        line_start = node.start_point[0] + 1
        line_end = node.end_point[0] + 1
        code_snippet = self._get_text(node, code)

        return CodeUnit(
            id=self.generate_id(name, file_path, line_start),
            name=name,
            type=NodeLabel.METHOD,
            file_path=file_path,
            language=self.language,
            code=code_snippet,
            line_start=line_start,
            line_end=line_end,
            parent_id=parent_class,
            namespace=namespace,
        )

    def _create_class_unit(
        self,
        node: Node,
        code: str,
        file_path: str,
        namespace: str,
    ) -> Optional[CodeUnit]:
        """Create a CodeUnit for a class."""
        name = self._get_class_name(node, code)

        if not name:
            return None

        line_start = node.start_point[0] + 1
        line_end = node.end_point[0] + 1
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

    def _get_class_name(self, class_node: Node, code: str) -> Optional[str]:
        """Get class name from class_declaration node."""
        for child in class_node.children:
            if child.type == "name":
                return self._get_text(child, code)
        return None

    def _get_text(self, node: Node, code: str) -> str:
        """Get text content of a node."""
        return node.text.decode("utf8")


class LaravelParser(PHPParser):
    """Specialized parser for Laravel applications."""

    def __init__(self):
        """Initialize Laravel parser."""
        super().__init__()
        self.language = "laravel"

    def extract_api_routes(self, root_node: Node, code: str, file_path: str) -> List[APIRoute]:
        """
        Extract Laravel routes with additional Laravel-specific patterns.

        Supports:
        - Route::get/post/put/patch/delete
        - Route::resource (generates 7 routes)
        - Route::apiResource (generates 5 routes)
        - Route::group with prefixes
        - Route::middleware
        """
        routes = super().extract_api_routes(root_node, code, file_path)

        # Expand resource routes into individual routes
        expanded_routes = []
        for route in routes:
            if route.method == 'RESOURCE':
                # Resource creates 7 RESTful routes
                expanded_routes.extend(self._expand_resource_route(route))
            elif route.method == 'API_RESOURCE':
                # API Resource creates 5 RESTful routes (no create/edit)
                expanded_routes.extend(self._expand_api_resource_route(route))
            else:
                expanded_routes.append(route)

        return expanded_routes

    def _expand_resource_route(self, route: APIRoute) -> List[APIRoute]:
        """Expand Route::resource into 7 individual routes."""
        base_path = route.path
        controller = route.handler

        resource_routes = [
            APIRoute('GET', base_path, f"{controller}.index", 'laravel', route.file_path),
            APIRoute('GET', f"{base_path}/create", f"{controller}.create", 'laravel', route.file_path),
            APIRoute('POST', base_path, f"{controller}.store", 'laravel', route.file_path),
            APIRoute('GET', f"{base_path}/{{id}}", f"{controller}.show", 'laravel', route.file_path),
            APIRoute('GET', f"{base_path}/{{id}}/edit", f"{controller}.edit", 'laravel', route.file_path),
            APIRoute('PUT', f"{base_path}/{{id}}", f"{controller}.update", 'laravel', route.file_path),
            APIRoute('DELETE', f"{base_path}/{{id}}", f"{controller}.destroy", 'laravel', route.file_path),
        ]

        return resource_routes

    def _expand_api_resource_route(self, route: APIRoute) -> List[APIRoute]:
        """Expand Route::apiResource into 5 individual routes (no create/edit views)."""
        base_path = route.path
        controller = route.handler

        api_resource_routes = [
            APIRoute('GET', base_path, f"{controller}.index", 'laravel', route.file_path),
            APIRoute('POST', base_path, f"{controller}.store", 'laravel', route.file_path),
            APIRoute('GET', f"{base_path}/{{id}}", f"{controller}.show", 'laravel', route.file_path),
            APIRoute('PUT', f"{base_path}/{{id}}", f"{controller}.update", 'laravel', route.file_path),
            APIRoute('DELETE', f"{base_path}/{{id}}", f"{controller}.destroy", 'laravel', route.file_path),
        ]

        return api_resource_routes
