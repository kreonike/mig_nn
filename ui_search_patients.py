from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

import database
from ui_gibdd_form import GibddFormDialog
from ui_weapon_form import WeaponFormDialog


class PatientSearchDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Поиск пациентов и выписка справок")
        self.resize(1200, 700)
        
        # Установка стилей для всего диалога
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                font-size: 13px;
                color: #333;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 13px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #4a90d9;
            }
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: white;
                gridline-color: #e0e0e0;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 6px;
            }
            QTableWidget::item:selected {
                background-color: #4a90d9;
                color: white;
            }
            QHeaderView::section {
                background-color: #4a90d9;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton {
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2a5f8f;
            }
        """)

        # Таймер для задержки быстрого ввода (200 мс)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(200)
        self.search_timer.timeout.connect(self._execute_search)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Поиск
        search_layout = QHBoxLayout()
        search_label = QLabel("🔎 Поиск (ФИО или Паспорт):")
        search_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        search_layout.addWidget(search_label)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Введите минимум 2 символа для начала поиска..."
        )
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.setFocus()
        search_layout.addWidget(self.search_input)

        layout.addLayout(search_layout)

        # Таблица результатов
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Фамилия", "Имя", "Отчество", "Дата рождения", "Паспорт"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

        # Действия по клику
        btn_layout = QHBoxLayout()
        btn_gibdd = QPushButton("🚗 Выписать ГИБДД")
        btn_weapon = QPushButton("🔫 Выписать Оружие")
        
        btn_gibdd.setStyleSheet("background-color: #28a745;")
        btn_weapon.setStyleSheet("background-color: #17a2b8;")

        btn_gibdd.clicked.connect(self.open_gibdd)
        btn_weapon.clicked.connect(self.open_weapon)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_gibdd)
        btn_layout.addWidget(btn_weapon)
        layout.addLayout(btn_layout)

        self.current_results = []

    def on_search_text_changed(self, text: str):
        self.search_timer.start()

    def _execute_search(self):
        query = self.search_input.text().strip()
        if len(query) < 2:
            self.table.setRowCount(0)
            return

        self.current_results = database.search_clients_for_completer(query, limit=150)
        self.table.setRowCount(len(self.current_results))

        for row, c in enumerate(self.current_results):
            passport = f"{c.get('СерПасп') or ''} {c.get('ПспНом') or ''}".strip()
            self.table.setItem(row, 0, QTableWidgetItem(str(c["id"])))
            self.table.setItem(
                row, 1, QTableWidgetItem(str(c.get("Фамилия") or ""))
            )
            self.table.setItem(
                row, 2, QTableWidgetItem(str(c.get("Имя") or ""))
            )
            self.table.setItem(
                row, 3, QTableWidgetItem(str(c.get("Отчество") or ""))
            )
            self.table.setItem(
                row, 4, QTableWidgetItem(str(c.get("ДатаРождения") or ""))
            )
            self.table.setItem(row, 5, QTableWidgetItem(passport))

    def get_selected_client(self):
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        return self.current_results[row]

    def open_gibdd(self):
        client = self.get_selected_client()
        if client:
            dialog = GibddFormDialog(self)
            dialog.fill_client_data(client)
            dialog.exec()

    def open_weapon(self):
        client = self.get_selected_client()
        if client:
            dialog = WeaponFormDialog(self, client_data=client)
            dialog.exec()