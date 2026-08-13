import os
import shutil
import logging
import sqlite3
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal

# Подключаемся к общему логгеру приложения
logger = logging.getLogger("MIG_NN")


def make_daily_backup(db_path: str, backup_dir: str = "backups"):
    """
    Создает бэкап базы данных строго 1 раз в день.
    Если сегодня бэкап уже делался, функция завершается без действий.
    """
    if not os.path.exists(db_path):
        logger.warning(f"Бекап пропущен: файл базы '{db_path}' не найден.")
        return

    # Создаем папку для бекапов, если ее нет
    os.makedirs(backup_dir, exist_ok=True)

    # Формируем префикс с сегодняшней датой: например "backup_mig_2026-08-11"
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Проверяем, делался ли уже бэкап СЕГОДНЯ
    existing_backups = [f for f in os.listdir(backup_dir) if f.startswith(f"backup_mig_{today_str}")]

    if existing_backups:
        logger.info(f"Дневной бэкап за сегодня ({today_str}) уже существует. Пропускаем.")
        return

    # Если бэкапа за сегодня нет — создаем его через SQLite Backup API
    backup_filename = f"backup_mig_{today_str}.db"
    backup_full_path = os.path.join(backup_dir, backup_filename)

    try:
        # Используем SQLite Backup API для безопасного копирования
        src_conn = sqlite3.connect(db_path)
        dst_conn = sqlite3.connect(backup_full_path)
        
        with src_conn:
            src_conn.backup(dst_conn)
        
        src_conn.close()
        dst_conn.close()
        
        logger.info(f"✅ Успешно создан дневной бэкап: {backup_full_path}")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании бэкапа: {e}", exc_info=True)


class BackupThread(QThread):
    """Поток для выполнения резервного копирования базы данных."""
    backup_complete = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, db_path: str, backup_dir: str = "backups"):
        super().__init__()
        self.db_path = db_path
        self.backup_dir = backup_dir
    
    def run(self):
        """Выполняет бэкап в фоновом потоке."""
        try:
            logger.info(f"Начало бэкапа базы данных: {self.db_path}")
            make_daily_backup(self.db_path, self.backup_dir)
            self.backup_complete.emit(True, "Бэкап успешно выполнен")
        except Exception as e:
            error_msg = f"Ошибка бэкапа: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.backup_complete.emit(False, error_msg)