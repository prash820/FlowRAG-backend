"""
Document chunking for text and markdown files.

Splits documents into semantic chunks with overlap.
Ingestion Agent is responsible for this module.
"""

from typing import List, Optional
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field

from config import get_settings


class DocumentChunk(BaseModel):
    """Represents a document chunk."""

    id: str = Field(..., description="Unique chunk ID")
    content: str = Field(..., description="Chunk text content")
    file_path: str = Field(..., description="Source file path")
    chunk_index: int = Field(..., description="Chunk index in document")
    total_chunks: int = Field(..., description="Total chunks in document")

    # Metadata
    section_title: Optional[str] = Field(None, description="Section title if any")
    word_count: int = Field(..., description="Number of words")
    char_count: int = Field(..., description="Number of characters")

    # Context
    namespace: str = Field(..., description="Namespace")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class DocumentChunker:
    """
    Chunker for text and markdown documents.

    Splits documents into overlapping chunks of specified size.
    """

    def __init__(
        self,
        max_chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        """
        Initialize chunker.

        Args:
            max_chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap between chunks
        """
        settings = get_settings()

        self.max_chunk_size = max_chunk_size or settings.max_chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

    def chunk_file(
        self,
        file_path: str,
        namespace: str,
        content: Optional[str] = None,
    ) -> List[DocumentChunk]:
        """
        Chunk a document file.

        Args:
            file_path: Path to document
            namespace: Namespace
            content: Optional pre-loaded content

        Returns:
            List of document chunks
        """
        if content is None:
            content = Path(file_path).read_text(encoding="utf-8")

        return self.chunk_text(content, file_path, namespace)

    def chunk_text(
        self,
        text: str,
        file_path: str,
        namespace: str,
    ) -> List[DocumentChunk]:
        """
        Chunk text content.

        Args:
            text: Text to chunk
            file_path: Source file path
            namespace: Namespace

        Returns:
            List of chunks
        """
        # Split by paragraphs first
        paragraphs = self._split_paragraphs(text)

        # Group paragraphs into chunks
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            # Start new chunk if adding this paragraph exceeds max size
            if current_size + para_size > self.max_chunk_size and current_chunk:
                # Create chunk
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(chunk_text)

                # Start new chunk with overlap
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = [overlap_text] if overlap_text else []
                current_size = len(overlap_text) if overlap_text else 0

            current_chunk.append(para)
            current_size += para_size

        # Add final chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(chunk_text)

        # Create DocumentChunk objects
        total = len(chunks)
        doc_chunks = []

        for idx, chunk_text in enumerate(chunks):
            chunk_id = f"{Path(file_path).stem}_chunk_{idx}"

            doc_chunks.append(
                DocumentChunk(
                    id=chunk_id,
                    content=chunk_text,
                    file_path=file_path,
                    chunk_index=idx,
                    total_chunks=total,
                    section_title=self._extract_title(chunk_text),
                    word_count=len(chunk_text.split()),
                    char_count=len(chunk_text),
                    namespace=namespace,
                )
            )

        return doc_chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        # Split by double newlines
        paragraphs = text.split("\n\n")

        # Clean and filter
        return [p.strip() for p in paragraphs if p.strip()]

    def _get_overlap(self, chunks: List[str]) -> str:
        """Get overlap text from previous chunks."""
        if not chunks:
            return ""

        # Take last N characters for overlap
        combined = "\n\n".join(chunks)
        if len(combined) <= self.chunk_overlap:
            return combined

        return combined[-self.chunk_overlap:]

    def _extract_title(self, text: str) -> Optional[str]:
        """Extract title from chunk (e.g., markdown heading)."""
        lines = text.split("\n")

        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            # Markdown heading
            if line.startswith("#"):
                return line.lstrip("#").strip()

        return None
