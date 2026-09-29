"""Entry point for the PDF page-size compressor desktop app."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .ui.main_window import MainWindow

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PDF Page Compressor")
    app.setOrganizationName("PDFCompressor")

    icon_path = ASSETS_DIR / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
