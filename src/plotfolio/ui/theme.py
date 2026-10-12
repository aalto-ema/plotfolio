"""Shared design tokens and application stylesheet."""

from pathlib import Path

STYLE = """
QMainWindow, QDialog { background: #F2F5F9; }
QWidget { color: #263448; font-family: "Helvetica Neue", "Arial"; font-size: 12px; }
QToolBar { background: #14263D; border: none; padding: 10px; spacing: 8px; }
QToolBar QLabel { color: #FFFFFF; font-size: 18px; font-weight: 600; padding-right: 18px; }
QToolBar QToolButton { color: #F3F7FF; background: #253A54; border-radius: 6px; padding: 7px 12px; }
QToolBar QToolButton:hover { background: #385777; }
QPushButton { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 7px 10px; }
QPushButton:hover { background: #E8F2F7; border-color: #46A5B7; }
QPushButton:checked { background: #D8F2F1; border-color: #008D8A; }
QPushButton#primary { background: #008D8A; color: white; border: none; font-weight: 600; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: white; border: 1px solid #CCD6E2; border-radius: 5px; padding: 5px; min-height: 19px; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #008D8A; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled { color: #9CA7B5; background: #F0F3F7; }
QListWidget { background: white; border: 1px solid #DCE3EC; border-radius: 7px; padding: 5px; outline: none; }
QListWidget::item { padding: 10px 6px; border-radius: 5px; }
QListWidget::item:selected { background: #DDF1F0; color: #007A78; }
QTabWidget::pane { border: 1px solid #DCE3EC; background: white; border-radius: 6px; }
QTabBar::tab { background: #E7ECF3; padding: 9px 10px; border: none; }
QTabBar::tab:selected { background: white; color: #007F7D; }
QScrollArea { border: none; background: white; }
QGroupBox { background: white; border: 1px solid #E0E6EF; border-radius: 7px; margin-top: 18px; padding: 12px 8px 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; font-weight: 600; }
QCheckBox { spacing: 8px; padding: 3px; }
QTableView { background: white; alternate-background-color: #F5F8FC; border: none; gridline-color: #E5EAF1; }
QHeaderView::section { background: #E9EFF6; border: none; padding: 8px; font-weight: 600; }
QStatusBar { background: #E7EEF5; padding: 5px; }
QSplitter::handle { background: #E0E6EF; width: 3px; }
QLabel#muted { color: #728096; font-size: 11px; }
QLabel#heading { font-weight: 600; font-size: 14px; }
"""


STYLE += """
QWidget#inspectorBody { background: #F2F5F9; }
QComboBox { padding-right: 25px; selection-background-color: #DDF1F0; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: white; color: #263448; selection-background-color: #DDF1F0; selection-color: #007A78; border: 1px solid #CBD5E1; padding: 5px; outline: none; }
QScrollBar:vertical { background: #F2F5F9; width: 9px; }
QScrollBar::handle:vertical { background: #BBC9D7; border-radius: 4px; min-height: 25px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

STYLE += (
    'QComboBox::down-arrow { image: url("'
    + (Path(__file__).parent / "icons/chevron.svg").as_posix()
    + '"); width: 14px; height: 14px; }'
)
