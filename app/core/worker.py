"""Background QThread that scans a folder and compresses every PDF in it."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Set

from PySide6.QtCore import QThread, Signal

from .compressor import FileResult, compress_pdf_file
from .scanner import find_pdf_files


class FolderScanWorker(QThread):
    """Lightweight background scan used to preview a folder's PDFs before
    the user presses Start — just lists files, no compression."""

    scan_done = Signal(list)  # list of str paths found
    scan_failed = Signal(str)

    def __init__(self, source_dir: Path, parent=None):
        super().__init__(parent)
        self.source_dir = Path(source_dir)

    def run(self):
        try:
            files = find_pdf_files(self.source_dir)
        except Exception as exc:  # noqa: BLE001
            self.scan_failed.emit(f"Không quét được thư mục: {exc}")
            return
        self.scan_done.emit([str(p) for p in files])


class CompressionWorker(QThread):
    scan_finished = Signal(list)  # list of str paths found, in processing order
    file_started = Signal(str, int, int)  # path, index (1-based), total
    file_progress = Signal(str, int, int)  # path, current page, total pages
    file_finished = Signal(object)  # FileResult
    all_finished = Signal(dict)  # summary
    fatal_error = Signal(str)

    def __init__(
        self,
        source_dir: Path,
        dest_dir: Optional[Path],
        max_kb_per_page: float,
        overwrite_in_place: bool,
        selected_paths: Optional[Set[str]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.source_dir = Path(source_dir)
        self.dest_dir = Path(dest_dir) if dest_dir else None
        self.max_kb_per_page = max_kb_per_page
        self.overwrite_in_place = overwrite_in_place
        self.selected_paths = selected_paths
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _is_cancelled(self) -> bool:
        return self._cancel

    def run(self):
        try:
            files = find_pdf_files(self.source_dir)
        except Exception as exc:  # noqa: BLE001
            self.fatal_error.emit(f"Không quét được thư mục: {exc}")
            return

        total = len(files)
        self.scan_finished.emit([str(p) for p in files])

        succeeded = 0
        limited = 0
        skipped = 0
        errored = 0
        cancelled = 0
        original_total = 0
        compressed_total = 0

        for idx, src_path in enumerate(files, start=1):
            if self._cancel:
                break

            self.file_started.emit(str(src_path), idx, total)

            if self.selected_paths is not None and str(src_path) not in self.selected_paths:
                result = FileResult(
                    input_path=src_path,
                    output_path=None,
                    original_bytes=src_path.stat().st_size,
                    status="skipped",
                    message="Bỏ qua (không được chọn để xử lý)",
                )
                original_total += result.original_bytes
                compressed_total += result.original_bytes
                skipped += 1
                self.file_finished.emit(result)
                continue

            if self.overwrite_in_place or self.dest_dir is None:
                out_path = src_path
            else:
                rel = src_path.relative_to(self.source_dir)
                out_path = self.dest_dir / rel

            def _progress(cur, tot, _p=str(src_path)):
                self.file_progress.emit(_p, cur, tot)

            result: FileResult = compress_pdf_file(
                src_path,
                out_path,
                self.max_kb_per_page,
                page_progress_cb=_progress,
                cancel_check=self._is_cancelled,
            )

            original_total += result.original_bytes
            compressed_total += result.compressed_bytes or result.original_bytes

            if result.status == "ok":
                succeeded += 1
            elif result.status == "limit":
                limited += 1
            elif result.status == "skipped":
                skipped += 1
            elif result.status == "cancelled":
                cancelled += 1
            else:
                errored += 1

            self.file_finished.emit(result)

        summary = {
            "total": total,
            "succeeded": succeeded,
            "limited": limited,
            "skipped": skipped,
            "errored": errored,
            "cancelled": cancelled,
            "original_total": original_total,
            "compressed_total": compressed_total,
            "was_cancelled": self._cancel,
        }
        self.all_finished.emit(summary)
