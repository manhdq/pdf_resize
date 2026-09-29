"""Resolve paths that work both when running from source and when frozen
into a single-file PyInstaller executable.

PyInstaller onefile builds extract bundled data files to a temporary
directory at runtime (exposed as ``sys._MEIPASS``); plain ``Path(__file__)``
math does not point there, so anything shipped as a data file (assets,
icons, ...) must be located through this helper instead.
"""

from __future__ import annotations

import sys
from pathlib import Path


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
ASSETS_DIR = BASE_DIR / "assets"
