import sqlite3 # Если вы конвертировали Access в SQLite
# ИЛИ import pyodbc (если читаете напрямую .mdb / .accdb)
import pyodbc

# Для прямого чтения файла .mdb / .accdb:
conn_str = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
    r"DBQ=mig_17.01.2025.mdb;"
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# 1. Посмотрим список всех таблиц в базе Access
for row in cursor.tables(tableType='TABLE'):
    print("Таблица:", row.table_name)

# 2. Выгружаем бинарное содержимое (например, из таблицы "Шаблоны" и колонки "Файл")
cursor.execute("SELECT ИмяФайла, ДанныеФайла FROM Шаблоны")
for row in cursor.fetchall():
    filename, file_data = row[0], row[1]
    if file_data:
        # Сохраняем обратно на диск
        with open(filename, "wb") as f:
            f.write(file_data)
        print(f"Шаблон {filename} успешно сохранен!")

conn.close()