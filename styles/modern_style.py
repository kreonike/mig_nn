from PyQt6.QtWidgets import QApplication, QWidget, QComboBox, QTableWidget, QScrollBar, QSlider, QSpinBox, \
    QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit, QTextEdit, QPlainTextEdit, QLineEdit, QCheckBox, QRadioButton, \
    QPushButton, QGroupBox, QTabWidget, QMenu, QMenuBar, QStatusBar, QToolTip, QAbstractItemView, QHeaderView, \
    QProgressBar, QDialog, QMessageBox, QCalendarWidget, QLabel, QFrame
from PyQt6.QtGui import QColor, QPalette, QBrush, QFont, QIcon, QPixmap, QPainter, QPen
from PyQt6.QtCore import Qt, QSettings, QEasingCurve, QPropertyAnimation

# Строгая современная светлая тема (Professional Business Light)
LIGHT_THEME = """
/* Global Styles */
QWidget {
    background-color: #F8F9FA;
    color: #2C3E50;
    font-family: "Segoe UI", "Roboto", "Arial", sans-serif;
    font-size: 13px;
}

/* Main Window */
QMainWindow {
    background-color: #FFFFFF;
}

/* Buttons */
QPushButton {
    background-color: #34495E;
    color: white;
    border: none;
    padding: 8px 18px;
    border-radius: 3px;
    font-weight: 500;
    min-width: 85px;
}
QPushButton:hover {
    background-color: #2C3E50;
}
QPushButton:pressed {
    background-color: #1A252F;
}
QPushButton:disabled {
    background-color: #BDC3C7;
    color: #7F8C8D;
}

/* Line Edits & Text Inputs */
QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit, QTimeEdit, QDateTimeEdit, QSpinBox, QDoubleSpinBox {
    background-color: white;
    border: 1px solid #DCE4EC;
    border-radius: 3px;
    padding: 8px 12px;
    selection-background-color: #E8F4F8;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #5D6D7E;
    background-color: #FFFFFF;
}

/* Combo Boxes */
QComboBox {
    background-color: white;
    border: 1px solid #DCE4EC;
    border-radius: 3px;
    padding: 8px 12px;
    min-width: 120px;
}
QComboBox:hover {
    border: 1px solid #5D6D7E;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #5D6D7E;
    margin-right: 10px;
}

/* Tables */
QTableWidget, QTableView {
    background-color: white;
    alternate-background-color: #FDFEFE;
    border: 1px solid #DCE4EC;
    border-radius: 3px;
    gridline-color: #EBF5FB;
    selection-background-color: #E8F4F8;
    selection-color: #2C3E50;
}
QTableWidget::item, QTableView::item {
    padding: 8px;
    border-bottom: 1px solid #EBF5FB;
}
QTableWidget::item:hover, QTableView::item:hover {
    background-color: #F4F6F7;
}
QTableWidget::item:selected, QTableView::item:selected {
    background-color: #E8F4F8;
}
QHeaderView::section {
    background-color: #ECF0F1;
    color: #34495E;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #BDC3C7;
    font-weight: 600;
    font-size: 12px;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #F8F9FA;
    width: 10px;
    border-radius: 0;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #BDC3C7;
    border-radius: 0;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #95A5A6;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background-color: #F8F9FA;
    height: 10px;
    border-radius: 0;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: #BDC3C7;
    border-radius: 0;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #95A5A6;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* Group Boxes */
QGroupBox {
    background-color: white;
    border: 1px solid #DCE4EC;
    border-radius: 3px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
    color: #34495E;
    font-size: 13px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #34495E;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #DCE4EC;
    border-radius: 3px;
    background-color: white;
    top: -1px;
}
QTabBar::tab {
    background-color: #F8F9FA;
    color: #7F8C8D;
    padding: 10px 20px;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    margin-right: 2px;
    border: 1px solid transparent;
    border-bottom: none;
}
QTabBar::tab:selected {
    background-color: white;
    color: #34495E;
    border: 1px solid #DCE4EC;
    border-bottom: 2px solid #34495E;
}
QTabBar::tab:hover:!selected {
    background-color: #EBF5FB;
    color: #34495E;
}

/* Progress Bars */
QProgressBar {
    background-color: #EBF5FB;
    border: 1px solid #DCE4EC;
    border-radius: 3px;
    text-align: center;
    height: 14px;
    color: #34495E;
    font-size: 11px;
}
QProgressBar::chunk {
    background-color: #34495E;
    border-radius: 2px;
}

/* Checkboxes & Radio Buttons */
QCheckBox, QRadioButton {
    spacing: 8px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 3px;
    border: 2px solid #BDC3C7;
    background-color: white;
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #34495E;
    border: 2px solid #2C3E50;
}
QRadioButton::indicator {
    border-radius: 9px;
}

/* Menu Bar */
QMenuBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #DCE4EC;
    padding: 4px;
}
QMenuBar::item {
    padding: 6px 12px;
    border-radius: 3px;
}
QMenuBar::item:selected {
    background-color: #EBF5FB;
}
QMenu {
    background-color: white;
    border: 1px solid #DCE4EC;
    border-radius: 3px;
    padding: 4px;
}
QMenu::item {
    padding: 8px 28px;
    border-radius: 3px;
}
QMenu::item:selected {
    background-color: #EBF5FB;
    color: #2C3E50;
}

/* Status Bar */
QStatusBar {
    background-color: #FFFFFF;
    border-top: 1px solid #DCE4EC;
    padding: 4px;
    color: #7F8C8D;
    font-size: 12px;
}

/* Tool Tips */
QToolTip {
    background-color: #2C3E50;
    color: white;
    border: none;
    border-radius: 3px;
    padding: 6px 10px;
    font-size: 12px;
}

/* Dialogs */
QDialog {
    background-color: #F8F9FA;
}
QMessageBox {
    background-color: #F8F9FA;
}
QMessageBox QLabel {
    color: #2C3E50;
}
QMessageBox QPushButton {
    min-width: 85px;
}

/* Calendar Widget */
QCalendarWidget {
    background-color: white;
    border: 1px solid #DCE4EC;
    border-radius: 3px;
}
QCalendarWidget QAbstractItemView:enabled {
    background-color: white;
    color: #2C3E50;
    selection-background-color: #34495E;
    selection-color: white;
    font-size: 11px;
}
QCalendarWidget QAbstractItemView QWidget {
    padding: 0px;
}
QCalendarWidget QTableView {
    background-color: white;
    border: none;
    selection-background-color: #34495E;
    selection-color: white;
}
QCalendarWidget QTableView::item {
    padding: 0px;
    border: none;
}
QCalendarWidget QToolButton {
    color: #2C3E50;
    background-color: #F8F9FA;
    border-radius: 3px;
    padding: 4px;
    border: 1px solid transparent;
}
QCalendarWidget QToolButton:hover {
    background-color: #EBF5FB;
    border: 1px solid #DCE4EC;
}
QCalendarWidget QMenu {
    background-color: white;
    border: 1px solid #DCE4EC;
}
QCalendarWidget QSpinBox {
    background-color: white;
    border: 1px solid #DCE4EC;
    border-radius: 3px;
}

/* List Widgets */
QListWidget, QListView {
    background-color: white;
    border: 1px solid #DCE4EC;
    border-radius: 3px;
    outline: none;
}
QListWidget::item, QListView::item {
    padding: 8px;
    border-bottom: 1px solid #EBF5FB;
}
QListWidget::item:selected, QListView::item:selected {
    background-color: #E8F4F8;
    color: #2C3E50;
}
QListWidget::item:hover, QListView::item:hover {
    background-color: #F4F6F7;
}

/* Slider */
QSlider::groove:horizontal {
    background-color: #EBF5FB;
    height: 6px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background-color: #34495E;
    width: 16px;
    margin: -5px 0;
    border-radius: 3px;
}
QSlider::handle:horizontal:hover {
    background-color: #2C3E50;
}
"""

