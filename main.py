import json
import logging
import os
import ssl
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime

from PyQt6.QtCore import QDate, QThread, Qt, QTimer, pyqtSignal
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
    QProgressBar,
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

APP_VERSION = "1.2.2"
_main_window = None


# ==============================================================================
# 📝 НАСТРОЙКА ЛОГИРОВАНИЯ
# ==============================================================================

def setup_logging():
    """Настройка логирования работы программы в папку logs."""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    log_filename = datetime.now().strftime("app_%Y-%m-%d.log")
    log_filepath = os.path.join(logs_dir, log_filename)

    logger = logging.getLogger("MIG_NN")
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    file_handler = logging.FileHandler(log_filepath, encoding="utf-8")
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info("=" * 60)
    logger.info(f"Запуск МИС МИГ-НН (Версия {APP_VERSION})")
    logger.info(f"Рабочая директория: {base_dir}")
    logger.info(f"Файл лога: {log_filepath}")
    logger.info("=" * 60)

    return logger


logger = setup_logging()


def log_uncaught_exceptions(exctype, value, traceback):
    logger.critical("Неперехваченная критическая ошибка!", exc_info=(exctype, value, traceback))
    sys.__excepthook__(exctype, value, traceback)


sys.excepthook = log_uncaught_exceptions


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


# ==============================================================================
# 🔄 ПОТОК И ДИАЛОГ НАГЛЯДНОГО СКАЧИВАНИЯ ОБНОВЛЕНИЙ
# ==============================================================================

class DownloadThread(QThread):
    progress_changed = pyqtSignal(int, int)  # downloaded_bytes, total_bytes
    download_finished = pyqtSignal(str)     # path to downloaded file
    download_failed = pyqtSignal(str)       # error message

    def __init__(self, download_url, dest_path):
        super().__init__()
        self.download_url = download_url
        self.dest_path = dest_path

    def run(self):
        ssl_context = ssl._create_unverified_context()
        try:
            req = urllib.request.Request(self.download_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                chunk_size = 1024 * 64  # 64 KB chunks

                with open(self.dest_path, 'wb') as out_file:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        downloaded += len(chunk)
                        self.progress_changed.emit(downloaded, total_size)

            self.download_finished.emit(self.dest_path)
        except Exception as e:
            self.download_failed.emit(str(e))


class UpdateProgressDialog(QDialog):
    """Окно с наглядным прогрессом скачивания обновления."""

    def __init__(self, download_url, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Загрузка обновления...")
        self.setFixedSize(420, 160)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)

        self.download_url = download_url
        self.downloaded_file = None

        layout = QVBoxLayout(self)

        self.lbl_status = QLabel("Подготовка к скачиванию...")
        self.lbl_status.setStyleSheet("font-weight: bold;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #0067c0; }")

        self.lbl_details = QLabel("0 MB / 0 MB")
        self.lbl_details.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout.addWidget(self.lbl_status)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.lbl_details)

        is_zip = download_url.lower().endswith(".zip")
        ext = ".zip" if is_zip else ".exe"

        temp_dir = tempfile.gettempdir()
        self.dest_path = os.path.join(temp_dir, f"mig_update_package{ext}")

        self.thread = DownloadThread(download_url, self.dest_path)
        self.thread.progress_changed.connect(self.on_progress)
        self.thread.download_finished.connect(self.on_finished)
        self.thread.download_failed.connect(self.on_failed)
        self.thread.start()

    def on_progress(self, downloaded, total):
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.progress_bar.setValue(percent)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self.lbl_status.setText(f"Загрузка обновления: {percent}%")
            self.lbl_details.setText(f"{mb_downloaded:.1f} MB из {mb_total:.1f} MB")
        else:
            mb_downloaded = downloaded / (1024 * 1024)
            self.lbl_status.setText("Загрузка обновления...")
            self.lbl_details.setText(f"{mb_downloaded:.1f} MB")

    def on_finished(self, downloaded_file):
        self.downloaded_file = downloaded_file
        self.accept()

    def on_failed(self, error_msg):
        logger.error(f"Ошибка загрузки обновления: {error_msg}")
        QMessageBox.critical(self, "Ошибка скачивания", f"Не удалось скачать обновление:\n{error_msg}")
        self.reject()


