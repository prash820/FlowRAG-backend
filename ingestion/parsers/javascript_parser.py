"""
JavaScript/TypeScript parser using esprima.

Extracts functions, classes, imports, and call graphs from JavaScript code.
Ingestion Agent is responsible for this module.
"""

import esprima
import time
from typing import List, Optional, Dict, Any, Set
from pathlib import Path

from databases.neo4j import NodeLabel
from .base import BaseParser, CodeUnit, ParseResult


class JavaScriptParser(BaseParser):
    """Parser for JavaScript source code."""

    def __init__(self):
        """Initialize JavaScript parser."""
        super().__init__("javascript")

    def parse_file(
        self,
        file_path: str,
        namespace: str,
        content: Optional[str] = None,
    ) -> ParseResult:
        """Parse a JavaScript file."""
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
        """Parse JavaScript code string."""
        try:
            # Parse with esprima
            tree = esprima.parseScript(code, {
                'loc': True,
                'range': True,
                'comment': True,
                'tolerant': True  # Continue parsing on errors
            })
        except Exception as e:
            # Return empty result for files with syntax errors
            return ParseResult(
                file_path=file_path,
                language=self.language,
                namespace=namespace,
            )

        # Extract code units
        functions = self.extract_functions(tree, code, file_path, namespace)
        classes = self.extract_classes(tree, code, file_path, namespace)

        # Extract relationships
        imports = self._extract_imports(tree, file_path)
        calls = self._extract_calls(tree, file_path)

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

    def extract_functions(self, tree: Any, code: str, file_path: str, namespace: str) -> List[CodeUnit]:
        """Extract function declarations and expressions."""
        functions = []

        def visit_node(node, parent_name=None):
            if not node or not hasattr(node, 'type'):
                return

            node_type = node.type

            if node_type == 'FunctionDeclaration':
                func = self._create_function_unit(node, code, file_path, namespace, parent_name)
                if func:
                    functions.append(func)

            elif node_type == 'FunctionExpression':
                # Anonymous or named function expressions
                func = self._create_function_unit(node, code, file_path, namespace, parent_name)
                if func:
                    functions.append(func)

            elif node_type == 'ArrowFunctionExpression':
                # Arrow functions
                func = self._create_function_unit(node, code, file_path, namespace, parent_name)
                if func:
                    functions.append(func)

            elif node_type == 'VariableDeclaration':
                # Process each declarator
                if hasattr(node, 'declarations'):
                    for declarator in node.declarations:
                        if hasattr(declarator, 'init') and declarator.init:
                            if hasattr(declarator.init, 'type') and declarator.init.type in ('ArrowFunctionExpression', 'FunctionExpression'):
                                func = self._create_function_unit(
                                    declarator.init, code, file_path, namespace, parent_name,
                                    name=declarator.id.name if hasattr(declarator.id, 'name') else None
                                )
                                if func:
                                    functions.append(func)

            # Recursively visit children (esprima returns objects, not dicts)
            for key in ['body', 'declarations', 'expression', 'consequent', 'alternate', 'argument', 'callee']:
                if hasattr(node, key):
                    attr = getattr(node, key)
                    if attr is None:
                        continue
                    if hasattr(attr, 'type'):
                        visit_node(attr, parent_name)
                    elif isinstance(attr, list):
                        for item in attr:
                            if item and hasattr(item, 'type'):
                                visit_node(item, parent_name)

        if hasattr(tree, 'body'):
            for stmt in tree.body:
                visit_node(stmt)

        return functions

    def extract_classes(self, tree: Any, code: str, file_path: str, namespace: str) -> List[CodeUnit]:
        """Extract class declarations."""
        classes = []

        def visit_node(node):
            if hasattr(node, 'type') and node.type == 'ClassDeclaration':
                cls = self._create_class_unit(node, code, file_path, namespace)
                if cls:
                    classes.append(cls)

            # Recursively visit children (esprima returns objects, not dicts)
            for key in ['body', 'declarations', 'init', 'callee', 'expression', 'arguments', 'consequent', 'alternate']:
                if hasattr(node, key):
                    attr = getattr(node, key)
                    if attr is None:
                        continue
                    if hasattr(attr, 'type'):
                        visit_node(attr)
                    elif isinstance(attr, list):
                        for item in attr:
                            if item and hasattr(item, 'type'):
                                visit_node(item)

        if hasattr(tree, 'body'):
            for stmt in tree.body:
                visit_node(stmt)

        return classes

    def _create_function_unit(
        self,
        node: Any,
        code: str,
        file_path: str,
        namespace: str,
        parent_name: Optional[str] = None,
        name: Optional[str] = None
    ) -> Optional[CodeUnit]:
        """Create a CodeUnit for a function."""
        if not hasattr(node, 'loc'):
            return None

        # Get function name
        if name is None:
            if hasattr(node, 'id') and node.id and hasattr(node.id, 'name'):
                name = node.id.name
            else:
                name = '<anonymous>'

        # Get location
        line_start = node.loc.start.line
        line_end = node.loc.end.line

        # Extract parameters
        params = []
        if hasattr(node, 'params'):
            for param in node.params:
                if hasattr(param, 'name'):
                    params.append(param.name)
                elif hasattr(param, 'type') and param.type == 'Identifier':
                    params.append(getattr(param, 'name', 'unknown'))

        # Get code snippet
        lines = code.split('\n')
        code_snippet = '\n'.join(lines[line_start-1:line_end])

        # Extract calls within this function
        calls = []
        self._extract_function_calls(node, calls)

        return CodeUnit(
            id=self.generate_id(name, file_path, line_start),
            name=name,
            type=NodeLabel.METHOD if parent_name else NodeLabel.FUNCTION,
            file_path=file_path,
            language=self.language,
            code=code_snippet,
            signature=f"{name}({', '.join(params)})",
            line_start=line_start,
            line_end=line_end,
            parameters=params,
            parent_id=parent_name,
            calls=calls,
            namespace=namespace,
        )

    def _create_class_unit(
        self,
        node: Any,
        code: str,
        file_path: str,
        namespace: str
    ) -> Optional[CodeUnit]:
        """Create a CodeUnit for a class."""
        if not hasattr(node, 'loc'):
            return None

        # Get class name
        if not hasattr(node, 'id') or not hasattr(node.id, 'name'):
            return None

        name = node.id.name
        line_start = node.loc.start.line
        line_end = node.loc.end.line

        # Get code snippet
        lines = code.split('\n')
        code_snippet = '\n'.join(lines[line_start-1:line_end])

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

    def _extract_imports(self, tree: Any, file_path: str) -> List[Dict[str, str]]:
        """Extract import statements."""
        imports = []

        def visit_node(node):
            if hasattr(node, 'type'):
                if node.type == 'ImportDeclaration':
                    # ES6 imports: import foo from 'module'
                    if hasattr(node, 'source') and hasattr(node.source, 'value'):
                        imports.append({
                            'from': file_path,
                            'to': node.source.value,
                            'type': 'import'
                        })

                elif node.type == 'CallExpression':
                    # CommonJS require: const foo = require('module')
                    if (hasattr(node, 'callee') and
                        hasattr(node.callee, 'name') and
                        node.callee.name == 'require'):
                        if hasattr(node, 'arguments') and len(node.arguments) > 0:
                            arg = node.arguments[0]
                            if hasattr(arg, 'value'):
                                imports.append({
                                    'from': file_path,
                                    'to': arg.value,
                                    'type': 'require'
                                })

            # Recursively visit children (esprima returns objects, not dicts)
            for key in ['body', 'declarations', 'init', 'callee', 'expression', 'arguments', 'consequent', 'alternate']:
                if hasattr(node, key):
                    attr = getattr(node, key)
                    if attr is None:
                        continue
                    if hasattr(attr, 'type'):
                        visit_node(attr)
                    elif isinstance(attr, list):
                        for item in attr:
                            if item and hasattr(item, 'type'):
                                visit_node(item)

        if hasattr(tree, 'body'):
            for stmt in tree.body:
                visit_node(stmt)

        return imports

    def _extract_calls(self, tree: Any, file_path: str) -> List[Dict[str, str]]:
        """Extract function/method calls."""
        calls = []

        def visit_node(node):
            if hasattr(node, 'type') and node.type == 'CallExpression':
                callee_name = self._get_callee_name(node.callee)
                if callee_name:
                    calls.append({
                        'from': file_path,
                        'to': callee_name,
                        'type': 'call'
                    })

            # Recursively visit children (esprima returns objects, not dicts)
            for key in ['body', 'declarations', 'init', 'callee', 'expression', 'arguments', 'consequent', 'alternate']:
                if hasattr(node, key):
                    attr = getattr(node, key)
                    if attr is None:
                        continue
                    if hasattr(attr, 'type'):
                        visit_node(attr)
                    elif isinstance(attr, list):
                        for item in attr:
                            if item and hasattr(item, 'type'):
                                visit_node(item)

        if hasattr(tree, 'body'):
            for stmt in tree.body:
                visit_node(stmt)

        return calls

    def _extract_function_calls(self, node: Any, calls: List[str]):
        """Extract function calls within a node (for CodeUnit.calls)."""
        if hasattr(node, 'type') and node.type == 'CallExpression':
            callee_name = self._get_callee_name(node.callee)
            if callee_name and callee_name not in calls:
                calls.append(callee_name)

        # Recursively visit children (esprima returns objects, not dicts)
        for key in ['body', 'declarations', 'init', 'callee', 'expression', 'arguments', 'consequent', 'alternate']:
            if hasattr(node, key):
                attr = getattr(node, key)
                if attr is None:
                    continue
                if hasattr(attr, 'type'):
                    self._extract_function_calls(attr, calls)
                elif isinstance(attr, list):
                    for item in attr:
                        if item and hasattr(item, 'type'):
                            self._extract_function_calls(item, calls)

    def _get_callee_name(self, callee: Any) -> Optional[str]:
        """Get the name of a function being called."""
        if not hasattr(callee, 'type'):
            return None

        if callee.type == 'Identifier':
            return getattr(callee, 'name', None)

        elif callee.type == 'MemberExpression':
            # obj.method() or obj.prop.method()
            parts = []
            current = callee
            while current:
                if hasattr(current, 'property') and hasattr(current.property, 'name'):
                    prop_name = current.property.name
                    if prop_name:  # Only add non-None names
                        parts.insert(0, prop_name)
                if hasattr(current, 'object'):
                    if hasattr(current.object, 'name'):
                        obj_name = current.object.name
                        if obj_name:  # Only add non-None names
                            parts.insert(0, obj_name)
                        break
                    elif hasattr(current.object, 'type') and current.object.type == 'MemberExpression':
                        current = current.object
                    else:
                        break
                else:
                    break
            # Filter out any None values that might have slipped through
            parts = [p for p in parts if p is not None]
            return '.'.join(parts) if parts else None

        return None


class TypeScriptParser(JavaScriptParser):
    """Parser for TypeScript code."""

    def __init__(self):
        BaseParser.__init__(self, "typescript")

    def parse_string(
        self,
        code: str,
        namespace: str,
        file_path: str = "<string>",
    ) -> ParseResult:
        """Parse TypeScript code - for now, treat as JavaScript."""
        # TODO: Use proper TypeScript parser
        # For MVP, we'll parse as JavaScript which handles most TS syntax
        return super().parse_string(code, namespace, file_path)
