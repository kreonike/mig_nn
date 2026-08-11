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
    # Создаем индексы для максимального ускорения выборки на стороне SQLite
    conn.execute(
        'CREATE INDEX IF NOT EXISTS "idx_клиенты_фио" ON "Клиенты" ("Фамилия", "Имя", "Отчество");'
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS "idx_клиенты_паспорт" ON "Клиенты" ("СерПасп", "ПспНом");'
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS "idx_клиенты_рождение" ON "Клиенты" ("ДатаРождения");'
    )
    return conn


# ==============================================================================
# 1. РАБОТА С ПАЦИЕНТАМИ (КЛИЕНТАМИ)
# ==============================================================================

def search_clients_for_completer(
        query: str, limit: int = 100
) -> List[Dict[str, Any]]:
    """Высокоскоростной SQL-поиск без полной выгрузки таблицы в Python."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        raw_q = str(query or "").strip()
        clean_q = raw_q.lower()

        if not clean_q:
            cursor.execute('SELECT * FROM "Клиенты" LIMIT ?', (limit,))
            return [dict(row) for row in cursor.fetchall()]

        # 1. ПОИСК: Инициалы + Дата (напр. 'сдг11121981', 'сдг 11.12.1981', 'сд11121981')
        match_date = re.match(
            r"^([a-zA-яёЁа-яА-Я]{2,3})[\s\.]*(\d{2})[\.\/]*(\d{2})[\.\/]*(\d{4})$",
            raw_q,
        )

        if match_date:
            inits = match_date.group(1)
            d, m, y = match_date.group(2), match_date.group(3), match_date.group(4)

            f_p = f"{inits[0]}%"
            i_p = f"{inits[1]}%" if len(inits) >= 2 else "%"
            o_p = f"{inits[2]}%" if len(inits) >= 3 else "%"

            d_dot = f"%{d}.{m}.{y}%"
            d_iso = f"%{y}-{m}-{d}%"
            d_raw = f"%{d}{m}{y}%"

            cursor.execute(
                """
                SELECT *
                FROM "Клиенты"
                WHERE ("Фамилия" LIKE ? OR "Фамилия" LIKE ?)
                  AND ("Имя" LIKE ? OR "Имя" LIKE ?)
                  AND ("Отчество" LIKE ? OR "Отчество" LIKE ? OR "Отчество" IS NULL OR "Отчество" = '')
                  AND ("ДатаРождения" LIKE ? OR "ДатаРождения" LIKE ? OR "ДатаРождения" LIKE ?)
                ORDER BY "Фамилия" ASC LIMIT ?
                """,
                (
                    f_p.lower(), f_p.capitalize(),
                    i_p.lower(), i_p.capitalize(),
                    o_p.lower(), o_p.capitalize(),
                    d_dot, d_iso, d_raw,
                    limit
                ),
            )
            rows = [dict(r) for r in cursor.fetchall()]
            if rows:
                return rows

        # 2. ПОИСК: Только инициалы (напр. 'сд' или 'сдг')
        match_inits = re.match(r"^([a-zA-яёЁа-яА-Я]{2,3})$", raw_q)
        if match_inits:
            inits = match_inits.group(1)
            f_p = f"{inits[0]}%"
            i_p = f"{inits[1]}%" if len(inits) >= 2 else "%"

            if len(inits) >= 3:
                o_p = f"{inits[2]}%"
                sql_o = 'AND ("Отчество" LIKE ? OR "Отчество" LIKE ? OR "Отчество" IS NULL OR "Отчество" = \'\')'
                params = (
                    f_p.lower(), f_p.capitalize(),
                    i_p.lower(), i_p.capitalize(),
                    o_p.lower(), o_p.capitalize(),
                    limit
                )
            else:
                sql_o = ""
                params = (
                    f_p.lower(), f_p.capitalize(),
                    i_p.lower(), i_p.capitalize(),
                    limit
                )

            cursor.execute(
                f"""
                SELECT * FROM "Клиенты"
                WHERE ("Фамилия" LIKE ? OR "Фамилия" LIKE ?)
                  AND ("Имя" LIKE ? OR "Имя" LIKE ?)
                  {sql_o}
                ORDER BY "Фамилия" ASC LIMIT ?
                """,
                params,
            )
            rows = [dict(r) for r in cursor.fetchall()]
            if rows:
                return rows

        # 3. ПОИСК: Прямой ввод текста ('соля', паспорта) с приоритетом совпадения с начала
        prefix_low = f"{clean_q}%"
        prefix_cap = f"{raw_q.capitalize()}%"
        anywhere = f"%{raw_q}%"

        cursor.execute(
            """
            SELECT *,
                   CASE
                       WHEN "Фамилия" LIKE ? OR "Фамилия" LIKE ? THEN 1
                       WHEN "Имя" LIKE ? OR "Имя" LIKE ? THEN 2
                       WHEN "Фамилия" LIKE ? THEN 3
                       ELSE 4
                       END AS match_rank
            FROM "Клиенты"
            WHERE "Фамилия" LIKE ?
               OR "Фамилия" LIKE ?
               OR "Фамилия" LIKE ?
               OR "Имя" LIKE ?
               OR "Отчество" LIKE ?
               OR "ПспНом" LIKE ?
               OR "СерПасп" LIKE ?
            ORDER BY match_rank ASC, "Фамилия" ASC LIMIT ?
            """,
            (
                prefix_low, prefix_cap,
                prefix_low, prefix_cap,
                anywhere,
                prefix_low, prefix_cap, anywhere,
                anywhere, anywhere,
                anywhere, anywhere,
                limit,
            ),
        )
        return [dict(row) for row in cursor.fetchall()]

    except Exception as e:
        print(f"Ошибка поиска клиентов: {e}")
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
                UPDATE "Клиенты"
                SET "Фамилия"           = ?,
                    "Имя"               = ?,
                    "Отчество"          = ?,
                    "Пол"               = ?,
                    "ДатаРождения"      = ?,
                    "СерПасп"           = ?,
                    "ПспНом"            = ?,
                    "ПаспортВыданМесто" = ?,
                    "ДатаВыдачи"        = ?,
                    "Область"           = ?,
                    "Город"             = ?,
                    "Район"             = ?,
                    "Улица"             = ?,
                    "Дом"               = ?,
                    "Квартира"          = ?
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
                INSERT INTO "Клиенты" ("Фамилия", "Имя", "Отчество", "Пол", "ДатаРождения",
                                       "СерПасп", "ПспНом", "ПаспортВыданМесто", "ДатаВыдачи",
                                       "Область", "Город", "Район", "Улица", "Дом", "Квартира")
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def update_client(client_data: Dict[str, Any]) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        street_clean = normalize_street_name(client_data.get("Улица", ""))
        cursor.execute(
            """
            UPDATE "Клиенты"
            SET "Фамилия"           = ?,
                "Имя"               = ?,
                "Отчество"          = ?,
                "Пол"               = ?,
                "ДатаРождения"      = ?,
                "СерПасп"           = ?,
                "ПспНом"            = ?,
                "ПаспортВыданМесто" = ?,
                "ДатаВыдачи"        = ?,
                "Область"           = ?,
                "Город"             = ?,
                "Район"             = ?,
                "Улица"             = ?,
                "Дом"               = ?,
                "Квартира"          = ?
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
                client_data.get("id"),
            ),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка обновления карточки пациента: {e}")
        return False
    finally:
        conn.close()


def get_client_by_id(client_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM "Клиенты" WHERE "id" = ?', (client_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
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
            INSERT INTO "Сделки" ("НомДоговора", "КлиентID", "Дата", "СуммаДоговора",
                                  "Выдана справкаСер", "ВыданаСправка№", "Сроком", "КатегорияТС",
                                  "Примечание", "Психиатр", "Нарколог")
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def save_weapon_deal(deal_data: Dict[str, Any]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO "Справки_Оружие" ("НомДоговора", "КлиентID", "Дата", "СуммаДоговора",
                                          "Справка№", "Примечание", "Психиатр", "Нарколог")
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                deal_data.get("НомДоговора"),
                deal_data.get("КлиентID"),
                deal_data.get("Дата"),
                deal_data.get("СуммаДоговора"),
                deal_data.get("Справка№"),
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