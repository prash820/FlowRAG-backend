"""
Dart/Flutter parser using regex-based extraction.

Extracts functions, classes (including widgets), imports, and relationships from Dart code.
Ingestion Agent is responsible for this module.
"""

import re
import time
from typing import List, Optional, Dict, Any
from pathlib import Path
import hashlib

from databases.neo4j import NodeLabel
from .base import BaseParser, CodeUnit, ParseResult


class DartParser(BaseParser):
    """Parser for Dart/Flutter source code."""

    def __init__(self):
        """Initialize Dart parser."""
        super().__init__("dart")

    def parse_file(
        self,
        file_path: str,
        namespace: str,
        content: Optional[str] = None,
    ) -> ParseResult:
        """Parse a Dart file."""
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
        """Parse Dart code string."""

        # Extract code units
        classes = self.extract_classes(code, file_path, namespace)
        functions = self.extract_functions(code, file_path, namespace)

        # Extract relationships
        imports = self._extract_imports(code, file_path)
        calls = self._extract_calls(code, file_path, classes, functions)

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

    def extract_classes(self, code: str, file_path: str, namespace: str) -> List[CodeUnit]:
        """Extract class declarations."""
        classes = []

        # Pattern for class declaration
        class_pattern = r'(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+([\w<>,\s]+))?(?:\s+with\s+([\w,\s]+))?(?:\s+implements\s+([\w,\s]+))?\s*{'

        for match in re.finditer(class_pattern, code):
            class_name = match.group(1)
            extends = match.group(2)
            mixins_str = match.group(3)
            implements_str = match.group(4)

            # Find line numbers
            line_start = code[:match.start()].count('\n') + 1

            # Extract class body (find matching brace)
            class_body_start = match.end()
            brace_count = 1
            pos = class_body_start
            while pos < len(code) and brace_count > 0:
                if code[pos] == '{':
                    brace_count += 1
                elif code[pos] == '}':
                    brace_count -= 1
                pos += 1

            line_end = code[:pos].count('\n') + 1 if brace_count == 0 else line_start

            # Extract class code
            class_code = code[match.start():pos] if brace_count == 0 else code[match.start():match.start() + 500]

            # Find dartdoc comment
            dartdoc = self._find_dartdoc_before(code, match.start())

            # Determine class type
            is_widget = False
            is_stateful = False
            is_stateless = False

            if extends:
                extends_clean = extends.strip()
                if 'StatelessWidget' in extends_clean:
                    is_stateless = True
                    is_widget = True
                elif 'StatefulWidget' in extends_clean:
                    is_stateful = True
                    is_widget = True
                elif 'Widget' in extends_clean:
                    is_widget = True

            # Generate unique ID
            class_id = self._generate_id(file_path, class_name, line_start)

            # Note: Dart-specific metadata (is_widget, mixins, etc.) is not stored in CodeUnit
            # CodeUnit only has standard fields. Custom metadata would need to be added to the model.

            code_unit = CodeUnit(
                id=class_id,
                name=class_name,
                type=NodeLabel.CLASS,
                file_path=file_path,
                language=self.language,
                code=class_code[:2000],  # Limit code length
                signature=match.group(0).rstrip('{').strip(),
                docstring=dartdoc,
                line_start=line_start,
                line_end=line_end,
                namespace=namespace,
            )

            classes.append(code_unit)

        return classes

    def extract_functions(self, code: str, file_path: str, namespace: str) -> List[CodeUnit]:
        """Extract top-level function declarations."""
        functions = []

        # Function pattern (avoiding class methods)
        func_pattern = r'^(?:Future<[\w<>,\s]+>|[\w<>,\s]+)\s+(\w+)\s*\(([^)]*)\)'

        for match in re.finditer(func_pattern, code, re.MULTILINE):
            func_name = match.group(1)
            params_str = match.group(2)

            # Skip if this looks like it's inside a class
            before_text = code[:match.start()]
            # Simple heuristic: if we have more opening braces than closing braces, we're inside something
            if before_text.count('{') > before_text.count('}'):
                continue

            line_start = code[:match.start()].count('\n') + 1

            # Find function body end
            body_start = match.end()
            # Find the opening brace
            brace_pos = code.find('{', body_start)
            if brace_pos == -1 or brace_pos > body_start + 100:
                continue

            # Find matching closing brace
            brace_count = 1
            pos = brace_pos + 1
            while pos < len(code) and brace_count > 0:
                if code[pos] == '{':
                    brace_count += 1
                elif code[pos] == '}':
                    brace_count -= 1
                pos += 1

            line_end = code[:pos].count('\n') + 1 if brace_count == 0 else line_start + 10

            # Extract function code
            func_code = code[match.start():pos] if brace_count == 0 else code[match.start():match.start() + 500]

            # Find dartdoc
            dartdoc = self._find_dartdoc_before(code, match.start())

            # Parse return type
            return_type = None
            return_type_match = re.match(r'^((?:Future<[\w<>,\s]+>|[\w<>,\s]+))\s+\w+', match.group(0))
            if return_type_match:
                return_type = return_type_match.group(1).strip()

            # Parse parameters
            parameters = []
            if params_str.strip():
                parameters = self._parse_parameters(params_str)

            # Check if async
            is_async = 'async' in code[match.end():min(len(code), match.end() + 50)]

            # Generate unique ID
            func_id = self._generate_id(file_path, func_name, line_start)

            # Note: is_async metadata not stored in CodeUnit (no metadata field)
            # Could be inferred from return_type containing 'Future'
            code_unit = CodeUnit(
                id=func_id,
                name=func_name,
                type=NodeLabel.FUNCTION,
                file_path=file_path,
                language=self.language,
                code=func_code[:2000],
                signature=match.group(0),
                docstring=dartdoc,
                line_start=line_start,
                line_end=line_end,
                parameters=parameters,
                return_type=return_type,
                namespace=namespace,
            )

            functions.append(code_unit)

        return functions

    def _parse_parameters(self, params_str: str) -> List[str]:
        """Parse function parameters."""
        parameters = []

        # Simple parameter extraction
        # Remove named/optional parameter markers
        cleaned = params_str.replace('{', '').replace('}', '').replace('[', '').replace(']', '')

        # Split by comma
        parts = []
        current = ""
        depth = 0

        for char in cleaned:
            if char == '<':
                depth += 1
            elif char == '>':
                depth -= 1
            elif char == ',' and depth == 0:
                parts.append(current.strip())
                current = ""
                continue
            current += char

        if current.strip():
            parts.append(current.strip())

        # Extract parameter names
        for part in parts:
            part = part.strip()
            if not part or 'required' in part:
                part = part.replace('required', '').strip()

            # Match: [type] name [= default]
            param_match = re.match(r'(?:[\w<>,\s]+\s+)?(\w+)(?:\s*=\s*.+)?', part)
            if param_match:
                parameters.append(param_match.group(1))

        return parameters

    def _extract_imports(self, code: str, file_path: str) -> List[Dict[str, str]]:
        """Extract import statements."""
        imports = []

        # Match import statements
        import_pattern = r"import\s+['\"]([^'\"]+)['\"]"

        for match in re.finditer(import_pattern, code):
            package = match.group(1)

            imports.append({
                'from': file_path,
                'to': package,
                'type': 'import'
            })

        return imports

    def _extract_calls(
        self,
        code: str,
        file_path: str,
        classes: List[CodeUnit],
        functions: List[CodeUnit]
    ) -> List[Dict[str, str]]:
        """Extract function/method call relationships."""
        calls = []

        # Build a set of all function/method names defined in this file
        defined_names = set()
        for func in functions:
            defined_names.add(func.name)
        for cls in classes:
            defined_names.add(cls.name)

        # Extract method names from classes by parsing their code
        for cls in classes:
            # Find methods within the class code
            method_pattern = r'(?:Future<[\w<>,\s]+>|[\w<>,\s]+)\s+(\w+)\s*\([^)]*\)\s*(?:async\s*)?{'
            for match in re.finditer(method_pattern, cls.code):
                method_name = match.group(1)
                if method_name not in ['if', 'for', 'while', 'switch']:  # Skip keywords
                    defined_names.add(method_name)

        # Pattern for function/method calls
        # Matches: functionName(...), object.methodName(...), await functionName(...)
        call_pattern = r'\b(\w+)(?:\.(\w+))?\s*\('

        # Analyze each function and method for calls
        for unit in functions + classes:
            # Find calls in the unit's code
            for match in re.finditer(call_pattern, unit.code):
                object_name = match.group(1)
                method_name = match.group(2)

                called_name = method_name if method_name else object_name

                # Skip common keywords and constructors
                skip_names = {
                    'if', 'for', 'while', 'switch', 'catch', 'return',
                    'print', 'setState', 'super', 'this', 'new'
                }

                if called_name in skip_names:
                    continue

                # Only record calls to functions/methods defined in this file
                if called_name in defined_names:
                    calls.append({
                        'from': file_path,
                        'to': called_name,
                        'type': 'calls'
                    })

        return calls

    def _find_dartdoc_before(self, source: str, position: int) -> Optional[str]:
        """Find dartdoc comment before a given position."""
        # Look backwards for dartdoc comment (///)
        preceding_text = source[max(0, position-1000):position]

        lines = preceding_text.split('\n')
        dartdoc_lines = []

        for line in reversed(lines):
            stripped = line.strip()
            if stripped.startswith('///'):
                dartdoc_lines.insert(0, stripped[3:].strip())
            elif stripped and not stripped.startswith('//'):
                break

        if dartdoc_lines:
            return ' '.join(dartdoc_lines)

        return None

    def _generate_id(self, file_path: str, name: str, line: int) -> str:
        """Generate unique ID for code unit."""
        unique_str = f"{file_path}:{name}:{line}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:16]

    def read_file(self, file_path: str) -> str:
        """Read file content."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def count_lines(self, code: str) -> tuple[int, int]:
        """
        Count total lines and code lines.

        Returns:
            Tuple of (total_lines, code_lines)
        """
        lines = code.split('\n')
        total_lines = len(lines)

        code_lines = 0
        in_multiline_comment = False

        for line in lines:
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                continue

            # Handle multiline comments
            if '/*' in stripped:
                in_multiline_comment = True
            if '*/' in stripped:
                in_multiline_comment = False
                continue

            if in_multiline_comment:
                continue

            # Skip single-line comments
            if stripped.startswith('//'):
                continue

            code_lines += 1

        return total_lines, code_lines


def get_dart_parser() -> DartParser:
    """Get Dart parser instance."""
    return DartParser()
