import json
import logging
import os
import re
import ssl
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QThread, Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon
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
from backup import BackupThread
from styles.modern_style import apply_modern_theme, LIGHT_THEME, DARK_THEME
from ui_client_card import ClientCardDialog
from ui_gibdd_form import GibddFormDialog
from ui_references import ReferencesDialog
from ui_stats import StatsDialog

APP_VERSION = "1.2.5"
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
# 🔄 ПОТОК И ДИАЛОГ НАГЛЯДНОГО СКАЧИВАНИЯ ОБНОВЛЕНИЙ
# ==============================================================================

class DownloadThread(QThread):
    progress_changed = pyqtSignal(int, int)  # downloaded_bytes, total_bytes
    download_finished = pyqtSignal(str)     # path to downloaded file
    download_failed = pyqtSignal(str)       # error message

    def __init__(self, download_url, dest_path, expected_hash: Optional[str] = None):
        super().__init__()
        self.download_url = download_url
        self.dest_path = dest_path
        self.expected_hash = expected_hash

    def run(self):
        # Используем стандартный SSL-контекст с проверкой сертификатов
        ssl_context = ssl.create_default_context()

        class CustomRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
                if new_req:
                    new_req.add_header(
                        'User-Agent',
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    )
                return new_req

        try:
            https_handler = urllib.request.HTTPSHandler(context=ssl_context)
            opener = urllib.request.build_opener(CustomRedirectHandler(), https_handler)

            req = urllib.request.Request(
                self.download_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': '*/*'
                }
            )

            with opener.open(req, timeout=30) as response:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                chunk_size = 1024 * 64

                with open(self.dest_path, 'wb') as out_file:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        downloaded += len(chunk)
                        self.progress_changed.emit(downloaded, total_size)

            # Проверяем хеш файла, если он указан
            if self.expected_hash:
                import hashlib
                sha256 = hashlib.sha256()
                with open(self.dest_path, 'rb') as f:
                    for block in iter(lambda: f.read(65536), b''):
                        sha256.update(block)
                actual_hash = sha256.hexdigest()
                if actual_hash != self.expected_hash:
                    os.remove(self.dest_path)
                    self.download_failed.emit(f"Хеш файла не совпадает! Ожидался: {self.expected_hash}, получен: {actual_hash}")
                    return

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
        self.expected_hash = None

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

        self.thread = DownloadThread(download_url, self.dest_path, self.expected_hash)
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

    def parse_version(self, v_str: str) -> tuple:
        """Преобразует строку версии ('1.2.2') в численный кортеж (1, 2, 2)."""
        try:
            return tuple(map(int, re.findall(r'\d+', str(v_str))))
        except Exception:
            return (0, 0, 0)

    def check_updates(self):
        """Проверка наличия обновлений через raw.githubusercontent.com."""
        logger.info("Запуск процедуры проверки обновлений...")

        raw_version_url = "https://raw.githubusercontent.com/kreonike/mig_nn/main/version.json"
        
        # Сначала пробуем стандартный SSL-контекст с проверкой сертификатов
        ssl_context = ssl.create_default_context()
        
        try:
            req = urllib.request.Request(
                raw_version_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            with urllib.request.urlopen(req, context=ssl_context, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    latest_version = data.get('version', '').strip()
                    download_url = data.get('download_url', '').strip()
                    changelog = data.get('changelog', '')
                    file_hash = data.get('sha256', '')  # SHA-256 хеш файла

                    logger.info(f"Получен ответ с сервера. Актуальная версия на GitHub: {latest_version}")

                    if latest_version and self.parse_version(latest_version) > self.parse_version(APP_VERSION):
                        logger.info(f"Найдена новая версия ({latest_version} > {APP_VERSION}).")
                        msg = f"Найдена новая версия: <b>{latest_version}</b>!\nТекущая версия: {APP_VERSION}\n\n"
                        if changelog:
                            msg += f"<b>Что нового:</b>\n{changelog}\n\n"
                        msg += "Хотите обновиться сейчас?"

                        reply = QMessageBox.question(
                            self, "Доступно обновление", msg,
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )

                        if reply == QMessageBox.StandardButton.Yes:
                            self.run_auto_update(download_url, file_hash)
                    else:
                        logger.info("Установлена самая свежая версия программы.")
                        QMessageBox.information(
                            self, "Проверка обновлений",
                            f"У вас установлена самая свежая версия программы ({APP_VERSION})."
                        )
                else:
                    logger.error(f"Сервер вернул статус ответа: {response.status}")
                    raise Exception(f"Код ответа сервера: {response.status}")
        except ssl.SSLCertVerificationError:
            # Для macOS: если нет сертификатов CA, пробуем без проверки (менее безопасно, но работает)
            logger.warning("SSL сертификат не найден, пробуем без проверки (macOS)")
            try:
                insecure_context = ssl._create_unverified_context()
                req = urllib.request.Request(
                    raw_version_url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                )
                with urllib.request.urlopen(req, context=insecure_context, timeout=5) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode('utf-8'))
                        latest_version = data.get('version', '').strip()
                        download_url = data.get('download_url', '').strip()
                        changelog = data.get('changelog', '')
                        file_hash = data.get('sha256', '')

                        logger.info(f"Получен ответ с сервера. Актуальная версия на GitHub: {latest_version}")

                        if latest_version and self.parse_version(latest_version) > self.parse_version(APP_VERSION):
                            logger.info(f"Найдена новая версия ({latest_version} > {APP_VERSION}).")
                            msg = f"Найдена новая версия: <b>{latest_version}</b>!\nТекущая версия: {APP_VERSION}\n\n"
                            if changelog:
                                msg += f"<b>Что нового:</b>\n{changelog}\n\n"
                            msg += "Хотите обновиться сейчас?"

                            reply = QMessageBox.question(
                                self, "Доступно обновление", msg,
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                            )

                            if reply == QMessageBox.StandardButton.Yes:
                                self.run_auto_update(download_url, file_hash)
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
                logger.error(f"Ошибка при проверке обновлений (без SSL): {e}", exc_info=True)
                QMessageBox.warning(self, "Ошибка связи", f"Не удалось проверить обновления.\nПроверьте подключение к интернету.\n({e})")
        except Exception as e:
            logger.error(f"Ошибка при проверке обновлений: {e}", exc_info=True)
            QMessageBox.warning(self, "Ошибка связи", f"Не удалось проверить обновления.\nПроверьте подключение к интернету.\n({e})")

    def run_auto_update(self, download_url: str, expected_hash: str = ""):
        """Скачивает и распаковывает обновление, перезапуская через bat-скрипт."""
        if not getattr(sys, 'frozen', False):
            logger.warning("Попытка запуска автообновления из исходного кода Python.")
            QMessageBox.information(
                self, "Режим разработки",
                "Автообновление работает только в собранной .exe версии программы."
            )
            return

        if not download_url:
            logger.error("Ссылка для скачивания файла пуста!")
            QMessageBox.critical(self, "Ошибка обновления", "Ссылка для скачивания обновления не указана в version.json.")
            return

        progress_dlg = UpdateProgressDialog(download_url, self)
        progress_dlg.expected_hash = expected_hash  # Передаем хеш в диалог
        if progress_dlg.exec() != QDialog.DialogCode.Accepted or not progress_dlg.downloaded_file:
            return

        # Обновляем поток с хешем
        progress_dlg.thread.expected_hash = expected_hash

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
        self.resize(1280, 760)

        self.current_clients = []
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
        self.search_query_cache = ""

        # Запускаем бэкап в фоновом потоке
        self.run_auto_backup()

        self.init_ui()

    def run_auto_backup(self):
        """Выполняет автоматическое резервное копирование базы данных в фоновом потоке."""
        logger.info("Запуск процедуры автоматического бэкапа базы данных в фоне...")
        try:
            db_filename = getattr(database, "DB_NAME", "mig_database.db")
            self.backup_thread = BackupThread(db_filename, backup_dir="backups")
            self.backup_thread.backup_complete.connect(self.on_backup_complete)
            self.backup_thread.start()
            logger.info("Поток бэкапа запущен")
        except Exception as e:
            logger.error(f"Ошибка при запуске бэкапа: {e}", exc_info=True)

    def on_backup_complete(self, success: bool, message: str):
        """Обработчик завершения бэкапа."""
        if success:
            logger.info(message)
        else:
            logger.error(message)

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
        self.combo_theme.addItems(["✨ Modern Light", "🌙 Modern Dark"])
        self.combo_theme.currentTextChanged.connect(self.change_theme)

        top_bar.addWidget(btn_gibdd)
        top_bar.addWidget(btn_references)
        top_bar.addWidget(btn_stats)
        top_bar.addWidget(btn_about)
        top_bar.addStretch()
        top_bar.addWidget(theme_label)
        top_bar.addWidget(self.combo_theme)

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
        self.field_search.setClearButtonEnabled(True)  # Кнопка ✖ для очистки
        self.field_search.textChanged.connect(self.on_search_text_changed)
        self.field_search.setFocus()  # Автофокус на поле поиска

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.field_search)

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
        self.table_clients.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.table_clients.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table_clients.cellDoubleClicked.connect(
            self.on_client_double_clicked
        )

        main_layout.addWidget(self.table_clients)

        self.statusBar().showMessage("Введите данные для поиска")

    def change_theme(self, theme_name: str):
        logger.info(f"Переключение темы оформления на: {theme_name}")
        apply_modern_theme(QApplication.instance(), theme_name)

    def on_search_text_changed(self, text: str):
        """Обрабатывает изменение текста в поле поиска с debounce (задержкой 300 мс)."""
        query = text.strip()

        # Не ищем при пустом запросе или меньше 2 символов
        if len(query) < 2:
            self.display_clients([])
            self.statusBar().showMessage("Введите минимум 2 символа для поиска")
            self.search_timer.stop()
            return

        # Кэшируем запрос и перезапускаем таймер
        self.search_query_cache = query
        self.search_timer.start(300)  # Debounce 300 мс

    def _perform_search(self):
        """Выполняет поиск по кэшированному запросу."""
        query = self.search_query_cache
        logger.info(f"Поиск пациентов по запросу: '{query}'")

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

            # Скрываем ID в UserRole, делаем колонку узкой
            id_item = QTableWidgetItem(str(c["id"]))
            id_item.setData(Qt.ItemDataRole.UserRole, c["id"])
            self.table_clients.setItem(row, 0, id_item)

            self.table_clients.setItem(row, 1, QTableWidgetItem(fio))
            self.table_clients.setItem(row, 2, QTableWidgetItem(birth))
            self.table_clients.setItem(row, 3, QTableWidgetItem(passport))
            self.table_clients.setItem(row, 4, QTableWidgetItem(address))

        # Показываем подсказку при пустом результате
        if not clients:
            self.statusBar().showMessage("Начните вводить запрос для поиска пациентов (минимум 2 символа)")

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
                # Обновляем результаты поиска после редактирования карточки
                self.on_search_text_changed(self.field_search.text())

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


def get_resource_path(relative_path: str) -> str:
    """Возвращает корректный путь к файлам ресурсов в dev и после компиляции PyInstaller."""
    if getattr(sys, 'frozen', False):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def main():
    global _main_window
    logger.info("Инициализация QApplication...")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    app.setStyle("Fusion")

    # Корректное получение пути к иконке в любых режимах
    icon_path = get_resource_path("icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        logger.info(f"Иконка приложения установлена: {icon_path}")
    else:
        logger.warning(f"Файл иконки не найден: {icon_path}")

    apply_modern_theme(app, "✨ Modern Light")

    _main_window = MainWindow()
    _main_window.show()
    logger.info("Главное окно успешно отображено.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()