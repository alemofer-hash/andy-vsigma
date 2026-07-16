from __future__ import annotations

from typing import Any

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget


FAMILY_TOKENS: dict[str, str] = {
    "bg_canvas": "#060d16",
    "bg_frame": "#0a1422",
    "bg_elevated": "#0f1d31",
    "bg_toolbar": "#0b1625",
    "bg_input": "#0d1a2b",
    "bg_grid": "#091320",
    "bg_grid_alt": "#0c1727",
    "bg_hover": "#132741",
    "bg_pressed": "#163252",
    "bg_selection": "#113b66",
    "accent_primary": "#23c7ff",
    "accent_bright": "#73dcff",
    "accent_deep": "#1187c7",
    "steel_100": "#f3f7fb",
    "steel_300": "#c7d4e3",
    "steel_500": "#8ea1b8",
    "steel_700": "#4f647d",
    "steel_900": "#203145",
    "text_primary": "#ecf5ff",
    "text_secondary": "#afc0d4",
    "text_muted": "#7b90a8",
    "border_subtle": "#22364d",
    "border_strong": "#33557a",
    "border_glow": "#2eaee8",
    "success": "#36d98f",
    "warning": "#f1b451",
    "danger": "#ff6c77",
    "info": "#65c8ff",
    "shadow_ambient": "rgba(3, 9, 18, 0.84)",
    "shadow_glow": "rgba(35, 199, 255, 0.14)",
}

FAMILY_BODY_FONT = "Segoe UI Variable Text"
FAMILY_HEADING_FONT = "Bahnschrift SemiBold"


def family_theme_tokens() -> dict[str, str]:
    return dict(FAMILY_TOKENS)


