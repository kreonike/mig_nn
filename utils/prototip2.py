import sys
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView
)
from PyQt6.QtCore import Qt


class ClientSearchApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Учет клиентов — PyQt6")
        self.resize(1000, 600)

        # Главный виджет и компоновка
        main_widget = QWidget()
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

        # Панель поиска
        search_layout = QHBoxLayout()
        search_label = QLabel("Поиск по фамилии:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите минимум 2 символа...")
        self.search_input.textChanged.connect(self.search_clients)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Таблица результатов
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Фамилия", "Имя", "Отчество", "Дата рождения"])

        # Растягиваем колонки по ширине окна
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Настройки таблицы для удобства работы оператора
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)  # Выделять всю строку
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # Только чтение

        layout.addWidget(self.table)

    def search_clients(self, query):
        query = query.strip()
        self.table.setRowCount(0)  # Очистка таблицы

        if len(query) < 2:
            return

        conn = sqlite3.connect("../mig_database.db")
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, Фамилия, Имя, Отчество, ДатаРождения 
            FROM Клиенты 
            WHERE Фамилия LIKE ? 
            LIMIT 50
            """,
            (f"{query}%",)
        )
        rows = cursor.fetchall()
        conn.close()

        # Заполнение таблицы
        self.table.setRowCount(len(rows))
        for row_idx, row_data in enumerate(rows):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value) if value is not None else "")
                # Центрируем ID и Дату рождения
                if col_idx in (0, 4):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_idx, col_idx, item)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ClientSearchApp()
    window.show()
    sys.exit(app.exec())