from PyQt6.QtWidgets import QApplication, QWidget, QComboBox, QTableWidget, QScrollBar, QSlider, QSpinBox, \
    QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit, QTextEdit, QPlainTextEdit, QLineEdit, QCheckBox, QRadioButton, \
    QPushButton, QGroupBox, QTabWidget, QMenu, QMenuBar, QStatusBar, QToolTip, QAbstractItemView, QHeaderView, \
    QProgressBar, QDialog, QMessageBox, QCalendarWidget, QLabel, QFrame
from PyQt6.QtGui import QColor, QPalette, QBrush, QFont, QIcon, QPixmap, QPainter, QPen
from PyQt6.QtCore import Qt, QSettings

# Современная светлая тема (Material Design Light)
LIGHT_THEME = """
/* Global Styles */
QWidget {
    background-color: #F5F5F5;
    color: #212121;
    font-family: "Segoe UI", "Roboto", "Arial", sans-serif;
    font-size: 14px;
}

/* Main Window */
QMainWindow {
    background-color: #FAFAFA;
}

/* Buttons */
QPushButton {
    background-color: #2196F3;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: bold;
    min-width: 80px;
}
QPushButton:hover {
    background-color: #1976D2;
}
QPushButton:pressed {
    background-color: #0D47A1;
}
QPushButton:disabled {
    background-color: #BDBDBD;
    color: #757575;
}

/* Line Edits & Text Inputs */
QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit, QTimeEdit, QDateTimeEdit, QSpinBox, QDoubleSpinBox {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: #BBDEFB;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #2196F3;
    background-color: #FFFFFF;
}

/* Combo Boxes */
QComboBox {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 120px;
}
QComboBox:hover {
    border: 1px solid #2196F3;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #757575;
    margin-right: 8px;
}

/* Tables */
QTableWidget, QTableView {
    background-color: white;
    alternate-background-color: #FAFAFA;
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    gridline-color: #EEEEEE;
    selection-background-color: #BBDEFB;
    selection-color: #0D47A1;
}
QTableWidget::item, QTableView::item {
    padding: 8px;
    border-bottom: 1px solid #EEEEEE;
}
QTableWidget::item:hover, QTableView::item:hover {
    background-color: #E3F2FD;
}
QHeaderView::section {
    background-color: #EEEEEE;
    color: #424242;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #BDBDBD;
    font-weight: bold;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #FAFAFA;
    width: 10px;
    border-radius: 5px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #BDBDBD;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #9E9E9E;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background-color: #FAFAFA;
    height: 10px;
    border-radius: 5px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: #BDBDBD;
    border-radius: 5px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #9E9E9E;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* Group Boxes */
QGroupBox {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
    color: #1976D2;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #1976D2;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    background-color: white;
    top: -1px;
}
QTabBar::tab {
    background-color: #EEEEEE;
    color: #757575;
    padding: 10px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: white;
    color: #1976D2;
    border-bottom: 2px solid #2196F3;
}
QTabBar::tab:hover:!selected {
    background-color: #E0E0E0;
    color: #424242;
}

/* Progress Bars */
QProgressBar {
    background-color: #E0E0E0;
    border: none;
    border-radius: 6px;
    text-align: center;
    height: 10px;
}
QProgressBar::chunk {
    background-color: #2196F3;
    border-radius: 6px;
}

/* Checkboxes & Radio Buttons */
QCheckBox, QRadioButton {
    spacing: 8px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #BDBDBD;
    background-color: white;
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #2196F3;
    border: 1px solid #1976D2;
}
QRadioButton::indicator {
    border-radius: 9px;
}

/* Menu Bar */
QMenuBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E0E0E0;
    padding: 4px;
}
QMenuBar::item {
    padding: 6px 12px;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background-color: #E3F2FD;
}
QMenu {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #E3F2FD;
    color: #0D47A1;
}

/* Status Bar */
QStatusBar {
    background-color: #FFFFFF;
    border-top: 1px solid #E0E0E0;
    padding: 4px;
    color: #757575;
}

/* Tool Tips */
QToolTip {
    background-color: #424242;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 10px;
}

/* Dialogs */
QDialog {
    background-color: #FAFAFA;
}
QMessageBox {
    background-color: #FAFAFA;
}
QMessageBox QLabel {
    color: #212121;
}
QMessageBox QPushButton {
    min-width: 80px;
}

/* Calendar Widget */
QCalendarWidget {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 6px;
}
QCalendarWidget QToolButton {
    color: #212121;
    background-color: #FAFAFA;
    border-radius: 6px;
    padding: 6px;
}
QCalendarWidget QToolButton:hover {
    background-color: #E3F2FD;
}
QCalendarWidget QMenu {
    background-color: white;
    border: 1px solid #E0E0E0;
}
QCalendarWidget QSpinBox {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
}

/* List Widgets */
QListWidget, QListView {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    outline: none;
}
QListWidget::item, QListView::item {
    padding: 8px;
    border-bottom: 1px solid #EEEEEE;
}
QListWidget::item:selected, QListView::item:selected {
    background-color: #BBDEFB;
    color: #0D47A1;
}
QListWidget::item:hover, QListView::item:hover {
    background-color: #E3F2FD;
}

/* Slider */
QSlider::groove:horizontal {
    background-color: #E0E0E0;
    height: 6px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background-color: #2196F3;
    width: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background-color: #1976D2;
}
"""