class AboutDialog(QDialog):
    """Диалоговое окно Информация о программе и проверка обновлений."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("О программе")
        self.setFixedSize(400, 240)

        layout = QVBoxLayout(self)

        title = QLabel("Медицинская информационная система")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #0067c0;")
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
        """Проверка наличия обновлений через raw.githubusercontent.com."""
        logger.info("Запуск процедуры проверки обновлений...")

        raw_version_url = "https://raw.githubusercontent.com/kreonike/mig_nn/main/version.json"
        ssl_context = ssl._create_unverified_context()

        try:
            req = urllib.request.Request(raw_version_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ssl_context, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    latest_version = data.get('version', '').strip()
                    download_url = data.get('download_url', '').strip()
                    changelog = data.get('changelog', '')

                    logger.info(f"Получен ответ с сервера. Актуальная версия на GitHub: {latest_version}")

                    if latest_version and latest_version != APP_VERSION:
                        logger.info(f"Найдена новая версия ({latest_version}). Запрос у пользователя на скачивание.")
                        msg = f"Найдена новая версия: <b>{latest_version}</b>!\nТекущая версия: {APP_VERSION}\n\n"
                        if changelog:
                            msg += f"<b>Что нового:</b>\n{changelog}\n\n"
                        msg += "Хотите обновиться сейчас?"

                        reply = QMessageBox.question(
                            self, "Доступно обновление", msg,
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )

                        if reply == QMessageBox.StandardButton.Yes:
                            self.run_auto_update(download_url)
                    else:
                        logger.info("Установлена самая свежая версия программы.")
                        QMessageBox.information(
                            self, "Проверка обновлений",
                            f"У вас установлена самая свежая версия программы ({APP_VERSION})."
                        )
                else:
                    logger.error(f"Сервер вернул статус ответа: {response.status}")
                    raise Exception(f"Код ответа сервера: {response.status}")
        except Exception as e:
            logger.error(f"Ошибка при проверке обновлений: {e}", exc_info=True)
            QMessageBox.warning(self, "Ошибка связи", f"Не удалось проверить обновления.\nПроверьте подключение к интернету.\n({e})")

    def run_auto_update(self, download_url: str):
        """Скачивает и распаковывает обновление, перезапуская через bat-скрипт."""
        if not getattr(sys, 'frozen', False):
            logger.warning("Попытка запуска автообновления из исходного кода Python.")
            QMessageBox.information(
                self, "Режим разработки",
                "Автообновление работает только в собранной .exe версии программы.\nДля обновления кода используйте git pull."
            )
            return

        if not download_url:
            logger.error("Ссылка для скачивания файла пуста!")
            QMessageBox.critical(self, "Ошибка обновления", "Ссылка для скачивания обновления не указана в version.json.")
            return

        progress_dlg = UpdateProgressDialog(download_url, self)
        if progress_dlg.exec() != QDialog.DialogCode.Accepted or not progress_dlg.downloaded_file:
            return

        downloaded_package = progress_dlg.downloaded_file
        current_exe = sys.executable
        exe_dir = os.path.dirname(current_exe)
        target_exe_tmp = os.path.join(exe_dir, "app_update.tmp")

        try:
            if downloaded_package.lower().endswith(".zip"):
                logger.info("Распаковка ZIP-архива обновления...")
                extract_dir = os.path.join(tempfile.gettempdir(), "mig_extracted")
                os.makedirs(extract_dir, exist_ok=True)

                with zipfile.ZipFile(downloaded_package, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)

                found_exe = None
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file.endswith(".exe") and not file.startswith("unins"):
                            found_exe = os.path.join(root, file)
                            break
                    if found_exe:
                        break

                if not found_exe:
                    raise Exception("В ZIP-архиве обновления не найден файл .exe!")

                import shutil
                shutil.copy2(found_exe, target_exe_tmp)
            else:
                import shutil
                shutil.copy2(downloaded_package, target_exe_tmp)

            bat_file = os.path.join(exe_dir, "update.bat")
            bat_content = f"""@echo off
