"""
PDF parser for documentation analysis.

Extracts text, structure, and procedure steps from PDF documents.
"""

import re
import hashlib
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise ImportError("Please install pypdf or PyPDF2: pip install pypdf")

from .base import DocumentUnit


class PDFParser:
    """
    Parser for PDF documentation files.

    Extracts:
    - Text content per page
    - Numbered lists and procedure steps
    - Section headers
    - Metadata
    """

    def __init__(self):
        """Initialize PDF parser."""
        self.language = "pdf"

    def parse_file(
        self,
        file_path: str,
        namespace: str,
    ) -> List[DocumentUnit]:
        """
        Parse a PDF file and extract documentation units.

        Args:
            file_path: Path to PDF file
            namespace: Namespace for multi-tenancy

        Returns:
            List of DocumentUnit objects
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        # Read PDF
        reader = PdfReader(str(path))

        documents = []

        # Extract text from each page
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()

            if not text or not text.strip():
                continue

            # Parse page into document units
            page_docs = self._parse_page(
                text=text,
                page_number=page_num,
                file_path=str(file_path),
                namespace=namespace,
            )

            documents.extend(page_docs)

        return documents

    def _parse_page(
        self,
        text: str,
        page_number: int,
        file_path: str,
        namespace: str,
    ) -> List[DocumentUnit]:
        """
        Parse a single page into document units.

        Args:
            text: Page text content
            page_number: Page number
            file_path: Source file path
            namespace: Namespace

        Returns:
            List of DocumentUnit objects for this page
        """
        documents = []

        # Split into paragraphs
        paragraphs = self._split_paragraphs(text)

        for para_num, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue

            # Detect if this is a numbered list/procedure
            is_numbered, step_number = self._is_numbered_list(paragraph)

            # Detect section headers
            is_header, header_level = self._is_section_header(paragraph)

            # Determine type
            if is_header:
                doc_type = "section"
                title = paragraph.strip()
            elif is_numbered:
                doc_type = "step"
                title = f"Step {step_number}"
            else:
                doc_type = "paragraph"
                title = self._extract_title(paragraph)

            # Generate ID
            doc_id = self._generate_id(
                title=title,
                file_path=file_path,
                page=page_number,
                index=para_num,
            )

            # Create DocumentUnit
            doc = DocumentUnit(
                id=doc_id,
                title=title,
                type=doc_type,
                file_path=file_path,
                content=paragraph.strip(),
                raw_content=paragraph,
                page_number=page_number,
                is_procedure=is_numbered,
                is_numbered_list=is_numbered,
                step_number=step_number if is_numbered else None,
                namespace=namespace,
            )

            documents.append(doc)

        return documents

    def _split_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs.

        Args:
            text: Page text

        Returns:
            List of paragraph strings
        """
        # Split on double newlines or numbered list items
        paragraphs = []
        current = []

        lines = text.split('\n')

        for line in lines:
            stripped = line.strip()

            # Check if this is a numbered list item
            is_num, _ = self._is_numbered_list(stripped)

            # Start new paragraph if:
            # - Empty line
            # - New numbered item
            # - Section header
            if not stripped:
                if current:
                    paragraphs.append('\n'.join(current))
                    current = []
            elif is_num and current:
                # Save previous paragraph and start new
                paragraphs.append('\n'.join(current))
                current = [line]
            else:
                current.append(line)

        # Add last paragraph
        if current:
            paragraphs.append('\n'.join(current))

        return paragraphs

    def _is_numbered_list(self, text: str) -> tuple[bool, Optional[int]]:
        """
        Check if text is a numbered list item.

        Args:
            text: Text to check

        Returns:
            Tuple of (is_numbered, step_number)
        """
        # Patterns for numbered lists:
        # 1. Step description
        # 1) Step description
        # Step 1: Description
        # (1) Description

        patterns = [
            r'^\s*(\d+)\.\s+',       # 1. Description
            r'^\s*(\d+)\)\s+',       # 1) Description
            r'^\s*Step\s+(\d+):?\s+', # Step 1: Description
            r'^\s*\((\d+)\)\s+',     # (1) Description
        ]

        for pattern in patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                try:
                    step_num = int(match.group(1))
                    return True, step_num
                except (ValueError, IndexError):
                    continue

        return False, None

    def _is_section_header(self, text: str) -> tuple[bool, Optional[int]]:
        """
        Check if text is a section header.

        Args:
            text: Text to check

        Returns:
            Tuple of (is_header, header_level)
        """
        stripped = text.strip()

        # Section headers are typically:
        # - All caps
        # - Short (< 100 chars)
        # - No punctuation at end (except :)
        # - May have numbering like "1.2.3 TITLE"

        if len(stripped) > 100:
            return False, None

        # Check for section numbering
        section_pattern = r'^(\d+(\.\d+)*)\s+'
        section_match = re.match(section_pattern, stripped)

        # Check if all caps (at least 50% uppercase)
        alpha_chars = [c for c in stripped if c.isalpha()]
        if alpha_chars:
            upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            is_caps = upper_ratio > 0.5
        else:
            is_caps = False

        # Check for header patterns
        is_header = (
            is_caps or
            section_match or
            stripped.endswith(':') and len(stripped.split()) <= 10
        )

        # Determine level from section numbering
        level = None
        if section_match:
            level = section_match.group(1).count('.') + 1

        return is_header, level

    def _extract_title(self, text: str) -> str:
        """
        Extract a title from paragraph text.

        Args:
            text: Paragraph text

        Returns:
            Title string (first line or first N words)
        """
        # Get first line
        first_line = text.split('\n')[0].strip()

        # Truncate to reasonable length
        if len(first_line) > 80:
            words = first_line.split()[:10]
            return ' '.join(words) + '...'

        return first_line

    def _generate_id(
        self,
        title: str,
        file_path: str,
        page: int,
        index: int,
    ) -> str:
        """
        Generate unique ID for a document unit.

        Args:
            title: Document title
            file_path: Source file path
            page: Page number
            index: Paragraph index

        Returns:
            Unique identifier
        """
        key = f"{file_path}:page{page}:para{index}:{title}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract PDF metadata.

        Args:
            file_path: Path to PDF file

        Returns:
            Dictionary of metadata
        """
        reader = PdfReader(str(file_path))

        metadata = {
            'page_count': len(reader.pages),
            'title': None,
            'author': None,
            'subject': None,
            'creator': None,
            'producer': None,
            'creation_date': None,
        }

        # Extract metadata if available
        if hasattr(reader, 'metadata') and reader.metadata:
            meta = reader.metadata
            if hasattr(meta, 'title'):
                metadata['title'] = meta.title
            if hasattr(meta, 'author'):
                metadata['author'] = meta.author
            if hasattr(meta, 'subject'):
                metadata['subject'] = meta.subject
            if hasattr(meta, 'creator'):
                metadata['creator'] = meta.creator
            if hasattr(meta, 'producer'):
                metadata['producer'] = meta.producer
            if hasattr(meta, 'creation_date'):
                metadata['creation_date'] = str(meta.creation_date)

        return metadata
