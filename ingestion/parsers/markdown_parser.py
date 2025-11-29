"""
Markdown parser for documentation analysis.

Extracts headers, lists, code blocks, and procedure steps from Markdown files.
"""

import re
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from .base import DocumentUnit


class MarkdownParser:
    """
    Parser for Markdown documentation files.

    Extracts:
    - Headers (h1-h6)
    - Numbered and bulleted lists
    - Code blocks
    - Procedure steps
    - Paragraphs
    """

    def __init__(self):
        """Initialize Markdown parser."""
        self.language = "markdown"

    def parse_file(
        self,
        file_path: str,
        namespace: str,
    ) -> List[DocumentUnit]:
        """
        Parse a Markdown file and extract documentation units.

        Args:
            file_path: Path to Markdown file
            namespace: Namespace for multi-tenancy

        Returns:
            List of DocumentUnit objects
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Markdown file not found: {file_path}")

        # Read file
        content = path.read_text(encoding='utf-8')

        # Parse content
        documents = self._parse_content(
            content=content,
            file_path=str(file_path),
            namespace=namespace,
        )

        return documents

    def _parse_content(
        self,
        content: str,
        file_path: str,
        namespace: str,
    ) -> List[DocumentUnit]:
        """
        Parse Markdown content into document units.

        Args:
            content: Markdown content
            file_path: Source file path
            namespace: Namespace

        Returns:
            List of DocumentUnit objects
        """
        documents = []
        lines = content.split('\n')

        i = 0
        line_start = 1
        current_section = None  # Track current section for hierarchy

        while i < len(lines):
            line = lines[i]

            # Check for header
            header_level, header_text = self._parse_header(line)
            if header_level:
                doc = self._create_header_doc(
                    text=header_text,
                    level=header_level,
                    line_start=i + 1,
                    file_path=file_path,
                    namespace=namespace,
                    parent_id=current_section,
                )
                documents.append(doc)

                # Update current section
                if header_level <= 2:
                    current_section = doc.id

                i += 1
                continue

            # Check for code block
            if line.strip().startswith('```'):
                code_block, end_line = self._extract_code_block(lines, i)
                if code_block:
                    doc = self._create_code_block_doc(
                        code=code_block,
                        line_start=i + 1,
                        line_end=end_line + 1,
                        file_path=file_path,
                        namespace=namespace,
                        parent_id=current_section,
                    )
                    documents.append(doc)
                    i = end_line + 1
                    continue

            # Check for numbered list
            is_num, step_number = self._is_numbered_list(line)
            if is_num:
                # Extract full list item (may span multiple lines)
                list_text, end_line = self._extract_list_item(lines, i)
                doc = self._create_step_doc(
                    text=list_text,
                    step_number=step_number,
                    line_start=i + 1,
                    line_end=end_line + 1,
                    file_path=file_path,
                    namespace=namespace,
                    parent_id=current_section,
                )
                documents.append(doc)
                i = end_line + 1
                continue

            # Check for bulleted list
            if self._is_bullet_list(line):
                list_text, end_line = self._extract_list_item(lines, i)
                doc = self._create_list_doc(
                    text=list_text,
                    line_start=i + 1,
                    line_end=end_line + 1,
                    file_path=file_path,
                    namespace=namespace,
                    parent_id=current_section,
                )
                documents.append(doc)
                i = end_line + 1
                continue

            # Regular paragraph
            if line.strip():
                para_text, end_line = self._extract_paragraph(lines, i)
                if para_text.strip():
                    doc = self._create_paragraph_doc(
                        text=para_text,
                        line_start=i + 1,
                        line_end=end_line + 1,
                        file_path=file_path,
                        namespace=namespace,
                        parent_id=current_section,
                    )
                    documents.append(doc)
                    i = end_line + 1
                    continue

            i += 1

        return documents

    def _parse_header(self, line: str) -> Tuple[Optional[int], Optional[str]]:
        """
        Parse Markdown header.

        Args:
            line: Line to check

        Returns:
            Tuple of (header_level, header_text) or (None, None)
        """
        # ATX-style headers: # Header
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            return level, text

        return None, None

    def _extract_code_block(
        self,
        lines: List[str],
        start_index: int,
    ) -> Tuple[Optional[str], int]:
        """
        Extract code block content.

        Args:
            lines: All lines
            start_index: Starting line index

        Returns:
            Tuple of (code_content, end_index) or (None, start_index)
        """
        if not lines[start_index].strip().startswith('```'):
            return None, start_index

        # Find closing ```
        code_lines = []
        i = start_index + 1

        while i < len(lines):
            if lines[i].strip().startswith('```'):
                # Found closing marker
                return '\n'.join(code_lines), i

            code_lines.append(lines[i])
            i += 1

        # No closing marker found
        return None, start_index

    def _is_numbered_list(self, line: str) -> Tuple[bool, Optional[int]]:
        """
        Check if line is a numbered list item.

        Args:
            line: Line to check

        Returns:
            Tuple of (is_numbered, step_number)
        """
        # Markdown numbered list: 1. Item or 1) Item
        patterns = [
            r'^\s*(\d+)\.\s+',       # 1. Item
            r'^\s*(\d+)\)\s+',       # 1) Item
        ]

        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                try:
                    step_num = int(match.group(1))
                    return True, step_num
                except (ValueError, IndexError):
                    continue

        return False, None

    def _is_bullet_list(self, line: str) -> bool:
        """
        Check if line is a bulleted list item.

        Args:
            line: Line to check

        Returns:
            True if bulleted list
        """
        # Markdown bullets: -, *, +
        return bool(re.match(r'^\s*[-*+]\s+', line))

    def _extract_list_item(
        self,
        lines: List[str],
        start_index: int,
    ) -> Tuple[str, int]:
        """
        Extract full list item (may span multiple lines).

        Args:
            lines: All lines
            start_index: Starting line index

        Returns:
            Tuple of (item_text, end_index)
        """
        item_lines = [lines[start_index]]
        i = start_index + 1

        # Continue while lines are indented (sub-items) or empty
        while i < len(lines):
            line = lines[i]

            # Stop if we hit another list item or header
            if self._is_numbered_list(line)[0] or self._is_bullet_list(line):
                break
            if self._parse_header(line)[0] is not None:
                break

            # Stop if unindented non-empty line
            if line and not line.startswith((' ', '\t')):
                break

            item_lines.append(line)
            i += 1

        return '\n'.join(item_lines), i - 1

    def _extract_paragraph(
        self,
        lines: List[str],
        start_index: int,
    ) -> Tuple[str, int]:
        """
        Extract paragraph text.

        Args:
            lines: All lines
            start_index: Starting line index

        Returns:
            Tuple of (paragraph_text, end_index)
        """
        para_lines = []
        i = start_index

        while i < len(lines):
            line = lines[i]

            # Stop on empty line
            if not line.strip():
                break

            # Stop on special markdown elements
            if (self._parse_header(line)[0] or
                self._is_numbered_list(line)[0] or
                self._is_bullet_list(line) or
                line.strip().startswith('```')):
                break

            para_lines.append(line)
            i += 1

        return '\n'.join(para_lines), i - 1

    def _create_header_doc(
        self,
        text: str,
        level: int,
        line_start: int,
        file_path: str,
        namespace: str,
        parent_id: Optional[str] = None,
    ) -> DocumentUnit:
        """Create DocumentUnit for header."""
        doc_id = self._generate_id(f"header-{text}", file_path, line_start)

        return DocumentUnit(
            id=doc_id,
            title=text,
            type="section",
            file_path=file_path,
            content=text,
            raw_content=f"{'#' * level} {text}",
            line_start=line_start,
            line_end=line_start,
            section_number=str(level),
            parent_id=parent_id,
            namespace=namespace,
        )

    def _create_step_doc(
        self,
        text: str,
        step_number: int,
        line_start: int,
        line_end: int,
        file_path: str,
        namespace: str,
        parent_id: Optional[str] = None,
    ) -> DocumentUnit:
        """Create DocumentUnit for numbered step."""
        doc_id = self._generate_id(f"step-{step_number}", file_path, line_start)

        # Remove numbering from text
        clean_text = re.sub(r'^\s*\d+[.)]\s+', '', text)

        return DocumentUnit(
            id=doc_id,
            title=f"Step {step_number}",
            type="step",
            file_path=file_path,
            content=clean_text.strip(),
            raw_content=text,
            line_start=line_start,
            line_end=line_end,
            is_procedure=True,
            is_numbered_list=True,
            step_number=step_number,
            parent_id=parent_id,
            namespace=namespace,
        )

    def _create_list_doc(
        self,
        text: str,
        line_start: int,
        line_end: int,
        file_path: str,
        namespace: str,
        parent_id: Optional[str] = None,
    ) -> DocumentUnit:
        """Create DocumentUnit for bulleted list item."""
        doc_id = self._generate_id(f"list-{line_start}", file_path, line_start)

        # Remove bullet from text
        clean_text = re.sub(r'^\s*[-*+]\s+', '', text)

        # Extract title from first line
        first_line = clean_text.split('\n')[0].strip()
        title = first_line[:50] + ('...' if len(first_line) > 50 else '')

        return DocumentUnit(
            id=doc_id,
            title=title,
            type="list_item",
            file_path=file_path,
            content=clean_text.strip(),
            raw_content=text,
            line_start=line_start,
            line_end=line_end,
            parent_id=parent_id,
            namespace=namespace,
        )

    def _create_code_block_doc(
        self,
        code: str,
        line_start: int,
        line_end: int,
        file_path: str,
        namespace: str,
        parent_id: Optional[str] = None,
    ) -> DocumentUnit:
        """Create DocumentUnit for code block."""
        doc_id = self._generate_id(f"code-{line_start}", file_path, line_start)

        # Extract language if specified
        first_line = code.split('\n')[0] if code else ''

        title = f"Code Block (line {line_start})"

        return DocumentUnit(
            id=doc_id,
            title=title,
            type="code_block",
            file_path=file_path,
            content=code.strip(),
            raw_content=f"```\n{code}\n```",
            line_start=line_start,
            line_end=line_end,
            parent_id=parent_id,
            namespace=namespace,
        )

    def _create_paragraph_doc(
        self,
        text: str,
        line_start: int,
        line_end: int,
        file_path: str,
        namespace: str,
        parent_id: Optional[str] = None,
    ) -> DocumentUnit:
        """Create DocumentUnit for paragraph."""
        doc_id = self._generate_id(f"para-{line_start}", file_path, line_start)

        # Extract title from first line
        first_line = text.split('\n')[0].strip()
        title = first_line[:50] + ('...' if len(first_line) > 50 else '')

        return DocumentUnit(
            id=doc_id,
            title=title,
            type="paragraph",
            file_path=file_path,
            content=text.strip(),
            raw_content=text,
            line_start=line_start,
            line_end=line_end,
            parent_id=parent_id,
            namespace=namespace,
        )

    def _generate_id(
        self,
        prefix: str,
        file_path: str,
        line: int,
    ) -> str:
        """
        Generate unique ID for a document unit.

        Args:
            prefix: ID prefix
            file_path: Source file path
            line: Line number

        Returns:
            Unique identifier
        """
        key = f"{file_path}:{line}:{prefix}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]
