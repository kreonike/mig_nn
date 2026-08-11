from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import database


class PresetEditDialog(QDialog):

    def __init__(self, parent=None, preset_data=None):
        super().__init__(parent)
        self.preset_data = preset_data or {}
        self.setWindowTitle(
            "Редактирование тарифа" if preset_data else "Новый тариф"
        )
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.combo_type = QComboBox()
        self.combo_type.addItems(["ГИБДД", "Оружие"])
        if "Тип" in self.preset_data and self.preset_data["Тип"]:
            self.combo_type.setCurrentText(str(self.preset_data["Тип"]))

        self.field_name = QLineEdit(str(self.preset_data.get("Название", "")))
        self.field_cats = QLineEdit(str(self.preset_data.get("Категории", "B")))

        self.field_price = QDoubleSpinBox()
        self.field_price.setRange(0, 100000)
        self.field_price.setSingleStep(100)
        self.field_price.setValue(float(self.preset_data.get("Сумма", 500)))

        layout.addRow("Назначение:", self.combo_type)
        layout.addRow("Название тарифа:", self.field_name)
        layout.addRow("Категории / Метка:", self.field_cats)
        layout.addRow("Цена (руб):", self.field_price)

        btn_box = QHBoxLayout()
        btn_save = QPushButton("💾 Сохранить")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_cancel)
        layout.addRow(btn_box)

    def get_data(self):
        return {
            "type": self.combo_type.currentText(),
            "name": self.field_name.text().strip(),
            "categories": self.field_cats.text().strip(),
            "price": self.field_price.value(),
        }


class ReferencesDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Справочники системы")
        self.resize(850, 550)

        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        # 1. Вкладка "Районы"
        self.tab_districts = QWidget()
        self.init_districts_tab()
        self.tabs.addTab(self.tab_districts, "📍 Районы НН")

        # 2. Вкладка "УВД"
        self.tab_uvd = QWidget()
        self.init_uvd_tab()
        self.tabs.addTab(self.tab_uvd, "🛡️ Отделения УВД")

        # 3. Вкладка "Тарифы и Пресеты"
        self.tab_presets = QWidget()
        self.init_presets_tab()
        self.tabs.addTab(self.tab_presets, "🏷️ Тарифы и Пресеты")

        # 4. Вкладка "Улицы (Очистка дублей)"
        self.tab_streets = QWidget()
        self.init_streets_tab()
        self.tabs.addTab(self.tab_streets, "🏙️ Улицы (Очистка дублей)")

        layout.addWidget(self.tabs)

        btn_layout = QHBoxLayout()
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def init_districts_tab(self):
        layout = QVBoxLayout(self.tab_districts)
        self.table_districts = QTableWidget()
        self.table_districts.setColumnCount(2)
        self.table_districts.setHorizontalHeaderLabels(
            ["ID", "Название района"]
        )
        self.table_districts.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table_districts.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        layout.addWidget(self.table_districts)

        btn_box = QHBoxLayout()
        btn_add = QPushButton("➕ Добавить район")
        btn_add.clicked.connect(self.add_district)
        btn_edit = QPushButton("✏️ Редактировать")
        btn_edit.clicked.connect(self.edit_district)
        btn_del = QPushButton("❌ Удалить выбранный")
        btn_del.clicked.connect(self.delete_district)

        btn_box.addWidget(btn_add)
        btn_box.addWidget(btn_edit)
        btn_box.addWidget(btn_del)
        btn_box.addStretch()
        layout.addLayout(btn_box)

    def init_uvd_tab(self):
        layout = QVBoxLayout(self.tab_uvd)
        self.table_uvd = QTableWidget()
        self.table_uvd.setColumnCount(2)
        self.table_uvd.setHorizontalHeaderLabels(["ID", "Название УВД"])
        self.table_uvd.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table_uvd.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        layout.addWidget(self.table_uvd)

        btn_box = QHBoxLayout()
        btn_add = QPushButton("➕ Добавить УВД")
        btn_add.clicked.connect(self.add_uvd)
        btn_edit = QPushButton("✏️ Редактировать")
        btn_edit.clicked.connect(self.edit_uvd)
        btn_del = QPushButton("❌ Удалить выбранный")
        btn_del.clicked.connect(self.delete_uvd)

        btn_box.addWidget(btn_add)
        btn_box.addWidget(btn_edit)
        btn_box.addWidget(btn_del)
        btn_box.addStretch()
        layout.addLayout(btn_box)

    def init_presets_tab(self):
        layout = QVBoxLayout(self.tab_presets)
        self.table_presets = QTableWidget()
        self.table_presets.setColumnCount(5)
        self.table_presets.setHorizontalHeaderLabels(
            ["ID", "Тип", "Название тарифа", "Категории", "Цена (руб)"]
        )
        self.table_presets.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table_presets.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        layout.addWidget(self.table_presets)

        btn_box = QHBoxLayout()
        btn_add = QPushButton("➕ Добавить тариф")
        btn_add.clicked.connect(self.add_preset)
        btn_edit = QPushButton("✏️ Редактировать")
        btn_edit.clicked.connect(self.edit_preset)
        btn_del = QPushButton("❌ Удалить выбранный")
        btn_del.clicked.connect(self.delete_preset)

        btn_box.addWidget(btn_add)
        btn_box.addWidget(btn_edit)
        btn_box.addWidget(btn_del)
        btn_box.addStretch()
        layout.addLayout(btn_box)

    def init_streets_tab(self):
        layout = QVBoxLayout(self.tab_streets)
        lbl_info = QLabel(
            "💡 Выделите одну или несколько улиц с опечатками (удерживая Shift или Ctrl) и нажмите кнопку ниже, чтобы объединить их в одно правильное название у всех пациентов."
        )
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #0067c0; font-size: 11px;")
        layout.addWidget(lbl_info)

        self.table_streets = QTableWidget()
        self.table_streets.setColumnCount(1)
        self.table_streets.setHorizontalHeaderLabels(["Название улицы в базе"])
        self.table_streets.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )

        # ВКЛЮЧАЕМ МУЛЬТИВЫДЕЛЕНИЕ (Shift/Ctrl)
        self.table_streets.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table_streets.setSelectionMode(
            QTableWidget.SelectionMode.ExtendedSelection
        )

        layout.addWidget(self.table_streets)

        btn_box = QHBoxLayout()
        btn_merge_streets = QPushButton("🔗 Объединить выделенные улицы в одну")
        btn_merge_streets.setObjectName("primaryButton")
        btn_merge_streets.clicked.connect(self.merge_selected_streets)

        btn_box.addWidget(btn_merge_streets)
        btn_box.addStretch()
        layout.addLayout(btn_box)

    def load_data(self):
        try:
            # 1. Районы
            districts = database.get_reference_table("Районы_НН")
            self.table_districts.setRowCount(len(districts))
            for row, d in enumerate(districts):
                keys = list(d.keys())
                self.table_districts.setItem(
                    row, 0, QTableWidgetItem(str(d.get(keys[0], "")))
                )
                self.table_districts.setItem(
                    row,
                    1,
                    QTableWidgetItem(
                        str(d.get(keys[1] if len(keys) > 1 else keys[0], ""))
                    ),
                )

            # 2. УВД
            uvd_list = database.get_reference_table("УВД")
            self.table_uvd.setRowCount(len(uvd_list))
            for row, u in enumerate(uvd_list):
                keys = list(u.keys())
                self.table_uvd.setItem(
                    row, 0, QTableWidgetItem(str(u.get(keys[0], "")))
                )
                self.table_uvd.setItem(
                    row,
                    1,
                    QTableWidgetItem(
                        str(u.get(keys[1] if len(keys) > 1 else keys[0], ""))
                    ),
                )

            # 3. Пресеты
            presets = list(
                {
                    p["id"]: p
                    for p in (
                        database.get_presets_list("ГИБДД")
                        + database.get_presets_list("Оружие")
                    )
                    if "id" in p
                }.values()
            )

            self.table_presets.setRowCount(len(presets))
            for row, p in enumerate(presets):
                self.table_presets.setItem(
                    row, 0, QTableWidgetItem(str(p.get("id", "")))
                )
                self.table_presets.setItem(
                    row, 1, QTableWidgetItem(str(p.get("Тип") or "ГИБДД"))
                )
                self.table_presets.setItem(
                    row, 2, QTableWidgetItem(str(p.get("Название", "")))
                )
                self.table_presets.setItem(
                    row, 3, QTableWidgetItem(str(p.get("Категории", "")))
                )
                self.table_presets.setItem(
                    row,
                    4,
                    QTableWidgetItem(str(int(p.get("Сумма", 0) or 0))),
                )

            # 4. Улицы
            streets = database.get_streets_list()
            self.table_streets.setRowCount(len(streets))
            for row, st in enumerate(streets):
                self.table_streets.setItem(row, 0, QTableWidgetItem(st))

        except Exception as e:
            print(f"Ошибка загрузки справочников: {e}")

    def add_district(self):
        name, ok = QInputDialog.getText(
            self, "Новый район", "Введите название района НН:"
        )
        if ok and name.strip():
            database.add_reference_item("Районы_НН", "НазРайона", name.strip())
            self.load_data()

    def edit_district(self):
        row = self.table_districts.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите район!")
            return
        old_name = self.table_districts.item(row, 1).text()
        new_name, ok = QInputDialog.getText(
            self,
            "Редактирование района",
            "Измените название района:",
            text=old_name,
        )
        if ok and new_name.strip() and new_name.strip() != old_name:
            database.update_reference_item(
                "Районы_НН", "НазРайона", old_name, new_name.strip()
            )
            self.load_data()

    def delete_district(self):
        row = self.table_districts.currentRow()
        if row >= 0:
            name = self.table_districts.item(row, 1).text()
            database.delete_reference_item("Районы_НН", "НазРайона", name)
            self.load_data()

    def add_uvd(self):
        name, ok = QInputDialog.getText(
            self, "Новое УВД", "Введите название отделения УВД:"
        )
        if ok and name.strip():
            database.add_reference_item("УВД", "Название", name.strip())
            self.load_data()

    def edit_uvd(self):
        row = self.table_uvd.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите отделение УВД!")
            return
        old_name = self.table_uvd.item(row, 1).text()
        new_name, ok = QInputDialog.getText(
            self, "Редактирование УВД", "Измените название УВД:", text=old_name
        )
        if ok and new_name.strip() and new_name.strip() != old_name:
            database.update_reference_item(
                "УВД", "Название", old_name, new_name.strip()
            )
            self.load_data()

    def delete_uvd(self):
        row = self.table_uvd.currentRow()
        if row >= 0:
            name = self.table_uvd.item(row, 1).text()
            database.delete_reference_item("УВД", "Название", name)
            self.load_data()

    def add_preset(self):
        dialog = PresetEditDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if data["name"]:
                database.add_preset_item(
                    data["type"], data["name"], data["categories"], data["price"]
                )
                self.load_data()

    def edit_preset(self):
        row = self.table_presets.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите тариф!")
            return
        preset_id = int(self.table_presets.item(row, 0).text())
        preset_data = {
            "id": preset_id,
            "Тип": self.table_presets.item(row, 1).text(),
            "Название": self.table_presets.item(row, 2).text(),
            "Категории": self.table_presets.item(row, 3).text(),
            "Сумма": float(self.table_presets.item(row, 4).text()),
        }
        dialog = PresetEditDialog(self, preset_data)
        if dialog.exec():
            data = dialog.get_data()
            database.update_preset_item(
                preset_id,
                data["type"],
                data["name"],
                data["categories"],
                data["price"],
            )
            self.load_data()

    def delete_preset(self):
        row = self.table_presets.currentRow()
        if row >= 0:
            p_id = int(self.table_presets.item(row, 0).text())
            database.delete_preset_item(p_id)
            self.load_data()

    def merge_selected_streets(self):
        selected_rows = self.table_streets.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(
                self,
                "Внимание",
                "Выделите одну или несколько улиц для объединения!",
            )
            return

        old_streets = [
            self.table_streets.item(r.row(), 0).text() for r in selected_rows
        ]

        # Подставляем наиболее красивый/частый вариант по умолчанию
        default_suggestion = old_streets[0]
        for st in old_streets:
            if "ул." in st or "Коминтерна" in st:
                default_suggestion = st
                break

        new_street, ok = QInputDialog.getText(
            self,
            "Объединение улиц",
            f"Выбрано вариантов: {len(old_streets)}.\nУкажите единое правильное название для всех клиентов:",
            text=default_suggestion,
        )

        if ok and new_street.strip():
            updated_count = database.merge_multiple_streets_in_db(
                old_streets, new_street.strip()
            )
            QMessageBox.information(
                self,
                "Успешно",
                f"Заменено у {updated_count} пациентов!\nВсе варианты объединены в '{new_street.strip()}'.",
            )
            self.load_data()