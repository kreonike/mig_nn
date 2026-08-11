import sqlite3

conn = sqlite3.connect("mig_database.db")
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
tables = [row[0] for row in cursor.fetchall()]

print("=== ТАБЛИЦЫ И КОЛОНКИ В BAZA DATA ===")
for t in tables:
    cursor.execute(f"PRAGMA table_info('{t}')")
    cols = [col[1] for col in cursor.fetchall()]
    print(f"Таблица: {t:<20} | Колонки: {cols}")

conn.close()