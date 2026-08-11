import os
import sys
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import database
from ui_client_card import ClientCardDialog
from ui_gibdd_form import GibddFormDialog
from ui_references import ReferencesDialog
from ui_stats import StatsDialog

_main_window = None
APP_VERSION = "1.2.0"

# ==============================================================================
# 🎨 СТИЛИ ОФОРМЛЕНИЯ
# ==============================================================================

FLUENT_LIGHT_STYLE = """
QWidget {
    background-color: #f3f3f3;
    color: #1a1a1a;
    font-family: '.AppleSystemUIFont', BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}
QMainWindow, QDialog, QTabWidget, QTabBar, QScrollArea {
    background-color: #f3f3f3;
    color: #1a1a1a;
}
QLabel {
    background-color: transparent;
    color: #1a1a1a;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #e5e5e5;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    background-color: #ffffff;
    color: #0067c0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    background-color: #ffffff;
    color: #0067c0;
}
QLineEdit, QComboBox, QDateEdit, QTextEdit {
    border: 1px solid #d1d1d1;
    border-bottom: 2px solid #0067c0;
    border-radius: 4px;
    padding: 6px 10px;
    background-color: #ffffff;
    color: #1a1a1a;
    selection-background-color: #0067c0;
    selection-color: #ffffff;
}
QPushButton {
    background-color: #ffffff;
    border: 1px solid #d1d1d1;
    border-radius: 5px;
    padding: 7px 15px;
    font-weight: bold;
    color: #1a1a1a;
}
QPushButton:hover {
    background-color: #e5f3ff;
    border-color: #0067c0;
    color: #0067c0;
}
QPushButton#primaryButton {
    background-color: #0067c0;
    color: #ffffff;
    border: none;
}
QPushButton#primaryButton:hover {
    background-color: #1875d1;
}
QTableWidget, QTableView {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #e5e5e5;
    border-radius: 8px;
    gridline-color: #f3f3f3;
}
QTableWidget::item {
    background-color: #ffffff;
    color: #1a1a1a;
}
QHeaderView::section {
    background-color: #f9f9f9;
    color: #333333;
    padding: 8px;
    font-weight: bold;
    border: none;
    border-bottom: 2px solid #e5e5e5;
}
QTableWidget::item:selected {
    background-color: #0067c0;
    color: #ffffff;
}
QStatusBar {
    background-color: #f3f3f3;
    color: #333333;
}
"""

DARK_EMERALD_STYLE = """
QWidget {
    background-color: #12181f;
    color: #e0e6ed;
    font-family: '.AppleSystemUIFont', BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}
QMainWindow, QDialog, QTabWidget, QTabBar, QScrollArea {
    background-color: #12181f;
    color: #e0e6ed;
}
QLabel {
    background-color: transparent;
    color: #e0e6ed;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #232d38;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 15px;
    background-color: #1a222d;
    color: #00b894;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    background-color: #1a222d;
    color: #00b894;
}
QLineEdit, QComboBox, QDateEdit, QTextEdit {
    border: 1px solid #2c3846;
    border-radius: 6px;
    padding: 6px 10px;
    background-color: #0f141a;
    color: #f1f5f9;
    selection-background-color: #00b894;
    selection-color: #12181f;
}
QPushButton {
    background-color: #232d38;
    border: 1px solid #324050;
    border-radius: 6px;
    padding: 7px 15px;
    font-weight: bold;
    color: #e0e6ed;
}
QPushButton:hover {
    background-color: #2c3846;
    border-color: #00b894;
    color: #00b894;
}
QPushButton#primaryButton {
    background-color: #00b894;
    color: #0a1015;
    border: none;
}
QPushButton#primaryButton:hover {
    background-color: #00dcaf;
}
QTableWidget, QTableView {
    background-color: #1a222d;
    color: #e0e6ed;
    border: 1px solid #232d38;
    gridline-color: #232d38;
}
QTableWidget::item {
    background-color: #1a222d;
    color: #e0e6ed;
}
QHeaderView::section {
    background-color: #12181f;
    color: #8da4be;
    padding: 8px;
    font-weight: bold;
    border-bottom: 2px solid #2c3846;
}
QTableWidget::item:selected {
    background-color: #00b894;
    color: #12181f;
}
QStatusBar {
    background-color: #12181f;
    color: #8da4be;
}
"""


class AboutDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("О программе")
        self.setFixedSize(400, 240)

        layout = QVBoxLayout(self)

        title = QLabel("Медицинская информационная система")
        title.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #0067c0;"
        )
        subtitle = QLabel("Модуль оформления медосвидетельствований (МИГ-НН)")

        ver_label = QLabel(f"<b>Версия программы:</b> {APP_VERSION}")
        dev_label = QLabel("<b>Разработчик:</b> Нижний Новгород")

        btn_check_update = QPushButton("🔄 Проверить обновления")
        btn_check_update.clicked.connect(self.check_updates)

        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addWidget(ver_label)
        layout.addWidget(dev_label)
        layout.addSpacing(15)
        layout.addWidget(btn_check_update)
        layout.addWidget(btn_close)

    def check_updates(self):
        QMessageBox.information(
            self,
            "Проверка обновлений",
            f"У вас установлена самая свежая версия программы ({APP_VERSION}).\nОбновлений не найдено.",
        )


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Медицинская информационная система — Справки ГИБДД")
        self.resize(1180, 720)

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300)
        self.search_timer.timeout.connect(self.perform_client_search)

        self.current_clients = []
        self.init_ui()
        self.load_initial_clients()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # ---------------- 1. ВЕРХНЯЯ ПАНЕЛЬ ----------------
        top_bar = QHBoxLayout()

        btn_gibdd = QPushButton("🚗 Справка ГИБДД")
        btn_gibdd.setObjectName("primaryButton")
        btn_gibdd.clicked.connect(self.open_gibdd_form)

        btn_references = QPushButton("📂 Справочники")
        btn_references.clicked.connect(self.open_references_dialog)

        btn_stats = QPushButton("📊 Статистика")
        btn_stats.clicked.connect(self.open_stats_dialog)

        btn_about = QPushButton("ℹ️ О программе")
        btn_about.clicked.connect(self.open_about_dialog)

        theme_label = QLabel("🎨 Тема:")
        theme_label.setStyleSheet("font-weight: bold;")

        self.combo_theme = QComboBox()
        self.combo_theme.setMinimumWidth(160)
        self.combo_theme.addItems(["☀️ Светлая тема", "🌙 Тёмная тема"])
        self.combo_theme.currentTextChanged.connect(self.change_theme)

        btn_refresh = QPushButton("🔄 Обновить")
        btn_refresh.clicked.connect(self.perform_client_search)

        top_bar.addWidget(btn_gibdd)
        top_bar.addWidget(btn_references)
        top_bar.addWidget(btn_stats)
        top_bar.addWidget(btn_about)
        top_bar.addStretch()
        top_bar.addWidget(theme_label)
        top_bar.addWidget(self.combo_theme)
        top_bar.addWidget(btn_refresh)

        main_layout.addLayout(top_bar)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)

        # ---------------- 2. ПАНЕЛЬ ПОИСКА ----------------
        search_layout = QHBoxLayout()
        search_label = QLabel("Поиск пациентов:")
        search_label.setFont(
            QFont(".AppleSystemUIFont", 11, QFont.Weight.Bold)
        )

        self.field_search = QLineEdit()
        self.field_search.setPlaceholderText(
            "Введите ФИО, Паспорт ('соля'), Инициалы ('сдг') или с Датой ('сдг11121981')..."
        )
        self.field_search.setClearButtonEnabled(True)

        self.field_search.textChanged.connect(self.on_search_text_changed)
        self.field_search.returnPressed.connect(self.perform_client_search)

        btn_search = QPushButton("🔍 Найти")
        btn_search.clicked.connect(self.perform_client_search)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.field_search)
        search_layout.addWidget(btn_search)

        main_layout.addLayout(search_layout)

        # ---------------- 3. ТАБЛИЦА ПАЦИЕНТОВ ----------------
        self.table_clients = QTableWidget()
        self.table_clients.setColumnCount(5)
        self.table_clients.setHorizontalHeaderLabels(
            [
                "ID",
                "ФИО Пациента",
                "Дата Рождения",
                "Паспорт",
                "Адрес проживания",
            ]
        )

        header = self.table_clients.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        self.table_clients.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table_clients.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table_clients.cellDoubleClicked.connect(
            self.on_client_double_clicked
        )

        main_layout.addWidget(self.table_clients)

        self.statusBar().showMessage("Готово к работе")

    def change_theme(self, theme_name: str):
        app = QApplication.instance()
        app.setStyleSheet("")

        if "Светлая" in theme_name:
            app.setStyleSheet(FLUENT_LIGHT_STYLE)
        elif "Тёмная" in theme_name:
            app.setStyleSheet(DARK_EMERALD_STYLE)

    def on_search_text_changed(self, text: str):
        if text.strip():
            self.search_timer.start()
        else:
            self.search_timer.stop()
            self.display_clients([])
            self.statusBar().showMessage("Введите данные для поиска")

    def perform_client_search(self):
        self.search_timer.stop()
        query = self.field_search.text().strip()

        results = database.search_clients_for_completer(query, limit=200)
        self.display_clients(results)

        if results:
            self.statusBar().showMessage(f"Найдено пациентов: {len(results)}")
        else:
            self.statusBar().showMessage("Пациенты не найдены")

    def load_initial_clients(self):
        self.field_search.clear()
        self.display_clients([])
        self.statusBar().showMessage("Введите ФИО или Паспорт для поиска")

    def display_clients(self, clients: list):
        self.current_clients = clients
        self.table_clients.setRowCount(len(clients))

        for row, c in enumerate(clients):
            fio = f"{c.get('Фамилия', '')} {c.get('Имя', '')} {c.get('Отчество', '')}".strip()
            birth_raw = str(c.get("ДатаРождения") or "")
            birth = self.format_date(birth_raw)
            passport = (
                f"{c.get('СерПасп', '')} {c.get('ПспНом', '')}".strip()
            )
            address = f"{c.get('Город', '')}, {c.get('Улица', '')} д.{c.get('Дом', '')} кв.{c.get('Квартира', '')}".strip(
                " ,."
            )

            self.table_clients.setItem(row, 0, QTableWidgetItem(str(c["id"])))
            self.table_clients.setItem(row, 1, QTableWidgetItem(fio))
            self.table_clients.setItem(row, 2, QTableWidgetItem(birth))
            self.table_clients.setItem(row, 3, QTableWidgetItem(passport))
            self.table_clients.setItem(row, 4, QTableWidgetItem(address))

    def format_date(self, raw_str: str) -> str:
        if not raw_str or len(raw_str) < 8:
            return raw_str
        clean = raw_str.split()[0]
        if "-" in clean:
            parts = clean.split("-")
            if len(parts) == 3 and len(parts[0]) == 4:
                return f"{parts[2].zfill(2)}.{parts[1].zfill(2)}.{parts[0]}"
        return clean

    def on_client_double_clicked(self, row: int, col: int):
        if 0 <= row < len(self.current_clients):
            client = self.current_clients[row]
            dialog = ClientCardDialog(client["id"], self)
            if dialog.exec():
                self.perform_client_search()

    def open_gibdd_form(self):
        dialog = GibddFormDialog(self)
        dialog.exec()

    def open_references_dialog(self):
        dialog = ReferencesDialog(self)
        dialog.exec()

    def open_stats_dialog(self):
        dialog = StatsDialog(self)
        dialog.exec()

    def open_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec()


def main():
    global _main_window
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    app.setStyle("Fusion")
    app.setStyleSheet(FLUENT_LIGHT_STYLE)

    _main_window = MainWindow()
    _main_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()