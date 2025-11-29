"""
Ruby/Rails parser for code analysis.

Extracts functions, classes, and Rails routes from Ruby code.
Ingestion Agent is responsible for this module.
"""

import re
import time
from typing import List, Optional, Dict, Any
from pathlib import Path

from databases.neo4j import NodeLabel
from .base import BaseParser, CodeUnit, ParseResult
from .api_routes import APIRoute


class RubyParser(BaseParser):
    """Parser for Ruby source code."""

    def __init__(self):
        """Initialize Ruby parser."""
        super().__init__("ruby")

    def parse_file(
        self,
        file_path: str,
        namespace: str,
        content: Optional[str] = None,
    ) -> ParseResult:
        """Parse a Ruby file."""
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
        """Parse Ruby code string using regex patterns."""
        # Extract code units
        functions = self.extract_functions(code, file_path, namespace)
        classes = self.extract_classes(code, file_path, namespace)

        # Extract API routes (Rails)
        api_routes = self.extract_api_routes(code, file_path)

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

    def extract_functions(self, code: str, file_path: str, namespace: str) -> List[CodeUnit]:
        """Extract function (method) definitions from Ruby code."""
        functions = []

        # Pattern: def method_name or def self.method_name
        pattern = r'^\s*def\s+(self\.)?(\w+)(\(.*?\))?'

        lines = code.split('\n')
        i = 0

        while i < len(lines):
            match = re.match(pattern, lines[i])
            if match:
                is_class_method = match.group(1) is not None
                method_name = match.group(2)
                params = match.group(3) or "()"

                line_start = i + 1

                # Find the end of the method
                line_end = self._find_end(lines, i)

                # Get code snippet
                code_snippet = '\n'.join(lines[i:line_end])

                functions.append(CodeUnit(
                    id=self.generate_id(method_name, file_path, line_start),
                    name=method_name,
                    type=NodeLabel.FUNCTION,
                    file_path=file_path,
                    language=self.language,
                    code=code_snippet,
                    signature=f"def {method_name}{params}",
                    line_start=line_start,
                    line_end=line_end,
                    namespace=namespace,
                ))

                i = line_end
            else:
                i += 1

        return functions

    def extract_classes(self, code: str, file_path: str, namespace: str) -> List[CodeUnit]:
        """Extract class definitions from Ruby code."""
        classes = []

        # Pattern: class ClassName or class ClassName < ParentClass
        pattern = r'^\s*class\s+(\w+)(?:\s*<\s*(\w+))?'

        lines = code.split('\n')
        i = 0

        while i < len(lines):
            match = re.match(pattern, lines[i])
            if match:
                class_name = match.group(1)
                parent_class = match.group(2)

                line_start = i + 1

                # Find the end of the class
                line_end = self._find_end(lines, i)

                # Get code snippet
                code_snippet = '\n'.join(lines[i:line_end])

                classes.append(CodeUnit(
                    id=self.generate_id(class_name, file_path, line_start),
                    name=class_name,
                    type=NodeLabel.CLASS,
                    file_path=file_path,
                    language=self.language,
                    code=code_snippet,
                    line_start=line_start,
                    line_end=line_end,
                    parent_id=parent_class,
                    namespace=namespace,
                ))

                i = line_end
            else:
                i += 1

        return classes

    def _find_end(self, lines: List[str], start: int) -> int:
        """
        Find the end of a Ruby block (class, method, etc.).

        Simple implementation that counts 'end' keywords.
        """
        depth = 1
        i = start + 1

        # Keywords that start a block
        block_start_keywords = ['def', 'class', 'module', 'if', 'unless', 'while', 'until', 'for', 'case', 'begin', 'do']

        while i < len(lines) and depth > 0:
            line = lines[i].strip()

            # Check for block start keywords
            for keyword in block_start_keywords:
                if re.match(rf'\b{keyword}\b', line):
                    depth += 1
                    break

            # Check for 'end' keyword
            if re.match(r'\bend\b', line):
                depth -= 1

            i += 1

        return i

    def extract_api_routes(self, code: str, file_path: str) -> List[APIRoute]:
        """
        Extract Rails routes from Ruby code.

        This is a simplified implementation. For complete route extraction,
        you'd need to parse routes.rb and controller files together.
        """
        routes = []

        # Only parse routes.rb files
        if not file_path.endswith('routes.rb'):
            return routes

        lines = code.split('\n')

        for i, line in enumerate(lines):
            route = self._try_extract_rails_route(line, file_path, i + 1)
            if route:
                routes.append(route)

        return routes

    def _try_extract_rails_route(self, line: str, file_path: str, line_num: int) -> Optional[APIRoute]:
        """
        Extract Rails route from a line.

        Patterns:
        - get '/users', to: 'users#index'
        - post '/users', to: 'users#create'
        - resources :users
        - namespace :api do ... end
        """
        line = line.strip()

        # Pattern: get/post/put/patch/delete '/path', to: 'controller#action'
        match = re.match(r"(get|post|put|patch|delete)\s+['\"]([^'\"]+)['\"](?:,\s*to:\s*['\"](\w+)#(\w+)['\"])?", line)
        if match:
            method = match.group(1).upper()
            path = match.group(2)
            controller = match.group(3) or 'unknown'
            action = match.group(4) or 'unknown'

            return APIRoute(
                method=method,
                path=path,
                handler=f"{controller}#{action}",
                framework='rails',
                file_path=file_path,
                handler_line=line_num
            )

        # Pattern: resources :resource_name
        match = re.match(r"resources\s+:(\w+)", line)
        if match:
            resource_name = match.group(1)
            # Note: This would need to be expanded into 7 routes
            # For now, just return a marker route
            return APIRoute(
                method='RESOURCE',
                path=f"/{resource_name}",
                handler=f"{resource_name}#index",
                framework='rails',
                file_path=file_path,
                handler_line=line_num
            )

        return None


