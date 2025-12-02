"""
Dart/Flutter parser using the official Dart analyzer for 100% accuracy.

This parser invokes the Dart AST extractor tool and converts the output
to FlowRAG's internal format for Neo4j and Qdrant storage.

Ingestion Agent is responsible for this module.
"""

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, List, Optional, Dict

from databases.neo4j import NodeLabel
from .base import BaseParser, CodeUnit, ParseResult

logger = logging.getLogger(__name__)

# Path to the Dart AST extractor tool
DART_ANALYZER_DIR = Path(__file__).parent.parent.parent / "tools" / "dart_analyzer"
DART_EXTRACTOR_SCRIPT = DART_ANALYZER_DIR / "bin" / "extract_ast.dart"

# Try to find Dart executable
DART_PATHS = [
    os.environ.get("DART_PATH", ""),
    os.path.expanduser("~/Documents/Flutter/flutter/bin/dart"),
    os.path.expanduser("~/flutter/bin/dart"),
    "/opt/homebrew/bin/dart",
    "/usr/local/bin/dart",
    "dart",  # fallback to PATH
]


def find_dart_executable() -> Optional[str]:
    """Find the Dart executable on the system."""
    for dart_path in DART_PATHS:
        if not dart_path:
            continue
        try:
            result = subprocess.run(
                [dart_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.debug(f"Found Dart at: {dart_path}")
                return dart_path
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
    return None


class DartAstParser(BaseParser):
    """Parser for Dart/Flutter source code using the official Dart analyzer."""

    def __init__(self):
        """Initialize Dart AST parser."""
        super().__init__("dart")
        self.dart_executable = find_dart_executable()
        if not self.dart_executable:
            logger.warning(
                "Dart executable not found. DartAstParser will fall back to regex parsing."
            )
        elif not DART_EXTRACTOR_SCRIPT.exists():
            logger.warning(
                f"Dart extractor script not found at {DART_EXTRACTOR_SCRIPT}. "
                "Run 'dart pub get' in tools/dart_analyzer to set up."
            )

    def _can_use_ast_parser(self) -> bool:
        """Check if we can use the AST-based parser."""
        return (
            self.dart_executable is not None
            and DART_EXTRACTOR_SCRIPT.exists()
        )

    def parse_file(
        self,
        file_path: str,
        namespace: str,
        content: Optional[str] = None,
    ) -> ParseResult:
        """Parse a Dart file using the Dart analyzer."""
        start_time = time.time()

        if self._can_use_ast_parser():
            try:
                result = self._parse_with_dart_analyzer(file_path, namespace)
                result.parse_time = time.time() - start_time
                return result
            except Exception as e:
                logger.warning(f"Dart analyzer failed, falling back to regex: {e}")

        # Fallback to regex-based parsing
        if content is None:
            content = self.read_file(file_path)
        result = self._parse_with_regex(content, namespace, file_path)
        result.parse_time = time.time() - start_time
        return result

    def _parse_with_dart_analyzer(
        self, file_path: str, namespace: str
    ) -> ParseResult:
        """Parse using the Dart AST extractor."""
        # Run the Dart extractor
        result = subprocess.run(
            [
                self.dart_executable,
                "run",
                str(DART_EXTRACTOR_SCRIPT),
                "-f", file_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(DART_ANALYZER_DIR),
        )

        if result.returncode != 0:
            raise RuntimeError(f"Dart extractor failed: {result.stderr}")

        # Parse JSON output
        data = json.loads(result.stdout)
        if not data.get("files"):
            raise RuntimeError("No files in Dart extractor output")

        file_data = data["files"][0]
        return self._convert_to_parse_result(file_data, namespace)

    def _convert_to_parse_result(
        self, file_data: Dict[str, Any], namespace: str
    ) -> ParseResult:
        """Convert Dart extractor output to ParseResult."""
        file_path = file_data["file_path"]

        classes: List[CodeUnit] = []
        functions: List[CodeUnit] = []
        methods: List[CodeUnit] = []
        imports: List[Dict[str, str]] = []
        calls: List[Dict[str, str]] = []

        # Process classes
        for cls_data in file_data.get("classes", []):
            class_unit = CodeUnit(
                id=self._generate_id(file_path, cls_data["name"], cls_data["line_start"]),
                name=cls_data["name"],
                type=self._get_class_type(cls_data),
                file_path=file_path,
                language="dart",
                code=cls_data.get("code", "")[:2000],
                signature=self._build_class_signature(cls_data),
                docstring=cls_data.get("docstring"),
                line_start=cls_data["line_start"],
                line_end=cls_data["line_end"],
                namespace=namespace,
            )
            classes.append(class_unit)

            # Process methods within the class
            for method_data in cls_data.get("methods", []):
                method_unit = CodeUnit(
                    id=self._generate_id(
                        file_path,
                        f"{cls_data['name']}.{method_data['name']}",
                        method_data["line_start"],
                    ),
                    name=method_data["name"],
                    type=NodeLabel.METHOD,
                    file_path=file_path,
                    language="dart",
                    code=method_data.get("code", "")[:2000],
                    signature=self._build_method_signature(method_data),
                    docstring=method_data.get("docstring"),
                    line_start=method_data["line_start"],
                    line_end=method_data["line_end"],
                    parameters=self._extract_param_names(method_data.get("parameters", [])),
                    return_type=method_data.get("return_type"),
                    namespace=namespace,
                )
                methods.append(method_unit)

        # Process top-level functions
        for func_data in file_data.get("functions", []):
            func_unit = CodeUnit(
                id=self._generate_id(file_path, func_data["name"], func_data["line_start"]),
                name=func_data["name"],
                type=NodeLabel.FUNCTION,
                file_path=file_path,
                language="dart",
                code=func_data.get("code", "")[:2000],
                signature=self._build_function_signature(func_data),
                docstring=func_data.get("docstring"),
                line_start=func_data["line_start"],
                line_end=func_data["line_end"],
                parameters=self._extract_param_names(func_data.get("parameters", [])),
                return_type=func_data.get("return_type"),
                namespace=namespace,
            )
            functions.append(func_unit)

        # Process imports - only include required string fields
        for imp_data in file_data.get("imports", []):
            import_entry = {
                "from": file_path,
                "to": imp_data["uri"],
                "type": "import",
            }
            # Only add prefix if it's not None
            if imp_data.get("prefix"):
                import_entry["prefix"] = imp_data["prefix"]
            imports.append(import_entry)

        # Process calls - only include string fields
        for call_data in file_data.get("calls", []):
            call_name = call_data.get("method") or call_data.get("constructor", "")
            target = call_data.get("target")

            calls.append({
                "from": file_path,
                "to": f"{target}.{call_name}" if target else call_name,
                "type": "calls",
            })

        # Process routes as special metadata
        routes = file_data.get("routes", [])
        if routes:
            # Add routes as special function metadata
            for func in functions:
                if func.name == "_createRouter" or "router" in func.name.lower():
                    func.calls = [
                        f"route:{r['path']}->{r.get('builder_widget', 'unknown')}"
                        for r in routes
                    ]

        return ParseResult(
            file_path=file_path,
            language="dart",
            namespace=namespace,
            classes=classes,
            functions=functions,
            methods=methods,
            imports=imports,
            calls=calls,
            total_lines=file_data.get("total_lines", 0),
            code_lines=file_data.get("code_lines", 0),
        )

    def _get_class_type(self, cls_data: Dict[str, Any]) -> NodeLabel:
        """Determine the appropriate NodeLabel for a class."""
        # Could extend to WIDGET type if we add it to NodeLabel
        return NodeLabel.CLASS

    def _build_class_signature(self, cls_data: Dict[str, Any]) -> str:
        """Build a class signature string."""
        parts = []
        if cls_data.get("is_abstract"):
            parts.append("abstract")
        parts.append("class")
        parts.append(cls_data["name"])

        if cls_data.get("extends"):
            parts.append(f"extends {cls_data['extends']}")
        if cls_data.get("mixins"):
            parts.append(f"with {', '.join(cls_data['mixins'])}")
        if cls_data.get("implements"):
            parts.append(f"implements {', '.join(cls_data['implements'])}")

        return " ".join(parts)

    def _build_function_signature(self, func_data: Dict[str, Any]) -> str:
        """Build a function signature string."""
        params = self._format_params(func_data.get("parameters", []))
        return_type = func_data.get("return_type", "void")
        async_marker = "async " if func_data.get("is_async") else ""
        return f"{return_type} {func_data['name']}({params}) {async_marker}".strip()

    def _build_method_signature(self, method_data: Dict[str, Any]) -> str:
        """Build a method signature string."""
        if method_data.get("is_constructor"):
            params = self._format_params(method_data.get("parameters", []))
            const = "const " if method_data.get("is_const") else ""
            factory = "factory " if method_data.get("is_factory") else ""
            return f"{const}{factory}{method_data['name']}({params})"
        return self._build_function_signature(method_data)

    def _format_params(self, params: List[Dict[str, Any]]) -> str:
        """Format parameter list for signature."""
        formatted = []
        for p in params:
            if p.get("type"):
                formatted.append(f"{p['type']} {p['name']}")
            else:
                formatted.append(p.get("name", "?"))
        return ", ".join(formatted)

    def _extract_param_names(self, params: List[Dict[str, Any]]) -> List[str]:
        """Extract just parameter names."""
        return [p.get("name", "") for p in params if p.get("name")]

    def _generate_id(self, file_path: str, name: str, line: int) -> str:
        """Generate unique ID for code unit."""
        import hashlib
        unique_str = f"{file_path}:{name}:{line}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:16]

    def _parse_with_regex(
        self, code: str, namespace: str, file_path: str
    ) -> ParseResult:
        """Fallback regex-based parsing (from original dart_parser.py)."""
        # Import the original regex-based parser as fallback
        from .dart_parser import DartParser
        fallback_parser = DartParser()
        return fallback_parser.parse_string(code, namespace, file_path)

    def parse_string(
        self,
        code: str,
        namespace: str,
        file_path: str = "<string>",
    ) -> ParseResult:
        """Parse Dart code string."""
        # For string input, use regex fallback (AST requires a file)
        return self._parse_with_regex(code, namespace, file_path)

    def read_file(self, file_path: str) -> str:
        """Read file content."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()


    def extract_functions(self, tree: Any) -> List[CodeUnit]:
        """
        Extract functions from AST.

        Note: For DartAstParser, the tree is the JSON dict from the Dart analyzer.
        This method is provided for interface compatibility but the main entry
        point is parse_file() which returns a complete ParseResult.
        """
        if isinstance(tree, dict) and "functions" in tree:
            # Convert from JSON format - but this requires namespace
            # which we don't have here. Return empty and use parse_file instead.
            return []
        return []

    def extract_classes(self, tree: Any) -> List[CodeUnit]:
        """
        Extract classes from AST.

        Note: For DartAstParser, the tree is the JSON dict from the Dart analyzer.
        This method is provided for interface compatibility but the main entry
        point is parse_file() which returns a complete ParseResult.
        """
        if isinstance(tree, dict) and "classes" in tree:
            return []
        return []


def get_dart_ast_parser() -> DartAstParser:
    """Get Dart AST parser instance."""
    return DartAstParser()
