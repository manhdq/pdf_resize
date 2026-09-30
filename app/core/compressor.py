"""
Core PDF page-size compression engine.

Strategy: for every page, rasterize it and re-encode as JPEG, searching a
descending ladder of DPI values and, at each DPI, binary-searching the JPEG
quality that yields the largest file still within the requested per-page
size budget. This mirrors how the reference tool handles scanned documents:
it aggressively shrinks image-heavy pages while reporting, per page, whether
the requested budget could actually be met.

If even the lowest DPI/quality combination in the ladder still exceeds the
requested budget, that result is kept anyway (it is the smallest this engine
can produce) and the page is flagged as having hit the compression limit.
"""

from __future__ import annotations

import io
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

import fitz  # PyMuPDF
from PIL import Image

# Descending ladder of render resolutions (dots-per-inch) to try.
DPI_LADDER: List[int] = [300, 220, 170, 130, 100, 85, 72]

# JPEG quality bounds used during the binary search at each DPI step.
QUALITY_MIN = 25
QUALITY_MAX = 90


class Cancelled(Exception):
    """Raised internally to unwind quickly when the user hits Stop."""


@dataclass
class PageResult:
    index: int
    dpi: int
    quality: int
    size_bytes: int
    met_target: bool
    kept_original: bool = False


@dataclass
class FileResult:
    input_path: Path
    output_path: Optional[Path]
    original_bytes: int
    compressed_bytes: int = 0
    page_count: int = 0
    pages: List[PageResult] = field(default_factory=list)
    status: str = "pending"  # ok | limit | skipped | error
    message: str = ""

    @property
    def saved_bytes(self) -> int:
        return max(self.original_bytes - self.compressed_bytes, 0)

    @property
    def ratio(self) -> float:
        if self.original_bytes <= 0:
            return 0.0
        return self.saved_bytes / self.original_bytes * 100.0

    @property
    def max_page_kb(self) -> float:
        if not self.pages:
            return 0.0
        return max(p.size_bytes for p in self.pages) / 1024.0

    @property
    def dpi_summary(self) -> str:
        if not self.pages:
            return "-"
        dpis = sorted({p.dpi for p in self.pages if not p.kept_original})
        if not dpis:
            return "Gốc"
        if len(dpis) == 1:
            return str(dpis[0])
        return f"{dpis[-1]}-{dpis[0]}"

    @property
    def pages_over_limit(self) -> int:
        return sum(1 for p in self.pages if not p.met_target)