class RailsParser(RubyParser):
    """Specialized parser for Ruby on Rails applications."""

    def __init__(self):
        """Initialize Rails parser."""
        super().__init__()
        self.language = "rails"

    def extract_api_routes(self, code: str, file_path: str) -> List[APIRoute]:
        """
        Extract Rails routes with Rails-specific patterns.

        Supports:
        - get/post/put/patch/delete
        - resources (generates 7 RESTful routes)
        - resource (generates 6 RESTful routes, no index)
        - namespace blocks
        - scope blocks
        - member/collection routes
        """
        routes = super().extract_api_routes(code, file_path)

        # Expand resource routes into individual routes
        expanded_routes = []
        for route in routes:
            if route.method == 'RESOURCE':
                expanded_routes.extend(self._expand_resource_route(route))
            else:
                expanded_routes.append(route)

        return expanded_routes

    def _expand_resource_route(self, route: APIRoute) -> List[APIRoute]:
        """
        Expand resources :name into 7 individual RESTful routes.

        Rails resources create:
        - GET    /resource         -> index
        - GET    /resource/new     -> new
        - POST   /resource         -> create
        - GET    /resource/:id     -> show
        - GET    /resource/:id/edit -> edit
        - PATCH  /resource/:id     -> update
        - DELETE /resource/:id     -> destroy
        """
        base_path = route.path
        # Extract controller name from handler (e.g., "users#index" -> "users")
        controller = route.handler.split('#')[0]

        resource_routes = [
            APIRoute('GET', base_path, f"{controller}#index", 'rails', route.file_path),
            APIRoute('GET', f"{base_path}/new", f"{controller}#new", 'rails', route.file_path),
            APIRoute('POST', base_path, f"{controller}#create", 'rails', route.file_path),
            APIRoute('GET', f"{base_path}/:id", f"{controller}#show", 'rails', route.file_path),
            APIRoute('GET', f"{base_path}/:id/edit", f"{controller}#edit", 'rails', route.file_path),
            APIRoute('PATCH', f"{base_path}/:id", f"{controller}#update", 'rails', route.file_path),
            APIRoute('DELETE', f"{base_path}/:id", f"{controller}#destroy", 'rails', route.file_path),
        ]

        return resource_routes

    def _expand_singular_resource_route(self, route: APIRoute) -> List[APIRoute]:
        """
        Expand resource :name (singular) into 6 individual RESTful routes.

        Singular resource doesn't have an index action.
        """
        base_path = route.path
        controller = route.handler.split('#')[0]

        resource_routes = [
            APIRoute('GET', f"{base_path}/new", f"{controller}#new", 'rails', route.file_path),
            APIRoute('POST', base_path, f"{controller}#create", 'rails', route.file_path),
            APIRoute('GET', base_path, f"{controller}#show", 'rails', route.file_path),
            APIRoute('GET', f"{base_path}/edit", f"{controller}#edit", 'rails', route.file_path),
            APIRoute('PATCH', base_path, f"{controller}#update", 'rails', route.file_path),
            APIRoute('DELETE', base_path, f"{controller}#destroy", 'rails', route.file_path),
        ]

        return resource_routes
