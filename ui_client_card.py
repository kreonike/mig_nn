from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

import database


class ClientCardDialog(QDialog):

    def __init__(self, client_id: int, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.setWindowTitle(f"Карточка пациента №{client_id}")
        self.resize(1100, 640)

        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # ---------------- 1. ПЕРСОНАЛЬНЫЕ ДАННЫЕ И АДРЕС ----------------
        box_info = QGroupBox("Персональные данные и Адрес пациента")
        grid = QFormLayout(box_info)

        self.field_fam = QLineEdit()
        self.field_name = QLineEdit()
        self.field_otch = QLineEdit()

        self.field_pol = QComboBox()
        self.field_pol.addItems(["Мужской", "Женский"])

        self.field_birth = QLineEdit()
        self.field_birth.setInputMask("99.99.9999;_")

        self.field_ser_p = QLineEdit()
        self.field_ser_p.setInputMask("99 99;_")

        self.field_nom_p = QLineEdit()
        self.field_nom_p.setInputMask("999999;_")

        self.field_vidan = QComboBox()
        self.field_vidan.setEditable(True)

        self.field_date_vidan = QLineEdit()
        self.field_date_vidan.setInputMask("99.99.9999;_")

        # Отдельные поля адреса
        self.field_oblast = QLineEdit("Нижегородская обл.")
        self.field_gorod = QLineEdit("г. Нижний Новгород")

        self.field_rayon = QComboBox()
        self.field_rayon.setEditable(True)

        self.field_ulica = QLineEdit()
        self.field_ulica.setPlaceholderText("Начните вводить улицу...")
        self.setup_street_completer()

        self.field_dom = QLineEdit()
        self.field_kv = QLineEdit()

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Фамилия:*"))
        row1.addWidget(self.field_fam)
        row1.addWidget(QLabel("Имя:*"))
        row1.addWidget(self.field_name)
        row1.addWidget(QLabel("Отчество:"))
        row1.addWidget(self.field_otch)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Пол:"))
        row2.addWidget(self.field_pol)
        row2.addWidget(QLabel("Дата рождения:*"))
        row2.addWidget(self.field_birth)
        row2.addWidget(QLabel("Паспорт:"))
        row2.addWidget(self.field_ser_p)
        row2.addWidget(self.field_nom_p)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Выдан:"))
        row3.addWidget(self.field_vidan)
        row3.addWidget(QLabel("Дата выдачи:"))
        row3.addWidget(self.field_date_vidan)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Область:"))
        row4.addWidget(self.field_oblast)
        row4.addWidget(QLabel("Город:"))
        row4.addWidget(self.field_gorod)
        row4.addWidget(QLabel("Район:"))
        row4.addWidget(self.field_rayon)

        row5 = QHBoxLayout()
        row5.addWidget(QLabel("Улица:*"))
        row5.addWidget(self.field_ulica)
        row5.addWidget(QLabel("Дом:"))
        row5.addWidget(self.field_dom)
        row5.addWidget(QLabel("Кв:"))
        row5.addWidget(self.field_kv)

        grid.addRow(row1)
        grid.addRow(row2)
        grid.addRow(row3)
        grid.addRow(row4)
        grid.addRow(row5)

        layout.addWidget(box_info)

        # ---------------- 2. ИСТОРИЯ ВЫПИСАННЫХ СПРАВОК ----------------
        box_history = QGroupBox("История справок пациента")
        layout_hist = QVBoxLayout(box_history)

        self.table_deals = QTableWidget()
        self.table_deals.setColumnCount(5)
        self.table_deals.setHorizontalHeaderLabels(
            ["№ Договора", "Тип справки", "Дата", "Номер справки", "Сумма"]
        )
        self.table_deals.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table_deals.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        layout_hist.addWidget(self.table_deals)
        layout.addWidget(box_history)

        # ---------------- 3. КНОПКИ ДЕЙСТВИЙ ----------------
        btn_box = QHBoxLayout()
        btn_save = QPushButton("💾 Сохранить изменения")
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(self.save_changes)

        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)

        btn_box.addWidget(btn_save)
        btn_box.addStretch()
        btn_box.addWidget(btn_close)

        layout.addLayout(btn_box)

    def setup_street_completer(self):
        streets = database.get_streets_list()
        street_completer = QCompleter(streets, self)
        street_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        street_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.field_ulica.setCompleter(street_completer)

    def format_date_to_ru(self, raw_str: str) -> str:
        """Преобразует строку даты из YYYY-MM-DD в DD.MM.YYYY для отображения в интерфейсе."""
        if not raw_str:
            return ""
        clean = str(raw_str).strip().split()[0]
        if "-" in clean:
            parts = clean.split("-")
            if len(parts) == 3 and len(parts[0]) == 4:
                return f"{parts[2].zfill(2)}.{parts[1].zfill(2)}.{parts[0]}"
        return clean

    def format_date_to_iso(self, ru_str: str) -> str:
        """Преобразует дату из DD.MM.YYYY обратно в YYYY-MM-DD для сохранения в БД."""
        clean = str(ru_str).strip().replace("_", "")
        if len(clean) == 10 and "." in clean:
            parts = clean.split(".")
            if len(parts) == 3:
                return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        return clean

    def load_data(self):
        self.field_vidan.clear()
        self.field_vidan.addItems(database.get_uvd_list())
        self.field_rayon.clear()
        self.field_rayon.addItems(database.get_districts_list())

        client = database.get_client_by_id(self.client_id)
        if not client:
            return

        self.field_fam.setText(str(client.get("Фамилия") or ""))
        self.field_name.setText(str(client.get("Имя") or ""))
        self.field_otch.setText(str(client.get("Отчество") or ""))

        pol_text = str(client.get("Пол") or "Мужской")
        self.field_pol.setCurrentText(pol_text)

        # Конвертация дат для корректной работы с маской ввода 99.99.9999
        birth_raw = str(client.get("ДатаРождения") or "")
        self.field_birth.setText(self.format_date_to_ru(birth_raw))

        self.field_ser_p.setText(str(client.get("СерПасп") or ""))
        self.field_nom_p.setText(str(client.get("ПспНом") or ""))

        vidan_text = str(client.get("ПаспортВыданМесто") or "")
        idx_v = self.field_vidan.findText(vidan_text)
        if idx_v >= 0:
            self.field_vidan.setCurrentIndex(idx_v)
        else:
            self.field_vidan.setCurrentText(vidan_text)

        date_vidan_raw = str(client.get("ДатаВыдачи") or "")
        self.field_date_vidan.setText(self.format_date_to_ru(date_vidan_raw))

        self.field_oblast.setText(
            str(client.get("Область") or "Нижегородская обл.")
        )
        self.field_gorod.setText(
            str(client.get("Город") or "г. Нижний Новгород")
        )

        rayon_text = str(client.get("Район") or "")
        idx_r = self.field_rayon.findText(rayon_text)
        if idx_r >= 0:
            self.field_rayon.setCurrentIndex(idx_r)
        else:
            self.field_rayon.setCurrentText(rayon_text)

        self.field_ulica.setText(str(client.get("Улица") or ""))
        self.field_dom.setText(str(client.get("Дом") or ""))
        self.field_kv.setText(str(client.get("Квартира") or ""))

        # Загрузка истории справок
        deals = database.get_client_deals(self.client_id)
        self.table_deals.setRowCount(len(deals))
        for row, d in enumerate(deals):
            self.table_deals.setItem(
                row, 0, QTableWidgetItem(str(d.get("НомДоговора", "")))
            )
            self.table_deals.setItem(
                row, 1, QTableWidgetItem(str(d.get("Тип", "")))
            )
            self.table_deals.setItem(
                row, 2, QTableWidgetItem(self.format_date_to_ru(str(d.get("Дата", ""))))
            )
            self.table_deals.setItem(
                row, 3, QTableWidgetItem(str(d.get("НомерСправки", "")))
            )
            self.table_deals.setItem(
                row, 4, QTableWidgetItem(str(d.get("СуммаДоговора", "")))
            )

    def save_changes(self):
        if not self.field_fam.text().strip():
            QMessageBox.warning(self, "Ошибка", "Фамилия не может быть пустой!")
            return

        client_data = {
            "id": self.client_id,
            "Фамилия": self.field_fam.text().strip(),
            "Имя": self.field_name.text().strip(),
            "Отчество": self.field_otch.text().strip(),
            "Пол": self.field_pol.currentText(),
            "ДатаРождения": self.format_date_to_iso(self.field_birth.text()),
            "СерПасп": self.field_ser_p.text().strip(),
            "ПспНом": self.field_nom_p.text().strip(),
            "ПаспортВыданМесто": self.field_vidan.currentText().strip(),
            "ДатаВыдачи": self.format_date_to_iso(self.field_date_vidan.text()),
            "Область": self.field_oblast.text().strip(),
            "Город": self.field_gorod.text().strip(),
            "Район": self.field_rayon.currentText().strip(),
            "Улица": self.field_ulica.text().strip(),
            "Дом": self.field_dom.text().strip(),
            "Квартира": self.field_kv.text().strip(),
        }

        # Проверяем дубликаты перед сохранением
        duplicate = database.check_duplicate_client(client_data, exclude_id=self.client_id)
        if duplicate:
            reply = QMessageBox.question(
                self,
                "Возможен дубликат",
                f"Найден похожий пациент:\n"
                f"{duplicate['Фамилия']} {duplicate['Имя']} {duplicate.get('Отчество', '')}\n"
                f"Дата рождения: {duplicate.get('ДатаРождения', '')}\n\n"
                f"Продолжить сохранение?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        if database.update_client(client_data):
            QMessageBox.information(
                self, "Успешно", "Данные пациента обновлены!"
            )
            self.accept()
        else:
            QMessageBox.critical(
                self, "Ошибка", "Не удалось сохранить изменения в базе."
            )