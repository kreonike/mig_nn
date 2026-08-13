import os
import sqlite3

# Абсолютный путь, не зависящий от того, откуда запущен скрипт
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mig_database.db")
DB_PATH = os.path.abspath(DB_PATH)
print("Использую БД:", DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Кириллица регистрозависима для LIKE в SQLite, поэтому перебираем варианты регистра
cur.execute('''
    SELECT "Фамилия","Имя","Отчество","ДатаРождения"
    FROM "Клиенты"
    WHERE ("Фамилия" LIKE 'с%' OR "Фамилия" LIKE 'С%')
      AND ("Имя" LIKE 'д%' OR "Имя" LIKE 'Д%')
      AND ("Отчество" LIKE 'г%' OR "Отчество" LIKE 'Г%')
    LIMIT 30
''')

rows = cur.fetchall()
print(f"Найдено: {len(rows)}")
for row in rows:
    print(row)

conn.close()