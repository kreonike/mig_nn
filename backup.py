import os
import shutil
from datetime import datetime


def make_daily_backup(db_path: str, backup_dir: str = "backups"):
    """
    Создает бэкап базы данных строго 1 раз в день.
    Если сегодня бэкап уже делался, функция завершается без действий.
    """
    if not os.path.exists(db_path):
        print(f"Бекап пропущен: файл базы '{db_path}' не найден.")
        return

    # Создаем папку для бекапов, если ее нет
    os.makedirs(backup_dir, exist_ok=True)

    # Формируем префикс с сегодняшней датой: например "backup_mig_2026-08-07"
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Проверяем, делался ли уже бэкап СЕГОДНЯ любым из ПК
    existing_backups = [f for f in os.listdir(backup_dir) if f.startswith(f"backup_mig_{today_str}")]

    if existing_backups:
        # Сегодня бекап уже создан — ничего не делаем
        return

    # Если бэкапа за сегодня нет — создаем его
    backup_filename = f"backup_mig_{today_str}.db"
    backup_full_path = os.path.join(backup_dir, backup_filename)

    try:
        shutil.copy2(db_path, backup_full_path)
        print(f"✅ Успешно создан дневной бэкап: {backup_full_path}")
    except Exception as e:
        print(f"❌ Ошибка при создании бэкапа: {e}")