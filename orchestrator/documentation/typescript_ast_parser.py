"""
TypeScript/JavaScript AST-based Documentation Parser.

Uses tree-sitter to parse TypeScript/JavaScript files and extract
comprehensive documentation information.

Documentation Agent is responsible for this module.
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class TSParameterInfo:
    """Information about a function parameter."""
    name: str
    type_annotation: Optional[str] = None
    is_optional: bool = False
    default_value: Optional[str] = None
    description: Optional[str] = None


@dataclass
class TSFunctionDoc:
    """Documentation for a TypeScript/JavaScript function."""
    name: str
    signature: str
    parameters: List[TSParameterInfo] = field(default_factory=list)
    return_type: Optional[str] = None
    jsdoc: Optional[str] = None
    description: Optional[str] = None
    is_async: bool = False
    is_export: bool = False
    is_arrow: bool = False
    decorators: List[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class TSInterfaceDoc:
    """Documentation for a TypeScript interface."""
    name: str
    properties: List[Dict[str, Any]] = field(default_factory=list)
    jsdoc: Optional[str] = None
    description: Optional[str] = None
    extends: List[str] = field(default_factory=list)
    is_export: bool = False
    line_number: int = 0


@dataclass
class TSClassDoc:
    """Documentation for a TypeScript/JavaScript class."""
    name: str
    jsdoc: Optional[str] = None
    description: Optional[str] = None
    extends: Optional[str] = None
    implements: List[str] = field(default_factory=list)
    methods: List[TSFunctionDoc] = field(default_factory=list)
    properties: List[Dict[str, Any]] = field(default_factory=list)
    is_export: bool = False
    decorators: List[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class TSModuleDoc:
    """Documentation for a TypeScript/JavaScript module."""
    name: str
    file_path: str
    description: Optional[str] = None
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    functions: List[TSFunctionDoc] = field(default_factory=list)
    classes: List[TSClassDoc] = field(default_factory=list)
    interfaces: List[TSInterfaceDoc] = field(default_factory=list)
    types: List[Dict[str, Any]] = field(default_factory=list)
    constants: List[Dict[str, Any]] = field(default_factory=list)


class TypeScriptASTParser:
    """
    Regex-based parser for TypeScript/JavaScript documentation.
    
    Note: This is a simplified parser. For production use, consider
    using tree-sitter or TypeScript compiler API.
    """

    def __init__(self):
        """Initialize the parser."""
        pass

    def parse_file(self, file_path: str) -> TSModuleDoc:
        """
        Parse a TypeScript/JavaScript file and extract documentation.

        Args:
            file_path: Path to TS/JS file

        Returns:
            TSModuleDoc with all extracted documentation
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            module_doc = TSModuleDoc(
                name=Path(file_path).stem,
                file_path=file_path
            )

            # Extract file-level JSDoc comment
            file_comment = self._extract_file_comment(source_code)
            if file_comment:
                module_doc.description = self._extract_jsdoc_description(file_comment)

            # Extract imports
            module_doc.imports = self._extract_imports(source_code)

            # Extract exports
            module_doc.exports = self._extract_exports(source_code)

            # Extract interfaces
            module_doc.interfaces = self._extract_interfaces(source_code)

            # Extract type aliases
            module_doc.types = self._extract_type_aliases(source_code)

            # Extract classes
            module_doc.classes = self._extract_classes(source_code)

            # Extract functions
            module_doc.functions = self._extract_functions(source_code)

            # Extract constants
            module_doc.constants = self._extract_constants(source_code)

            logger.info(f"Parsed {file_path}: {len(module_doc.classes)} classes, "
                       f"{len(module_doc.interfaces)} interfaces, {len(module_doc.functions)} functions")

            return module_doc

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return TSModuleDoc(
                name=Path(file_path).stem,
                file_path=file_path,
                description=f"Failed to parse: {str(e)}"
            )

    def _extract_file_comment(self, source: str) -> Optional[str]:
        """Extract file-level comment."""
        # Look for comment at start of file
        match = re.match(r'^\s*/\*\*(.*?)\*/\s*', source, re.DOTALL)
        if match:
            return match.group(1)
        return None

    def _extract_jsdoc_description(self, jsdoc: str) -> str:
        """Extract description from JSDoc comment."""
        lines = jsdoc.strip().split('\n')
        desc_lines = []

        for line in lines:
            line = line.strip().lstrip('*').strip()
            if line.startswith('@'):
                break
            if line:
                desc_lines.append(line)

        return ' '.join(desc_lines)

    def _extract_imports(self, source: str) -> List[str]:
        """Extract import statements."""
        imports = []

        # Match ES6 imports
        import_pattern = r'import\s+(?:{[^}]+}|[\w\s,]+)\s+from\s+[\'"]([^\'"]+)[\'"]'
        for match in re.finditer(import_pattern, source):
            imports.append(match.group(1))

        # Match require statements
        require_pattern = r'require\([\'"]([^\'"]+)[\'"]\)'
        for match in re.finditer(require_pattern, source):
            imports.append(match.group(1))

        return list(set(imports))

    def _extract_exports(self, source: str) -> List[str]:
        """Extract export statements."""
        exports = []

        # Named exports
        export_pattern = r'export\s+(?:const|let|var|function|class|interface|type)\s+(\w+)'
        for match in re.finditer(export_pattern, source):
            exports.append(match.group(1))

        # Export { ... }
        export_list_pattern = r'export\s+{([^}]+)}'
        for match in re.finditer(export_list_pattern, source):
            names = match.group(1).split(',')
            for name in names:
                clean_name = name.strip().split(' as ')[0].strip()
                exports.append(clean_name)

        return list(set(exports))

    def _extract_interfaces(self, source: str) -> List[TSInterfaceDoc]:
        """Extract TypeScript interfaces."""
        interfaces = []

        # Pattern to match interface declarations
        interface_pattern = r'(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+([\w,\s]+))?\s*{([^}]*)}'

        for match in re.finditer(interface_pattern, source, re.MULTILINE | re.DOTALL):
            name = match.group(1)
            extends_str = match.group(2)
            body = match.group(3)

            interface_doc = TSInterfaceDoc(
                name=name,
                is_export='export' in source[max(0, match.start()-10):match.start()],
                line_number=source[:match.start()].count('\n') + 1
            )

            if extends_str:
                interface_doc.extends = [e.strip() for e in extends_str.split(',')]

            # Extract properties
            for prop_match in re.finditer(r'(\w+)(?:\?)?\s*:\s*([^;]+);?', body):
                prop_name = prop_match.group(1)
                prop_type = prop_match.group(2).strip()
                interface_doc.properties.append({
                    'name': prop_name,
                    'type': prop_type
                })

            # Look for JSDoc comment before interface
            jsdoc = self._find_jsdoc_before(source, match.start())
            if jsdoc:
                interface_doc.jsdoc = jsdoc
                interface_doc.description = self._extract_jsdoc_description(jsdoc)

            interfaces.append(interface_doc)

        return interfaces

    def _extract_type_aliases(self, source: str) -> List[Dict[str, Any]]:
        """Extract TypeScript type aliases."""
        types = []

        type_pattern = r'(?:export\s+)?type\s+(\w+)\s*=\s*([^;]+);'

        for match in re.finditer(type_pattern, source):
            types.append({
                'name': match.group(1),
                'definition': match.group(2).strip(),
                'is_export': 'export' in source[max(0, match.start()-10):match.start()],
                'line_number': source[:match.start()].count('\n') + 1
            })

        return types

    def _extract_classes(self, source: str) -> List[TSClassDoc]:
        """Extract class declarations."""
        classes = []

        # Simplified class pattern
        class_pattern = r'(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?\s*{'

        for match in re.finditer(class_pattern, source):
            name = match.group(1)
            extends = match.group(2)
            implements_str = match.group(3)

            class_doc = TSClassDoc(
                name=name,
                extends=extends,
                is_export='export' in source[max(0, match.start()-10):match.start()],
                line_number=source[:match.start()].count('\n') + 1
            )

            if implements_str:
                class_doc.implements = [i.strip() for i in implements_str.split(',')]

            # Look for JSDoc
            jsdoc = self._find_jsdoc_before(source, match.start())
            if jsdoc:
                class_doc.jsdoc = jsdoc
                class_doc.description = self._extract_jsdoc_description(jsdoc)

            classes.append(class_doc)

        return classes

    def _extract_functions(self, source: str) -> List[TSFunctionDoc]:
        """Extract function declarations."""
        functions = []

        # Function declaration pattern
        func_pattern = r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)(?:\s*:\s*([^{]+))?\s*{'

        for match in re.finditer(func_pattern, source):
            name = match.group(1)
            params_str = match.group(2)
            return_type = match.group(3)

            func_doc = TSFunctionDoc(
                name=name,
                signature=match.group(0).rstrip('{').strip(),
                is_export='export' in source[max(0, match.start()-10):match.start()],
                is_async='async' in match.group(0),
                line_number=source[:match.start()].count('\n') + 1
            )

            if return_type:
                func_doc.return_type = return_type.strip()

            # Parse parameters
            if params_str.strip():
                func_doc.parameters = self._parse_parameters(params_str)

            # Look for JSDoc
            jsdoc = self._find_jsdoc_before(source, match.start())
            if jsdoc:
                func_doc.jsdoc = jsdoc
                func_doc.description = self._extract_jsdoc_description(jsdoc)

            functions.append(func_doc)

        # Arrow functions
        arrow_pattern = r'(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)(?:\s*:\s*([^=]+))?\s*=>'

        for match in re.finditer(arrow_pattern, source):
            name = match.group(1)
            params_str = match.group(2)
            return_type = match.group(3)

            func_doc = TSFunctionDoc(
                name=name,
                signature=match.group(0).strip(),
                is_export='export' in source[max(0, match.start()-10):match.start()],
                is_async='async' in match.group(0),
                is_arrow=True,
                line_number=source[:match.start()].count('\n') + 1
            )

            if return_type:
                func_doc.return_type = return_type.strip()

            if params_str.strip():
                func_doc.parameters = self._parse_parameters(params_str)

            jsdoc = self._find_jsdoc_before(source, match.start())
            if jsdoc:
                func_doc.jsdoc = jsdoc
                func_doc.description = self._extract_jsdoc_description(jsdoc)

            functions.append(func_doc)

        return functions

    def _parse_parameters(self, params_str: str) -> List[TSParameterInfo]:
        """Parse function parameters."""
        parameters = []

        for param in params_str.split(','):
            param = param.strip()
            if not param:
                continue

            # Parse parameter with type annotation
            match = re.match(r'(\w+)(\?)?(?:\s*:\s*([^=]+))?(?:\s*=\s*(.+))?', param)
            if match:
                name = match.group(1)
                is_optional = match.group(2) is not None
                type_annotation = match.group(3)
                default_value = match.group(4)

                param_info = TSParameterInfo(
                    name=name,
                    is_optional=is_optional or default_value is not None
                )

                if type_annotation:
                    param_info.type_annotation = type_annotation.strip()

                if default_value:
                    param_info.default_value = default_value.strip()

                parameters.append(param_info)

        return parameters

    def _extract_constants(self, source: str) -> List[Dict[str, Any]]:
        """Extract constant declarations."""
        constants = []

        const_pattern = r'(?:export\s+)?const\s+([A-Z_][A-Z0-9_]*)\s*(?::\s*([^=]+))?\s*=\s*([^;]+);'

        for match in re.finditer(const_pattern, source):
            constants.append({
                'name': match.group(1),
                'type': match.group(2).strip() if match.group(2) else None,
                'value': match.group(3).strip(),
                'is_export': 'export' in source[max(0, match.start()-10):match.start()],
                'line_number': source[:match.start()].count('\n') + 1
            })

        return constants

    def _find_jsdoc_before(self, source: str, position: int) -> Optional[str]:
        """Find JSDoc comment before a given position."""
        # Look backwards for JSDoc comment
        preceding_text = source[max(0, position-500):position]

        match = re.search(r'/\*\*(.*?)\*/\s*$', preceding_text, re.DOTALL)
        if match:
            return match.group(1)

        return None


def get_typescript_ast_parser() -> TypeScriptASTParser:
    """Get TypeScript AST parser instance."""
    return TypeScriptASTParser()
