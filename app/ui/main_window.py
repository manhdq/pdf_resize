"""Main window: modern PySide6 UI for the PDF page-size compressor."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.compressor import FileResult
from ..core.worker import CompressionWorker, FolderScanWorker
from ..paths import ASSETS_DIR
from .styles import COLORS, STYLESHEET
from .watermark import GradientBar

STATUS_COLORS = {
    "ok": COLORS["success"],
    "limit": COLORS["warning"],
    "error": COLORS["danger"],
    "skipped": COLORS["text_muted"],
    "cancelled": COLORS["text_muted"],
    "pending": COLORS["text_muted"],
    "processing": COLORS["primary"],
}

STATUS_LABELS = {
    "pending": "Đang chờ xử lý...",
    "processing": "Đang xử lý...",
}

COLUMNS = [
    "Thư mục / Tên file",
    "Gốc (MB)",
    "Sau nén (MB)",
    "Giảm (MB)",
    "Tỷ lệ giảm",
    "DPI",
    "Trang lớn nhất (KB)",
    "Trạng thái",
]


def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setProperty("class", "card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 16)
    layout.setSpacing(8)
    if title:
        lbl = QLabel(title)
        lbl.setProperty("class", "cardTitle")
        layout.addWidget(lbl)
    return frame, layout


def _apply_shadow(widget: QWidget):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(18)
    effect.setOffset(0, 4)
    effect.setColor(QColor(30, 36, 51, 26))
    widget.setGraphicsEffect(effect)


def _mb(num_bytes: int) -> str:
    return f"{num_bytes / (1024 * 1024):.2f}"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Giảm dung lượng trang PDF")
        self.resize(1180, 760)
        self.setMinimumSize(980, 620)

        self.worker: Optional[CompressionWorker] = None
        self.preview_worker: Optional[FolderScanWorker] = None
        self._scan_token = 0
        self._source_dir: Optional[Path] = None
        self.folder_items: Dict[str, QTreeWidgetItem] = {}
        self.folder_stats: Dict[str, dict] = {}
        self.file_items: Dict[str, QTreeWidgetItem] = {}
        self.processed_count = 0

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 18, 20, 18)
        body_layout.setSpacing(14)
        root.addWidget(body)

        body_layout.addLayout(self._build_settings_row())
        body_layout.addLayout(self._build_action_bar())
        body_layout.addWidget(self._build_results_section(), stretch=1)
        body_layout.addWidget(self._build_footer())

        self.setStyleSheet(STYLESHEET)
        self._set_running(False)

    # ------------------------------------------------------------------ UI

    def _build_header(self) -> QFrame:
        header = GradientBar(motifs=["star", "party"])
        header.setObjectName("headerBar")
        header.setFixedHeight(84)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)

        logo_lbl = QLabel()
        logo_lbl.setObjectName("logoBadge")
        logo_lbl.setFixedSize(52, 52)
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_path = ASSETS_DIR / "logo.jpg"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path)).scaled(
                40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo_lbl.setPixmap(pixmap)
        layout.addWidget(logo_lbl)
        layout.addSpacing(12)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        title = QLabel("Giảm dung lượng trang PDF")
        title.setObjectName("appTitle")
        subtitle = QLabel("Nén hàng loạt PDF theo giới hạn dung lượng mỗi trang")
        subtitle.setObjectName("appSubtitle")
        text_box.addWidget(title)
        text_box.addWidget(subtitle)
        layout.addLayout(text_box)
        layout.addStretch(1)
        return header

    def _build_settings_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(14)

        # Card 1: source folder
        src_card, src_layout = _card("1. Chọn thư mục nguồn")
        _apply_shadow(src_card)
        src_row = QHBoxLayout()
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("Chưa chọn thư mục...")
        self.source_edit.setReadOnly(True)
        src_btn = QPushButton("📁 Chọn thư mục...")
        src_btn.clicked.connect(self.browse_source)
        self.source_btn = src_btn
        src_row.addWidget(self.source_edit, stretch=1)
        src_row.addWidget(src_btn)
        src_layout.addLayout(src_row)
        hint = QLabel("Hỗ trợ chọn thư mục lớn hoặc toàn bộ ổ đĩa để quét hàng loạt")
        hint.setProperty("class", "hint")
        hint.setWordWrap(True)
        src_layout.addWidget(hint)
        src_layout.addStretch(1)

        # Card 2: params
        opt_card, opt_layout = _card("2. Tùy chỉnh thông số nén")
        _apply_shadow(opt_card)

        limit_row = QHBoxLayout()
        limit_lbl = QLabel("Giới hạn dung lượng tối đa mỗi trang (KB):")
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(20, 20000)
        self.limit_spin.setSingleStep(10)
        self.limit_spin.setValue(482)
        self.limit_spin.setFixedWidth(100)
        limit_row.addWidget(limit_lbl)
        limit_row.addStretch(1)
        limit_row.addWidget(self.limit_spin)
        opt_layout.addLayout(limit_row)

        self.overwrite_check = QCheckBox("Ghi đè trực tiếp lên file gốc (bỏ tích để chọn thư mục lưu riêng)")
        self.overwrite_check.stateChanged.connect(self._on_overwrite_toggled)
        opt_layout.addWidget(self.overwrite_check)

        dest_row = QHBoxLayout()
        dest_lbl = QLabel("Thư mục đích lưu file:")
        self.dest_edit = QLineEdit()
        self.dest_edit.setPlaceholderText("Chưa chọn thư mục đích...")
        self.dest_edit.setReadOnly(True)
        dest_btn = QPushButton("Chọn...")
        dest_btn.clicked.connect(self.browse_dest)
        self.dest_btn = dest_btn
        dest_row.addWidget(dest_lbl)
        dest_row.addWidget(self.dest_edit, stretch=1)
        dest_row.addWidget(dest_btn)
        opt_layout.addLayout(dest_row)
        opt_layout.addStretch(1)

        row.addWidget(src_card, stretch=1)
        row.addWidget(opt_card, stretch=1)
        return row

    def _build_action_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        self.start_btn = QPushButton("▶  Bắt đầu xử lý")
        self.start_btn.setObjectName("primaryButton")
        self.start_btn.clicked.connect(self.start_processing)

        self.stop_btn = QPushButton("■  Dừng")
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.clicked.connect(self.stop_processing)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Sẵn sàng")

        row.addWidget(self.start_btn)
        row.addWidget(self.stop_btn)
        row.addWidget(self.progress_bar, stretch=1)

        self.status_label = QLabel("Chọn thư mục nguồn để bắt đầu.")
        self.status_label.setObjectName("statusText")

        wrapper = QVBoxLayout()
        wrapper.setSpacing(6)
        wrapper.addLayout(row)
        wrapper.addWidget(self.status_label)
        return wrapper

    def _build_results_section(self) -> QFrame:
        card, layout = _card("3. Kết quả xử lý chi tiết theo danh mục")
        _apply_shadow(card)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(len(COLUMNS))
        self.tree.setHeaderLabels(COLUMNS)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setRootIsDecorated(True)
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(COLUMNS)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        layout.addWidget(self.tree)
        return card

    def _build_footer(self) -> QFrame:
        footer = GradientBar(motifs=["star", "party"], corner_radius=10, align="center")
        footer.setObjectName("footerBar")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(16, 10, 16, 10)
        self.footer_label = QLabel("Tổng: 0 file | Thành công: 0 | Giới hạn: 0 | Lỗi: 0 | Bỏ qua: 0")
        self.footer_label.setObjectName("footerText")
        layout.addWidget(self.footer_label)
        layout.addStretch(1)
        credit_label = QLabel("Design by Huy Đỗ")
        credit_label.setObjectName("creditText")
        layout.addWidget(credit_label)
        return footer

    # ------------------------------------------------------------- actions

    def browse_source(self):
        directory = QFileDialog.getExistingDirectory(self, "Chọn thư mục nguồn", self.source_edit.text() or str(Path.home()))
        if directory:
            self.source_edit.setText(directory)
            self._preview_scan(directory)

    def _preview_scan(self, directory: str):
        self._reset_results()
        self._source_dir = Path(directory)
        self._scan_token += 1
        token = self._scan_token

        self.status_label.setText("Đang quét thư mục nguồn...")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("Đang quét...")

        if self.preview_worker is not None and self.preview_worker.isRunning():
            # A previous scan (e.g. the user picked another folder quickly)
            # is still running. Detach it from the UI and let it clean
            # itself up once done instead of blocking or killing it.
            self.preview_worker.scan_done.disconnect()
            self.preview_worker.scan_failed.disconnect()
            self.preview_worker.finished.connect(self.preview_worker.deleteLater)

        self.preview_worker = FolderScanWorker(self._source_dir, parent=self)
        self.preview_worker.scan_done.connect(lambda paths: self._on_preview_scan_done(token, paths))
        self.preview_worker.scan_failed.connect(lambda msg: self._on_preview_scan_failed(token, msg))
        self.preview_worker.start()

    def _on_preview_scan_done(self, token: int, paths):
        if token != self._scan_token:
            return  # a newer folder selection superseded this scan
        total = len(paths)
        if total == 0:
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Không có file")
            self.status_label.setText("Không tìm thấy file PDF nào trong thư mục đã chọn.")
            return

        self._populate_skeleton(paths)
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"0/{total}")
        self.status_label.setText(f"Tìm thấy {total} file PDF. Nhấn 'Bắt đầu xử lý' để nén.")

    def _on_preview_scan_failed(self, token: int, message: str):
        if token != self._scan_token:
            return
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Lỗi quét")
        self.status_label.setText(message)

    def browse_dest(self):
        directory = QFileDialog.getExistingDirectory(self, "Chọn thư mục đích", self.dest_edit.text() or str(Path.home()))
        if directory:
            self.dest_edit.setText(directory)

    def _show_detailed_warning(self, title: str, summary: str, detail: str, icon=QMessageBox.Warning):
        box = QMessageBox(self)
        box.setIcon(icon)
        box.setWindowTitle(title)
        box.setText(summary)
        box.setInformativeText(detail)
        box.exec()

    def _on_overwrite_toggled(self, _state):
        overwrite = self.overwrite_check.isChecked()
        self.dest_edit.setEnabled(not overwrite)
        self.dest_btn.setEnabled(not overwrite)

    def _set_running(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.source_edit.setEnabled(not running)
        self.source_btn.setEnabled(not running)
        self.dest_edit.setEnabled(not running and not self.overwrite_check.isChecked())
        self.dest_btn.setEnabled(not running and not self.overwrite_check.isChecked())
        self.overwrite_check.setEnabled(not running)
        self.limit_spin.setEnabled(not running)

    def start_processing(self):
        source_text = self.source_edit.text().strip()
        if not source_text:
            self._show_detailed_warning(
                "Thiếu thư mục nguồn",
                "Chưa chọn thư mục nguồn chứa file PDF.",
                "Bấm nút 'Chọn thư mục...' ở mục 1 để chọn thư mục (hoặc cả ổ đĩa) "
                "chứa các file PDF cần nén.",
            )
            return
        source_dir = Path(source_text)
        if not source_dir.is_dir():
            self._show_detailed_warning(
                "Thư mục nguồn không hợp lệ",
                f"Không tìm thấy thư mục:\n{source_dir}",
                "Thư mục có thể đã bị xoá, đổi tên, hoặc nằm trên ổ đĩa/máy khác hiện "
                "không còn kết nối. Vui lòng bấm 'Chọn thư mục...' để chọn lại.",
            )
            return

        overwrite = self.overwrite_check.isChecked()
        dest_dir: Optional[Path] = None
        if overwrite:
            reply = QMessageBox.question(
                self,
                "Xác nhận ghi đè",
                "Chế độ này sẽ THAY THẾ trực tiếp các file PDF gốc bằng bản đã nén "
                "(nội dung trang sẽ được chuyển thành ảnh nén, không thể hoàn tác). "
                "Bạn có chắc chắn muốn tiếp tục?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        else:
            dest_text = self.dest_edit.text().strip()
            if not dest_text:
                self._show_detailed_warning(
                    "Thiếu thư mục đích",
                    "Chưa chọn thư mục đích để lưu file PDF đã nén.",
                    "Vì ô 'Ghi đè trực tiếp lên file gốc' đang KHÔNG được tích, ứng dụng "
                    "cần một thư mục riêng để lưu kết quả. Cách khắc phục — chọn 1 trong 2:\n\n"
                    "• Bấm nút 'Chọn...' cạnh ô 'Thư mục đích lưu file' để chọn nơi lưu, hoặc\n"
                    "• Tích vào 'Ghi đè trực tiếp lên file gốc' để nén thẳng vào file gốc "
                    "(sẽ có xác nhận riêng vì không thể hoàn tác).",
                )
                return
            dest_dir = Path(dest_text)
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
            except Exception as exc:  # noqa: BLE001
                self._show_detailed_warning(
                    "Không tạo được thư mục đích",
                    f"Không tạo được thư mục đích:\n{dest_dir}",
                    f"Chi tiết lỗi: {exc}\n\nKiểm tra quyền ghi hoặc chọn một thư mục đích khác.",
                    icon=QMessageBox.Critical,
                )
                return

        max_kb = float(self.limit_spin.value())

        self._reset_results()
        self._set_running(True)
        self.status_label.setText("Đang quét thư mục nguồn...")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("Đang quét...")

        self.worker = CompressionWorker(source_dir, dest_dir, max_kb, overwrite)
        self._source_dir = source_dir
        self.worker.scan_finished.connect(self.on_scan_finished)
        self.worker.file_started.connect(self.on_file_started)
        self.worker.file_progress.connect(self.on_file_progress)
        self.worker.file_finished.connect(self.on_file_finished)
        self.worker.all_finished.connect(self.on_all_finished)
        self.worker.fatal_error.connect(self.on_fatal_error)
        self.worker.finished.connect(lambda: self._set_running(False))
        self.worker.start()

    def stop_processing(self):
        if self.worker is not None:
            self.worker.cancel()
            self.stop_btn.setEnabled(False)
            self.status_label.setText("Đang dừng, vui lòng chờ...")

    # ------------------------------------------------------------- results

    def _reset_results(self):
        self.tree.clear()
        self.folder_items.clear()
        self.folder_stats.clear()
        self.file_items.clear()
        self.processed_count = 0
        self.footer_label.setText("Tổng: 0 file | Thành công: 0 | Giới hạn: 0 | Lỗi: 0 | Bỏ qua: 0")

    def _folder_key(self, path_str: str) -> str:
        rel = Path(path_str).parent.relative_to(self._source_dir)
        return str(rel)

    def _folder_item(self, key: str) -> QTreeWidgetItem:
        if key in self.folder_items:
            return self.folder_items[key]
        label = "📁 (thư mục gốc)" if key in (".", "") else f"📁 {key}"
        item = QTreeWidgetItem([label, "", "", "", "", "", "", ""])
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        self.tree.addTopLevelItem(item)
        item.setExpanded(True)
        self.folder_items[key] = item
        self.folder_stats[key] = {"orig": 0, "comp": 0, "total": 0, "done": 0}
        return item

    def _populate_skeleton(self, paths):
        """Build the folder/file tree rows in a 'pending' state, without
        touching the progress bar or status text (callers decide those)."""
        for p in paths:
            key = self._folder_key(p)
            folder_item = self._folder_item(key)
            self.folder_stats[key]["total"] += 1
            name = Path(p).name
            child = QTreeWidgetItem(["   📄 " + name, "-", "-", "-", "-", "-", "-", STATUS_LABELS["pending"]])
            child.setForeground(7, QColor(STATUS_COLORS["pending"]))
            folder_item.addChild(child)
            self.file_items[p] = child

    def on_scan_finished(self, paths):
        # Emitted by the real CompressionWorker once processing has started.
        # If the preview scan already built the tree for this exact folder,
        # skip re-building it so in-progress rows aren't wiped.
        if not self.file_items:
            self._populate_skeleton(paths)

        total = len(paths)
        if total == 0:
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Không có file")
            self.status_label.setText("Không tìm thấy file PDF nào trong thư mục đã chọn.")
            return

        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"0/{total}")
        self.status_label.setText(f"Tìm thấy {total} file PDF. Đang xử lý...")

    def on_file_started(self, path, idx, total):
        item = self.file_items.get(path)
        if item:
            item.setText(7, STATUS_LABELS["processing"])
            item.setForeground(7, QColor(STATUS_COLORS["processing"]))
        self.status_label.setText(f"Đang xử lý ({idx}/{total}): {Path(path).name}")

    def on_file_progress(self, path, cur, tot):
        item = self.file_items.get(path)
        if item and tot > 1:
            item.setText(7, f"Đang xử lý trang {cur}/{tot}...")

    def on_file_finished(self, result: FileResult):
        path = str(result.input_path)
        item = self.file_items.get(path)
        if item:
            item.setText(1, _mb(result.original_bytes))
            item.setText(2, _mb(result.compressed_bytes or result.original_bytes))
            item.setText(3, _mb(result.saved_bytes))
            item.setText(4, f"{result.ratio:.1f}%")
            item.setText(5, result.dpi_summary)
            item.setText(6, f"{result.max_page_kb:.0f}" if result.pages else "-")
            item.setText(7, result.message or result.status)
            color = STATUS_COLORS.get(result.status, COLORS["text_muted"])
            item.setForeground(7, QColor(color))

        key = self._folder_key(path)
        stats = self.folder_stats.get(key)
        if stats is not None:
            contributed_comp = result.compressed_bytes or result.original_bytes
            stats["orig"] += result.original_bytes
            stats["comp"] += contributed_comp
            stats["done"] += 1
            folder_item = self.folder_items[key]
            folder_item.setText(1, _mb(stats["orig"]))
            folder_item.setText(2, _mb(stats["comp"]))
            saved = max(stats["orig"] - stats["comp"], 0)
            folder_item.setText(3, _mb(saved))
            ratio = (saved / stats["orig"] * 100.0) if stats["orig"] else 0.0
            folder_item.setText(4, f"{ratio:.1f}%")
            folder_item.setText(7, f"{stats['done']}/{stats['total']} file đã xử lý")

        self.processed_count += 1
        self.progress_bar.setValue(self.processed_count)
        self.progress_bar.setFormat(f"{self.processed_count}/{self.progress_bar.maximum()}")

    def on_all_finished(self, summary: dict):
        orig_mb = summary["original_total"] / (1024 * 1024)
        comp_mb = summary["compressed_total"] / (1024 * 1024)
        saved_mb = max(orig_mb - comp_mb, 0)
        ratio = (saved_mb / orig_mb * 100.0) if orig_mb else 0.0

        self.footer_label.setText(
            f"Tổng: {summary['total']} file | Thành công: {summary['succeeded']} | "
            f"Giới hạn: {summary['limited']} | Lỗi: {summary['errored']} | "
            f"Bỏ qua: {summary['skipped']}  ▸  "
            f"Dung lượng gốc: {orig_mb:.2f} MB → Còn lại: {comp_mb:.2f} MB "
            f"(Giảm {saved_mb:.2f} MB, {ratio:.1f}%)"
        )

        if summary["was_cancelled"]:
            self.status_label.setText("Đã dừng xử lý theo yêu cầu.")
        else:
            self.status_label.setText("Hoàn tất xử lý toàn bộ hệ thống file tài liệu đã chọn!")

        if summary["limited"] > 0:
            QMessageBox.information(
                self,
                "Đã đạt giới hạn nén",
                f"Có {summary['limited']} file không thể nén xuống mức dung lượng mong muốn dù đã "
                "dùng độ phân giải và chất lượng thấp nhất cho phép. Đây là giới hạn nén tối đa cho "
                "những trang đó — xem cột 'Trạng thái' để biết chi tiết từng file.",
            )
        if summary["errored"] > 0:
            QMessageBox.warning(
                self,
                "Có lỗi xảy ra",
                f"Có {summary['errored']} file gặp lỗi khi xử lý. Xem cột 'Trạng thái' để biết chi tiết.",
            )

    def on_fatal_error(self, message: str):
        QMessageBox.critical(self, "Lỗi", message)
        self._set_running(False)

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(3000)
        if self.preview_worker is not None and self.preview_worker.isRunning():
            self.preview_worker.wait(3000)
        event.accept()
