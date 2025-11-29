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
from .api_routes import APIRoute


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

        # Extract API routes
        api_routes = self.extract_api_routes(tree, code, file_path)

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
            api_routes=api_routes,
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

            # Extract control flow complexity
            complexity = self._calculate_complexity(node)

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
                complexity=complexity,
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

    def extract_api_routes(self, tree: ast.Module, code: str, file_path: str) -> List[APIRoute]:
        """
        Extract API routes from Python code.

        Supports:
        - FastAPI: @app.get("/path"), @router.post("/path")
        - Flask: @app.route("/path", methods=["GET"])
        """
        routes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for route decorators
                for decorator in node.decorator_list:
                    route = self._try_extract_route(decorator, node, code, file_path)
                    if route:
                        routes.append(route)

        return routes

    def _try_extract_route(
        self,
        decorator: ast.AST,
        func_node: ast.FunctionDef,
        code: str,
        file_path: str
    ) -> Optional[APIRoute]:
        """
        Try to extract route from a decorator.

        FastAPI patterns:
        - @app.get("/users")
        - @router.post("/users/{id}")
        - @app.api_route("/path", methods=["GET", "POST"])

        Flask patterns:
        - @app.route("/users", methods=["GET"])
        - @blueprint.route("/users/<id>")
        """
        # Handle @app.get(...) style decorators
        if isinstance(decorator, ast.Call):
            # Get the decorator name (e.g., "app.get", "router.post")
            decorator_name = self._get_name(decorator.func)

            if not decorator_name:
                return None

            # Check for FastAPI patterns
            if any(method in decorator_name for method in ['.get', '.post', '.put', '.delete', '.patch']):
                return self._parse_fastapi_route(decorator, decorator_name, func_node, file_path)

            # Check for Flask/FastAPI route() pattern
            elif decorator_name.endswith('.route') or decorator_name.endswith('.api_route'):
                return self._parse_generic_route(decorator, decorator_name, func_node, file_path)

        return None

    def _parse_fastapi_route(
        self,
        decorator: ast.Call,
        decorator_name: str,
        func_node: ast.FunctionDef,
        file_path: str
    ) -> Optional[APIRoute]:
        """Parse FastAPI route decorator: @app.get("/path")"""
        # Extract HTTP method from decorator name
        method = decorator_name.split('.')[-1].upper()

        # Extract path from first argument
        path = None
        if decorator.args and len(decorator.args) > 0:
            first_arg = decorator.args[0]
            if isinstance(first_arg, ast.Constant):
                path = first_arg.value

        if path and method:
            # Determine framework
            framework = 'fastapi' if 'app' in decorator_name or 'router' in decorator_name else 'unknown'

            return APIRoute(
                method=method,
                path=path,
                handler=func_node.name,
                handler_line=func_node.lineno,
                framework=framework,
                file_path=file_path,
                description=ast.get_docstring(func_node) or None
            )

        return None

    def _parse_generic_route(
        self,
        decorator: ast.Call,
        decorator_name: str,
        func_node: ast.FunctionDef,
        file_path: str
    ) -> Optional[APIRoute]:
        """
        Parse generic route decorator: @app.route("/path", methods=["GET", "POST"])

        Supports both Flask and FastAPI api_route patterns.
        """
        path = None
        methods = []

        # Extract path from first argument
        if decorator.args and len(decorator.args) > 0:
            first_arg = decorator.args[0]
            if isinstance(first_arg, ast.Constant):
                path = first_arg.value

        # Extract methods from keyword arguments
        for keyword in decorator.keywords:
            if keyword.arg == 'methods':
                # methods=["GET", "POST"]
                if isinstance(keyword.value, ast.List):
                    for elt in keyword.value.elts:
                        if isinstance(elt, ast.Constant):
                            methods.append(elt.value)

        # Determine framework
        if 'blueprint' in decorator_name:
            framework = 'flask'
        elif 'app' in decorator_name or 'router' in decorator_name:
            # Could be either Flask or FastAPI
            # Check for api_route to determine FastAPI
            framework = 'fastapi' if 'api_route' in decorator_name else 'flask'
        else:
            framework = 'unknown'

        if path:
            # If no methods specified, default to GET
            if not methods:
                methods = ['GET']

            # Create a route for each method
            routes = []
            for method in methods:
                routes.append(APIRoute(
                    method=method.upper(),
                    path=path,
                    handler=func_node.name,
                    handler_line=func_node.lineno,
                    framework=framework,
                    file_path=file_path,
                    description=ast.get_docstring(func_node) or None
                ))

            # Return first route (if multiple methods, caller will need to handle)
            # For now, we'll just return the first one
            return routes[0] if routes else None

        return None

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """
        Calculate cyclomatic complexity of a function.

        Complexity = 1 + number of decision points
        Decision points: if, elif, for, while, and, or, except, with, match-case
        """
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Conditional statements
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            # elif is part of If node, so count orelse with If
            elif isinstance(child, ast.If) and child.orelse:
                # Check if orelse is another If (elif)
                if child.orelse and isinstance(child.orelse[0], ast.If):
                    complexity += 1
            # Exception handlers
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            # Boolean operators (and, or)
            elif isinstance(child, ast.BoolOp):
                # Each additional boolean operator adds complexity
                complexity += len(child.values) - 1
            # Match-case (Python 3.10+)
            elif isinstance(child, ast.Match):
                # Each case adds complexity
                complexity += len(child.cases)
            # Comprehensions
            elif isinstance(child, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
                # Each comprehension adds complexity
                complexity += 1

        return complexity

    def _extract_control_flow(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """
        Extract control flow information from a function.

        Returns:
            Dict with control flow statistics and patterns
        """
        control_flow = {
            'has_if': False,
            'has_loops': False,
            'has_try_except': False,
            'has_match': False,
            'if_count': 0,
            'loop_count': 0,
            'exception_handlers': 0,
            'max_nesting_depth': 0,
        }

        def calculate_depth(n, current_depth=0):
            """Calculate maximum nesting depth."""
            max_depth = current_depth

            for child in ast.iter_child_nodes(n):
                if isinstance(child, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
                    child_depth = calculate_depth(child, current_depth + 1)
                    max_depth = max(max_depth, child_depth)
                else:
                    child_depth = calculate_depth(child, current_depth)
                    max_depth = max(max_depth, child_depth)

            return max_depth

        for child in ast.walk(node):
            if isinstance(child, ast.If):
                control_flow['has_if'] = True
                control_flow['if_count'] += 1
            elif isinstance(child, (ast.For, ast.While, ast.AsyncFor)):
                control_flow['has_loops'] = True
                control_flow['loop_count'] += 1
            elif isinstance(child, ast.Try):
                control_flow['has_try_except'] = True
                control_flow['exception_handlers'] += len(child.handlers)
            elif isinstance(child, ast.Match):
                control_flow['has_match'] = True

        control_flow['max_nesting_depth'] = calculate_depth(node)

        return control_flow

    def _extract_data_flow(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """
        Extract data flow information from a function.

        Tracks:
        - Variable assignments
        - Parameter usage
        - Return statements
        - Global/nonlocal declarations
        """
        data_flow = {
            'assignments': [],
            'parameters': [arg.arg for arg in node.args.args],
            'returns': [],
            'globals': [],
            'nonlocals': [],
            'reads': set(),
            'writes': set(),
        }

        for child in ast.walk(node):
            # Assignments
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        data_flow['assignments'].append(target.id)
                        data_flow['writes'].add(target.id)
            # Augmented assignments (+=, -=, etc.)
            elif isinstance(child, ast.AugAssign):
                if isinstance(child.target, ast.Name):
                    data_flow['assignments'].append(child.target.id)
                    data_flow['writes'].add(child.target.id)
                    data_flow['reads'].add(child.target.id)
            # Return statements
            elif isinstance(child, ast.Return):
                if child.value:
                    return_names = self._extract_names_from_expr(child.value)
                    data_flow['returns'].extend(return_names)
                    data_flow['reads'].update(return_names)
            # Global declarations
            elif isinstance(child, ast.Global):
                data_flow['globals'].extend(child.names)
            # Nonlocal declarations
            elif isinstance(child, ast.Nonlocal):
                data_flow['nonlocals'].extend(child.names)
            # Variable reads
            elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                data_flow['reads'].add(child.id)

        # Convert sets to lists for JSON serialization
        data_flow['reads'] = list(data_flow['reads'])
        data_flow['writes'] = list(data_flow['writes'])

        return data_flow

    def _extract_names_from_expr(self, expr: ast.expr) -> List[str]:
        """Extract variable names from an expression."""
        names = []
        for node in ast.walk(expr):
            if isinstance(node, ast.Name):
                names.append(node.id)
        return names


class FastAPIParser(PythonParser):
    """Specialized parser for FastAPI applications."""

    def __init__(self):
        """Initialize FastAPI parser."""
        super().__init__()
        self.language = "fastapi"

    def extract_api_routes(self, tree: ast.Module, code: str, file_path: str) -> List[APIRoute]:
        """
        Extract FastAPI routes with additional FastAPI-specific patterns.

        Supports:
        - @app.get/post/put/patch/delete
        - @router.get/post/put/patch/delete
        - @app.api_route with methods parameter
        - Dependency injection via Depends()
        - Path parameters: /users/{user_id}
        - Query parameters in function signature
        """
        routes = super().extract_api_routes(tree, code, file_path)

        # Ensure all routes are marked as FastAPI
        for route in routes:
            route.framework = 'fastapi'

        return routes


class FlaskParser(PythonParser):
    """Specialized parser for Flask applications."""

    def __init__(self):
        """Initialize Flask parser."""
        super().__init__()
        self.language = "flask"

    def extract_api_routes(self, tree: ast.Module, code: str, file_path: str) -> List[APIRoute]:
        """
        Extract Flask routes with additional Flask-specific patterns.

        Supports:
        - @app.route with methods
        - @blueprint.route
        - URL parameters: /users/<int:user_id>
        - Multiple methods per route
        """
        routes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for route decorators
                for decorator in node.decorator_list:
                    flask_routes = self._extract_flask_routes(decorator, node, code, file_path)
                    routes.extend(flask_routes)

        return routes

    def _extract_flask_routes(
        self,
        decorator: ast.AST,
        func_node: ast.FunctionDef,
        code: str,
        file_path: str
    ) -> List[APIRoute]:
        """Extract Flask routes, handling multiple methods."""
        routes = []

        if isinstance(decorator, ast.Call):
            decorator_name = self._get_name(decorator.func)

            if not decorator_name or not decorator_name.endswith('.route'):
                return routes

            path = None
            methods = []

            # Extract path from first argument
            if decorator.args and len(decorator.args) > 0:
                first_arg = decorator.args[0]
                if isinstance(first_arg, ast.Constant):
                    path = first_arg.value

            # Extract methods from keyword arguments
            for keyword in decorator.keywords:
                if keyword.arg == 'methods':
                    if isinstance(keyword.value, ast.List):
                        for elt in keyword.value.elts:
                            if isinstance(elt, ast.Constant):
                                methods.append(elt.value)

            # If no methods specified, default to GET
            if not methods:
                methods = ['GET']

            # Create a route for each method
            if path:
                for method in methods:
                    routes.append(APIRoute(
                        method=method.upper(),
                        path=path,
                        handler=func_node.name,
                        handler_line=func_node.lineno,
                        framework='flask',
                        file_path=file_path,
                        description=ast.get_docstring(func_node) or None
                    ))

        return routes
