import os
import sqlite3
import pyodbc

# 1. Пути к файлам
access_file = "mig_17.01.2025.mdb"
access_db_path = os.path.abspath(access_file)
sqlite_db_path = os.path.abspath("../mig_database.db")

# Если старая база SQLite существует — удаляем её для чистого импорта
if os.path.exists(sqlite_db_path):
    os.remove(sqlite_db_path)

conn_str = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
    f"DBQ={access_db_path};"
)

# Список основных таблиц
target_tables = [
    "USysAtributs",
    "Врачи",
    "Клиенты",
    "Районы_НН",
    "Сделки",
    "Справки_Оружие",
    "УВД",
]

try:
    # Подключение к Access и SQLite
    access_conn = pyodbc.connect(conn_str)
    access_cursor = access_conn.cursor()

    sqlite_conn = sqlite3.connect(sqlite_db_path)
    sqlite_cursor = sqlite_conn.cursor()

    print("🚀 Начинаем миграцию данных в SQLite...\n")

    for table in target_tables:
        print(f"📦 Перенос таблицы: {table}...")

        # Получаем данные из Access
        access_cursor.execute(f"SELECT * FROM [{table}]")
        rows = access_cursor.fetchall()
        columns_info = access_cursor.description

        col_names = [col[0] for col in columns_info]

        # Преобразуем имена колонок для безопасного SQL (заменяем № и пробелы)
        safe_col_names = [
            f'"{c}"' if (" " in c or "№" in c) else c for c in col_names
        ]

        # Создаем таблицу в SQLite (простое динамическое объявление)
        create_table_sql = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join([f"{col} TEXT" for col in safe_col_names])});'
        sqlite_cursor.execute(create_table_sql)

        # Подготавливаем запрос на вставку
        placeholders = ", ".join(["?"] * len(col_names))
        insert_sql = f'INSERT INTO "{table}" VALUES ({placeholders})'

        # Конвертируем строки (приводим данные к корректным типам Python)
        cleaned_rows = []
        for row in rows:
            cleaned_row = [
                str(val) if val is not None else None for val in row
            ]
            cleaned_rows.append(cleaned_row)

        sqlite_cursor.executemany(insert_sql, cleaned_rows)
        sqlite_conn.commit()
        print(f"   └─ Успешно перенесено записей: {len(cleaned_rows)}")

    access_conn.close()
    sqlite_conn.close()

    print(f"\n✅ Миграция успешно завершена! Создан файл: {sqlite_db_path}")

except Exception as e:
    print(f"\n❌ Ошибка в процессе миграции: {e}")