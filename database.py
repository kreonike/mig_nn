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

    # Регистрируем Python-функцию для ПОЛНОЦЕННОГО перевода кириллицы в нижний регистр в SQLite
    conn.create_function("py_lower", 1, lambda s: str(s).lower() if s is not None else "")

    # Создаем индексы для мгновенного поиска
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
    """Поиск пациентов с гарантированной поддержкой кириллицы и приоритетом совпадения с начала фамилии."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        raw_q = str(query or "").strip()
        clean_q = raw_q.lower()

        if not clean_q:
            cursor.execute(
                'SELECT * FROM "Клиенты" ORDER BY "Фамилия" ASC LIMIT ?',
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

        # 1. Поиск по Инициалам + Дате (например: 'сдг11121981' или 'сдг 11.12.1981')
        pattern_date = re.match(
            r"^([a-zA-яёЁа-яА-Я]{2,3})[\s\.]*(\d{2})[\.\/]*(\d{2})[\.\/]*(\d{4})$",
            raw_q,
        )

        if pattern_date:
            letters = pattern_date.group(1).lower()
            day, month, year = (
                pattern_date.group(2),
                pattern_date.group(3),
                pattern_date.group(4),
            )
            f_init = f"{letters[0]}%" if len(letters) >= 1 else "%"
            i_init = f"{letters[1]}%" if len(letters) >= 2 else "%"
            o_init = f"{letters[2]}%" if len(letters) >= 3 else "%"

            target_date_dot = f"%{day}.{month}.{year}%"
            target_date_iso = f"%{year}-{month}-{day}%"

            cursor.execute(
                """
                SELECT *
                FROM "Клиенты"
                WHERE py_lower("Фамилия") LIKE ?
                  AND py_lower("Имя") LIKE ?
                  AND (py_lower("Отчество") LIKE ? OR "Отчество" IS NULL)
                  AND ("ДатаРождения" LIKE ? OR "ДатаРождения" LIKE ?)
                ORDER BY "Фамилия" ASC LIMIT ?
                """,
                (f_init, i_init, o_init, target_date_dot, target_date_iso, limit),
            )
            rows = [dict(r) for r in cursor.fetchall()]
            if rows:
                return rows

        # 2. Поиск только по Инициалам (например: 'сд' или 'сдг')
        pattern_inits = re.match(r"^([a-zA-яёЁа-яА-Я]{2,3})$", raw_q)
        if pattern_inits:
            letters = pattern_inits.group(1).lower()
            f_init = f"{letters[0]}%" if len(letters) >= 1 else "%"
            i_init = f"{letters[1]}%" if len(letters) >= 2 else "%"
            o_init = f"{letters[2]}%" if len(letters) >= 3 else "%"

            cursor.execute(
                """
                SELECT *
                FROM "Клиенты"
                WHERE py_lower("Фамилия") LIKE ?
                  AND py_lower("Имя") LIKE ?
                  AND (py_lower("Отчество") LIKE ? OR "Отчество" IS NULL)
                ORDER BY "Фамилия" ASC LIMIT ?
                """,
                (f_init, i_init, o_init, limit),
            )
            rows = [dict(r) for r in cursor.fetchall()]
            if rows:
                return rows

        # 3. Поиск по подстроке с ИСПОЛЬЗОВАНИЕМ py_lower ДЛЯ КИРИЛЛИЦЫ
        prefix_q = f"{clean_q}%"
        anywhere_q = f"%{clean_q}%"

        cursor.execute(
            """
            SELECT *,
                   CASE
                       WHEN py_lower("Фамилия") LIKE ?
                           THEN 1 -- Высший приоритет: Фамилия начинается на 'соля%' (Соляник)
                       WHEN py_lower("Имя") LIKE ? THEN 2 -- Имя начинается на 'соля%'
                       WHEN py_lower("Фамилия") LIKE ? THEN 3 -- Содержит 'соля' внутри (Сысолятин)
                       ELSE 4
                       END AS match_rank
            FROM "Клиенты"
            WHERE py_lower("Фамилия") LIKE ?
               OR py_lower("Имя") LIKE ?
               OR py_lower("Отчество") LIKE ?
               OR "ПспНом" LIKE ?
               OR "СерПасп" LIKE ?
            ORDER BY match_rank ASC, "Фамилия" ASC LIMIT ?
            """,
            (
                prefix_q,
                prefix_q,
                anywhere_q,
                anywhere_q,
                anywhere_q,
                anywhere_q,
                anywhere_q,
                anywhere_q,
                limit,
            ),
        )
        return [dict(row) for row in cursor.fetchall()]

    except Exception as e:
        print(f"Ошибка поиска пациентов: {e}")
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


# ==============================================================================
# 2. ОЧИСТКА И НОРМАЛИЗАЦИЯ УЛИЦ
# ==============================================================================

def normalize_street_name(street: str) -> str:
    if not street:
        return ""
    s = street.strip()
    s = re.sub(r"\.([а-яА-Яa-zA-Z])", r". \1", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def get_streets_list() -> List[str]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'SELECT DISTINCT "Улица" FROM "Клиенты" WHERE "Улица" IS NOT NULL AND "Улица" != ""'
        )
        raw_streets = [row[0] for row in cursor.fetchall() if row[0]]

        cleaned_set = set()
        for st in raw_streets:
            norm = normalize_street_name(st)
            if norm:
                cleaned_set.add(norm)

        return sorted(list(cleaned_set))
    except Exception as e:
        print(f"Ошибка получения списка улиц: {e}")
        return []
    finally:
        conn.close()


def replace_street_in_db(old_name: str, new_name: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        new_clean = normalize_street_name(new_name)
        cursor.execute(
            'UPDATE "Клиенты" SET "Улица" = ? WHERE "Улица" = ?',
            (new_clean, old_name),
        )
        updated_count = cursor.rowcount
        conn.commit()
        return updated_count
    finally:
        conn.close()


# ==============================================================================
# 3. РАБОТА СО СПРАВКАМИ И ДОГОВОРАМИ
# ==============================================================================

def get_client_gibdd_certs(client_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT ROWID                                            as id,
                   "НомДоговора",
                   "Дата",
                   "СуммаДоговора",
                   'ГИБДД'                                          AS "Тип",
                   ("Выдана справкаСер" || ' ' || "ВыданаСправка№") AS "НомерСправки",
                   "КатегорияТС",
                   "Примечание"
            FROM "Сделки"
            WHERE "КлиентID" = ?
            ORDER BY ROWID DESC
            """,
            (client_id,),
        )
        return [dict(r) for r in cursor.fetchall()]
    except Exception as e:
        print(f"Ошибка получения справок ГИБДД: {e}")
        return []
    finally:
        conn.close()