def _widget_css() -> str:
    t = FAMILY_TOKENS
    return f"""
    QWidget {{
        background: {t['bg_canvas']};
        color: {t['text_primary']};
        selection-background-color: {t['bg_selection']};
        selection-color: {t['text_primary']};
        font-family: "{FAMILY_BODY_FONT}";
        font-size: 13px;
    }}
    QMainWindow#AndyDesktopWindow {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:1,
            stop:0 {t['bg_canvas']},
            stop:0.55 {t['bg_frame']},
            stop:1 #050a12
        );
    }}
    QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}
    QToolBar {{
        background: {t['bg_toolbar']};
        border: none;
        border-bottom: 1px solid {t['border_subtle']};
        spacing: 8px;
        padding: 10px 14px;
    }}
    QToolBar QToolButton {{
        background: {t['bg_elevated']};
        border: 1px solid {t['border_subtle']};
        border-radius: 10px;
        color: {t['text_primary']};
        padding: 8px 12px;
        margin-right: 4px;
        font-weight: 600;
    }}
    QToolBar QToolButton:hover {{
        background: {t['bg_hover']};
        border-color: {t['border_glow']};
    }}
    QStatusBar {{
        background: {t['bg_toolbar']};
        border-top: 1px solid {t['border_subtle']};
        color: {t['text_secondary']};
        padding: 4px 12px;
    }}
    QStatusBar QLabel {{
        color: {t['text_secondary']};
    }}
    QFrame[role="heroPanel"] {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:1,
            stop:0 {t['bg_frame']},
            stop:0.68 {t['bg_elevated']},
            stop:1 #101f31
        );
        border: 1px solid {t['border_strong']};
        border-radius: 22px;
    }}
    QLabel[role="heroEyebrow"] {{
        color: {t['accent_bright']};
        font-family: "{FAMILY_HEADING_FONT}";
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
    }}
    QLabel[role="heroTitle"] {{
        color: {t['steel_100']};
        font-family: "{FAMILY_HEADING_FONT}";
        font-size: 28px;
        font-weight: 700;
    }}
    QLabel[role="heroBody"] {{
        color: {t['text_secondary']};
        font-size: 14px;
        line-height: 1.35;
    }}
    QLabel[role="statusBadge"] {{
        background: {t['bg_input']};
        border: 1px solid {t['border_subtle']};
        border-radius: 11px;
        color: {t['text_secondary']};
        padding: 4px 10px;
        font-family: "{FAMILY_HEADING_FONT}";
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.08em;
    }}
    QLabel[role="statusBadge"][tone="accent"] {{
        background: rgba(35, 199, 255, 0.12);
        border-color: {t['border_glow']};
        color: {t['accent_bright']};
    }}
    QLabel[role="statusBadge"][tone="success"] {{
        background: rgba(54, 217, 143, 0.12);
        border-color: {t['success']};
        color: {t['success']};
    }}
    QLabel[role="statusBadge"][tone="warning"] {{
        background: rgba(241, 180, 81, 0.12);
        border-color: {t['warning']};
        color: {t['warning']};
    }}
    QLabel[role="statusBadge"][tone="danger"] {{
        background: rgba(255, 108, 119, 0.12);
        border-color: {t['danger']};
        color: {t['danger']};
    }}
    QGroupBox {{
        background: {t['bg_frame']};
        border: 1px solid {t['border_subtle']};
        border-radius: 18px;
        margin-top: 16px;
        padding: 18px 16px 16px 16px;
        font-family: "{FAMILY_HEADING_FONT}";
        font-size: 13px;
        font-weight: 700;
        color: {t['steel_100']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 8px;
        color: {t['accent_bright']};
        background: {t['bg_canvas']};
    }}
    QLabel[role="valueLabel"] {{
        color: {t['text_secondary']};
        background: transparent;
    }}
    QLabel[role="helpText"] {{
        color: {t['text_muted']};
        font-size: 12px;
    }}
    QTextEdit[role="messageLog"] {{
        background: {t['bg_grid']};
        border: 1px solid {t['border_subtle']};
        border-radius: 16px;
        color: {t['text_secondary']};
        padding: 10px 12px;
    }}
    QLineEdit, QComboBox, QTextEdit, QListWidget {{
        background: {t['bg_input']};
        border: 1px solid {t['border_subtle']};
        border-radius: 10px;
        color: {t['text_primary']};
        padding: 8px 10px;
    }}
    QLineEdit:hover, QComboBox:hover, QTextEdit:hover, QListWidget:hover {{
        border-color: {t['border_strong']};
    }}
    QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QListWidget:focus {{
        border-color: {t['border_glow']};
    }}
    QLineEdit:disabled, QComboBox:disabled, QTextEdit:disabled, QListWidget:disabled {{
        background: {t['bg_frame']};
        color: {t['text_muted']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}
    QPushButton, QToolButton {{
        background: {t['bg_elevated']};
        border: 1px solid {t['border_subtle']};
        border-radius: 11px;
        color: {t['text_primary']};
        padding: 9px 14px;
        font-weight: 600;
    }}
    QPushButton:hover, QToolButton:hover {{
        background: {t['bg_hover']};
        border-color: {t['border_glow']};
    }}
    QPushButton:pressed, QToolButton:pressed {{
        background: {t['bg_pressed']};
    }}
    QPushButton[variant="primary"] {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {t['accent_primary']},
            stop:1 {t['accent_deep']}
        );
        border-color: {t['accent_bright']};
        color: #04111a;
        font-family: "{FAMILY_HEADING_FONT}";
        font-weight: 700;
    }}
    QPushButton[variant="primary"]:hover {{
        background: {t['accent_bright']};
        color: #06111a;
    }}
    QPushButton[variant="secondary"] {{
        background: rgba(35, 199, 255, 0.10);
        border-color: {t['border_glow']};
        color: {t['accent_bright']};
    }}
    QPushButton[variant="ghost"], QToolButton[variant="ghost"] {{
        background: transparent;
        color: {t['text_secondary']};
    }}
    QPushButton:disabled, QToolButton:disabled {{
        background: {t['bg_frame']};
        border-color: {t['border_subtle']};
        color: {t['text_muted']};
    }}
    QCheckBox {{
        spacing: 8px;
        color: {t['text_secondary']};
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 1px solid {t['border_strong']};
        background: {t['bg_input']};
    }}
    QCheckBox::indicator:checked {{
        background: {t['accent_primary']};
        border-color: {t['accent_bright']};
    }}
    QTableView {{
        background: {t['bg_grid']};
        alternate-background-color: {t['bg_grid_alt']};
        border: 1px solid {t['border_subtle']};
        border-radius: 18px;
        gridline-color: {t['border_subtle']};
        color: {t['text_primary']};
        selection-background-color: {t['bg_selection']};
        selection-color: {t['steel_100']};
    }}
    QHeaderView::section {{
        background: {t['bg_elevated']};
        color: {t['accent_bright']};
        border: none;
        border-bottom: 1px solid {t['border_subtle']};
        padding: 10px 8px;
        font-family: "{FAMILY_HEADING_FONT}";
        font-weight: 700;
    }}
    QSplitter::handle {{
        background: {t['border_subtle']};
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 12px;
        margin: 3px;
    }}
    QScrollBar::handle:vertical {{
        background: {t['steel_700']};
        border-radius: 6px;
        min-height: 28px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {t['accent_deep']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
    QScrollBar:horizontal, QScrollBar::handle:horizontal,
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
        border: none;
        height: 0px;
        width: 0px;
    }}
    QDialog {{
        background: {t['bg_frame']};
        color: {t['text_primary']};
    }}
    QMessageBox QLabel {{
        color: {t['text_primary']};
    }}
    """


def build_family_stylesheet() -> str:
    return _widget_css()


def build_family_palette() -> QPalette:
    t = FAMILY_TOKENS
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(t["bg_canvas"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(t["bg_input"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(t["bg_grid_alt"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(t["bg_elevated"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(t["text_primary"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(t["text_primary"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(t["text_primary"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(t["accent_primary"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(t["bg_canvas"]))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(t["text_muted"]))
    palette.setColor(QPalette.ColorRole.Mid, QColor(t["border_subtle"]))
    palette.setColor(QPalette.ColorRole.Midlight, QColor(t["border_strong"]))
    return palette


def apply_family_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setPalette(build_family_palette())
    app.setStyleSheet(build_family_stylesheet())


def polish_widget(widget: QWidget, **properties: Any) -> None:
    for key, value in properties.items():
        widget.setProperty(str(key), value)
    style = widget.style()
    if style is not None:
        style.unpolish(widget)
        style.polish(widget)
    widget.update()
