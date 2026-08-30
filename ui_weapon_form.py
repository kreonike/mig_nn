from datetime import datetime
from PyQt6.QtCore import QDate, QStringListModel, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDateEdit,
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

import database
from ui_print_menu import PrintMenuDialog


class WeaponFormDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔫 Оформление справки на Оружие (Форма 002-О/у)")
        self.resize(1200, 620)
        self.current_client_id = None
        self.found_clients_map = {}
        self._block_search_signal = False
        self.presets_data = []

        self.init_ui()
        self.create_new_deal_number()
        self.setup_shortcuts()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # ---------------- 1. УМНЫЙ ПОИСК ПАЦИЕНТА ----------------
        search_box = QHBoxLayout()
        search_label = QLabel("🔍 Поиск пациента:")
        search_label.setStyleSheet("font-weight: bold;")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "ФИО, паспорт ('соля'), инициалы ('сдг') или с датой ('сдг11121981')..."
        )

        self.completer_model = QStringListModel(self)
        self.completer = QCompleter(self.completer_model, self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchMatch)
        self.search_input.setCompleter(self.completer)

        self.search_input.textEdited.connect(self.on_search_text_edited)
        self.completer.activated.connect(self.on_client_selected)

        btn_clear = QPushButton("✨ Новый пациент (Очистить)")
        btn_clear.clicked.connect(self.clear_patient_fields)

        search_box.addWidget(search_label)
        search_box.addWidget(self.search_input)
        search_box.addWidget(btn_clear)
        main_layout.addLayout(search_box)

        # ---------------- 2. ТРЕХКОЛОНОЧНЫЙ МАКЕТ ----------------
        grid_layout = QGridLayout()

        # === КОЛОНКА 1: ЛИЧНЫЕ ДАННЫЕ ===
        box_personal = QGroupBox("1. Личные данные")
        form_personal = QFormLayout(box_personal)

        self.field_id = QLineEdit()
        self.field_id.setReadOnly(True)
        self.field_id.setPlaceholderText("Авто")

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

        form_personal.addRow("ID:", self.field_id)
        form_personal.addRow("Фамилия:*", self.field_fam)
        form_personal.addRow("Имя:*", self.field_name)
        form_personal.addRow("Отчество:", self.field_otch)
        form_personal.addRow("Пол:", self.field_pol)
        form_personal.addRow("Дата рождения:*", self.field_birth)
        form_personal.addRow("Серия паспорта:", self.field_ser_p)
        form_personal.addRow("Номер паспорта:", self.field_nom_p)

        # === КОЛОНКА 2: АДРЕС И ПАСПОРТ ===
        box_address = QGroupBox("2. Адрес и Паспорт")
        form_address = QFormLayout(box_address)

        self.field_vidan = QComboBox()
        self.field_vidan.setEditable(True)

        self.field_date_vidan = QLineEdit()
        self.field_date_vidan.setInputMask("99.99.9999;_")

        self.field_oblast = QLineEdit("Нижегородская обл.")
        self.field_gorod = QLineEdit("г. Нижний Новгород")

        self.field_rayon = QComboBox()
        self.field_rayon.setEditable(True)

        self.field_ulica = QLineEdit()
        self.field_ulica.setPlaceholderText("Начните вводить улицу...")
        self.setup_street_completer()

        self.field_dom = QLineEdit()
        self.field_kv = QLineEdit()

        form_address.addRow("Кем выдан:", self.field_vidan)
        form_address.addRow("Дата выдачи:", self.field_date_vidan)
        form_address.addRow("Область:", self.field_oblast)
        form_address.addRow("Город:", self.field_gorod)
        form_address.addRow("Район:", self.field_rayon)
        form_address.addRow("Улица:", self.field_ulica)
        form_address.addRow("Дом:", self.field_dom)
        form_address.addRow("Квартира:", self.field_kv)

        # === КОЛОНКА 3: ДЕТАЛИ СПРАВКИ НА ОРУЖИЕ ===
        box_deal = QGroupBox("3. Справка на Оружие")
        form_deal = QFormLayout(box_deal)

        self.field_num_dog = QLineEdit()
        self.field_num_dog.setReadOnly(True)

        self.field_date_dog = QDateEdit()
        self.field_date_dog.setCalendarPopup(True)
        self.field_date_dog.setDate(QDate.currentDate())
        self.field_date_dog.setDisplayFormat("dd.MM.yyyy")

        self.combo_preset = QComboBox()
        self.combo_preset.currentIndexChanged.connect(self.on_preset_changed)

        self.field_summa = QLineEdit("1000")
        self.field_spr_num = QLineEdit()
        self.field_spr_num.setPlaceholderText("Номер бланка 002-О/у")

        chk_layout = QHBoxLayout()
        self.chk_psih = QCheckBox("Психиатр")
        self.chk_psih.setChecked(True)
        self.chk_nark = QCheckBox("Нарколог")
        self.chk_nark.setChecked(True)
        chk_layout.addWidget(self.chk_psih)
        chk_layout.addWidget(self.chk_nark)

        self.field_primech = QTextEdit()
        self.field_primech.setMaximumHeight(80)

        form_deal.addRow("№ Договора:", self.field_num_dog)
        form_deal.addRow("Дата выписки:", self.field_date_dog)
        form_deal.addRow("Тариф / Пресет:", self.combo_preset)
        form_deal.addRow("Сумма (руб):", self.field_summa)
        form_deal.addRow("Справка №:*", self.field_spr_num)
        form_deal.addRow("Врачи:", chk_layout)
        form_deal.addRow("Примечание:", self.field_primech)

        grid_layout.addWidget(box_personal, 0, 0)
        grid_layout.addWidget(box_address, 0, 1)
        grid_layout.addWidget(box_deal, 0, 2)

        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(2, 1)

        main_layout.addLayout(grid_layout)

        self.load_presets()
        self.refresh_combo_boxes()

        # ---------------- 3. НИЖНЯЯ ПАНЕЛЬ С КНОПКАМИ ----------------
        btn_box = QHBoxLayout()
        lbl_hint = QLabel("💡 Ctrl+Enter — сохранить и перейти к печати")
        lbl_hint.setStyleSheet("color: #666; font-style: italic;")

        btn_save_print = QPushButton("💾 Сохранить и Печать (Ctrl+Enter)")
        btn_save_print.setObjectName("primaryButton")
        btn_save_print.setStyleSheet(
            "font-size: 13px; font-weight: bold; padding: 10px 20px;"
        )
        btn_save_print.clicked.connect(self.save_and_print)

        btn_close = QPushButton("Закрыть (Esc)")
        btn_close.clicked.connect(self.reject)

        btn_box.addWidget(lbl_hint)
        btn_box.addStretch()
        btn_box.addWidget(btn_save_print)
        btn_box.addWidget(btn_close)

        main_layout.addLayout(btn_box)

    def setup_street_completer(self):
        streets = database.get_streets_list()
        street_completer = QCompleter(streets, self)
        street_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        street_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.field_ulica.setCompleter(street_completer)

    def load_presets(self):
        self.presets_data = database.get_presets_list("Оружие")
        self.combo_preset.blockSignals(True)
        self.combo_preset.clear()

        for p in self.presets_data:
            name = p.get("Название", "")
            price = p.get("Сумма", 0)
            self.combo_preset.addItem(f"{name} — {int(price)} руб.", p)

        self.combo_preset.addItem("Ручной ввод суммы", None)
        self.combo_preset.blockSignals(False)

    def on_preset_changed(self, index: int):
        data = self.combo_preset.currentData()
        if data:
            self.field_summa.setText(str(int(data.get("Сумма", 1000))))

    def setup_shortcuts(self):
        shortcut_save = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut_save.activated.connect(self.save_and_print)

    def refresh_combo_boxes(self):
        self.field_rayon.clear()
        self.field_rayon.addItems(database.get_districts_list())
        self.field_vidan.clear()
        self.field_vidan.addItems(database.get_uvd_list())

    def parse_and_format_date(self, raw_date_str: str) -> str:
        if not raw_date_str or len(raw_date_str.strip()) < 8:
            return ""
        clean_str = raw_date_str.strip().split()[0]
        if "-" in clean_str:
            parts = clean_str.split("-")
            if len(parts) == 3 and len(parts[0]) == 4:
                return f"{parts[2].zfill(2)}{parts[1].zfill(2)}{parts[0]}"
        if "." in clean_str:
            parts = clean_str.split(".")
            if len(parts) == 3:
                return f"{parts[0].zfill(2)}{parts[1].zfill(2)}{parts[2]}"
        return clean_str

    def create_new_deal_number(self):
        next_id = database.get_next_deal_number("Справки_Оружие")
        self.field_num_dog.setText(str(next_id))
        self.field_spr_num.clear()

    def on_search_text_edited(self, text: str):
        """Умный поиск пациентов через единый алгоритм database.search_clients_for_completer."""
        if self._block_search_signal:
            return
        query = text.strip()
        if not query:
            self.completer_model.setStringList([])
            return

        self._block_search_signal = True
        results = database.search_clients_for_completer(query, limit=50)
        self.found_clients_map.clear()
        suggestions = []

        for c in results:
            fam = c.get("Фамилия") or ""
            nam = c.get("Имя") or ""
            otch = c.get("Отчество") or ""
            birth = str(c.get("ДатаРождения") or "")
            passport = f"{c.get('СерПасп') or ''} {c.get('ПспНом') or ''}".strip()

            display_text = f"{fam} {nam} {otch} ({birth}) [Паспорт: {passport}]".strip()
            suggestions.append(display_text)
            self.found_clients_map[display_text] = c

        self.completer_model.setStringList(suggestions)
        self.completer.complete()
        self._block_search_signal = False

    def on_client_selected(self, selected_text: str):
        client = self.found_clients_map.get(selected_text)
        if client:
            self.fill_client_data(client)

    def set_combo_value(self, combo: QComboBox, text_val: str):
        idx = combo.findText(text_val)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            combo.setCurrentText(text_val)

    def fill_client_data(self, c: dict):
        self.current_client_id = c["id"]
        self.field_id.setText(str(c["id"]))
        self.field_fam.setText(str(c.get("Фамилия") or ""))
        self.field_name.setText(str(c.get("Имя") or ""))
        self.field_otch.setText(str(c.get("Отчество") or ""))

        raw_birth = str(c.get("ДатаРождения") or "")
        self.field_birth.setText(self.parse_and_format_date(raw_birth))

        self.field_ser_p.setText(str(c.get("СерПасп") or ""))
        self.field_nom_p.setText(str(c.get("ПспНом") or ""))

        self.set_combo_value(
            self.field_vidan, str(c.get("ПаспортВыданМесто") or "")
        )
        self.field_date_vidan.setText(
            self.parse_and_format_date(str(c.get("ДатаВыдачи") or ""))
        )

        self.field_oblast.setText(str(c.get("Область") or "Нижегородская обл."))
        self.field_gorod.setText(str(c.get("Город") or "г. Нижний Новгород"))
        self.set_combo_value(self.field_rayon, str(c.get("Район") or ""))

        self.field_ulica.setText(str(c.get("Улица") or ""))
        self.field_dom.setText(str(c.get("Дом") or ""))
        self.field_kv.setText(str(c.get("Квартира") or ""))

        deal = database.get_latest_deal_info(c["id"], "Справки_Оружие")
        if deal and (deal.get("НомДоговора") or deal.get("Справка№")):
            self.field_num_dog.setText(
                str(deal.get("НомДоговора") or deal.get("Справка№"))
            )
            self.field_summa.setText(str(deal.get("СуммаДоговора") or "1000"))
            self.field_spr_num.setText(str(deal.get("Справка№") or ""))
        else:
            self.create_new_deal_number()

    def clear_patient_fields(self):
        self.current_client_id = None
        self.search_input.clear()
        self.field_id.clear()
        self.field_fam.clear()
        self.field_name.clear()
        self.field_otch.clear()
        self.field_birth.clear()
        self.field_ser_p.clear()
        self.field_nom_p.clear()
        self.field_vidan.setCurrentIndex(0)
        self.field_date_vidan.clear()
        self.field_rayon.setCurrentIndex(0)
        self.field_ulica.clear()
        self.field_dom.clear()
        self.field_kv.clear()
        self.field_primech.clear()

        self.field_summa.setText("1000")
        self.create_new_deal_number()

    def save_and_print(self):
        if not self.field_fam.text().strip():
            QMessageBox.warning(self, "Ошибка", "Заполните Фамилию пациента!")
            self.field_fam.setFocus()
            return

        client_data = {
            "id": self.current_client_id,
            "Фамилия": self.field_fam.text().strip(),
            "Имя": self.field_name.text().strip(),
            "Отчество": self.field_otch.text().strip(),
            "Пол": self.field_pol.currentText(),
            "ДатаРождения": self.field_birth.text().strip(),
            "СерПасп": self.field_ser_p.text().strip(),
            "ПспНом": self.field_nom_p.text().strip(),
            "ПаспортВыданМесто": self.field_vidan.currentText().strip(),
            "ДатаВыдачи": self.field_date_vidan.text().strip(),
            "Область": self.field_oblast.text().strip(),
            "Город": self.field_gorod.text().strip(),
            "Район": self.field_rayon.currentText().strip(),
            "Улица": self.field_ulica.text().strip(),
            "Дом": self.field_dom.text().strip(),
            "Квартира": self.field_kv.text().strip(),
        }
        client_id = database.save_client(client_data)
        client_data["id"] = client_id

        deal_data = {
            "НомДоговора": self.field_num_dog.text().strip(),
            "КлиентID": client_id,
            "Дата": self.field_date_dog.date().toString("dd.MM.yyyy"),
            "СуммаДоговора": self.field_summa.text().strip(),
            "Справка№": self.field_spr_num.text().strip(),
            "Примечание": self.field_primech.toPlainText().strip(),
            "Психиатр": self.chk_psih.isChecked(),
            "Нарколог": self.chk_nark.isChecked(),
        }
        database.save_weapon_deal(deal_data)

        parent_widget = self.parent()
        self.accept()

        print_dialog = PrintMenuDialog(client_data, deal_data, parent_widget)
        print_dialog.exec()