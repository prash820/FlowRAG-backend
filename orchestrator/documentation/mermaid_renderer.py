"""
Mermaid Diagram Renderer.

Converts Mermaid diagram code to PNG images using mermaid-cli (mmdc).
"""

import logging
import subprocess
import tempfile
import os
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class MermaidRenderer:
    """Renders Mermaid diagrams to PNG images."""

    def __init__(self):
        """Initialize renderer and check for mmdc availability."""
        self.mmdc_path = self._find_mmdc()
        self.available = self.mmdc_path is not None

        if self.available:
            logger.info(f"Mermaid CLI found at: {self.mmdc_path}")
        else:
            logger.warning("Mermaid CLI (mmdc) not found. Diagrams will use placeholders.")

    def _find_mmdc(self) -> Optional[str]:
        """Find mmdc executable."""
        # Try common locations
        paths_to_try = [
            "/usr/local/bin/mmdc",
            "/usr/bin/mmdc",
            "/opt/homebrew/bin/mmdc",
            os.path.expanduser("~/.npm-global/bin/mmdc"),
            os.path.expanduser("~/node_modules/.bin/mmdc"),
        ]

        # Check which command
        try:
            result = subprocess.run(
                ["which", "mmdc"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        # Try known paths
        for path in paths_to_try:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path

        return None

    def render_to_png(self, mermaid_code: str, width: int = 800, height: int = 600, scale: int = 3) -> Optional[bytes]:
        """
        Render Mermaid diagram to PNG.

        Args:
            mermaid_code: Mermaid diagram syntax
            width: Output width in pixels
            height: Output height in pixels
            scale: Scale factor for higher resolution (default 3 for crisp diagrams)

        Returns:
            PNG image bytes or None if rendering fails
        """
        if not self.available:
            logger.warning("Mermaid CLI not available, cannot render diagram")
            return None

        try:
            # Create temp files
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as mmd_file:
                mmd_file.write(mermaid_code)
                mmd_path = mmd_file.name

            png_path = mmd_path.replace('.mmd', '.png')

            try:
                # Run mmdc to generate PNG with higher resolution
                result = subprocess.run(
                    [
                        self.mmdc_path,
                        "-i", mmd_path,
                        "-o", png_path,
                        "-w", str(width),
                        "-H", str(height),
                        "-s", str(scale),  # Scale factor for higher resolution
                        "-b", "white",  # White background
                        "--quiet"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30  # 30 second timeout
                )

                if result.returncode != 0:
                    logger.error(f"mmdc failed: {result.stderr}")
                    return None

                # Read PNG file
                if os.path.exists(png_path):
                    with open(png_path, 'rb') as f:
                        png_bytes = f.read()
                    logger.info(f"Rendered Mermaid diagram: {len(png_bytes)} bytes")
                    return png_bytes
                else:
                    logger.error("PNG file not created by mmdc")
                    return None

            finally:
                # Clean up temp files
                for path in [mmd_path, png_path]:
                    if os.path.exists(path):
                        try:
                            os.unlink(path)
                        except Exception:
                            pass

        except subprocess.TimeoutExpired:
            logger.error("Mermaid rendering timed out")
            return None
        except Exception as e:
            logger.error(f"Mermaid rendering failed: {e}", exc_info=True)
            return None

    def render_to_file(self, mermaid_code: str, output_path: str,
                       width: int = 800, height: int = 600) -> bool:
        """
        Render Mermaid diagram to a PNG file.

        Args:
            mermaid_code: Mermaid diagram syntax
            output_path: Path for output PNG file
            width: Output width in pixels
            height: Output height in pixels

        Returns:
            True if successful, False otherwise
        """
        png_bytes = self.render_to_png(mermaid_code, width, height)
        if png_bytes:
            with open(output_path, 'wb') as f:
                f.write(png_bytes)
            return True
        return False

    def get_diagram_dimensions(self, mermaid_code: str) -> Tuple[int, int]:
        """
        Estimate appropriate dimensions for a diagram.

        Args:
            mermaid_code: Mermaid diagram syntax

        Returns:
            Tuple of (width, height) in pixels
        """
        lines = mermaid_code.strip().split('\n')
        first_line = lines[0].strip().lower()

        # Count elements for sizing
        num_lines = len(lines)
        max_line_length = max(len(line) for line in lines) if lines else 0

        # Base dimensions
        if 'sequencediagram' in first_line or 'sequence' in first_line:
            # Sequence diagrams are typically taller
            width = min(1000, max(600, max_line_length * 8))
            height = min(1200, max(400, num_lines * 40))
        elif 'graph lr' in first_line or 'flowchart lr' in first_line:
            # Horizontal flowcharts are wider
            width = min(1200, max(800, num_lines * 120))
            height = min(600, max(300, num_lines * 30))
        elif 'classDiagram' in first_line or 'class' in first_line:
            # Class diagrams need more space
            width = min(1000, max(600, max_line_length * 6))
            height = min(800, max(400, num_lines * 25))
        else:
            # Default for flowcharts (TB/TD)
            width = min(900, max(500, max_line_length * 7))
            height = min(800, max(400, num_lines * 35))

        return (width, height)


# Singleton instance
_mermaid_renderer: Optional[MermaidRenderer] = None


def get_mermaid_renderer() -> MermaidRenderer:
    """Get or create Mermaid renderer instance."""
    global _mermaid_renderer

    if _mermaid_renderer is None:
        _mermaid_renderer = MermaidRenderer()

    return _mermaid_renderer