def _render_page_rgb(page: "fitz.Page", dpi: int) -> Image.Image:
    matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def _encode_jpeg(img: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def _best_quality_for_dpi(img: Image.Image, target_bytes: int):
    """Binary-search the max JPEG quality that still fits target_bytes.

    Returns (data, quality, met_target).
    """
    floor_data = _encode_jpeg(img, QUALITY_MIN)
    if len(floor_data) > target_bytes:
        return floor_data, QUALITY_MIN, False

    ceil_data = _encode_jpeg(img, QUALITY_MAX)
    if len(ceil_data) <= target_bytes:
        return ceil_data, QUALITY_MAX, True

    lo, hi = QUALITY_MIN, QUALITY_MAX
    best_data, best_q = floor_data, QUALITY_MIN
    while lo <= hi:
        mid = (lo + hi) // 2
        data = _encode_jpeg(img, mid)
        if len(data) <= target_bytes:
            best_data, best_q = data, mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best_data, best_q, True


def _standalone_page_bytes(src: "fitz.Document", index: int) -> int:
    """Approximate how large this one page is on its own, so pages that are
    already under the target budget (e.g. mostly text, or a small embedded
    image) can be left untouched instead of being rasterized unnecessarily."""
    tmp_doc = fitz.open()
    tmp_doc.insert_pdf(src, from_page=index, to_page=index)
    size = len(tmp_doc.tobytes(garbage=4, deflate=True))
    tmp_doc.close()
    return size


def _compress_page(page: "fitz.Page", target_bytes: int, dpi_ladder: List[int]):
    fallback = None
    for dpi in dpi_ladder:
        img = _render_page_rgb(page, dpi)
        data, quality, met = _best_quality_for_dpi(img, target_bytes)
        if met:
            return data, dpi, quality, True
        fallback = (data, dpi, quality)
    data, dpi, quality = fallback
    return data, dpi, quality, False


PageProgressCb = Optional[Callable[[int, int], None]]
CancelCheck = Optional[Callable[[], bool]]


def compress_pdf_file(
    input_path: Path,
    output_path: Path,
    max_kb_per_page: float,
    page_progress_cb: PageProgressCb = None,
    cancel_check: CancelCheck = None,
    dpi_ladder: List[int] = None,
) -> FileResult:
    """Compress a single PDF so every page fits within max_kb_per_page.

    Writes the result to output_path (via a temp file + atomic replace so a
    partially-written file never clobbers valid input, including when
    output_path == input_path for "overwrite in place" mode).
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    dpi_ladder = dpi_ladder or DPI_LADDER
    target_bytes = int(max_kb_per_page * 1024)

    original_bytes = input_path.stat().st_size
    result = FileResult(input_path=input_path, output_path=output_path, original_bytes=original_bytes)

    try:
        src = fitz.open(str(input_path))
    except Exception as exc:  # noqa: BLE001 - report any open failure back to UI
        result.status = "error"
        result.message = f"Không mở được file: {exc}"
        return result

    if src.is_encrypted:
        if not src.authenticate(""):
            src.close()
            result.status = "skipped"
            result.message = "PDF có mật khẩu bảo vệ"
            return result

    page_count = src.page_count
    result.page_count = page_count

    if page_count == 0:
        src.close()
        result.status = "skipped"
        result.message = "PDF không có trang nào"
        return result

    out_doc = fitz.open()
    try:
        for i in range(page_count):
            if cancel_check and cancel_check():
                raise Cancelled()

            orig_page_bytes = _standalone_page_bytes(src, i)
            if orig_page_bytes <= target_bytes:
                # Already within budget: keep the page as-is instead of
                # rasterizing/re-encoding it (avoids needless quality loss).
                out_doc.insert_pdf(src, from_page=i, to_page=i)
                result.pages.append(
                    PageResult(index=i, dpi=0, quality=0, size_bytes=orig_page_bytes, met_target=True, kept_original=True)
                )
            else:
                page = src.load_page(i)
                rect = page.rect
                data, dpi, quality, met = _compress_page(page, target_bytes, dpi_ladder)
                result.pages.append(PageResult(index=i, dpi=dpi, quality=quality, size_bytes=len(data), met_target=met))

                new_page = out_doc.new_page(width=rect.width, height=rect.height)
                new_page.insert_image(rect, stream=data)

            if page_progress_cb:
                page_progress_cb(i + 1, page_count)

        src.close()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".tmp_pdfcomp_", suffix=".pdf", dir=str(output_path.parent))
        os.close(fd)
        try:
            out_doc.save(tmp_name, garbage=4, deflate=True, clean=True)
            out_doc.close()
            os.replace(tmp_name, output_path)
        except Exception:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
            raise

        result.compressed_bytes = output_path.stat().st_size
        result.status = "ok" if result.pages_over_limit == 0 else "limit"
        if result.status == "limit":
            result.message = (
                f"Đạt giới hạn nén tối đa ở {result.pages_over_limit}/{page_count} trang "
                f"(trang lớn nhất còn {result.max_page_kb:.0f} KB > {max_kb_per_page:.0f} KB)"
            )
        else:
            result.message = f"Đã nén chuẩn (mọi trang ≤ {max_kb_per_page:.0f} KB)"
        return result

    except Cancelled:
        out_doc.close()
        src.close() if not src.is_closed else None
        result.status = "cancelled"
        result.message = "Đã dừng"
        return result
    except Exception as exc:  # noqa: BLE001
        out_doc.close()
        if not src.is_closed:
            src.close()
        result.status = "error"
        result.message = f"Lỗi khi xử lý: {exc}"
        return result