def get_client_weapon_certs(client_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT ROWID      as id,
                   "НомДоговора",
                   "Дата",
                   "СуммаДоговора",
                   'Оружие'   AS "Тип",
                   "Справка№" AS "НомерСправки",
                   "Примечание"
            FROM "Справки_Оружие"
            WHERE "КлиентID" = ?
            ORDER BY ROWID DESC
            """,
            (client_id,),
        )
        return [dict(r) for r in cursor.fetchall()]
    except Exception as e:
        print(f"Ошибка получения справок на Оружие: {e}")
        return []
    finally:
        conn.close()


def get_client_deals(client_id: int) -> List[Dict[str, Any]]:
    gibdd = get_client_gibdd_certs(client_id)
    weapon = get_client_weapon_certs(client_id)
    all_deals = gibdd + weapon
    all_deals.sort(key=lambda x: str(x.get("Дата") or ""), reverse=True)
    return all_deals


def get_next_deal_number(table_name: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        col_id = (
            "НомДоговора"
            if table_name in ("Сделки", "Справки_Оружие")
            else "ROWID"
        )
        cursor.execute(
            f'SELECT MAX(CAST("{col_id}" AS INTEGER)) FROM "{table_name}"'
        )
        res = cursor.fetchone()[0]
        return (res or 0) + 1
    except Exception:
        return 1
    finally:
        conn.close()


def get_latest_deal_info(
        client_id: int, table_name: str
) -> Optional[Dict[str, Any]]:
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


# ==============================================================================
# 4. СТАТИСТИКА, СПРАВОЧНИКИ И ТАРИФЫ
# ==============================================================================

def get_statistics_for_period(
        start_date: str, end_date: str
) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    def normalize_date(d_str: str) -> str:
        if not d_str:
            return ""
        d_str = d_str.strip().split()[0]
        if "." in d_str:
            parts = d_str.split(".")
            if len(parts) == 3 and len(parts[2]) == 4:
                return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        return d_str

    norm_start, norm_end = normalize_date(start_date), normalize_date(end_date)
    gibdd_count, gibdd_sum = 0, 0.0
    weapon_count, weapon_sum = 0, 0.0

    try:
        cursor.execute('SELECT Дата, СуммаДоговора FROM "Сделки"')
        for row in cursor.fetchall():
            d_val = normalize_date(str(row[0] or ""))
            if norm_start <= d_val <= norm_end:
                gibdd_count += 1
                try:
                    gibdd_sum += float(str(row[1] or 0).replace(",", "."))
                except ValueError:
                    pass

        cursor.execute('SELECT Дата, СуммаДоговора FROM "Справки_Оружие"')
        for row in cursor.fetchall():
            d_val = normalize_date(str(row[0] or ""))
            if norm_start <= d_val <= norm_end:
                weapon_count += 1
                try:
                    weapon_sum += float(str(row[1] or 0).replace(",", "."))
                except ValueError:
                    pass
    except Exception as e:
        print(f"Ошибка расчета статистики: {e}")
    finally:
        conn.close()

    return {
        "gibdd_count": gibdd_count,
        "gibdd_sum": gibdd_sum,
        "weapon_count": weapon_count,
        "weapon_sum": weapon_sum,
        "total_count": gibdd_count + weapon_count,
        "total_sum": gibdd_sum + weapon_sum,
    }


def get_districts_list() -> List[str]:
    rows = get_reference_table("Районы_НН")
    res = [
        str(list(r.values())[1] if len(r.values()) > 1 else list(r.values())[0])
        for r in rows
        if r
    ]
    return res if res else ["Автозаводский", "Сормовский", "Нижегородский"]


def get_uvd_list() -> List[str]:
    rows = get_reference_table("УВД")
    res = [
        str(list(r.values())[1] if len(r.values()) > 1 else list(r.values())[0])
        for r in rows
        if r
    ]
    return (
        res
        if res
        else ["УВД Нижегородского района", "УВД Автозаводского района"]
    )


def get_reference_table(table_name: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        target_table = table_name
        for t in tables:
            if t.lower().replace("_", "") == table_name.lower().replace("_", ""):
                target_table = t
                break
        cursor.execute(f'SELECT * FROM "{target_table}"')
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Ошибка чтения справочника {table_name}: {e}")
        return []
    finally:
        conn.close()


def add_reference_item(table_name: str, column_name: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f'INSERT INTO "{table_name}" ("{column_name}") VALUES (?)', (value,)
        )
        conn.commit()
    finally:
        conn.close()


def update_reference_item(
        table_name: str, column_name: str, old_value: str, new_value: str
):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f'UPDATE "{table_name}" SET "{column_name}" = ? WHERE "{column_name}" = ?',
            (new_value, old_value),
        )
        conn.commit()
    finally:
        conn.close()


def delete_reference_item(table_name: str, column_name: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f'DELETE FROM "{table_name}" WHERE "{column_name}" = ?', (value,)
        )
        conn.commit()
    finally:
        conn.close()


def get_presets_list(preset_type: str = "ГИБДД") -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='Тарифы';"
        )
        if not cursor.fetchone():
            cursor.execute(
                """
                CREATE TABLE "Тарифы"
                (
                    "id"        INTEGER PRIMARY KEY AUTOINCREMENT,
                    "Тип"       TEXT DEFAULT 'ГИБДД',
                    "Название"  TEXT,
                    "Категории" TEXT,
                    "Сумма"     REAL
                )
                """
            )
            conn.commit()

        cursor.execute("PRAGMA table_info('Тарифы');")
        columns = [col[1] for col in cursor.fetchall()]
        if "Тип" not in columns:
            cursor.execute(
                'ALTER TABLE "Тарифы" ADD COLUMN "Тип" TEXT DEFAULT "ГИБДД";'
            )
            conn.commit()

        cursor.execute(
            'SELECT COUNT(*) FROM "Тарифы" WHERE "Тип" = ? OR "Тип" IS NULL',
            ("ГИБДД",),
        )
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                """
                INSERT INTO "Тарифы" ("Тип", "Название", "Категории", "Сумма")
                VALUES (?, ?, ?, ?)
                """,
                [
                    ("ГИБДД", "Легковые (A, B)", "B", 500),
                    (
                        "ГИБДД",
                        "Грузовые / Автобусы (C, D, CE, DE)",
                        "C, D, CE, DE",
                        1000,
                    ),
                ],
            )
            conn.commit()

        cursor.execute(
            'SELECT COUNT(*) FROM "Тарифы" WHERE "Тип" = ?', ("Оружие",)
        )
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                """
                INSERT INTO "Тарифы" ("Тип", "Название", "Категории", "Сумма")
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        "Оружие",
                        "Освидетельствование (Форма 002-О/у)",
                        "002-О/у",
                        1000,
                    ),
                    ("Оружие", "Повторное / Льготное", "002-О/у", 800),
                ],
            )
            conn.commit()

        cursor.execute(
            """
            SELECT *
            FROM "Тарифы"
            WHERE "Тип" = ?
               OR "Тип" IS NULL
               OR "Тип" = ''
            """,
            (preset_type,),
        )
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Ошибка загрузки тарифов: {e}")
        return []
    finally:
        conn.close()


