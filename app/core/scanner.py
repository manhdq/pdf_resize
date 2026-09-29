"""Folder scanning helpers for locating PDF files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List


def find_pdf_files(root: Path) -> List[Path]:
    """Recursively find every .pdf file under root (case-insensitive), sorted."""
    root = Path(root)
    found: List[Path] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.lower().endswith(".pdf"):
                found.append(Path(dirpath) / name)
    found.sort(key=lambda p: str(p).lower())
    return found