chcp 1251 > nul
timeout /t 2 /nobreak > nul
move /y "{target_exe_tmp}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
            with open(bat_file, "w", encoding="cp1251") as f:
                f.write(bat_content)

            logger.info("Перезапуск через update.bat...")
            QMessageBox.information(
                self, "Обновление готово",
                "Файлы успешно загружены. Программа перезапустится через 2 секунды."
            )

            subprocess.Popen([bat_file], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            sys.exit(0)

        except Exception as e:
            logger.error(f"Сбой при распаковке или автозамене: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка обновления", f"Сбой обработки файла обновления:\n{e}")


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        logger.info("Инициализация главного окна...")
        self.setWindowTitle("Медицинская информационная система — Справки ГИБДД")
        self.resize(1180, 720)

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300)
        self.search_timer.timeout.connect(self.perform_client_search)

        self.current_clients = []
        self.init_ui()
        self.load_initial_clients()

        self.run_auto_backup()

    def run_auto_backup(self):
        """Выполняет автоматическое резервное копирование базы данных."""
        logger.info("Старт процедуры автоматического бэкапа базы данных...")
        try:
            if hasattr(database, "make_daily_backup"):
                db_filename = getattr(database, "DB_NAME", "mig_database.db")
                database.make_daily_backup(db_filename, backup_dir="backups")
                logger.info("Процедура бэкапа успешно отработала.")
            elif hasattr(database, "create_backup"):
                database.create_backup()
                logger.info("Процедура бэкапа успешно отработала через create_backup.")
            else:
                logger.warning("Метод бэкапа в модуле database не обнаружен.")
        except Exception as e:
            logger.error(f"Ошибка при создании автоматического бэкапа БД: {e}", exc_info=True)

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
        logger.info(f"Переключение темы оформления на: {theme_name}")
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

        logger.info(f"Выполнение поиска пациентов по запросу: '{query}'")
        try:
            results = database.search_clients_for_completer(query, limit=200)
            self.display_clients(results)

            if results:
                self.statusBar().showMessage(f"Найдено пациентов: {len(results)}")
            else:
                self.statusBar().showMessage("Пациенты не найдены")
        except Exception as e:
            logger.error(f"Ошибка при выполнении поиска в базе данных: {e}", exc_info=True)
            self.statusBar().showMessage("Ошибка поиска")

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
            logger.info(f"Открытие карточки пациента ID: {client['id']}")
            dialog = ClientCardDialog(client["id"], self)
            if dialog.exec():
                self.perform_client_search()

    def open_gibdd_form(self):
        logger.info("Открытие формы создания справки ГИБДД...")
        dialog = GibddFormDialog(self)
        dialog.exec()

    def open_references_dialog(self):
        logger.info("Открытие окна справочников...")
        dialog = ReferencesDialog(self)
        dialog.exec()

    def open_stats_dialog(self):
        logger.info("Открытие окна статистики...")
        dialog = StatsDialog(self)
        dialog.exec()

    def open_about_dialog(self):
        logger.info("Открытие окна 'О программе'...")
        dialog = AboutDialog(self)
        dialog.exec()

    def closeEvent(self, event):
        logger.info("Завершение работы приложения...")
        event.accept()


def main():
    global _main_window
    logger.info("Инициализация QApplication...")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    app.setStyle("Fusion")
    app.setStyleSheet(FLUENT_LIGHT_STYLE)

    _main_window = MainWindow()
    _main_window.show()
    logger.info("Главное окно успешно отображено.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()