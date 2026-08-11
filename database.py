import os
import re
import sqlite3
import sys
from typing import Any, Dict, List, Optional


def get_db_path() -> str:
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "mig_database.db")


DB_NAME = get_db_path()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute(
        'CREATE INDEX IF NOT EXISTS "idx_клиенты_фио" ON "Клиенты" ("Фамилия", "Имя", "Отчество");'
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS "idx_клиенты_паспорт" ON "Клиенты" ("СерПасп", "ПспНом");'
    )
    return conn


def search_clients_for_completer(
    query: str, limit: int = 100
) -> List[Dict[str, Any]]:
    """Поиск клиентов без сторонних SQL-функций."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        raw_q = str(query or "").strip()
        if not raw_q:
            cursor.execute(
                'SELECT * FROM "Клиенты" ORDER BY "Фамилия" ASC LIMIT ?',
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

        # Поиск по совпадению подстроки
        q_like = f"%{raw_q}%"
        cursor.execute(
            """
            SELECT * FROM "Клиенты"
            WHERE "Фамилия" LIKE ? OR "Имя" LIKE ? OR "Отчество" LIKE ?
               OR "ПспНом" LIKE ? OR "СерПасп" LIKE ?
            LIMIT ?
            """,
            (q_like, q_like, q_like, q_like, q_like, limit * 2),
        )
        rows = [dict(r) for r in cursor.fetchall()]

        # Сортировка совпадений прямо в Python: фамилии, начинающиеся на запрос, выходят наверх
        clean_q = raw_q.lower()

        def sort_key(client):
            fam = str(client.get("Фамилия") or "").lower()
            if fam.startswith(clean_q):
                return (0, fam)
            elif clean_q in fam:
                return (1, fam)
            return (2, fam)

        rows.sort(key=sort_key)
        return rows[:limit]

    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return []
    finally:
        conn.close()


def search_clients(query: str, limit: int = 200) -> List[Dict[str, Any]]:
    return search_clients_for_completer(query, limit=limit)


def save_client(client_data: Dict[str, Any]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        client_id = client_data.get("id")
        street_clean = normalize_street_name(client_data.get("Улица", ""))

        if client_id:
            cursor.execute(
                """
                UPDATE "Клиенты" SET
                    "Фамилия" = ?, "Имя" = ?, "Отчество" = ?, "Пол" = ?, "ДатаРождения" = ?,
                    "СерПасп" = ?, "ПспНом" = ?, "ПаспортВыданМесто" = ?, "ДатаВыдачи" = ?,
                    "Область" = ?, "Город" = ?, "Район" = ?, "Улица" = ?, "Дом" = ?, "Квартира" = ?
                WHERE "id" = ?
            """,
                (
                    client_data.get("Фамилия"),
                    client_data.get("Имя"),
                    client_data.get("Отчество"),
                    client_data.get("Пол"),
                    client_data.get("ДатаРождения"),
                    client_data.get("СерПасп"),
                    client_data.get("ПспНом"),
                    client_data.get("ПаспортВыданМесто"),
                    client_data.get("ДатаВыдачи"),
                    client_data.get("Область"),
                    client_data.get("Город"),
                    client_data.get("Район"),
                    street_clean,
                    client_data.get("Дом"),
                    client_data.get("Квартира"),
                    client_id,
                ),
            )
            conn.commit()
            return client_id
        else:
            cursor.execute(
                """
                INSERT INTO "Клиенты" (
                    "Фамилия", "Имя", "Отчество", "Пол", "ДатаРождения",
                    "СерПасп", "ПспНом", "ПаспортВыданМесто", "ДатаВыдачи",
                    "Область", "Город", "Район", "Улица", "Дом", "Квартира"
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    client_data.get("Фамилия"),
                    client_data.get("Имя"),
                    client_data.get("Отчество"),
                    client_data.get("Пол"),
                    client_data.get("ДатаРождения"),
                    client_data.get("СерПасп"),
                    client_data.get("ПспНом"),
                    client_data.get("ПаспортВыданМесто"),
                    client_data.get("ДатаВыдачи"),
                    client_data.get("Область"),
                    client_data.get("Город"),
                    client_data.get("Район"),
                    street_clean,
                    client_data.get("Дом"),
                    client_data.get("Квартира"),
                ),
            )
            conn.commit()
            return cursor.lastrowid
    finally:
        conn.close()


def normalize_street_name(street: str) -> str:
    if not street:
        return ""
    s = street.strip()
    s = re.sub(r"\.([а-яА-Яa-zA-Z])", r". \1", s)
    return re.sub(r"\s+", " ", s).strip()


def get_streets_list() -> List[str]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'SELECT DISTINCT "Улица" FROM "Клиенты" WHERE "Улица" IS NOT NULL AND "Улица" != ""'
        )
        return sorted(
            list(
                set(
                    normalize_street_name(r[0])
                    for r in cursor.fetchall()
                    if r[0]
                )
            )
        )
    finally:
        conn.close()


def get_next_deal_number(table_name: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f'SELECT MAX(CAST("НомДоговора" AS INTEGER)) FROM "{table_name}"')
        res = cursor.fetchone()[0]
        return (res or 0) + 1
    except Exception:
        return 1
    finally:
        conn.close()


def get_latest_deal_info(client_id: int, table_name: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f'SELECT *, ROWID as deal_id FROM "{table_name}" WHERE "КлиентID" = ? ORDER BY ROWID DESC LIMIT 1',
            (client_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_gibdd_deal(deal_data: Dict[str, Any]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO "Сделки" (
                "НомДоговора", "КлиентID", "Дата", "СуммаДоговора",
                "Выдана справкаСер", "ВыданаСправка№", "Сроком", "КатегорияТС",
                "Примечание", "Психиатр", "Нарколог"
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                deal_data.get("НомДоговора"),
                deal_data.get("КлиентID"),
                deal_data.get("Дата"),
                deal_data.get("СуммаДоговора"),
                deal_data.get("Выдана_справкаСер"),
                deal_data.get("ВыданаСправка№"),
                deal_data.get("Сроком"),
                deal_data.get("КатегорияТС"),
                deal_data.get("Примечание"),
                deal_data.get("Психиатр"),
                deal_data.get("Нарколог"),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_districts_list() -> List[str]:
    return ["Автозаводский", "Сормовский", "Нижегородский", "Советский", "Приокский"]


def get_uvd_list() -> List[str]:
    return ["УВД Нижегородского района", "УВД Автозаводского района", "УВД Сормовского района"]


def get_presets_list(preset_type: str = "ГИБДД") -> List[Dict[str, Any]]:
    return [
        {"Название": "Легковые (A, B)", "Категории": "B", "Сумма": 500},
        {"Название": "Грузовые / Автобусы (C, D)", "Категории": "C, D", "Сумма": 1000},
    ]