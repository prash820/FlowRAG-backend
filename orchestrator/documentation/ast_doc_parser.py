"""
AST-based Documentation Parser.

Uses Abstract Syntax Tree parsing to extract comprehensive documentation
information from source code, including:
- Function signatures, parameters, return types
- Class definitions and methods
- Docstrings and inline comments
- Type annotations
- Import dependencies
- Code examples

Documentation Agent is responsible for this module.
"""

import ast
import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParameterInfo:
    """Information about a function parameter."""
    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None
    is_optional: bool = False
    description: Optional[str] = None


@dataclass
class FunctionDoc:
    """Documentation for a function or method."""
    name: str
    signature: str
    parameters: List[ParameterInfo] = field(default_factory=list)
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    description: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    raises: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    is_async: bool = False
    is_method: bool = False
    is_property: bool = False
    decorators: List[str] = field(default_factory=list)
    line_number: int = 0
    code_snippet: Optional[str] = None


@dataclass
class ClassDoc:
    """Documentation for a class."""
    name: str
    docstring: Optional[str] = None
    description: Optional[str] = None
    base_classes: List[str] = field(default_factory=list)
    methods: List[FunctionDoc] = field(default_factory=list)
    properties: List[FunctionDoc] = field(default_factory=list)
    attributes: List[Dict[str, Any]] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    line_number: int = 0
    examples: List[str] = field(default_factory=list)


@dataclass
class ModuleDoc:
    """Documentation for an entire module/file."""
    name: str
    file_path: str
    docstring: Optional[str] = None
    description: Optional[str] = None
    imports: List[str] = field(default_factory=list)
    classes: List[ClassDoc] = field(default_factory=list)
    functions: List[FunctionDoc] = field(default_factory=list)
    constants: List[Dict[str, Any]] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)