def add_preset_item(preset_type: str, name: str, categories: str, price: float):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO "Тарифы" ("Тип", "Название", "Категории", "Сумма") VALUES (?, ?, ?, ?)',
            (preset_type, name, categories, price),
        )
        conn.commit()
    finally:
        conn.close()


def update_preset_item(
        preset_id: int, preset_type: str, name: str, categories: str, price: float
):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE "Тарифы"
            SET "Тип"       = ?,
                "Название"  = ?,
                "Категории" = ?,
                "Сумма"     = ?
            WHERE "id" = ?
            """,
            (preset_type, name, categories, price, preset_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_preset_item(preset_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM "Тарифы" WHERE "id" = ?', (preset_id,))
        conn.commit()
    finally:
        conn.close()


def merge_multiple_streets_in_db(
        old_names: List[str], new_name: str
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        new_clean = normalize_street_name(new_name)
        if not new_clean or not old_names:
            return 0

        placeholders = ",".join(["?"] * len(old_names))
        query = f'UPDATE "Клиенты" SET "Улица" = ? WHERE "Улица" IN ({placeholders})'

        params = [new_clean] + old_names
        cursor.execute(query, params)

        updated_count = cursor.rowcount
        conn.commit()
        return updated_count
    except Exception as e:
        print(f"Ошибка массового объединения улиц: {e}")
        return 0
    finally:
        conn.close()