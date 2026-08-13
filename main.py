import sys
import os
import sqlite3
import re
from datetime import datetime
import threading
import time
from collections import defaultdict

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView, QTabWidget, QFrame, QFormLayout,
    QComboBox, QTextEdit, QDateEdit, QCheckBox, QScrollArea,
    QGroupBox, QDialog, QDialogButtonBox, QSpinBox, QDoubleSpinBox,
    QGridLayout, QListWidget, QListWidgetItem, QAbstractItemView
)
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSettings, QDate
)
from PyQt5.QtGui import (
    QFont, QIcon, QPixmap, QColor, QPainter, QPen, QBrush
)

from styles.modern_style import apply_modern_theme


class DatabaseManager:
    def __init__(self, db_path="patients.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

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
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

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

    def add_patient(self, data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO patients (
                full_name, birth_date, gender, phone, email, 
                address, passport_series, passport_number, 
                insurance_policy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['full_name'], data['birth_date'], data['gender'],
            data['phone'], data['email'], data['address'],
            data['passport_series'], data['passport_number'],
            data['insurance_policy']
        ))

        patient_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return patient_id

    def get_patients(self, search_query=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if search_query:
            query = '''
                SELECT * FROM patients 
                WHERE full_name LIKE ? OR phone LIKE ? OR email LIKE ?
            '''
            search_term = f"%{search_query}%"
            cursor.execute(query, (search_term, search_term, search_term))
        else:
            cursor.execute("SELECT * FROM patients")

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

        cursor.execute('''
            UPDATE patients SET
                full_name = ?, birth_date = ?, gender = ?, phone = ?,
                email = ?, address = ?, passport_series = ?,
                passport_number = ?, insurance_policy = ?
            WHERE id = ?
        ''', (
            data['full_name'], data['birth_date'], data['gender'],
            data['phone'], data['email'], data['address'],
            data['passport_series'], data['passport_number'],
            data['insurance_policy'], patient_id
        ))

        conn.commit()
        conn.close()

    def delete_patient(self, patient_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Delete related appointments and records first
        cursor.execute("DELETE FROM appointments WHERE patient_id = ?", (patient_id,))
        cursor.execute("DELETE FROM medical_records WHERE patient_id = ?", (patient_id,))
        cursor.execute("DELETE FROM patients WHERE id = ?", (patient_id,))

        conn.commit()
        conn.close()

    def check_duplicate_patient(self, full_name, birth_date):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
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
    backup_finished = pyqtSignal(str)
    backup_error = pyqtSignal(str)

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.backup_interval = 300  # 5 minutes

    def run(self):
        while True:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = f"backup_{timestamp}.db"

                import shutil
                shutil.copy2(self.db_manager.db_path, backup_file)

                self.backup_finished.emit(f"Backup created: {backup_file}")

            except Exception as e:
                self.backup_error.emit(f"Backup error: {str(e)}")

            time.sleep(self.backup_interval)


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

        layout = QFormLayout()

        # Personal information
        self.full_name_edit = QLineEdit()
        self.birth_date_edit = QDateEdit()
        self.birth_date_edit.setCalendarPopup(True)
        self.birth_date_edit.setDate(QDate.currentDate().addYears(-30))

        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["Мужской", "Женский"])

        self.phone_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.address_edit = QTextEdit()

        # Document information
        self.passport_series_edit = QLineEdit()
        self.passport_number_edit = QLineEdit()
        self.insurance_policy_edit = QLineEdit()

        layout.addRow("ФИО*", self.full_name_edit)
        layout.addRow("Дата рождения", self.birth_date_edit)
        layout.addRow("Пол", self.gender_combo)
        layout.addRow("Телефон", self.phone_edit)
        layout.addRow("Email", self.email_edit)
        layout.addRow("Адрес", self.address_edit)
        layout.addRow("Серия паспорта", self.passport_series_edit)
        layout.addRow("Номер паспорта", self.passport_number_edit)
        layout.addRow("Полис ОМС", self.insurance_policy_edit)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addRow(button_box)
        self.setLayout(layout)

    def load_patient_data(self):
        self.full_name_edit.setText(self.patient_data[1])
        if self.patient_data[2]:  # birth_date
            date = QDate.fromString(self.patient_data[2], "yyyy-MM-dd")
            self.birth_date_edit.setDate(date)
        self.gender_combo.setCurrentText(self.patient_data[3] or "")
        self.phone_edit.setText(self.patient_data[4] or "")
        self.email_edit.setText(self.patient_data[5] or "")
        self.address_edit.setPlainText(self.patient_data[6] or "")
        self.passport_series_edit.setText(self.patient_data[7] or "")
        self.passport_number_edit.setText(self.patient_data[8] or "")
        self.insurance_policy_edit.setText(self.patient_data[9] or "")

    def get_patient_data(self):
        return {
            'full_name': self.full_name_edit.text(),
            'birth_date': self.birth_date_edit.date().toString("yyyy-MM-dd"),
            'gender': self.gender_combo.currentText(),
            'phone': self.phone_edit.text(),
            'email': self.email_edit.text(),
            'address': self.address_edit.toPlainText(),
            'passport_series': self.passport_series_edit.text(),
            'passport_number': self.passport_number_edit.text(),
            'insurance_policy': self.insurance_policy_edit.text()
        }


class AppointmentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Назначить визит")
        self.setModal(True)

        layout = QFormLayout()

        self.appointment_date = QDateEdit()
        self.appointment_date.setCalendarPopup(True)
        self.appointment_date.setDate(QDate.currentDate())

        self.doctor_edit = QLineEdit()
        self.department_edit = QLineEdit()
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Запланирован", "Подтвержден", "Отменен", "Завершен"])
        self.notes_edit = QTextEdit()

        layout.addRow("Дата визита", self.appointment_date)
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
            'doctor': self.doctor_edit.text(),
            'department': self.department_edit.text(),
            'status': self.status_combo.currentText(),
            'notes': self.notes_edit.toPlainText()
        }


class MedicalRecordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Медицинская карта")
        self.setModal(True)

        layout = QVBoxLayout()

        form_layout = QFormLayout()

        self.diagnosis_edit = QTextEdit()
        self.treatment_edit = QTextEdit()
        self.notes_edit = QTextEdit()

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
            'diagnosis': self.diagnosis_edit.toPlainText(),
            'treatment': self.treatment_edit.toPlainText(),
            'notes': self.notes_edit.toPlainText()
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
        self.load_patients()
        self.start_backup_thread()

        # Load saved theme
        settings = QSettings("MedicalApp", "Theme")
        saved_theme = settings.value("theme", "System Default")
        self.theme_combo.setCurrentText(saved_theme)
        apply_modern_theme(self, saved_theme)

    def init_ui(self):
        self.setWindowTitle("Медицинская система учета пациентов")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)

        # Header
        header_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по ФИО, телефону или email...")
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.setFocus()  # Auto-focus on search field

        self.add_patient_btn = QPushButton("Добавить пациента")
        self.edit_patient_btn = QPushButton("Редактировать")
        self.delete_patient_btn = QPushButton("Удалить")
        self.refresh_btn = QPushButton("Обновить")

        self.theme_combo = QComboBox()
        self.theme_combo.addItems([
            "System Default", "✨ Modern Light", "🌙 Modern Dark"
        ])
        self.theme_combo.currentTextChanged.connect(self.change_theme)

        header_layout.addWidget(QLabel("Поиск:"))
        header_layout.addWidget(self.search_input)
        header_layout.addWidget(self.add_patient_btn)
        header_layout.addWidget(self.edit_patient_btn)
        header_layout.addWidget(self.delete_patient_btn)
        header_layout.addWidget(self.refresh_btn)
        header_layout.addWidget(QLabel("Тема:"))
        header_layout.addWidget(self.theme_combo)

        main_layout.addLayout(header_layout)

        # Tabs
        self.tabs = QTabWidget()

        # Patients tab
        self.patients_tab = QWidget()
        patients_layout = QVBoxLayout(self.patients_tab)

        self.patients_table = QTableWidget()
        self.patients_table.setColumnCount(10)
        self.patients_table.setHorizontalHeaderLabels([
            "ID", "ФИО", "Дата рождения", "Пол", "Телефон",
            "Email", "Адрес", "Паспорт", "Полис", "Дата регистрации"
        ])
        self.patients_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.patients_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.patients_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.patients_table.itemSelectionChanged.connect(self.on_patient_selected)

        patients_layout.addWidget(self.patients_table)
        self.tabs.addTab(self.patients_tab, "Пациенты")

        # Patient details tab
        self.details_tab = QWidget()
        details_layout = QVBoxLayout(self.details_tab)

        # Details group
        details_group = QGroupBox("Данные пациента")
        details_form = QFormLayout(details_group)

        self.detail_name_label = QLabel("-")
        self.detail_birth_label = QLabel("-")
        self.detail_gender_label = QLabel("-")
        self.detail_phone_label = QLabel("-")
        self.detail_email_label = QLabel("-")
        self.detail_address_label = QLabel("-")
        self.detail_passport_label = QLabel("-")
        self.detail_insurance_label = QLabel("-")

        details_form.addRow("ФИО:", self.detail_name_label)
        details_form.addRow("Дата рождения:", self.detail_birth_label)
        details_form.addRow("Пол:", self.detail_gender_label)
        details_form.addRow("Телефон:", self.detail_phone_label)
        details_form.addRow("Email:", self.detail_email_label)
        details_form.addRow("Адрес:", self.detail_address_label)
        details_form.addRow("Паспорт:", self.detail_passport_label)
        details_form.addRow("Полис ОМС:", self.detail_insurance_label)

        details_layout.addWidget(details_group)

        # Appointments section
        appointments_group = QGroupBox("Назначения")
        appointments_layout = QVBoxLayout(appointments_group)

        self.appointments_list = QListWidget()
        self.add_appointment_btn = QPushButton("Добавить назначение")
        self.add_appointment_btn.clicked.connect(self.add_appointment)

        appointments_layout.addWidget(self.appointments_list)
        appointments_layout.addWidget(self.add_appointment_btn)

        details_layout.addWidget(appointments_group)

        # Medical records section
        records_group = QGroupBox("Медицинские записи")
        records_layout = QVBoxLayout(records_group)

        self.records_list = QListWidget()
        self.add_record_btn = QPushButton("Добавить запись")
        self.add_record_btn.clicked.connect(self.add_medical_record)

        records_layout.addWidget(self.records_list)
        records_layout.addWidget(self.add_record_btn)

        details_layout.addWidget(records_group)

        self.tabs.addTab(self.details_tab, "Детали")

        main_layout.addWidget(self.tabs)

        # Connect buttons
        self.add_patient_btn.clicked.connect(self.add_patient)
        self.edit_patient_btn.clicked.connect(self.edit_patient)
        self.delete_patient_btn.clicked.connect(self.delete_patient)
        self.refresh_btn.clicked.connect(self.load_patients)

    def on_search_text_changed(self):
        # Debounce search with 300ms delay
        if len(self.search_input.text()) < 2:
            self.search_timer.stop()
            self.perform_search()
        else:
            self.search_timer.start(300)

    def perform_search(self):
        search_query = self.search_input.text()
        self.load_patients(search_query)

    def load_patients(self, search_query=None):
        patients = self.db_manager.get_patients(search_query)

        self.patients_table.setRowCount(len(patients))

        for row_idx, patient in enumerate(patients):
            for col_idx, value in enumerate(patient):
                item = QTableWidgetItem(str(value) if value else "-")
                self.patients_table.setItem(row_idx, col_idx, item)

        # Set alternating row colors for better readability
        self.patients_table.setAlternatingRowColors(True)

    def on_patient_selected(self):
        selected_items = self.patients_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            patient_id_item = self.patients_table.item(row, 0)
            if patient_id_item:
                self.selected_patient_id = int(patient_id_item.text())
                self.load_patient_details()
                self.tabs.setCurrentIndex(1)  # Switch to details tab

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
            self.detail_address_label.setPlainText(patient[6] or "-")

            passport_info = ""
            if patient[7] and patient[8]:  # series and number
                passport_info = f"{patient[7]} {patient[8]}"
            elif patient[7]:
                passport_info = patient[7]
            elif patient[8]:
                passport_info = patient[8]
            self.detail_passport_label.setText(passport_info or "-")

            self.detail_insurance_label.setText(patient[9] or "-")

            # Load appointments
            appointments = self.db_manager.get_appointments_for_patient(self.selected_patient_id)
            self.appointments_list.clear()
            for appt in appointments:
                item_text = f"{appt[2]} - {appt[4]} ({appt[5]}) - {appt[6]}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, appt[0])  # Store appointment ID
                self.appointments_list.addItem(item)

            # Load medical records
            records = self.db_manager.get_medical_records_for_patient(self.selected_patient_id)
            self.records_list.clear()
            for record in records:
                item_text = f"{record[2][:10]} - {record[3][:50]}..." if record[
                    3] else f"{record[2][:10]} - Без диагноза"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, record[0])  # Store record ID
                self.records_list.addItem(item)

    def add_patient(self):
        dialog = PatientRegistrationDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            patient_data = dialog.get_patient_data()

            # Check for duplicates
            if self.db_manager.check_duplicate_patient(
                    patient_data['full_name'],
                    patient_data['birth_date']
            ):
                reply = QMessageBox.question(
                    self, "Дубликат обнаружен",
                    "Пациент с такими данными уже существует. Продолжить регистрацию?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return

            self.db_manager.add_patient(patient_data)
            self.load_patients()
            QMessageBox.information(self, "Успех", "Пациент успешно добавлен!")

    def edit_patient(self):
        if not self.selected_patient_id:
            QMessageBox.warning(self, "Ошибка", "Выберите пациента для редактирования")
            return

        patient = self.db_manager.get_patient_by_id(self.selected_patient_id)
        if patient:
            dialog = PatientRegistrationDialog(self, patient)
            if dialog.exec_() == QDialog.Accepted:
                patient_data = dialog.get_patient_data()
                self.db_manager.update_patient(self.selected_patient_id, patient_data)
                self.load_patients()
                QMessageBox.information(self, "Успех", "Данные пациента обновлены!")

    def delete_patient(self):
        if not self.selected_patient_id:
            QMessageBox.warning(self, "Ошибка", "Выберите пациента для удаления")
            return

        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите удалить этого пациента и всю связанную информацию?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.db_manager.delete_patient(self.selected_patient_id)
            self.load_patients()
            self.clear_patient_details()
            QMessageBox.information(self, "Успех", "Пациент удален!")

    def clear_patient_details(self):
        self.selected_patient_id = None
        self.detail_name_label.setText("-")
        self.detail_birth_label.setText("-")
        self.detail_gender_label.setText("-")
        self.detail_phone_label.setText("-")
        self.detail_email_label.setText("-")
        self.detail_address_label.setPlainText("-")
        self.detail_passport_label.setText("-")
        self.detail_insurance_label.setText("-")
        self.appointments_list.clear()
        self.records_list.clear()

    def add_appointment(self):
        if not self.selected_patient_id:
            QMessageBox.warning(self, "Ошибка", "Выберите пациента")
            return

        dialog = AppointmentDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            appointment_data = dialog.get_appointment_data()
            self.db_manager.add_appointment(self.selected_patient_id, appointment_data)
            self.load_patient_details()
            QMessageBox.information(self, "Успех", "Назначение добавлено!")

    def add_medical_record(self):
        if not self.selected_patient_id:
            QMessageBox.warning(self, "Ошибка", "Выберите пациента")
            return

        dialog = MedicalRecordDialog(self)
        if dialog.exec_() == QDialog.Accepted:
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
            QMessageBox.information(self, "Успех", "Медицинская запись добавлена!")

    def change_theme(self, theme_name):
        apply_modern_theme(self, theme_name)
        settings = QSettings("MedicalApp", "Theme")
        settings.setValue("theme", theme_name)

    def start_backup_thread(self):
        self.backup_thread = BackupThread(self.db_manager)
        self.backup_thread.backup_finished.connect(
            lambda msg: print(msg)  # Log to console
        )
        self.backup_thread.backup_error.connect(
            lambda msg: print(msg)  # Log to console
        )
        self.backup_thread.start()


def main():
    app = QApplication(sys.argv)

    # Apply modern theme by default
    apply_modern_theme(app, "System Default")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()