class PythonASTDocParser:
    """
    AST-based documentation parser for Python files.

    Extracts comprehensive documentation information by parsing
    the Abstract Syntax Tree and analyzing code structure.
    """

    def __init__(self):
        """Initialize the parser."""
        self.current_file = None

    def parse_file(self, file_path: str) -> ModuleDoc:
        """
        Parse a Python file and extract documentation.

        Args:
            file_path: Path to Python file

        Returns:
            ModuleDoc with all extracted documentation
        """
        self.current_file = file_path

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            tree = ast.parse(source_code, filename=file_path)

            module_doc = ModuleDoc(
                name=Path(file_path).stem,
                file_path=file_path,
                docstring=ast.get_docstring(tree)
            )

            # Extract module-level description from docstring
            if module_doc.docstring:
                module_doc.description = self._extract_description(module_doc.docstring)

            # Walk through AST nodes
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    module_doc.imports.extend(self._extract_imports(node))
                elif isinstance(node, ast.ImportFrom):
                    module_doc.imports.extend(self._extract_import_from(node))

            # Extract top-level elements
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    class_doc = self._parse_class(node, source_code)
                    module_doc.classes.append(class_doc)
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    func_doc = self._parse_function(node, source_code, is_method=False)
                    module_doc.functions.append(func_doc)
                elif isinstance(node, ast.Assign):
                    constants = self._extract_constants(node, source_code)
                    module_doc.constants.extend(constants)

            # Extract code examples from docstring
            if module_doc.docstring:
                module_doc.examples = self._extract_code_examples(module_doc.docstring)

            # Try to extract __all__ exports
            module_doc.exports = self._extract_exports(tree)

            logger.info(f"Parsed {file_path}: {len(module_doc.classes)} classes, {len(module_doc.functions)} functions")

            return module_doc

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            # Return minimal module doc
            return ModuleDoc(
                name=Path(file_path).stem,
                file_path=file_path,
                description=f"Failed to parse: {str(e)}"
            )

    def _parse_class(self, node: ast.ClassDef, source_code: str) -> ClassDoc:
        """Parse a class definition."""
        class_doc = ClassDoc(
            name=node.name,
            docstring=ast.get_docstring(node),
            line_number=node.lineno,
            decorators=[self._get_decorator_name(d) for d in node.decorator_list]
        )

        # Extract description
        if class_doc.docstring:
            class_doc.description = self._extract_description(class_doc.docstring)
            class_doc.examples = self._extract_code_examples(class_doc.docstring)

        # Extract base classes
        for base in node.bases:
            class_doc.base_classes.append(ast.unparse(base))

        # Extract methods and properties
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_doc = self._parse_function(item, source_code, is_method=True)

                # Check if it's a property
                if any(d in func_doc.decorators for d in ['property', 'cached_property']):
                    func_doc.is_property = True
                    class_doc.properties.append(func_doc)
                else:
                    class_doc.methods.append(func_doc)

            elif isinstance(item, ast.AnnAssign):
                # Class attribute with type annotation
                attr = self._extract_attribute(item, source_code)
                if attr:
                    class_doc.attributes.append(attr)

        return class_doc

    def _parse_function(self, node, source_code: str, is_method: bool = False) -> FunctionDoc:
        """Parse a function or method definition."""
        is_async = isinstance(node, ast.AsyncFunctionDef)

        func_doc = FunctionDoc(
            name=node.name,
            signature=self._get_function_signature(node),
            docstring=ast.get_docstring(node),
            is_async=is_async,
            is_method=is_method,
            line_number=node.lineno,
            decorators=[self._get_decorator_name(d) for d in node.decorator_list]
        )

        # Parse parameters
        func_doc.parameters = self._parse_parameters(node.args)

        # Extract return type
        if node.returns:
            func_doc.return_type = ast.unparse(node.returns)

        # Parse docstring for additional info
        if func_doc.docstring:
            self._parse_docstring_sections(func_doc)
            func_doc.description = self._extract_description(func_doc.docstring)
            func_doc.examples = self._extract_code_examples(func_doc.docstring)

        # Extract code snippet (first few lines)
        func_doc.code_snippet = self._get_code_snippet(node, source_code, max_lines=10)

        return func_doc

    def _parse_parameters(self, args: ast.arguments) -> List[ParameterInfo]:
        """Parse function parameters."""
        params = []

        # Regular arguments
        for i, arg in enumerate(args.args):
            # Skip 'self' and 'cls' for methods
            if arg.arg in ['self', 'cls']:
                continue

            param = ParameterInfo(name=arg.arg)

            # Type annotation
            if arg.annotation:
                param.type_hint = ast.unparse(arg.annotation)

            # Default value
            defaults_offset = len(args.args) - len(args.defaults)
            if i >= defaults_offset:
                default_index = i - defaults_offset
                param.default_value = ast.unparse(args.defaults[default_index])
                param.is_optional = True

            params.append(param)

        # *args
        if args.vararg:
            param = ParameterInfo(
                name=f"*{args.vararg.arg}",
                type_hint=ast.unparse(args.vararg.annotation) if args.vararg.annotation else None
            )
            params.append(param)

        # **kwargs
        if args.kwarg:
            param = ParameterInfo(
                name=f"**{args.kwarg.arg}",
                type_hint=ast.unparse(args.kwarg.annotation) if args.kwarg.annotation else None
            )
            params.append(param)

        return params

    def _parse_docstring_sections(self, func_doc: FunctionDoc):
        """Parse structured sections from docstring (Google/NumPy style)."""
        if not func_doc.docstring:
            return

        lines = func_doc.docstring.split('\n')
        current_section = None

        for line in lines:
            line_stripped = line.strip()

            # Check for section headers
            if line_stripped.lower().startswith('args:') or line_stripped.lower().startswith('parameters:'):
                current_section = 'args'
                continue
            elif line_stripped.lower().startswith('returns:'):
                current_section = 'returns'
                continue
            elif line_stripped.lower().startswith('raises:'):
                current_section = 'raises'
                continue
            elif line_stripped.lower().startswith('example:') or line_stripped.lower().startswith('examples:'):
                current_section = 'examples'
                continue
            elif line_stripped.lower().startswith('note:') or line_stripped.lower().startswith('notes:'):
                current_section = 'notes'
                continue

            # Process content based on current section
            if current_section == 'args' and line_stripped:
                # Try to match parameter description
                match = re.match(r'(\w+)(?:\s*\([^)]+\))?\s*:\s*(.+)', line_stripped)
                if match:
                    param_name, desc = match.groups()
                    for param in func_doc.parameters:
                        if param.name == param_name:
                            param.description = desc
                            break

            elif current_section == 'raises' and line_stripped:
                func_doc.raises.append(line_stripped)

            elif current_section == 'notes' and line_stripped:
                func_doc.notes.append(line_stripped)

    def _get_function_signature(self, node) -> str:
        """Get complete function signature."""
        try:
            return ast.unparse(node).split('\n')[0].rstrip(':')
        except:
            return f"def {node.name}(...)"

    def _get_decorator_name(self, decorator) -> str:
        """Extract decorator name."""
        try:
            if isinstance(decorator, ast.Name):
                return decorator.id
            elif isinstance(decorator, ast.Call):
                return ast.unparse(decorator.func)
            else:
                return ast.unparse(decorator)
        except:
            return "unknown"

    def _extract_imports(self, node: ast.Import) -> List[str]:
        """Extract import statements."""
        return [alias.name for alias in node.names]

    def _extract_import_from(self, node: ast.ImportFrom) -> List[str]:
        """Extract from...import statements."""
        module = node.module or ''
        imports = []
        for alias in node.names:
            if alias.name == '*':
                imports.append(f"from {module} import *")
            else:
                imports.append(f"from {module} import {alias.name}")
        return imports

    def _extract_constants(self, node: ast.Assign, source_code: str) -> List[Dict[str, Any]]:
        """Extract module-level constants."""
        constants = []

        for target in node.targets:
            if isinstance(target, ast.Name):
                # Check if it's a constant (uppercase)
                if target.id.isupper():
                    try:
                        value = ast.unparse(node.value)
                        constants.append({
                            'name': target.id,
                            'value': value,
                            'line_number': node.lineno
                        })
                    except:
                        pass

        return constants

    def _extract_attribute(self, node: ast.AnnAssign, source_code: str) -> Optional[Dict[str, Any]]:
        """Extract class attribute with type annotation."""
        if isinstance(node.target, ast.Name):
            attr = {
                'name': node.target.id,
                'type': ast.unparse(node.annotation) if node.annotation else None,
                'line_number': node.lineno
            }

            if node.value:
                try:
                    attr['default'] = ast.unparse(node.value)
                except:
                    pass

            return attr

        return None

    def _extract_exports(self, tree: ast.Module) -> List[str]:
        """Extract __all__ exports."""
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == '__all__':
                        if isinstance(node.value, ast.List):
                            return [
                                ast.literal_eval(elt)
                                for elt in node.value.elts
                                if isinstance(elt, ast.Constant)
                            ]
        return []

    def _extract_description(self, docstring: str) -> str:
        """Extract the main description from docstring (first paragraph)."""
        if not docstring:
            return ""

        lines = docstring.strip().split('\n')
        description_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                break
            # Stop at section headers
            if any(line.lower().startswith(header) for header in
                   ['args:', 'parameters:', 'returns:', 'raises:', 'example:', 'note:']):
                break
            description_lines.append(line)

        return ' '.join(description_lines)

    def _extract_code_examples(self, docstring: str) -> List[str]:
        """Extract code examples from docstring."""
        if not docstring:
            return []

        examples = []
        in_code_block = False
        current_example = []

        for line in docstring.split('\n'):
            # Check for code block markers
            if '```' in line or '>>>' in line:
                if in_code_block and current_example:
                    examples.append('\n'.join(current_example))
                    current_example = []
                in_code_block = not in_code_block
                continue

            if in_code_block:
                current_example.append(line)

        if current_example:
            examples.append('\n'.join(current_example))

        return examples

    def _get_code_snippet(self, node, source_code: str, max_lines: int = 10) -> str:
        """Get code snippet for a node."""
        try:
            lines = source_code.split('\n')
            start = node.lineno - 1

            # Find end line (limited by max_lines)
            end = min(start + max_lines, len(lines))
            if hasattr(node, 'end_lineno') and node.end_lineno:
                end = min(node.end_lineno, start + max_lines)

            snippet_lines = lines[start:end]
            return '\n'.join(snippet_lines)
        except:
            return ""


def get_ast_doc_parser() -> PythonASTDocParser:
    """Get AST documentation parser instance."""
    return PythonASTDocParser()
