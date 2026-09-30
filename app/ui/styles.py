"""Modern flat theme (QSS) for the PDF page-size compressor."""

from ..paths import ASSETS_DIR

_CHECK_ON = (ASSETS_DIR / "check_on.png").as_posix()
_CHECK_PARTIAL = (ASSETS_DIR / "check_partial.png").as_posix()

COLORS = {
    "bg": "#F3F5FB",
    "card": "#FFFFFF",
    "border": "#E4E8F1",
    "text": "#1E2433",
    "text_muted": "#6B7280",
    "primary": "#4457F0",
    "primary_hover": "#3646D6",
    "primary_pressed": "#2C39B8",
    "danger": "#EF4444",
    "danger_hover": "#DC2626",
    "success": "#16A34A",
    "warning": "#D97706",
    "muted_bg": "#EEF1F8",
}

STYLESHEET = f"""
* {{
    font-family: "Segoe UI", "Inter", "Noto Sans", "Ubuntu", sans-serif;
    font-size: 13px;
    color: {COLORS['text']};
}}

QMainWindow, QWidget#centralWidget {{
    background: {COLORS['bg']};
}}

QFrame#headerBar {{
    border: none;
}}

QLabel#appTitle {{
    color: white;
    font-size: 20px;
    font-weight: 600;
}}

QLabel#appSubtitle {{
    color: rgba(255, 255, 255, 0.85);
    font-size: 12px;
}}

QLabel#logoBadge {{
    background: rgba(255, 255, 255, 0.92);
    border-radius: 14px;
}}

QFrame[class="card"] {{
    background: {COLORS['card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
}}

QLabel[class="cardTitle"] {{
    font-size: 13px;
    font-weight: 600;
    color: {COLORS['text']};
    padding-bottom: 2px;
}}

QLabel[class="hint"] {{
    color: {COLORS['text_muted']};
    font-size: 11px;
}}

QLineEdit, QSpinBox {{
    background: {COLORS['muted_bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: {COLORS['primary']};
}}

QLineEdit:disabled, QSpinBox:disabled {{
    color: {COLORS['text_muted']};
    background: #F5F6FA;
}}

QLineEdit:focus, QSpinBox:focus {{
    border: 1px solid {COLORS['primary']};
}}

QPushButton {{
    background: {COLORS['muted_bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 7px 16px;
    font-weight: 500;
}}

QPushButton:hover {{
    background: #E4E9FB;
}}

QPushButton:disabled {{
    color: #B0B5C2;
    background: #F0F1F5;
}}

QPushButton#primaryButton {{
    background: {COLORS['primary']};
    color: white;
    font-weight: 600;
    border: none;
    padding: 10px 22px;
    border-radius: 10px;
    font-size: 14px;
}}

QPushButton#primaryButton:hover {{
    background: {COLORS['primary_hover']};
}}

QPushButton#primaryButton:pressed {{
    background: {COLORS['primary_pressed']};
}}

QPushButton#primaryButton:disabled {{
    background: #A9B2F5;
    color: #F0F1FF;
}}

QPushButton#stopButton {{
    background: {COLORS['card']};
    color: {COLORS['danger']};
    border: 1px solid {COLORS['danger']};
    font-weight: 600;
    padding: 10px 20px;
    border-radius: 10px;
}}

QPushButton#stopButton:hover {{
    background: #FDEDED;
}}

QPushButton#stopButton:disabled {{
    color: #E7A9A9;
    border: 1px solid #F3D0D0;
}}

QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator, QTreeView::indicator {{
    width: 17px;
    height: 17px;
    border-radius: 5px;
    border: 1px solid {COLORS['border']};
    background: {COLORS['card']};
}}

QCheckBox::indicator:checked, QTreeView::indicator:checked {{
    image: url({_CHECK_ON});
    border: 1px solid {COLORS['success']};
}}

QCheckBox::indicator:indeterminate, QTreeView::indicator:indeterminate {{
    image: url({_CHECK_PARTIAL});
    border: 1px solid {COLORS['success']};
}}

QProgressBar {{
    background: {COLORS['muted_bg']};
    border: none;
    border-radius: 7px;
    height: 14px;
    text-align: center;
    color: {COLORS['text']};
    font-size: 11px;
}}

QProgressBar::chunk {{
    background: {COLORS['primary']};
    border-radius: 7px;
}}

QTreeWidget {{
    background: {COLORS['card']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    alternate-background-color: #FAFBFE;
    outline: none;
}}

QTreeWidget::item {{
    padding: 5px 2px;
    border-bottom: 1px solid #F0F2F8;
}}

QTreeWidget::item:selected {{
    background: #E9EDFD;
    color: {COLORS['text']};
}}

QHeaderView::section {{
    background: {COLORS['muted_bg']};
    color: {COLORS['text_muted']};
    padding: 7px 6px;
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    font-weight: 600;
    font-size: 11px;
}}

QFrame#footerBar {{
    border: none;
    border-radius: 10px;
}}

QLabel#footerText {{
    color: rgba(255, 255, 255, 0.98);
    font-size: 12px;
    font-weight: 700;
}}

QLabel#creditText {{
    color: rgba(255, 255, 255, 0.98);
    font-size: 12px;
    font-weight: 800;
}}

QLabel#statusText {{
    color: {COLORS['text_muted']};
    font-size: 12px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
}}

QScrollBar::handle:vertical {{
    background: #C7CDE0;
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: #AEB6D0;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 16px;
}}

QMenu {{
    background: {COLORS['card']};
    border: 1px solid {COLORS['border']};
}}

QToolTip {{
    background: {COLORS['text']};
    color: white;
    border: none;
    padding: 4px 8px;
    border-radius: 4px;
}}
"""
