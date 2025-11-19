"""
Base parser interface for code analysis.

Ingestion Agent is responsible for this module.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field

from databases.neo4j import NodeLabel


class CodeUnit(BaseModel):
    """Represents a parsed code unit (function, class, module)."""

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Name of the code unit")
    type: NodeLabel = Field(..., description="Type of code unit")
    file_path: str = Field(..., description="Source file path")
    language: str = Field(..., description="Programming language")

    # Code content
    code: str = Field(..., description="Source code")
    signature: Optional[str] = Field(None, description="Function/method signature")
    docstring: Optional[str] = Field(None, description="Documentation string")

    # Location
    line_start: int = Field(..., description="Starting line number")
    line_end: int = Field(..., description="Ending line number")

    # Metadata
    complexity: Optional[int] = Field(None, description="Cyclomatic complexity")
    parameters: List[str] = Field(default_factory=list, description="Parameter names")
    return_type: Optional[str] = Field(None, description="Return type")
    decorators: List[str] = Field(default_factory=list, description="Decorators")

    # Relationships
    parent_id: Optional[str] = Field(None, description="Parent class/module ID")
    calls: List[str] = Field(default_factory=list, description="Called function names")
    imports: List[str] = Field(default_factory=list, description="Imported modules")

    # Context
    namespace: str = Field(..., description="Namespace for multi-tenancy")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ParseResult(BaseModel):
    """Result of parsing a source file."""

    file_path: str = Field(..., description="Parsed file path")
    language: str = Field(..., description="Programming language")
    namespace: str = Field(..., description="Namespace")

    # Extracted code units
    modules: List[CodeUnit] = Field(default_factory=list)
    classes: List[CodeUnit] = Field(default_factory=list)
    functions: List[CodeUnit] = Field(default_factory=list)
    methods: List[CodeUnit] = Field(default_factory=list)

    # Relationships
    imports: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Import relationships"
    )
    calls: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Function call relationships"
    )

    # Metrics
    total_lines: int = Field(default=0, description="Total lines of code")
    code_lines: int = Field(default=0, description="Non-comment, non-blank lines")
    parse_time: float = Field(default=0.0, description="Parse time in seconds")

    @property
    def all_units(self) -> List[CodeUnit]:
        """Get all code units."""
        return self.modules + self.classes + self.functions + self.methods

    @property
    def unit_count(self) -> int:
        """Get total number of code units."""
        return len(self.all_units)


class BaseParser(ABC):
    """
    Abstract base class for language-specific code parsers.

    Parsers extract code structure and relationships from source files.
    """

    def __init__(self, language: str):
        """
        Initialize parser.

        Args:
            language: Programming language name
        """
        self.language = language

    @abstractmethod
    def parse_file(
        self,
        file_path: str,
        namespace: str,
        content: Optional[str] = None,
    ) -> ParseResult:
        """
        Parse a source code file.

        Args:
            file_path: Path to source file
            namespace: Namespace for multi-tenancy
            content: Optional file content (if already loaded)

        Returns:
            ParseResult with extracted code units and relationships
        """
        pass

    @abstractmethod
    def parse_string(
        self,
        code: str,
        namespace: str,
        file_path: str = "<string>",
    ) -> ParseResult:
        """
        Parse a code string.

        Args:
            code: Source code string
            namespace: Namespace
            file_path: Virtual file path

        Returns:
            ParseResult with extracted code units
        """
        pass

    @abstractmethod
    def extract_functions(self, tree: Any) -> List[CodeUnit]:
        """
        Extract functions from AST.

        Args:
            tree: Language-specific AST

        Returns:
            List of function code units
        """
        pass

    @abstractmethod
    def extract_classes(self, tree: Any) -> List[CodeUnit]:
        """
        Extract classes from AST.

        Args:
            tree: Language-specific AST

        Returns:
            List of class code units
        """
        pass

    def read_file(self, file_path: str) -> str:
        """
        Read file content with encoding detection.

        Args:
            file_path: Path to file

        Returns:
            File content as string
        """
        path = Path(file_path)

        # Try UTF-8 first
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback to latin-1
            return path.read_text(encoding="latin-1")

    def count_lines(self, code: str) -> tuple[int, int]:
        """
        Count total and code lines.

        Args:
            code: Source code

        Returns:
            Tuple of (total_lines, code_lines)
        """
        lines = code.split("\n")
        total = len(lines)

        # Count non-empty, non-comment lines
        code_lines = sum(
            1 for line in lines
            if line.strip() and not line.strip().startswith(("#", "//", "/*", "*"))
        )

        return total, code_lines

    def generate_id(self, name: str, file_path: str, line: int) -> str:
        """
        Generate unique ID for a code unit.

        Args:
            name: Code unit name
            file_path: File path
            line: Line number

        Returns:
            Unique identifier
        """
        import hashlib

        # Create deterministic ID
        key = f"{file_path}:{line}:{name}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]


def get_parser(language: str) -> Optional[BaseParser]:
    """
    Get parser for a programming language.

    Args:
        language: Language name (python, javascript, typescript, etc.)

    Returns:
        Parser instance or None if language not supported
    """
    language = language.lower()

    if language == "python":
        from .python_parser import PythonParser
        return PythonParser()
    elif language in ("javascript", "js"):
        from .javascript_parser import JavaScriptParser
        return JavaScriptParser()
    elif language in ("typescript", "ts"):
        from .javascript_parser import TypeScriptParser
        return TypeScriptParser()
    elif language == "go":
        from .go_parser import GoParser
        return GoParser()
    elif language == "java":
        from .java_parser import JavaParser
        return JavaParser()
    else:
        return None


def detect_language(file_path: str) -> Optional[str]:
    """
    Detect programming language from file extension.

    Args:
        file_path: Path to file

    Returns:
        Language name or None
    """
    extension_map = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".rb": "ruby",
        ".php": "php",
    }

    suffix = Path(file_path).suffix.lower()
    return extension_map.get(suffix)
