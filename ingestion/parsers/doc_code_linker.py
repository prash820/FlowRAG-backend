"""
Semantic code-to-documentation linking.

Uses embeddings to match code units with relevant documentation sections.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class DocCodeLinker:
    """
    Link code units to documentation using semantic similarity.

    Uses embeddings to find relevant documentation for code functions,
    classes, and modules.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        embedding_model: str = "text-embedding-3-small",
        similarity_threshold: float = 0.75,
    ):
        """
        Initialize doc-code linker.

        Args:
            api_key: OpenAI API key (if None, uses OPENAI_API_KEY env var)
            embedding_model: OpenAI embedding model
            similarity_threshold: Minimum similarity score (0-1) for linking
        """
        if OpenAI is None:
            raise ImportError("openai package not installed. Run: pip install openai")

        import os
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")

        self.client = OpenAI(api_key=self.api_key)
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold

        # Cache for embeddings
        self._embedding_cache: Dict[str, List[float]] = {}

    def link_code_to_docs(
        self,
        code_units: List[Any],
        doc_units: List[Any],
        top_k: int = 3,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Link code units to relevant documentation.

        Args:
            code_units: List of CodeUnit objects
            doc_units: List of DocumentUnit objects
            top_k: Number of top matches to return per code unit

        Returns:
            Dictionary mapping code_unit_id -> list of doc matches
            Each match contains:
                - doc_id: str
                - doc_title: str
                - doc_type: str
                - similarity_score: float
                - relevance_reason: str
        """
        links = {}

        # Get embeddings for all documents
        print(f"Generating embeddings for {len(doc_units)} documentation units...")
        doc_embeddings = self._get_embeddings_batch(
            [self._doc_to_text(doc) for doc in doc_units]
        )

        # Get embeddings for code units
        print(f"Generating embeddings for {len(code_units)} code units...")
        code_embeddings = self._get_embeddings_batch(
            [self._code_to_text(code) for code in code_units]
        )

        # Calculate similarities
        print("Calculating semantic similarities...")
        for i, code_unit in enumerate(code_units):
            code_emb = code_embeddings[i]

            # Calculate similarity with all docs
            similarities = []
            for j, doc_unit in enumerate(doc_units):
                doc_emb = doc_embeddings[j]
                similarity = self._cosine_similarity(code_emb, doc_emb)

                if similarity >= self.similarity_threshold:
                    similarities.append({
                        'doc_id': doc_unit.id,
                        'doc_title': doc_unit.title,
                        'doc_type': doc_unit.type,
                        'doc_content': doc_unit.content,
                        'similarity_score': float(similarity),
                    })

            # Sort by similarity and take top_k
            similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
            top_matches = similarities[:top_k]

            # Add relevance reasons
            for match in top_matches:
                match['relevance_reason'] = self._explain_relevance(
                    code_unit,
                    match,
                )

            if top_matches:
                links[code_unit.id] = top_matches

        print(f"Created {len(links)} code-to-doc links")
        return links

    def _doc_to_text(self, doc_unit: Any) -> str:
        """
        Convert DocumentUnit to text for embedding.

        Args:
            doc_unit: DocumentUnit object

        Returns:
            Text representation
        """
        parts = []

        # Add type and title
        parts.append(f"{doc_unit.type}: {doc_unit.title}")

        # Add content
        if doc_unit.content:
            parts.append(doc_unit.content[:500])  # Limit length

        # Add procedure info if available
        if doc_unit.is_procedure:
            parts.append(f"This is step {doc_unit.step_number} of a procedure")

        return "\n".join(parts)

    def _code_to_text(self, code_unit: Any) -> str:
        """
        Convert CodeUnit to text for embedding.

        Args:
            code_unit: CodeUnit object

        Returns:
            Text representation
        """
        parts = []

        # Add type and name
        parts.append(f"{code_unit.type}: {code_unit.name}")

        # Add signature if available
        if code_unit.signature:
            parts.append(f"Signature: {code_unit.signature}")

        # Add docstring if available
        if code_unit.docstring:
            parts.append(f"Documentation: {code_unit.docstring[:300]}")

        # Add code snippet (first few lines)
        if code_unit.code:
            code_lines = code_unit.code.split('\n')[:10]
            parts.append("Code:\n" + "\n".join(code_lines))

        return "\n".join(parts)

    def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        # Check cache
        cache_key = hash(text)
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        # Get embedding from API
        response = self.client.embeddings.create(
            input=text,
            model=self.embedding_model,
        )

        embedding = response.data[0].embedding

        # Cache it
        self._embedding_cache[cache_key] = embedding

        return embedding

    def _get_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 100,
    ) -> List[List[float]]:
        """
        Get embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for API calls

        Returns:
            List of embedding vectors
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # Check cache first
            batch_embeddings = []
            uncached_indices = []
            uncached_texts = []

            for j, text in enumerate(batch):
                cache_key = hash(text)
                if cache_key in self._embedding_cache:
                    batch_embeddings.append(self._embedding_cache[cache_key])
                else:
                    batch_embeddings.append(None)
                    uncached_indices.append(j)
                    uncached_texts.append(text)

            # Get uncached embeddings
            if uncached_texts:
                response = self.client.embeddings.create(
                    input=uncached_texts,
                    model=self.embedding_model,
                )

                # Fill in uncached embeddings
                for idx, emb_data in zip(uncached_indices, response.data):
                    embedding = emb_data.embedding
                    batch_embeddings[idx] = embedding

                    # Cache it
                    cache_key = hash(uncached_texts[uncached_indices.index(idx)])
                    self._embedding_cache[cache_key] = embedding

            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (0-1)
        """
        v1 = np.array(vec1)
        v2 = np.array(vec2)

        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def _explain_relevance(
        self,
        code_unit: Any,
        doc_match: Dict[str, Any],
    ) -> str:
        """
        Generate explanation for why doc is relevant to code.

        Args:
            code_unit: CodeUnit object
            doc_match: Documentation match dictionary

        Returns:
            Human-readable explanation
        """
        reasons = []

        # Check for name overlap
        code_name_lower = code_unit.name.lower()
        doc_title_lower = doc_match['doc_title'].lower()

        if code_name_lower in doc_title_lower or doc_title_lower in code_name_lower:
            reasons.append("Name similarity")

        # Check similarity score
        score = doc_match['similarity_score']
        if score > 0.9:
            reasons.append("Very high semantic similarity")
        elif score > 0.8:
            reasons.append("High semantic similarity")
        else:
            reasons.append("Moderate semantic similarity")

        # Check doc type
        if doc_match['doc_type'] == "step":
            reasons.append("Procedure step")
        elif doc_match['doc_type'] == "code_block":
            reasons.append("Contains code example")

        return ", ".join(reasons) if reasons else "Semantic match"

    def create_link_graph(
        self,
        links: Dict[str, List[Dict[str, Any]]],
        min_score: float = 0.8,
    ) -> List[Dict[str, Any]]:
        """
        Create graph edges for Neo4j DOCUMENTS relationships.

        Args:
            links: Links from link_code_to_docs()
            min_score: Minimum similarity score for creating edge

        Returns:
            List of edge dictionaries with:
                - from_id: Code unit ID
                - to_id: Document unit ID
                - relationship_type: "DOCUMENTS"
                - similarity_score: float
                - relevance: str
        """
        edges = []

        for code_id, doc_matches in links.items():
            for match in doc_matches:
                if match['similarity_score'] >= min_score:
                    edge = {
                        'from_id': code_id,
                        'to_id': match['doc_id'],
                        'relationship_type': 'DOCUMENTS',
                        'similarity_score': match['similarity_score'],
                        'relevance': match.get('relevance_reason', ''),
                    }
                    edges.append(edge)

        return edges

    def get_statistics(
        self,
        links: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Get statistics about code-to-doc linking.

        Args:
            links: Links from link_code_to_docs()

        Returns:
            Statistics dictionary
        """
        total_code_units = len(links)
        total_links = sum(len(matches) for matches in links.values())

        # Count by doc type
        doc_type_counts = defaultdict(int)
        for matches in links.values():
            for match in matches:
                doc_type_counts[match['doc_type']] += 1

        # Similarity score distribution
        all_scores = [
            match['similarity_score']
            for matches in links.values()
            for match in matches
        ]

        avg_score = np.mean(all_scores) if all_scores else 0.0
        max_score = max(all_scores) if all_scores else 0.0
        min_score = min(all_scores) if all_scores else 0.0

        return {
            'total_code_units_linked': total_code_units,
            'total_links_created': total_links,
            'avg_links_per_code_unit': total_links / total_code_units if total_code_units > 0 else 0,
            'doc_type_distribution': dict(doc_type_counts),
            'similarity_scores': {
                'avg': float(avg_score),
                'max': float(max_score),
                'min': float(min_score),
            }
        }