# Строгая современная темная тема (Professional Business Dark)
DARK_THEME = """
/* Global Styles */
QWidget {
    background-color: #1B2631;
    color: #E8E8E8;
    font-family: "Segoe UI", "Roboto", "Arial", sans-serif;
    font-size: 13px;
}

/* Main Window */
QMainWindow {
    background-color: #17202A;
}

/* Buttons */
QPushButton {
    background-color: #5D6D7E;
    color: white;
    border: none;
    padding: 8px 18px;
    border-radius: 3px;
    font-weight: 500;
    min-width: 85px;
}
QPushButton:hover {
    background-color: #707B8C;
}
QPushButton:pressed {
    background-color: #34495E;
}
QPushButton:disabled {
    background-color: #3A4550;
    color: #7F8C8D;
}

/* Line Edits & Text Inputs */
QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit, QTimeEdit, QDateTimeEdit, QSpinBox, QDoubleSpinBox {
    background-color: #1F2D3D;
    border: 1px solid #3A4550;
    border-radius: 3px;
    padding: 8px 12px;
    color: #E8E8E8;
    selection-background-color: #2E4053;
    selection-color: #E8E8E8;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #5D6D7E;
    background-color: #243342;
}

/* Combo Boxes */
QComboBox {
    background-color: #1F2D3D;
    border: 1px solid #3A4550;
    border-radius: 3px;
    padding: 8px 12px;
    min-width: 120px;
    color: #E8E8E8;
}
QComboBox:hover {
    border: 1px solid #5D6D7E;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #7F8C8D;
    margin-right: 10px;
}

/* Tables */
QTableWidget, QTableView {
    background-color: #17202A;
    alternate-background-color: #1B2631;
    border: 1px solid #3A4550;
    border-radius: 3px;
    gridline-color: #2E4053;
    selection-background-color: #2E4053;
    selection-color: #E8E8E8;
    color: #E8E8E8;
}
QTableWidget::item, QTableView::item {
    padding: 8px;
    border-bottom: 1px solid #2E4053;
}
QTableWidget::item:hover, QTableView::item:hover {
    background-color: #243342;
}
QTableWidget::item:selected, QTableView::item:selected {
    background-color: #2E4053;
}
QHeaderView::section {
    background-color: #243342;
    color: #AEB6BF;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #3A4550;
    font-weight: 600;
    font-size: 12px;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #1B2631;
    width: 10px;
    border-radius: 0;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #3A4550;
    border-radius: 0;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #5D6D7E;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background-color: #1B2631;
    height: 10px;
    border-radius: 0;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: #3A4550;
    border-radius: 0;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #5D6D7E;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* Group Boxes */
QGroupBox {
    background-color: #17202A;
    border: 1px solid #3A4550;
    border-radius: 3px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
    color: #AEB6BF;
    font-size: 13px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #AEB6BF;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #3A4550;
    border-radius: 3px;
    background-color: #17202A;
    top: -1px;
}
QTabBar::tab {
    background-color: #1B2631;
    color: #7F8C8D;
    padding: 10px 20px;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    margin-right: 2px;
    border: 1px solid transparent;
    border-bottom: none;
}
QTabBar::tab:selected {
    background-color: #17202A;
    color: #E8E8E8;
    border: 1px solid #3A4550;
    border-bottom: 2px solid #5D6D7E;
}
QTabBar::tab:hover:!selected {
    background-color: #243342;
    color: #AEB6BF;
}

/* Progress Bars */
QProgressBar {
    background-color: #2E4053;
    border: 1px solid #3A4550;
    border-radius: 3px;
    text-align: center;
    height: 14px;
    color: #AEB6BF;
    font-size: 11px;
}
QProgressBar::chunk {
    background-color: #5D6D7E;
    border-radius: 2px;
}

/* Checkboxes & Radio Buttons */
QCheckBox, QRadioButton {
    spacing: 8px;
    color: #E8E8E8;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 3px;
    border: 2px solid #3A4550;
    background-color: #1F2D3D;
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #5D6D7E;
    border: 2px solid #34495E;
}
QRadioButton::indicator {
    border-radius: 9px;
}

/* Menu Bar */
QMenuBar {
    background-color: #17202A;
    border-bottom: 1px solid #3A4550;
    padding: 4px;
    color: #E8E8E8;
}
QMenuBar::item {
    padding: 6px 12px;
    border-radius: 3px;
}
QMenuBar::item:selected {
    background-color: #243342;
}
QMenu {
    background-color: #17202A;
    border: 1px solid #3A4550;
    border-radius: 3px;
    padding: 4px;
    color: #E8E8E8;
}
QMenu::item {
    padding: 8px 28px;
    border-radius: 3px;
}
QMenu::item:selected {
    background-color: #243342;
    color: #E8E8E8;
}

/* Status Bar */
QStatusBar {
    background-color: #17202A;
    border-top: 1px solid #3A4550;
    padding: 4px;
    color: #7F8C8D;
    font-size: 12px;
}

/* Tool Tips */
QToolTip {
    background-color: #2C3E50;
    color: #E8E8E8;
    border: none;
    border-radius: 3px;
    padding: 6px 10px;
    font-size: 12px;
}

/* Dialogs */
QDialog {
    background-color: #1B2631;
}
QMessageBox {
    background-color: #1B2631;
}
QMessageBox QLabel {
    color: #E8E8E8;
}
QMessageBox QPushButton {
    min-width: 85px;
}

/* Calendar Widget */
QCalendarWidget {
    background-color: #17202A;
    border: 1px solid #3A4550;
    border-radius: 3px;
    color: #E8E8E8;
}
QCalendarWidget QAbstractItemView:enabled {
    background-color: #17202A;
    color: #E8E8E8;
    selection-background-color: #5D6D7E;
    selection-color: white;
    font-size: 11px;
}
QCalendarWidget QAbstractItemView QWidget {
    padding: 0px;
}
QCalendarWidget QTableView {
    background-color: #17202A;
    border: none;
    selection-background-color: #5D6D7E;
    selection-color: white;
}
QCalendarWidget QTableView::item {
    padding: 0px;
    border: none;
}
QCalendarWidget QToolButton {
    color: #E8E8E8;
    background-color: #1B2631;
    border-radius: 3px;
    padding: 4px;
    border: 1px solid transparent;
}
QCalendarWidget QToolButton:hover {
    background-color: #243342;
    border: 1px solid #3A4550;
}
QCalendarWidget QMenu {
    background-color: #17202A;
    border: 1px solid #3A4550;
}
QCalendarWidget QSpinBox {
    background-color: #1F2D3D;
    border: 1px solid #3A4550;
    border-radius: 3px;
    color: #E8E8E8;
}

/* List Widgets */
QListWidget, QListView {
    background-color: #17202A;
    border: 1px solid #3A4550;
    border-radius: 3px;
    outline: none;
    color: #E8E8E8;
}
QListWidget::item, QListView::item {
    padding: 8px;
    border-bottom: 1px solid #2E4053;
}
QListWidget::item:selected, QListView::item:selected {
    background-color: #2E4053;
    color: #E8E8E8;
}
QListWidget::item:hover, QListView::item:hover {
    background-color: #243342;
}

/* Slider */
QSlider::groove:horizontal {
    background-color: #2E4053;
    height: 6px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background-color: #5D6D7E;
    width: 16px;
    margin: -5px 0;
    border-radius: 3px;
}
QSlider::handle:horizontal:hover {
    background-color: #707B8C;
}
"""


def apply_modern_theme(app=None, theme_name="✨ Modern Light"):
    """
    Применяет современный строгий стиль ко всем виджетам приложения

    Args:
        app: экземпляр QApplication
        theme_name: название темы ("✨ Modern Light" или "🌙 Modern Dark")
    """
    if app is None:
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

    # Определяем тип темы по названию
    if 'Dark' in theme_name or 'dark' in theme_name:
        app.setStyleSheet(DARK_THEME)
    else:
        app.setStyleSheet(LIGHT_THEME)

    # Устанавливаем шрифты по умолчанию
    font = QFont("Segoe UI", 13)
    app.setFont(font)

    return app