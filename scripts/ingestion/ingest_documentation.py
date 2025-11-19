#!/usr/bin/env python3
"""
Ingest Sock Shop Memory Bank Documentation into Qdrant

This script:
1. Reads the comprehensive documentation
2. Chunks it intelligently (by section)
3. Generates embeddings
4. Stores in Qdrant for semantic search
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from ingestion.chunkers.document_chunker import DocumentChunker
from ingestion.loaders.qdrant_loader import QdrantLoader
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DOCS_PATH = Path(__file__).parent / "docs/sock_shop_memory_bank.md"
NAMESPACE = "sock_shop:documentation"

def extract_sections(markdown_content: str):
    """Extract sections from markdown for intelligent chunking."""
    sections = []

    # Split by major headers (## )
    parts = re.split(r'\n## ', markdown_content)

    # First part is title + overview
    if parts:
        sections.append({
            'title': 'Overview',
            'content': parts[0],
            'level': 1
        })

    # Rest are sections
    for i, part in enumerate(parts[1:], 1):
        lines = part.split('\n', 1)
        if len(lines) == 2:
            title, content = lines
            sections.append({
                'title': title.strip(),
                'content': content.strip(),
                'level': 2,
                'section_id': i
            })

    return sections

def create_document_chunks(sections):
    """Create document chunks from sections."""
    chunks = []

    for section in sections:
        # For very long sections, split by subsections (###)
        if len(section['content']) > 3000:
            subsections = re.split(r'\n### ', section['content'])

            # First part
            chunks.append({
                'content': subsections[0],
                'section_title': section['title'],
                'subsection': 'main',
                'word_count': len(subsections[0].split())
            })

            # Subsections
            for subsection in subsections[1:]:
                lines = subsection.split('\n', 1)
                if len(lines) == 2:
                    subtitle, content = lines
                    chunks.append({
                        'content': content,
                        'section_title': section['title'],
                        'subsection': subtitle.strip(),
                        'word_count': len(content.split())
                    })
        else:
            # Small section - keep as one chunk
            chunks.append({
                'content': section['content'],
                'section_title': section['title'],
                'subsection': 'main',
                'word_count': len(section['content'].split())
            })

    return chunks

def main():
    """Ingest documentation into Qdrant."""
    logger.info(f"🚀 Starting documentation ingestion")
    logger.info(f"   File: {DOCS_PATH}")
    logger.info(f"   Namespace: {NAMESPACE}")

    # Read documentation
    if not DOCS_PATH.exists():
        logger.error(f"Documentation not found: {DOCS_PATH}")
        return

    logger.info(f"\n📖 Reading documentation...")
    content = DOCS_PATH.read_text()
    logger.info(f"   Total size: {len(content):,} characters")

    # Extract sections
    logger.info(f"\n✂️  Extracting sections...")
    sections = extract_sections(content)
    logger.info(f"   Found {len(sections)} major sections")

    # Create chunks
    logger.info(f"\n📦 Creating document chunks...")
    chunks = create_document_chunks(sections)
    logger.info(f"   Created {len(chunks)} chunks")

    # Show chunk distribution
    total_words = sum(c['word_count'] for c in chunks)
    logger.info(f"   Total words: {total_words:,}")
    logger.info(f"   Avg words per chunk: {total_words // len(chunks)}")

    # Convert to DocumentChunk objects
    logger.info(f"\n🔄 Converting to DocumentChunk objects...")
    from ingestion.chunkers.document_chunker import DocumentChunk
    import uuid

    doc_chunks = []
    for i, chunk in enumerate(chunks):
        doc_chunk = DocumentChunk(
            id=str(uuid.uuid4()),
            file_path=str(DOCS_PATH),
            chunk_index=i,
            total_chunks=len(chunks),
            content=chunk['content'],
            word_count=chunk['word_count'],
            char_count=len(chunk['content']),
            section_title=chunk['section_title'],
            namespace=NAMESPACE,
            metadata={
                'subsection': chunk['subsection'],
                'type': 'documentation',
                'source': 'sock_shop_memory_bank'
            }
        )
        doc_chunks.append(doc_chunk)

    # Load into Qdrant
    logger.info(f"\n📤 Loading into Qdrant...")
    loader = QdrantLoader()
    result = loader.load_document_chunks(doc_chunks, NAMESPACE)

    logger.info(f"\n✅ Documentation ingestion complete!")
    logger.info(f"   Chunks stored: {result.get('upserted_count', 0)}")
    logger.info(f"   Namespace: {NAMESPACE}")

    # Show some example chunks
    logger.info(f"\n📋 Sample chunks:")
    for i, chunk in enumerate(chunks[:5]):
        logger.info(f"\n   {i+1}. {chunk['section_title']}")
        if chunk['subsection'] != 'main':
            logger.info(f"      → {chunk['subsection']}")
        logger.info(f"      Words: {chunk['word_count']}")
        preview = chunk['content'][:100].replace('\n', ' ')
        logger.info(f"      Preview: {preview}...")

    logger.info(f"\n{'='*80}")
    logger.info(f"🎉 You can now ask questions about Sock Shop!")
    logger.info(f"{'='*80}")
    logger.info(f"\n💡 Example queries:")
    logger.info(f"   - How does payment authorization work?")
    logger.info(f"   - Explain the user registration flow")
    logger.info(f"   - What databases are used and why?")
    logger.info(f"   - How do services communicate?")
    logger.info(f"   - Show me the order creation flow")
    logger.info(f"\n{'='*80}\n")

if __name__ == "__main__":
    main()