# Современная темная тема (Material Design Dark)
DARK_THEME = """
/* Global Styles */
QWidget {
    background-color: #121212;
    color: #E0E0E0;
    font-family: "Segoe UI", "Roboto", "Arial", sans-serif;
    font-size: 14px;
}

/* Main Window */
QMainWindow {
    background-color: #1E1E1E;
}

/* Buttons */
QPushButton {
    background-color: #BB86FC;
    color: #000000;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: bold;
    min-width: 80px;
}
QPushButton:hover {
    background-color: #9965F4;
}
QPushButton:pressed {
    background-color: #7B1FA2;
}
QPushButton:disabled {
    background-color: #3C3C3C;
    color: #757575;
}

/* Line Edits & Text Inputs */
QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit, QTimeEdit, QDateTimeEdit, QSpinBox, QDoubleSpinBox {
    background-color: #2C2C2C;
    border: 1px solid #3C3C3C;
    border-radius: 6px;
    padding: 8px 12px;
    color: #E0E0E0;
    selection-background-color: #BB86FC;
    selection-color: #000000;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #BB86FC;
    background-color: #333333;
}

/* Combo Boxes */
QComboBox {
    background-color: #2C2C2C;
    border: 1px solid #3C3C3C;
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 120px;
    color: #E0E0E0;
}
QComboBox:hover {
    border: 1px solid #BB86FC;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #BDBDBD;
    margin-right: 8px;
}

/* Tables */
QTableWidget, QTableView {
    background-color: #1E1E1E;
    alternate-background-color: #252525;
    border: 1px solid #3C3C3C;
    border-radius: 6px;
    gridline-color: #333333;
    selection-background-color: #3C3C3C;
    selection-color: #BB86FC;
    color: #E0E0E0;
}
QTableWidget::item, QTableView::item {
    padding: 8px;
    border-bottom: 1px solid #333333;
}
QTableWidget::item:hover, QTableView::item:hover {
    background-color: #2C2C2C;
}
QHeaderView::section {
    background-color: #2C2C2C;
    color: #BB86FC;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #555555;
    font-weight: bold;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #1E1E1E;
    width: 10px;
    border-radius: 5px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #555555;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #757575;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background-color: #1E1E1E;
    height: 10px;
    border-radius: 5px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: #555555;
    border-radius: 5px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #757575;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* Group Boxes */
QGroupBox {
    background-color: #1E1E1E;
    border: 1px solid #3C3C3C;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
    color: #BB86FC;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #BB86FC;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #3C3C3C;
    border-radius: 6px;
    background-color: #1E1E1E;
    top: -1px;
}
QTabBar::tab {
    background-color: #2C2C2C;
    color: #9E9E9E;
    padding: 10px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #1E1E1E;
    color: #BB86FC;
    border-bottom: 2px solid #BB86FC;
}
QTabBar::tab:hover:!selected {
    background-color: #333333;
    color: #BDBDBD;
}

/* Progress Bars */
QProgressBar {
    background-color: #3C3C3C;
    border: none;
    border-radius: 6px;
    text-align: center;
    height: 10px;
    color: #BB86FC;
}
QProgressBar::chunk {
    background-color: #BB86FC;
    border-radius: 6px;
}

/* Checkboxes & Radio Buttons */
QCheckBox, QRadioButton {
    spacing: 8px;
    color: #E0E0E0;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #555555;
    background-color: #2C2C2C;
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #BB86FC;
    border: 1px solid #9965F4;
}
QRadioButton::indicator {
    border-radius: 9px;
}

/* Menu Bar */
QMenuBar {
    background-color: #1E1E1E;
    border-bottom: 1px solid #3C3C3C;
    padding: 4px;
    color: #E0E0E0;
}
QMenuBar::item {
    padding: 6px 12px;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background-color: #2C2C2C;
    color: #BB86FC;
}
QMenu {
    background-color: #1E1E1E;
    border: 1px solid #3C3C3C;
    border-radius: 6px;
    padding: 4px;
    color: #E0E0E0;
}
QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #2C2C2C;
    color: #BB86FC;
}

/* Status Bar */
QStatusBar {
    background-color: #1E1E1E;
    border-top: 1px solid #3C3C3C;
    padding: 4px;
    color: #9E9E9E;
}

/* Tool Tips */
QToolTip {
    background-color: #333333;
    color: #E0E0E0;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 6px 10px;
}

/* Dialogs */
QDialog {
    background-color: #1E1E1E;
}
QMessageBox {
    background-color: #1E1E1E;
}
QMessageBox QLabel {
    color: #E0E0E0;
}
QMessageBox QPushButton {
    min-width: 80px;
}

/* Calendar Widget */
QCalendarWidget {
    background-color: #1E1E1E;
    border: 1px solid #3C3C3C;
    border-radius: 6px;
    color: #E0E0E0;
}
QCalendarWidget QToolButton {
    color: #E0E0E0;
    background-color: #2C2C2C;
    border-radius: 6px;
    padding: 6px;
}
QCalendarWidget QToolButton:hover {
    background-color: #333333;
    color: #BB86FC;
}
QCalendarWidget QMenu {
    background-color: #1E1E1E;
    border: 1px solid #3C3C3C;
}
QCalendarWidget QSpinBox {
    background-color: #2C2C2C;
    border: 1px solid #3C3C3C;
    border-radius: 4px;
    color: #E0E0E0;
}

/* List Widgets */
QListWidget, QListView {
    background-color: #1E1E1E;
    border: 1px solid #3C3C3C;
    border-radius: 6px;
    outline: none;
    color: #E0E0E0;
}
QListWidget::item, QListView::item {
    padding: 8px;
    border-bottom: 1px solid #333333;
}
QListWidget::item:selected, QListView::item:selected {
    background-color: #3C3C3C;
    color: #BB86FC;
}
QListWidget::item:hover, QListView::item:hover {
    background-color: #2C2C2C;
}

/* Slider */
QSlider::groove:horizontal {
    background-color: #3C3C3C;
    height: 6px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background-color: #BB86FC;
    width: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background-color: #9965F4;
}
"""


def apply_modern_theme(app_or_widget, theme_name):
    """
    Применяет современную тему к приложению или виджету.

    Args:
        app_or_widget: QApplication или QWidget
        theme_name: Название темы ("System Default", "✨ Modern Light", "🌙 Modern Dark")
    """
    if theme_name == "✨ Modern Light":
        stylesheet = LIGHT_THEME
    elif theme_name == "🌙 Modern Dark":
        stylesheet = DARK_THEME
    else:
        # System Default или любая другая - сбрасываем стили
        stylesheet = ""

    if isinstance(app_or_widget, QApplication):
        app_or_widget.setStyleSheet(stylesheet)
    else:
        # Применяем к главному окну и всем виджетам
        app = QApplication.instance()
        if app:
            app.setStyleSheet(stylesheet)