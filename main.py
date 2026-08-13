import sys
import os
import sqlite3
import re
from datetime import datetime
import threading
import time
from collections import defaultdict
import shutil

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView, QTabWidget, QFrame, QFormLayout,
    QComboBox, QTextEdit, QDateEdit, QCheckBox, QScrollArea,
    QGroupBox, QDialog, QDialogButtonBox, QSpinBox, QDoubleSpinBox,
    QGridLayout, QListWidget, QListWidgetItem, QAbstractItemView,
    QStatusBar
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSettings, QDate, QSize
)
from PyQt6.QtGui import (
    QFont, QIcon, QColor, QAction, QShortcut, QKeySequence
)

# Импорт стилей (будет создан отдельно)
try:
    from styles.modern_style import apply_modern_theme
except ImportError:
    def apply_modern_theme(widget, theme_name):
        """Заглушка, если файл стилей еще не создан"""
        pass


class DatabaseManager:
    def __init__(self, db_path="patients.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Таблица пациентов с нормализованными полями для поиска
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                birth_date DATE,
                gender TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                passport_series TEXT,
                passport_number TEXT,
                insurance_policy TEXT,
                search_fio TEXT,
                search_passport TEXT,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Индексы для ускорения поиска
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_fio ON patients(search_fio)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_passport ON patients(search_passport)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_birth_date ON patients(birth_date)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                appointment_date DATETIME,
                doctor_name TEXT,
                department TEXT,
                status TEXT DEFAULT 'Запланирован',
                notes TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medical_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                record_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                diagnosis TEXT,
                treatment TEXT,
                doctor_notes TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients (id)
            )
        ''')

        conn.commit()
        conn.close()

    def normalize_fio(self, fio):
        """Нормализация ФИО для поиска (нижний регистр, удаление лишних пробелов)"""
        if not fio:
            return ""
        return ' '.join(fio.lower().split())

    def normalize_passport(self, series, number):
        """Нормализация паспорта для поиска (только цифры)"""
        result = ""
        if series:
            result += ''.join(filter(str.isdigit, series))
        if number:
            result += ''.join(filter(str.isdigit, number))
        return result

    def add_patient(self, data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        search_fio = self.normalize_fio(data['full_name'])
        search_passport = self.normalize_passport(data.get('passport_series'), data.get('passport_number'))

        cursor.execute('''
            INSERT INTO patients (
                full_name, birth_date, gender, phone, email, 
                address, passport_series, passport_number, 
                insurance_policy, search_fio, search_passport
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['full_name'], data['birth_date'], data['gender'],
            data['phone'], data['email'], data['address'],
            data.get('passport_series'), data.get('passport_number'),
            data.get('insurance_policy'), search_fio, search_passport
        ))

        patient_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return patient_id

    def get_patients(self, search_query=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if search_query and len(search_query) >= 2:
            normalized_query = self.normalize_fio(search_query)
            query = '''
                SELECT * FROM patients 
                WHERE search_fio LIKE ? OR phone LIKE ? OR email LIKE ? OR search_passport LIKE ?
            '''
            search_term = f"%{normalized_query}%"
            cursor.execute(query, (search_term, search_term, search_term, search_term))
        else:
            cursor.execute("SELECT * FROM patients ORDER BY registration_date DESC")

        results = cursor.fetchall()
        conn.close()
        return results

    def get_patient_by_id(self, patient_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        result = cursor.fetchone()
        conn.close()
        return result

    def update_patient(self, patient_id, data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        search_fio = self.normalize_fio(data['full_name'])
        search_passport = self.normalize_passport(data.get('passport_series'), data.get('passport_number'))

        cursor.execute('''
            UPDATE patients SET
                full_name = ?, birth_date = ?, gender = ?, phone = ?,
                email = ?, address = ?, passport_series = ?,
                passport_number = ?, insurance_policy = ?,
                search_fio = ?, search_passport = ?
            WHERE id = ?
        ''', (
            data['full_name'], data['birth_date'], data['gender'],
            data['phone'], data['email'], data['address'],
            data.get('passport_series'), data.get('passport_number'),
            data.get('insurance_policy'), search_fio, search_passport, patient_id
        ))

        conn.commit()
        conn.close()

    def delete_patient(self, patient_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM appointments WHERE patient_id = ?", (patient_id,))
        cursor.execute("DELETE FROM medical_records WHERE patient_id = ?", (patient_id,))
        cursor.execute("DELETE FROM patients WHERE id = ?", (patient_id,))

        conn.commit()
        conn.close()

    def check_duplicate_patient(self, full_name, birth_date, exclude_id=None):
        """Проверка на дубликаты по ФИО и дате рождения"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if exclude_id:
            cursor.execute(
                "SELECT COUNT(*) FROM patients WHERE full_name = ? AND birth_date = ? AND id != ?",
                (full_name, birth_date, exclude_id)
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM patients WHERE full_name = ? AND birth_date = ?",
                (full_name, birth_date)
            )

        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def add_appointment(self, patient_id, appointment_data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO appointments (
                patient_id, appointment_date, doctor_name, 
                department, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            patient_id, appointment_data['date'],
            appointment_data['doctor'], appointment_data['department'],
            appointment_data['status'], appointment_data['notes']
        ))

        appointment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return appointment_id

    def get_appointments_for_patient(self, patient_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM appointments WHERE patient_id = ? ORDER BY appointment_date DESC",
            (patient_id,)
        )
        results = cursor.fetchall()
        conn.close()
        return results

    def get_medical_records_for_patient(self, patient_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM medical_records WHERE patient_id = ? ORDER BY record_date DESC",
            (patient_id,)
        )
        results = cursor.fetchall()
        conn.close()
        return results


class BackupThread(QThread):
    """Фоновый поток для автоматического бэкапа базы данных"""
    backup_finished = pyqtSignal(str)
    backup_error = pyqtSignal(str)

    def __init__(self, db_path, backup_interval=300):
        super().__init__()
        self.db_path = db_path
        self.backup_interval = backup_interval
        self.daemon = True

    def run(self):
        while True:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_dir = "backups"
                os.makedirs(backup_dir, exist_ok=True)
                backup_file = os.path.join(backup_dir, f"backup_{timestamp}.db")

                shutil.copy2(self.db_path, backup_file)

                self.backup_finished.emit(f"Бэкап создан: {backup_file}")

                # Ротация бэкапов (хранить последние 10)
                self.rotate_backups(backup_dir, max_backups=10)

            except Exception as e:
                self.backup_error.emit(f"Ошибка бэкапа: {str(e)}")

            time.sleep(self.backup_interval)

    def rotate_backups(self, backup_dir, max_backups=10):
        """Удаление старых бэкапов"""
        try:
            backups = sorted(
                [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.startswith('backup_')],
                key=os.path.getmtime
            )
            while len(backups) > max_backups:
                os.remove(backups.pop(0))
        except Exception as e:
            self.backup_error.emit(f"Ошибка ротации бэкапов: {str(e)}")


class PatientRegistrationDialog(QDialog):
    def __init__(self, parent=None, patient_data=None):
        super().__init__(parent)
        self.patient_data = patient_data
        self.init_ui()

        if patient_data:
            self.load_patient_data()

    def init_ui(self):
        self.setWindowTitle("Регистрация пациента" if not self.patient_data else "Редактировать пациента")
        self.setModal(True)
        self.setMinimumWidth(500)

        layout = QFormLayout()

        self.full_name_edit = QLineEdit()
        self.birth_date_edit = QDateEdit()
        self.birth_date_edit.setCalendarPopup(True)
        self.birth_date_edit.setDate(QDate.currentDate().addYears(-30))
        self.birth_date_edit.setDisplayFormat("dd.MM.yyyy")

        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["Мужской", "Женский"])

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+7 (___) ___-__-__")

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("example@mail.ru")

        self.address_edit = QTextEdit()
        self.address_edit.setMaximumHeight(60)

        self.passport_series_edit = QLineEdit()
        self.passport_series_edit.setPlaceholderText("0000")
        self.passport_series_edit.setMaxLength(4)

        self.passport_number_edit = QLineEdit()
        self.passport_number_edit.setPlaceholderText("000000")
        self.passport_number_edit.setMaxLength(6)

        self.insurance_policy_edit = QLineEdit()
        self.insurance_policy_edit.setPlaceholderText("000-000-000 00")

        layout.addRow("ФИО*", self.full_name_edit)
        layout.addRow("Дата рождения", self.birth_date_edit)
        layout.addRow("Пол", self.gender_combo)
        layout.addRow("Телефон", self.phone_edit)
        layout.addRow("Email", self.email_edit)
        layout.addRow("Адрес", self.address_edit)
        layout.addRow("Серия паспорта", self.passport_series_edit)
        layout.addRow("Номер паспорта", self.passport_number_edit)
        layout.addRow("Полис ОМС", self.insurance_policy_edit)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)

        layout.addRow(button_box)
        self.setLayout(layout)

    def load_patient_data(self):
        self.full_name_edit.setText(self.patient_data[1])
        if self.patient_data[2]:
            date = QDate.fromString(self.patient_data[2], "yyyy-MM-dd")
            if date.isValid():
                self.birth_date_edit.setDate(date)
        self.gender_combo.setCurrentText(self.patient_data[3] or "")
        self.phone_edit.setText(self.patient_data[4] or "")
        self.email_edit.setText(self.patient_data[5] or "")
        self.address_edit.setPlainText(self.patient_data[6] or "")
        self.passport_series_edit.setText(self.patient_data[7] or "")
        self.passport_number_edit.setText(self.patient_data[8] or "")
        self.insurance_policy_edit.setText(self.patient_data[9] or "")

    def validate_and_accept(self):
        if not self.full_name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Поле ФИО обязательно для заполнения")
            return

        if not self.birth_date_edit.date().isValid():
            QMessageBox.warning(self, "Ошибка", "Некорректная дата рождения")
            return

        self.accept()

    def get_patient_data(self):
        return {
            'full_name': self.full_name_edit.text().strip(),
            'birth_date': self.birth_date_edit.date().toString("yyyy-MM-dd"),
            'gender': self.gender_combo.currentText(),
            'phone': self.phone_edit.text().strip(),
            'email': self.email_edit.text().strip(),
            'address': self.address_edit.toPlainText().strip(),
            'passport_series': self.passport_series_edit.text().strip(),
            'passport_number': self.passport_number_edit.text().strip(),
            'insurance_policy': self.insurance_policy_edit.text().strip()
        }


class AppointmentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Назначить визит")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QFormLayout()

        self.appointment_date = QDateEdit()
        self.appointment_date.setCalendarPopup(True)
        self.appointment_date.setDate(QDate.currentDate())
        self.appointment_date.setDisplayFormat("dd.MM.yyyy HH:mm")

        self.doctor_edit = QLineEdit()
        self.department_edit = QLineEdit()
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Запланирован", "Подтвержден", "Отменен", "Завершен"])
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(60)

        layout.addRow("Дата и время визита", self.appointment_date)
        layout.addRow("Врач", self.doctor_edit)
        layout.addRow("Отделение", self.department_edit)
        layout.addRow("Статус", self.status_combo)
        layout.addRow("Примечания", self.notes_edit)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addRow(button_box)
        self.setLayout(layout)

    def get_appointment_data(self):
        return {
            'date': self.appointment_date.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            'doctor': self.doctor_edit.text().strip(),
            'department': self.department_edit.text().strip(),
            'status': self.status_combo.currentText(),
            'notes': self.notes_edit.toPlainText().strip()
        }


class MedicalRecordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Медицинская карта")
        self.setModal(True)
        self.setMinimumWidth(500)

        layout = QVBoxLayout()

        form_layout = QFormLayout()

        self.diagnosis_edit = QTextEdit()
        self.diagnosis_edit.setMaximumHeight(80)

        self.treatment_edit = QTextEdit()
        self.treatment_edit.setMaximumHeight(80)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(60)

        form_layout.addRow("Диагноз", self.diagnosis_edit)
        form_layout.addRow("Лечение", self.treatment_edit)
        form_layout.addRow("Примечания врача", self.notes_edit)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def get_record_data(self):
        return {
            'diagnosis': self.diagnosis_edit.toPlainText().strip(),
            'treatment': self.treatment_edit.toPlainText().strip(),
            'notes': self.notes_edit.toPlainText().strip()
        }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.selected_patient_id = None

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)

        self.init_ui()
        self.setup_shortcuts()
        self.load_patients()
        self.start_backup_thread()

        settings = QSettings("MedicalApp", "Theme")
        saved_theme = settings.value("theme", "✨ Modern Light")
        self.theme_combo.setCurrentText(saved_theme)
        apply_modern_theme(self, saved_theme)

    def init_ui(self):
        self.setWindowTitle("Медицинская система учета пациентов")
        self.setGeometry(100, 100, 1280, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск по ФИО, телефону или email...")
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.setFocus()
        self.search_input.setMinimumWidth(300)

        self.add_patient_btn = QPushButton("➕ Новый пациент")
        self.edit_patient_btn = QPushButton("✏️ Редактировать")
        self.delete_patient_btn = QPushButton("🗑️ Удалить")
        self.refresh_btn = QPushButton("🔄 Обновить")

        self.theme_combo = QComboBox()
        self.theme_combo.addItems([
            "System Default",
            "✨ Modern Light",
            "🌙 Modern Dark"
        ])
        self.theme_combo.currentTextChanged.connect(self.change_theme)

        header_layout.addWidget(QLabel("Поиск:"))
        header_layout.addWidget(self.search_input, 1)
        header_layout.addWidget(self.add_patient_btn)
        header_layout.addWidget(self.edit_patient_btn)
        header_layout.addWidget(self.delete_patient_btn)
        header_layout.addWidget(self.refresh_btn)
        header_layout.addWidget(QLabel("Тема:"))
        header_layout.addWidget(self.theme_combo)

        main_layout.addLayout(header_layout)

        self.tabs = QTabWidget()

        self.patients_tab = QWidget()
        patients_layout = QVBoxLayout(self.patients_tab)
        patients_layout.setContentsMargins(0, 0, 0, 0)

        self.patients_table = QTableWidget()
        self.patients_table.setColumnCount(9)
        self.patients_table.setHorizontalHeaderLabels([
            "ID", "ФИО", "Дата рождения", "Пол", "Телефон",
            "Email", "Адрес", "Паспорт", "Полис"
        ])
        self.patients_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.patients_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.patients_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.patients_table.setAlternatingRowColors(True)
        self.patients_table.itemSelectionChanged.connect(self.on_patient_selected)
        self.patients_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.patients_table.customContextMenuRequested.connect(self.show_context_menu)

        patients_layout.addWidget(self.patients_table)
        self.tabs.addTab(self.patients_tab, "📋 Пациенты")

        self.details_tab = QWidget()
        details_layout = QVBoxLayout(self.details_tab)
        details_layout.setSpacing(15)

        details_group = QGroupBox("👤 Данные пациента")
        details_form = QFormLayout(details_group)
        details_form.setSpacing(8)

        self.detail_name_label = QLabel("-")
        self.detail_birth_label = QLabel("-")
        self.detail_gender_label = QLabel("-")
        self.detail_phone_label = QLabel("-")
        self.detail_email_label = QLabel("-")
        self.detail_address_label = QLabel("-")
        self.detail_passport_label = QLabel("-")
        self.detail_insurance_label = QLabel("-")

        for label in [self.detail_name_label, self.detail_birth_label,
                      self.detail_gender_label, self.detail_phone_label,
                      self.detail_email_label, self.detail_address_label,
                      self.detail_passport_label, self.detail_insurance_label]:
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        details_form.addRow("ФИО:", self.detail_name_label)
        details_form.addRow("Дата рождения:", self.detail_birth_label)
        details_form.addRow("Пол:", self.detail_gender_label)
        details_form.addRow("Телефон:", self.detail_phone_label)
        details_form.addRow("Email:", self.detail_email_label)
        details_form.addRow("Адрес:", self.detail_address_label)
        details_form.addRow("Паспорт:", self.detail_passport_label)
        details_form.addRow("Полис ОМС:", self.detail_insurance_label)

        details_layout.addWidget(details_group)

        appointments_group = QGroupBox("📅 Назначения")
        appointments_layout = QVBoxLayout(appointments_group)

        self.appointments_list = QListWidget()
        self.appointments_list.setAlternatingRowColors(True)
        self.add_appointment_btn = QPushButton("➕ Добавить назначение")
        self.add_appointment_btn.clicked.connect(self.add_appointment)

        appointments_layout.addWidget(self.appointments_list)
        appointments_layout.addWidget(self.add_appointment_btn)

        details_layout.addWidget(appointments_group)

        records_group = QGroupBox("📝 Медицинские записи")
        records_layout = QVBoxLayout(records_group)

        self.records_list = QListWidget()
        self.records_list.setAlternatingRowColors(True)
        self.add_record_btn = QPushButton("➕ Добавить запись")
        self.add_record_btn.clicked.connect(self.add_medical_record)

        records_layout.addWidget(self.records_list)
        records_layout.addWidget(self.add_record_btn)

        details_layout.addWidget(records_group)

        self.tabs.addTab(self.details_tab, "📊 Детали")

        main_layout.addWidget(self.tabs)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе. Введите минимум 2 символа для поиска.")

        self.add_patient_btn.clicked.connect(self.add_patient)
        self.edit_patient_btn.clicked.connect(self.edit_patient)
        self.delete_patient_btn.clicked.connect(self.delete_patient)
        self.refresh_btn.clicked.connect(self.load_patients)

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(
            lambda: self.search_input.setFocus()
        )
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self.add_patient)
        QShortcut(QKeySequence("Escape"), self).activated.connect(
            lambda: self.search_input.clear()
        )
        QShortcut(QKeySequence("F5"), self).activated.connect(self.load_patients)
        QShortcut(QKeySequence("Delete"), self).activated.connect(self.delete_patient)

    def on_search_text_changed(self):
        search_text = self.search_input.text()

        if len(search_text) < 2:
            self.search_timer.stop()
            self.perform_search()
            if len(search_text) == 1:
                self.status_bar.showMessage("⚠️ Введите минимум 2 символа для поиска")
            elif len(search_text) == 0:
                self.status_bar.showMessage("Готов к работе. Введите минимум 2 символа для поиска.")
        else:
            self.search_timer.start(300)
            self.status_bar.showMessage("🔍 Поиск...")

    def perform_search(self):
        search_query = self.search_input.text()
        self.load_patients(search_query)

        if len(search_query) >= 2:
            count = self.patients_table.rowCount()
            self.status_bar.showMessage(f"Найдено пациентов: {count}")

    def load_patients(self, search_query=None):
        patients = self.db_manager.get_patients(search_query)

        self.patients_table.setRowCount(len(patients))
        self.patients_table.setUpdatesEnabled(False)

        for row_idx, patient in enumerate(patients):
            for col_idx, value in enumerate(patient[1:9], start=0):
                item = QTableWidgetItem(str(value) if value else "-")
                item.setData(Qt.ItemDataRole.UserRole, patient[0])
                self.patients_table.setItem(row_idx, col_idx, item)

        self.patients_table.setUpdatesEnabled(True)

    def on_patient_selected(self):
        selected_items = self.patients_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            patient_id_item = self.patients_table.item(row, 0)
            if patient_id_item:
                self.selected_patient_id = patient_id_item.data(Qt.ItemDataRole.UserRole)
                self.load_patient_details()

    def load_patient_details(self):
        if not self.selected_patient_id:
            return

        patient = self.db_manager.get_patient_by_id(self.selected_patient_id)
        if patient:
            self.detail_name_label.setText(patient[1] or "-")
            self.detail_birth_label.setText(patient[2] or "-")
            self.detail_gender_label.setText(patient[3] or "-")
            self.detail_phone_label.setText(patient[4] or "-")
            self.detail_email_label.setText(patient[5] or "-")
            self.detail_address_label.setText(patient[6] or "-")

            passport_info = ""
            if patient[7] and patient[8]:
                passport_info = f"{patient[7]} {patient[8]}"
            elif patient[7]:
                passport_info = patient[7]
            elif patient[8]:
                passport_info = patient[8]
            self.detail_passport_label.setText(passport_info or "-")

            self.detail_insurance_label.setText(patient[9] or "-")

            appointments = self.db_manager.get_appointments_for_patient(self.selected_patient_id)
            self.appointments_list.clear()
            for appt in appointments:
                item_text = f"{appt[2][:16]} - {appt[4]} ({appt[5]})"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, appt[0])
                self.appointments_list.addItem(item)

            records = self.db_manager.get_medical_records_for_patient(self.selected_patient_id)
            self.records_list.clear()
            for record in records:
                item_text = f"{record[2][:16]} - {record[3][:40] if record[3] else 'Без диагноза'}..."
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, record[0])
                self.records_list.addItem(item)

    def show_context_menu(self, position):
        menu = self.patients_table.createStandardContextMenu()
        menu.addSeparator()

        edit_action = menu.addAction("✏️ Редактировать")
        edit_action.triggered.connect(self.edit_patient)

        delete_action = menu.addAction("🗑️ Удалить")
        delete_action.triggered.connect(self.delete_patient)

        menu.exec_(self.patients_table.viewport().mapToGlobal(position))

    def add_patient(self):
        dialog = PatientRegistrationDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            patient_data = dialog.get_patient_data()

            if self.db_manager.check_duplicate_patient(
                    patient_data['full_name'],
                    patient_data['birth_date']
            ):
                reply = QMessageBox.question(
                    self, "⚠️ Дубликат обнаружен",
                    "Пациент с такими ФИО и датой рождения уже существует.\n\n"
                    "Продолжить регистрацию?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return

            self.db_manager.add_patient(patient_data)
            self.load_patients()
            self.status_bar.showMessage("✅ Пациент успешно добавлен!")

    def edit_patient(self):
        if not self.selected_patient_id:
            QMessageBox.warning(self, "Ошибка", "Выберите пациента для редактирования")
            return

        patient = self.db_manager.get_patient_by_id(self.selected_patient_id)
        if patient:
            dialog = PatientRegistrationDialog(self, patient)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                patient_data = dialog.get_patient_data()

                if self.db_manager.check_duplicate_patient(
                        patient_data['full_name'],
                        patient_data['birth_date'],
                        exclude_id=self.selected_patient_id
                ):
                    reply = QMessageBox.question(
                        self, "⚠️ Дубликат обнаружен",
                        "Пациент с такими данными уже существует.\n\nПродолжить?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        return

                self.db_manager.update_patient(self.selected_patient_id, patient_data)
                self.load_patients()
                self.load_patient_details()
                self.status_bar.showMessage("✅ Данные пациента обновлены!")

    def delete_patient(self):
        if not self.selected_patient_id:
            QMessageBox.warning(self, "Ошибка", "Выберите пациента для удаления")
            return

        reply = QMessageBox.question(
            self, "Подтверждение удаления",
            "Вы уверены, что хотите удалить этого пациента и всю связанную информацию?\n\n"
            "Это действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.db_manager.delete_patient(self.selected_patient_id)
            self.load_patients()
            self.clear_patient_details()
            self.status_bar.showMessage("🗑️ Пациент удален!")

    def clear_patient_details(self):
        self.selected_patient_id = None
        self.detail_name_label.setText("-")
        self.detail_birth_label.setText("-")
        self.detail_gender_label.setText("-")
        self.detail_phone_label.setText("-")
        self.detail_email_label.setText("-")
        self.detail_address_label.setText("-")
        self.detail_passport_label.setText("-")
        self.detail_insurance_label.setText("-")
        self.appointments_list.clear()
        self.records_list.clear()

    def add_appointment(self):
        if not self.selected_patient_id:
            QMessageBox.warning(self, "Ошибка", "Выберите пациента")
            return

        dialog = AppointmentDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            appointment_data = dialog.get_appointment_data()
            self.db_manager.add_appointment(self.selected_patient_id, appointment_data)
            self.load_patient_details()
            self.status_bar.showMessage("✅ Назначение добавлено!")

    def add_medical_record(self):
        if not self.selected_patient_id:
            QMessageBox.warning(self, "Ошибка", "Выберите пациента")
            return

        dialog = MedicalRecordDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            record_data = dialog.get_record_data()

            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO medical_records (
                    patient_id, diagnosis, treatment, doctor_notes
                ) VALUES (?, ?, ?, ?)
            ''', (
                self.selected_patient_id, record_data['diagnosis'],
                record_data['treatment'], record_data['notes']
            ))
            conn.commit()
            conn.close()

            self.load_patient_details()
            self.status_bar.showMessage("✅ Медицинская запись добавлена!")

    def change_theme(self, theme_name):
        apply_modern_theme(self, theme_name)
        settings = QSettings("MedicalApp", "Theme")
        settings.setValue("theme", theme_name)

    def start_backup_thread(self):
        self.backup_thread = BackupThread(self.db_manager.db_path)
        self.backup_thread.backup_finished.connect(
            lambda msg: self.status_bar.showMessage(msg)
        )
        self.backup_thread.backup_error.connect(
            lambda msg: QMessageBox.warning(self, "Ошибка бэкапа", msg)
        )
        self.backup_thread.start()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Медицинская система")
    app.setOrganizationName("MedicalApp")

    apply_modern_theme(app, "✨ Modern Light")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()