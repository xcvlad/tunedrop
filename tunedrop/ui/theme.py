"""Tema oscuro de la app. Los colores están centralizados aquí."""

from __future__ import annotations

BG = "#0e1014"
SURFACE = "#15181f"
CARD = "#1b1f28"
CARD_HOVER = "#222835"
BORDER = "#2a303c"
TEXT = "#eceef3"
MUTED = "#8f98a8"
ACCENT = "#8b5cf6"
ACCENT_2 = "#d946ef"
ACCENT_HOVER = "#9d74f8"
SUCCESS = "#34d399"
ERROR = "#fb7185"
WARNING = "#fbbf24"

STYLESHEET = f"""
* {{
    /* Se usa la primera fuente que exista: Segoe en Windows; Inter, Cantarell,
       Ubuntu o Noto en Linux. */
    font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", "Cantarell", "Ubuntu",
                 "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 10pt;
    color: {TEXT};
}}
QMainWindow, QDialog {{ background: {BG}; }}
QWidget#Panel {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 16px;
}}
QLabel {{ background: transparent; }}
QLabel#Logo {{ font-size: 20pt; font-weight: 700; }}
QLabel#Tagline, QLabel#Muted {{ color: {MUTED}; }}
QLabel#PanelTitle {{ font-size: 12.5pt; font-weight: 600; }}
QLabel#CardTitle {{ font-weight: 600; }}
QLabel#Empty {{ color: {MUTED}; font-size: 10.5pt; }}
QLabel#Badge {{
    color: {SUCCESS}; background: rgba(52, 211, 153, 0.12);
    border-radius: 6px; padding: 1px 7px; font-size: 8.5pt; font-weight: 600;
}}
QLabel#Toast {{
    background: {CARD_HOVER}; border: 1px solid {BORDER};
    border-radius: 12px; padding: 10px 16px;
}}

QLineEdit {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px;
    padding: 10px 14px; selection-background-color: {ACCENT};
}}
QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
QLineEdit#Search {{ font-size: 12pt; padding: 13px 16px; border-radius: 14px; }}

QPushButton {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px;
    padding: 8px 14px; font-weight: 600;
}}
QPushButton:hover {{ background: {CARD_HOVER}; }}
QPushButton:pressed {{ background: {BORDER}; }}
QPushButton:disabled {{ color: {MUTED}; background: {SURFACE}; }}
QPushButton#Primary {{
    border: none; color: white;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_2});
}}
QPushButton#Primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACCENT_HOVER}, stop:1 #e879f9);
}}
QPushButton#Primary:disabled {{ background: {BORDER}; color: {MUTED}; }}
QPushButton#Big {{ font-size: 12pt; padding: 13px; border-radius: 14px; }}
QPushButton#Icon {{ background: transparent; border: none; padding: 6px; border-radius: 8px; }}
QPushButton#Icon:hover {{ background: {CARD_HOVER}; }}
QPushButton#Add {{
    background: {CARD_HOVER}; border: none; border-radius: 17px; padding: 0;
    min-width: 34px; max-width: 34px; min-height: 34px; max-height: 34px;
}}
QPushButton#Add:hover {{ background: {ACCENT}; }}
QPushButton#Add[added="true"] {{ background: {ACCENT}; }}
QPushButton#Link {{ background: transparent; border: none; color: {MUTED}; padding: 4px 6px; }}
QPushButton#Link:hover {{ color: {TEXT}; }}

QComboBox, QSpinBox {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px; padding: 7px 12px;
}}
QComboBox:hover, QSpinBox:hover {{ border: 1px solid {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 8px; padding: 4px;
    selection-background-color: {CARD_HOVER}; outline: none;
}}
QCheckBox {{ spacing: 10px; background: transparent; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 5px; border: 1px solid {BORDER}; background: {CARD};
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border: 1px solid {ACCENT}; }}

QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ border: none; padding: 0; margin: 0; }}
QListWidget::item:selected, QListWidget::item:hover {{ background: transparent; }}
QWidget#Card {{ background: {CARD}; border-radius: 12px; }}
QWidget#Card:hover {{ background: {CARD_HOVER}; }}

QProgressBar {{
    background: {BORDER}; border: none; border-radius: 3px;
    max-height: 6px; min-height: 6px; text-align: center;
}}
QProgressBar::chunk {{
    border-radius: 3px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_2});
}}
QProgressBar[state="done"]::chunk {{ background: {SUCCESS}; }}
QProgressBar[state="failed"]::chunk {{ background: {ERROR}; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 3px; min-height: 40px; }}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    background: none; height: 0;
}}
QSplitter::handle {{ background: transparent; width: 12px; }}
QToolTip {{ background: {CARD}; border: 1px solid {BORDER}; padding: 6px; border-radius: 6px; }}
"""
