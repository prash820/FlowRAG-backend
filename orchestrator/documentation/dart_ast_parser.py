"""
Dart/Flutter AST-based Documentation Parser.

Uses regex patterns to extract comprehensive documentation information
from Dart/Flutter code, including:
- Class definitions (Widgets, State, Services)
- Functions and methods
- Properties and fields
- Dart doc comments
- Type annotations
- Async patterns
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class DartParameterInfo:
    """Information about a Dart function parameter."""
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None
    is_optional: bool = False
    is_named: bool = False
    is_required: bool = False
    description: Optional[str] = None


@dataclass
class DartFunctionDoc:
    """Documentation for a Dart function or method."""
    name: str
    signature: str
    parameters: List[DartParameterInfo] = field(default_factory=list)
    return_type: Optional[str] = None
    dartdoc: Optional[str] = None
    description: Optional[str] = None
    is_async: bool = False
    is_static: bool = False
    is_const: bool = False
    is_factory: bool = False
    is_override: bool = False
    decorators: List[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class DartPropertyDoc:
    """Documentation for a Dart property/field."""
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None
    is_final: bool = False
    is_const: bool = False
    is_static: bool = False
    is_late: bool = False
    dartdoc: Optional[str] = None
    description: Optional[str] = None
    line_number: int = 0


@dataclass
class DartClassDoc:
    """Documentation for a Dart class."""
    name: str
    dartdoc: Optional[str] = None
    description: Optional[str] = None
    extends: Optional[str] = None
    implements: List[str] = field(default_factory=list)
    mixins: List[str] = field(default_factory=list)
    methods: List[DartFunctionDoc] = field(default_factory=list)
    properties: List[DartPropertyDoc] = field(default_factory=list)
    constructors: List[DartFunctionDoc] = field(default_factory=list)
    is_abstract: bool = False
    is_widget: bool = False
    is_stateful_widget: bool = False
    is_stateless_widget: bool = False
    line_number: int = 0


@dataclass
class DartModuleDoc:
    """Documentation for a Dart module/file."""
    name: str
    file_path: str
    description: Optional[str] = None
    library_name: Optional[str] = None
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    classes: List[DartClassDoc] = field(default_factory=list)
    functions: List[DartFunctionDoc] = field(default_factory=list)
    constants: List[Dict[str, Any]] = field(default_factory=list)
    enums: List[Dict[str, Any]] = field(default_factory=list)


class DartASTParser:
    """
    Regex-based documentation parser for Dart/Flutter files.

    Extracts comprehensive documentation information by parsing
    Dart code using regex patterns to identify code elements.
    """

    def __init__(self):
        """Initialize the parser."""
        self.current_file = None

    def parse_file(self, file_path: str) -> DartModuleDoc:
        """
        Parse a Dart file and extract documentation.

        Args:
            file_path: Path to Dart file

        Returns:
            DartModuleDoc with all extracted documentation
        """
        self.current_file = file_path

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            module_doc = DartModuleDoc(
                name=Path(file_path).stem,
                file_path=file_path
            )

            # Extract library declaration
            library_match = re.search(r'library\s+([\w\.]+);', source_code)
            if library_match:
                module_doc.library_name = library_match.group(1)

            # Extract file-level dartdoc
            file_comment = self._find_file_dartdoc(source_code)
            if file_comment:
                module_doc.description = self._extract_dartdoc_description(file_comment)

            # Extract imports
            module_doc.imports = self._extract_imports(source_code)

            # Extract exports
            module_doc.exports = self._extract_exports(source_code)

            # Extract classes
            module_doc.classes = self._extract_classes(source_code)

            # Extract top-level functions
            module_doc.functions = self._extract_functions(source_code, is_top_level=True)

            # Extract constants
            module_doc.constants = self._extract_constants(source_code)

            # Extract enums
            module_doc.enums = self._extract_enums(source_code)

            logger.info(f"Parsed {file_path}: {len(module_doc.classes)} classes, {len(module_doc.functions)} functions")

            return module_doc

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return DartModuleDoc(
                name=Path(file_path).stem,
                file_path=file_path,
                description=f"Failed to parse: {str(e)}"
            )

    def _find_file_dartdoc(self, source: str) -> Optional[str]:
        """Find file-level dartdoc comment at the beginning of file."""
        # Match dartdoc at start of file
        match = re.match(r'^\s*///(.+?)(?:\n(?!///)|\Z)', source, re.MULTILINE | re.DOTALL)
        if match:
            return match.group(1)
        return None

    def _extract_dartdoc_description(self, dartdoc: str) -> str:
        """Extract description from dartdoc comment."""
        lines = dartdoc.strip().split('\n')
        desc_lines = []

        for line in lines:
            line = line.strip().lstrip('/').strip()
            # Stop at dartdoc tags
            if line.startswith('[') or line.startswith('@'):
                break
            if line:
                desc_lines.append(line)

        return ' '.join(desc_lines)

    def _find_dartdoc_before(self, source: str, position: int) -> Optional[str]:
        """Find dartdoc comment before a given position."""
        # Look backwards for dartdoc comment (///)
        preceding_text = source[max(0, position-1000):position]

        # Match triple-slash comments
        lines = preceding_text.split('\n')
        dartdoc_lines = []

        for line in reversed(lines):
            stripped = line.strip()
            if stripped.startswith('///'):
                dartdoc_lines.insert(0, stripped[3:].strip())
            elif stripped and not stripped.startswith('//'):
                break

        if dartdoc_lines:
            return '\n'.join(dartdoc_lines)

        return None

    def _extract_imports(self, source: str) -> List[str]:
        """Extract import statements."""
        imports = []

        # Match import statements
        import_pattern = r"import\s+['\"]([^'\"]+)['\"](?:\s+as\s+(\w+))?(?:\s+show\s+([^;]+))?;"

        for match in re.finditer(import_pattern, source):
            package = match.group(1)
            alias = match.group(2)
            shows = match.group(3)

            import_str = f"import '{package}'"
            if alias:
                import_str += f" as {alias}"
            if shows:
                import_str += f" show {shows}"

            imports.append(import_str)

        return imports

    def _extract_exports(self, source: str) -> List[str]:
        """Extract export statements."""
        exports = []

        export_pattern = r"export\s+['\"]([^'\"]+)['\"](?:\s+show\s+([^;]+))?(?:\s+hide\s+([^;]+))?;"

        for match in re.finditer(export_pattern, source):
            exports.append(match.group(1))

        return exports

    def _extract_classes(self, source: str) -> List[DartClassDoc]:
        """Extract class declarations."""
        classes = []

        # Pattern for class declaration
        class_pattern = r'(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+([\w<>,\s]+))?(?:\s+with\s+([\w,\s]+))?(?:\s+implements\s+([\w,\s]+))?\s*{'

        for match in re.finditer(class_pattern, source):
            name = match.group(1)
            extends = match.group(2)
            mixins_str = match.group(3)
            implements_str = match.group(4)

            class_doc = DartClassDoc(
                name=name,
                extends=extends.strip() if extends else None,
                is_abstract='abstract' in source[max(0, match.start()-20):match.start()],
                line_number=source[:match.start()].count('\n') + 1
            )

            # Check if it's a Flutter widget
            if extends:
                if 'StatelessWidget' in extends:
                    class_doc.is_stateless_widget = True
                    class_doc.is_widget = True
                elif 'StatefulWidget' in extends:
                    class_doc.is_stateful_widget = True
                    class_doc.is_widget = True
                elif 'Widget' in extends:
                    class_doc.is_widget = True

            # Parse mixins
            if mixins_str:
                class_doc.mixins = [m.strip() for m in mixins_str.split(',')]

            # Parse implements
            if implements_str:
                class_doc.implements = [i.strip() for i in implements_str.split(',')]

            # Find dartdoc
            dartdoc = self._find_dartdoc_before(source, match.start())
            if dartdoc:
                class_doc.dartdoc = dartdoc
                class_doc.description = self._extract_dartdoc_description(dartdoc)

            # Extract class body (simplified - find matching brace)
            class_body_start = match.end()
            brace_count = 1
            pos = class_body_start

            while pos < len(source) and brace_count > 0:
                if source[pos] == '{':
                    brace_count += 1
                elif source[pos] == '}':
                    brace_count -= 1
                pos += 1

            if brace_count == 0:
                class_body = source[class_body_start:pos-1]

                # Extract methods
                class_doc.methods = self._extract_methods(class_body)

                # Extract properties
                class_doc.properties = self._extract_properties(class_body)

                # Extract constructors
                class_doc.constructors = self._extract_constructors(class_body, name)

            classes.append(class_doc)

        return classes

    def _extract_methods(self, class_body: str) -> List[DartFunctionDoc]:
        """Extract methods from class body."""
        methods = []

        # Method pattern (simplified)
        method_pattern = r'(?:@override\s+)?(?:static\s+)?(?:const\s+)?(?:Future<[\w<>,\s]+>|[\w<>,\s]+)\s+(\w+)\s*\(([^)]*)\)'

        for match in re.finditer(method_pattern, class_body):
            name = match.group(1)
            params_str = match.group(2)

            # Skip if it looks like a constructor (name starts with uppercase)
            if name[0].isupper():
                continue

            method_doc = DartFunctionDoc(
                name=name,
                signature=match.group(0),
                is_override='@override' in class_body[max(0, match.start()-20):match.start()],
                is_static='static' in match.group(0),
                is_async='async' in class_body[match.end():min(len(class_body), match.end()+50)],
                line_number=class_body[:match.start()].count('\n') + 1
            )

            # Parse return type
            return_type_match = re.match(r'(?:@override\s+)?(?:static\s+)?(?:const\s+)?((?:Future<[\w<>,\s]+>|[\w<>,\s]+))\s+\w+', match.group(0))
            if return_type_match:
                method_doc.return_type = return_type_match.group(1).strip()

            # Parse parameters
            if params_str.strip():
                method_doc.parameters = self._parse_parameters(params_str)

            # Find dartdoc
            dartdoc = self._find_dartdoc_before(class_body, match.start())
            if dartdoc:
                method_doc.dartdoc = dartdoc
                method_doc.description = self._extract_dartdoc_description(dartdoc)

            methods.append(method_doc)

        return methods

    def _extract_properties(self, class_body: str) -> List[DartPropertyDoc]:
        """Extract properties/fields from class body."""
        properties = []

        # Property pattern
        prop_pattern = r'(?:final\s+|const\s+|static\s+|late\s+)*(?:final\s+|const\s+)?(?:[\w<>,\s]+)\s+(\w+)(?:\s*=\s*([^;]+))?;'

        for match in re.finditer(prop_pattern, class_body):
            name = match.group(1)
            default_value = match.group(2)

            # Skip if it looks like a method call
            if '(' in name or ')' in name:
                continue

            property_doc = DartPropertyDoc(
                name=name,
                default_value=default_value.strip() if default_value else None,
                is_final='final' in match.group(0),
                is_const='const' in match.group(0),
                is_static='static' in match.group(0),
                is_late='late' in match.group(0),
                line_number=class_body[:match.start()].count('\n') + 1
            )

            # Extract type annotation
            type_match = re.match(r'(?:final\s+|const\s+|static\s+|late\s+)*(?:final\s+|const\s+)?([\w<>,\s]+)\s+\w+', match.group(0))
            if type_match:
                prop_type = type_match.group(1).strip()
                if prop_type not in ['final', 'const', 'static', 'late']:
                    property_doc.type_annotation = prop_type

            properties.append(property_doc)

        return properties

    def _extract_constructors(self, class_body: str, class_name: str) -> List[DartFunctionDoc]:
        """Extract constructors from class body."""
        constructors = []

        # Named and default constructors
        constructor_pattern = rf'{class_name}(?:\.(\w+))?\s*\(([^)]*)\)'

        for match in re.finditer(constructor_pattern, class_body):
            named_part = match.group(1)
            params_str = match.group(2)

            name = f"{class_name}.{named_part}" if named_part else class_name

            constructor_doc = DartFunctionDoc(
                name=name,
                signature=match.group(0),
                is_factory='factory' in class_body[max(0, match.start()-20):match.start()],
                is_const='const' in class_body[max(0, match.start()-20):match.start()],
                line_number=class_body[:match.start()].count('\n') + 1
            )

            # Parse parameters
            if params_str.strip():
                constructor_doc.parameters = self._parse_parameters(params_str)

            constructors.append(constructor_doc)

        return constructors

    def _extract_functions(self, source: str, is_top_level: bool = False) -> List[DartFunctionDoc]:
        """Extract function declarations."""
        functions = []

        # Function pattern
        func_pattern = r'(?:Future<[\w<>,\s]+>|[\w<>,\s]+)\s+(\w+)\s*\(([^)]*)\)'

        for match in re.finditer(func_pattern, source):
            name = match.group(1)
            params_str = match.group(2)

            # Skip if inside a class (for top-level functions)
            if is_top_level:
                # Simple heuristic: check if we're inside braces
                before_text = source[:match.start()]
                if before_text.count('{') > before_text.count('}'):
                    continue

            func_doc = DartFunctionDoc(
                name=name,
                signature=match.group(0),
                is_async='async' in source[match.end():min(len(source), match.end()+50)],
                line_number=source[:match.start()].count('\n') + 1
            )

            # Parse return type
            return_type_match = re.match(r'((?:Future<[\w<>,\s]+>|[\w<>,\s]+))\s+\w+', match.group(0))
            if return_type_match:
                func_doc.return_type = return_type_match.group(1).strip()

            # Parse parameters
            if params_str.strip():
                func_doc.parameters = self._parse_parameters(params_str)

            # Find dartdoc
            dartdoc = self._find_dartdoc_before(source, match.start())
            if dartdoc:
                func_doc.dartdoc = dartdoc
                func_doc.description = self._extract_dartdoc_description(dartdoc)

            functions.append(func_doc)

        return functions

    def _parse_parameters(self, params_str: str) -> List[DartParameterInfo]:
        """Parse function parameters."""
        parameters = []

        # Handle positional and named parameters
        # Split by comma, but be careful with generics
        parts = []
        current = ""
        depth = 0
        in_braces = False

        for char in params_str:
            if char == '<':
                depth += 1
            elif char == '>':
                depth -= 1
            elif char == '{':
                in_braces = True
            elif char == '}':
                in_braces = False
            elif char == ',' and depth == 0 and not in_braces:
                parts.append(current.strip())
                current = ""
                continue

            current += char

        if current.strip():
            parts.append(current.strip())

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check if it's a named parameter
            is_named = part.startswith('{') or '}' in part
            is_required = 'required' in part

            # Clean up
            part = part.replace('{', '').replace('}', '').replace('required', '').strip()

            # Parse parameter: [type] name [= default]
            param_match = re.match(r'(?:([\w<>,\s]+)\s+)?(\w+)(?:\s*=\s*(.+))?', part)
            if param_match:
                type_annotation = param_match.group(1)
                name = param_match.group(2)
                default_value = param_match.group(3)

                param_info = DartParameterInfo(
                    name=name,
                    type_annotation=type_annotation.strip() if type_annotation else None,
                    default_value=default_value.strip() if default_value else None,
                    is_optional=default_value is not None,
                    is_named=is_named,
                    is_required=is_required
                )

                parameters.append(param_info)

        return parameters

    def _extract_constants(self, source: str) -> List[Dict[str, Any]]:
        """Extract constant declarations."""
        constants = []

        const_pattern = r'const\s+([\w<>,\s]+)\s+([A-Z_][A-Z0-9_]*)\s*=\s*([^;]+);'

        for match in re.finditer(const_pattern, source):
            constants.append({
                'name': match.group(2),
                'type': match.group(1).strip(),
                'value': match.group(3).strip(),
                'line_number': source[:match.start()].count('\n') + 1
            })

        return constants

    def _extract_enums(self, source: str) -> List[Dict[str, Any]]:
        """Extract enum declarations."""
        enums = []

        enum_pattern = r'enum\s+(\w+)\s*{([^}]+)}'

        for match in re.finditer(enum_pattern, source):
            name = match.group(1)
            values_str = match.group(2)

            # Parse enum values
            values = [v.strip().rstrip(',') for v in values_str.split(',') if v.strip()]

            enums.append({
                'name': name,
                'values': values,
                'line_number': source[:match.start()].count('\n') + 1
            })

        return enums


def get_dart_ast_parser() -> DartASTParser:
    """Get Dart AST parser instance."""
    return DartASTParser()
