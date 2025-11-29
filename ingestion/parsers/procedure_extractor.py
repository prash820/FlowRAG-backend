"""
LLM-based procedure step extraction.

Uses OpenAI API to intelligently extract procedure steps from documentation.
"""

import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class ProcedureExtractor:
    """
    Extract procedure steps from documentation using LLM.

    This enhances basic pattern matching with semantic understanding.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize procedure extractor.

        Args:
            api_key: OpenAI API key (if None, uses OPENAI_API_KEY env var)
            model: OpenAI model to use (default: gpt-4o-mini for speed/cost)
        """
        if OpenAI is None:
            raise ImportError("openai package not installed. Run: pip install openai")

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def extract_procedures(
        self,
        text: str,
        context: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract procedure steps from text using LLM.

        Args:
            text: Documentation text to analyze
            context: Optional context (e.g., section title, file name)

        Returns:
            List of procedure dictionaries with:
                - step_number: int
                - description: str
                - is_prerequisite: bool
                - dependencies: List[int] (which steps must come before)
                - estimated_time: Optional[str]
                - difficulty: str (easy, medium, hard)
        """
        prompt = self._build_extraction_prompt(text, context)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing technical documentation and extracting structured procedure steps."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistency
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("procedures", [])

        except Exception as e:
            print(f"Warning: LLM extraction failed: {e}")
            return []

    def _build_extraction_prompt(
        self,
        text: str,
        context: Optional[str] = None,
    ) -> str:
        """Build prompt for LLM extraction."""
        context_str = f"\n\nContext: {context}" if context else ""

        return f"""Extract all procedure steps from the following documentation text.

A procedure step is:
- An action that needs to be performed
- Part of a sequence (installation, configuration, deployment, etc.)
- Has a clear objective

For each procedure step, provide:
1. step_number: Sequential number (1, 2, 3...)
2. description: Clear description of what to do
3. is_prerequisite: True if this must be done before other steps
4. dependencies: List of step numbers that must be completed first (empty if none)
5. estimated_time: Estimate like "5 minutes", "1 hour" (or null if unclear)
6. difficulty: "easy", "medium", or "hard"

Return ONLY a JSON object with this structure:
{{
  "procedures": [
    {{
      "step_number": 1,
      "description": "...",
      "is_prerequisite": false,
      "dependencies": [],
      "estimated_time": "5 minutes",
      "difficulty": "easy"
    }}
  ]
}}

Documentation text:{context_str}

{text}

JSON output:"""

    def enhance_document_units(
        self,
        document_units: List[Any],
        batch_size: int = 5,
    ) -> List[Any]:
        """
        Enhance document units with LLM-extracted procedure information.

        Args:
            document_units: List of DocumentUnit objects
            batch_size: Number of steps to process at once

        Returns:
            Enhanced document units
        """
        # Group by procedure sequences (consecutive numbered steps)
        sequences = self._group_sequences(document_units)

        for seq_docs in sequences:
            if not seq_docs:
                continue

            # Extract text from sequence
            text = "\n".join([
                f"{doc.step_number}. {doc.content}"
                for doc in seq_docs
                if doc.is_procedure
            ])

            # Get context from parent section
            context = None
            if seq_docs[0].parent_id:
                parent = next((d for d in document_units if d.id == seq_docs[0].parent_id), None)
                if parent:
                    context = parent.title

            # Extract procedures with LLM
            procedures = self.extract_procedures(text, context)

            # Enhance document units with LLM data
            for doc in seq_docs:
                if not doc.is_procedure:
                    continue

                # Find matching procedure
                proc = next(
                    (p for p in procedures if p["step_number"] == doc.step_number),
                    None
                )

                if proc:
                    # Add LLM metadata to document
                    if not hasattr(doc, 'metadata'):
                        doc.metadata = {}

                    doc.metadata.update({
                        'llm_enhanced': True,
                        'dependencies': proc.get('dependencies', []),
                        'estimated_time': proc.get('estimated_time'),
                        'difficulty': proc.get('difficulty'),
                        'is_prerequisite': proc.get('is_prerequisite', False),
                    })

        return document_units

    def _group_sequences(self, document_units: List[Any]) -> List[List[Any]]:
        """
        Group consecutive procedure steps into sequences.

        Args:
            document_units: List of DocumentUnit objects

        Returns:
            List of sequence groups
        """
        sequences = []
        current_sequence = []
        last_parent = None

        for doc in document_units:
            if doc.is_procedure:
                # Start new sequence if parent changed
                if last_parent is not None and doc.parent_id != last_parent:
                    if current_sequence:
                        sequences.append(current_sequence)
                    current_sequence = [doc]
                else:
                    current_sequence.append(doc)

                last_parent = doc.parent_id
            else:
                # Non-procedure breaks sequence
                if current_sequence:
                    sequences.append(current_sequence)
                    current_sequence = []
                last_parent = None

        # Add last sequence
        if current_sequence:
            sequences.append(current_sequence)

        return sequences

    def identify_workflows(
        self,
        document_units: List[Any],
    ) -> List[Dict[str, Any]]:
        """
        Identify complete workflows from procedure sequences.

        Args:
            document_units: List of DocumentUnit objects

        Returns:
            List of workflow dictionaries with:
                - name: Workflow name
                - steps: List of step IDs
                - total_time: Estimated total time
                - difficulty: Overall difficulty
        """
        sequences = self._group_sequences(document_units)
        workflows = []

        for seq_docs in sequences:
            if not seq_docs or len(seq_docs) < 2:
                continue

            # Get workflow context
            context = "Unknown Workflow"
            if seq_docs[0].parent_id:
                parent = next((d for d in document_units if d.id == seq_docs[0].parent_id), None)
                if parent:
                    context = parent.title

            workflow = {
                'name': context,
                'steps': [doc.id for doc in seq_docs],
                'step_count': len(seq_docs),
                'document_ids': [doc.id for doc in seq_docs],
            }

            # Calculate total time and difficulty if enhanced
            if hasattr(seq_docs[0], 'metadata') and 'llm_enhanced' in seq_docs[0].metadata:
                total_minutes = 0
                difficulties = []

                for doc in seq_docs:
                    if hasattr(doc, 'metadata'):
                        est_time = doc.metadata.get('estimated_time')
                        if est_time:
                            # Parse time estimate
                            minutes = self._parse_time_estimate(est_time)
                            total_minutes += minutes

                        difficulty = doc.metadata.get('difficulty')
                        if difficulty:
                            difficulties.append(difficulty)

                workflow['estimated_total_time'] = f"{total_minutes} minutes"

                # Overall difficulty is highest difficulty in sequence
                if difficulties:
                    difficulty_order = {'easy': 1, 'medium': 2, 'hard': 3}
                    max_diff = max(difficulties, key=lambda d: difficulty_order.get(d, 0))
                    workflow['overall_difficulty'] = max_diff

            workflows.append(workflow)

        return workflows

    def _parse_time_estimate(self, time_str: str) -> int:
        """
        Parse time estimate to minutes.

        Args:
            time_str: Time string like "5 minutes", "1 hour", "30 mins"

        Returns:
            Time in minutes
        """
        import re

        if not time_str:
            return 0

        # Extract numbers
        numbers = re.findall(r'\d+', time_str)
        if not numbers:
            return 0

        value = int(numbers[0])

        # Check unit
        time_lower = time_str.lower()

        if 'hour' in time_lower or 'hr' in time_lower:
            return value * 60
        elif 'day' in time_lower:
            return value * 60 * 8  # 8-hour workday
        else:
            # Assume minutes
            return value
