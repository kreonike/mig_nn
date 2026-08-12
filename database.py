import logging
import os
import re
import sqlite3
import sys
from typing import Any, Dict, List, Optional

from backup import make_daily_backup

logger = logging.getLogger("MIG_NN")


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
    # Регистрируем нижний регистр для кириллицы
    conn.create_function(
        "LOWER", 1, lambda val: str(val).lower() if val is not None else None
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS "idx_клиенты_фио" ON "Клиенты" ("Фамилия",'
        ' "Имя", "Отчество");'
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS "idx_клиенты_паспорт" ON "Клиенты"'
        ' ("СерПасп", "ПспНом");'
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS "idx_клиенты_рождение" ON "Клиенты"'
        ' ("ДатаРождения");'
    )
    return conn


# ==============================================================================
# 1. ИНИЦИАЛИЗАЦИЯ И ТАБЛИЦЫ СПРАВОЧНИКОВ
# ==============================================================================


def init_reference_tables():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "Пресеты_ГИБДД" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "Название" TEXT NOT NULL,
                "Категории" TEXT,
                "Сумма" REAL DEFAULT 0
            );
        """)

        cursor.execute('SELECT COUNT(*) FROM "Пресеты_ГИБДД"')
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                'INSERT INTO "Пресеты_ГИБДД" ("Название", "Категории", "Сумма") VALUES'
                " (?, ?, ?)",
                [
                    ("Легковые (A, B)", "A, B", 500.0),
                    ("Грузовые / Автобусы (C, D)", "C, D, CE, DE", 1000.0),
                    ("Медосмотр с наркологом и психиатром", "A, B, C, D", 1500.0),
                ],
            )

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "Врачи" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "ФИО" TEXT NOT NULL,
                "Специальность" TEXT
            );
        """)

        cursor.execute('SELECT COUNT(*) FROM "Врачи"')
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                'INSERT INTO "Врачи" ("ФИО", "Специальность") VALUES (?, ?)',
                [
                    ("Лещева Н.Г.", "Нарколог"),
                    ("Червоный А.В.", "Психиатр"),
                ],
            )

        conn.commit()
    except Exception as e:
        logger.error(f"Ошибка инициализации справочников: {e}", exc_info=True)
    finally:
        conn.close()


def get_reference_table(table_name: str) -> List[Dict[str, Any]]:
    if table_name == "Пресеты_ГИБДД":
        return get_presets_list()

    init_reference_tables()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f'SELECT * FROM "{table_name}"')
        rows = cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            if "id" in d and d["id"] is not None:
                try:
                    d["id"] = int(d["id"])
                except ValueError:
                    pass
            result.append(d)
        return result
    except Exception as e:
        logger.error(f"Ошибка чтения таблицы '{table_name}': {e}", exc_info=True)
        return []
    finally:
        conn.close()


def add_reference_item(table_name: str, item_data: Dict[str, Any]) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        keys = list(item_data.keys())
        cols = ", ".join([f'"{k}"' for k in keys])
        placeholders = ", ".join(["?"] * len(keys))
        values = [item_data[k] for k in keys]

        cursor.execute(
            f'INSERT INTO "{table_name}" ({cols}) VALUES ({placeholders})', values
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка добавления записи в '{table_name}': {e}", exc_info=True)
        return False
    finally:
        conn.close()


def delete_reference_item(table_name: str, item_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f'DELETE FROM "{table_name}" WHERE "id" = ?', (item_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления записи из '{table_name}': {e}", exc_info=True)
        return False
    finally:
        conn.close()


def update_reference_item(
    table_name: str, item_id: int, item_data: Dict[str, Any]
) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        set_clause = ", ".join([f'"{k}" = ?' for k in item_data.keys()])
        values = list(item_data.values()) + [item_id]

        cursor.execute(
            f'UPDATE "{table_name}" SET {set_clause} WHERE "id" = ?',
            values,
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(
            f"Ошибка обновления справочника '{table_name}' ID {item_id}: {e}",
            exc_info=True,
        )
        return False
    finally:
        conn.close()


# ==============================================================================
# 2. УПРАВЛЕНИЕ ТАРИФАМИ И ПРЕСЕТАМИ
# ==============================================================================


def _parse_price_value(val: Any) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    s_val = str(val).strip().replace(",", ".")
    s_val = re.sub(r"[^\d.]", "", s_val)
    try:
        return float(s_val) if s_val else 0.0
    except ValueError:
        return 0.0


def get_presets_list(preset_type: str = "ГИБДД") -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        init_reference_tables()
        cursor.execute(
            'SELECT "id", "Название", "Категории", "Сумма" FROM "Пресеты_ГИБДД"'
        )
        rows = cursor.fetchall()

        result = []
        for r in rows:
            try:
                preset_id = int(r["id"])
            except (ValueError, TypeError):
                preset_id = 0

            title_val = str(r["Название"] or "")
            cats_val = str(r["Категории"] or "")
            price_val = _parse_price_value(r["Сумма"])

            result.append({
                "id": preset_id,
                "Название": title_val,
                "title": title_val,
                "name": title_val,
                "Категории": cats_val,
                "categories": cats_val,
                "Сумма": price_val,
                "price": price_val,
            })
        logger.info(f"[PRESETS] Загружено пресетов: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"[PRESETS] Ошибка чтения пресетов: {e}", exc_info=True)
        return []
    finally:
        conn.close()


def update_preset_item(*args, **kwargs) -> bool:
    logger.info(f"[PRESET_UPDATE] Сырые аргументы: args={args}, kwargs={kwargs}")

    preset_id = None
    preset_name = ""
    preset_cats = ""
    preset_price = 0.0

    if "preset_id" in kwargs:
        preset_id = kwargs["preset_id"]
    if "id" in kwargs:
        preset_id = kwargs["id"]

    all_args = list(args)

    if all_args:
        if len(all_args) >= 2 and isinstance(all_args[1], dict):
            preset_id = all_args[0]
            d = all_args[1]
            preset_name = d.get("Название") or d.get("title") or d.get("name") or ""
            preset_cats = d.get("Категории") or d.get("categories") or ""
            preset_price = _parse_price_value(
                d.get("Сумма") if "Сумма" in d else d.get("price")
            )
        else:
            clean_args = [a for a in all_args if str(a).strip().upper() != "ГИБДД"]

            if clean_args:
                preset_id = clean_args[0]

            if len(clean_args) >= 2:
                preset_name = clean_args[1]
            if len(clean_args) >= 3:
                preset_cats = clean_args[2]
            if len(clean_args) >= 4:
                preset_price = _parse_price_value(clean_args[3])

    if not preset_name and (
        "title" in kwargs or "Название" in kwargs or "name" in kwargs
    ):
        preset_name = (
            kwargs.get("title") or kwargs.get("Название") or kwargs.get("name")
        )
    if not preset_cats and ("categories" in kwargs or "Категории" in kwargs):
        preset_cats = kwargs.get("categories") or kwargs.get("Категории")
    if preset_price == 0.0 and ("price" in kwargs or "Сумма" in kwargs):
        preset_price = _parse_price_value(
            kwargs.get("price") if "price" in kwargs else kwargs.get("Сумма")
        )

    if preset_id is None:
        logger.error("[PRESET_UPDATE] Не удалось определить preset_id!")
        return False

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE "Пресеты_ГИБДД"
            SET "Название"  = ?,
                "Категории" = ?,
                "Сумма"     = ?
            WHERE "id" = ?
            """,
            (str(preset_name), str(preset_cats), preset_price, int(preset_id)),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(
            f"[PRESET_UPDATE] Ошибка записи пресета в БД: {e}", exc_info=True
        )
        return False
    finally:
        conn.close()


def add_preset_item(*args, **kwargs) -> bool:
    preset_name = ""
    preset_cats = ""
    preset_price = 0.0

    all_args = list(args)
    clean_args = [a for a in all_args if str(a).strip().upper() != "ГИБДД"]

    if clean_args and isinstance(clean_args[0], dict):
        d = clean_args[0]
        preset_name = d.get("Название") or d.get("title") or d.get("name") or ""
        preset_cats = d.get("Категории") or d.get("categories") or ""
        preset_price = _parse_price_value(
            d.get("Сумма") if "Сумма" in d else d.get("price")
        )
    else:
        if len(clean_args) >= 1:
            preset_name = clean_args[0]
        if len(clean_args) >= 2:
            preset_cats = clean_args[1]
        if len(clean_args) >= 3:
            preset_price = _parse_price_value(clean_args[2])

    if not preset_name and (
        "title" in kwargs or "Название" in kwargs or "name" in kwargs
    ):
        preset_name = (
            kwargs.get("title") or kwargs.get("Название") or kwargs.get("name")
        )
    if not preset_cats and ("categories" in kwargs or "Категории" in kwargs):
        preset_cats = kwargs.get("categories") or kwargs.get("Категории")
    if preset_price == 0.0 and ("price" in kwargs or "Сумма" in kwargs):
        preset_price = _parse_price_value(
            kwargs.get("price") if "price" in kwargs else kwargs.get("Сумма")
        )

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO "Пресеты_ГИБДД" ("Название", "Категории", "Сумма")
            VALUES (?, ?, ?)
            """,
            (str(preset_name), str(preset_cats), preset_price),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"[PRESET_ADD] Ошибка добавления пресета: {e}", exc_info=True)
        return False
    finally:
        conn.close()


def delete_preset_item(preset_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'DELETE FROM "Пресеты_ГИБДД" WHERE "id" = ?', (int(preset_id),)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(
            f"[PRESET_DELETE] Ошибка удаления пресета ID {preset_id}: {e}",
            exc_info=True,
        )
        return False
    finally:
        conn.close()


# ==============================================================================
# 3. РАБОТА С УЛИЦАМИ И ОБЪЕДИНЕНИЕМ ДУБЛИКАТОВ
# ==============================================================================


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
            'SELECT DISTINCT "Улица" FROM "Клиенты" WHERE "Улица" IS NOT NULL AND'
            ' "Улица" != ""'
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


def merge_multiple_streets_in_db(
    old_streets: List[str], target_street: str
) -> int:
    if not old_streets or not target_street:
        return 0

    clean_target = normalize_street_name(target_street)
    conn = get_connection()
    cursor = conn.cursor()
    total_updated = 0

    try:
        for old_st in old_streets:
            clean_old = old_st.strip()
            if not clean_old or clean_old == clean_target:
                continue

            cursor.execute(
                """
                UPDATE "Клиенты"
                SET "Улица" = ?
                WHERE "Улица" = ? OR TRIM("Улица") = ?
                """,
                (clean_target, old_st, clean_old),
            )
            total_updated += cursor.rowcount

        conn.commit()
        return total_updated
    except Exception as e:
        logger.error(f"Ошибка при объединении улиц в БД: {e}", exc_info=True)
        conn.rollback()
        return 0
    finally:
        conn.close()


# ==============================================================================
# 4. УНИВЕРСАЛЬНЫЙ ПОИСК ПАЦИЕНТОВ
# ==============================================================================


def search_clients_for_completer(
    query: str, limit: int = 100
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        raw_q = str(query or "").strip()
        logger.info(f"[SEARCH_DEBUG] Начало поиска. Введенный запрос: '{raw_q}'")

        if not raw_q:
            cursor.execute('SELECT * FROM "Клиенты" ORDER BY "Фамилия" ASC LIMIT ?', (limit,))
            return [dict(row) for row in cursor.fetchall()]

        q_clean = re.sub(r"\s+", "", raw_q)

        def get_case_variants(text: str) -> tuple:
            low = text.lower()
            cap = text.capitalize()
            up = text.upper()
            return low, cap, up

        # ----------------------------------------------------------------------
        # 1. ПОИСК: БУКВЫ + ЦИФРЫ (например: слс13, слс27, сдг11121981)
        # ----------------------------------------------------------------------
        match_letters_digits = re.match(
            r"^([a-zA-яёЁа-яА-Я]{1,10})(\d{1,8})$", q_clean
        )
        if match_letters_digits:
            letters = match_letters_digits.group(1)
            digits = match_letters_digits.group(2)
            logger.info(f"[SEARCH_DEBUG] Распознан шаблон 'БУКВЫ + ЦИФРЫ': Буквы='{letters}', Цифры='{digits}'")

            d_masks = []
            if len(digits) in (1, 2):
                day_num = str(int(digits))
                day_padded = digits.zfill(2)
                d_masks = [f"%{day_padded}%", f"%{day_num}%"]
            elif len(digits) in (3, 4):
                day_str = digits[:2].zfill(2)
                month_str = digits[2:].zfill(2)
                d_masks = [f"%{day_str}.{month_str}%", f"%{month_str}-{day_str}%"]
            else:
                day_str = digits[:2]
                month_str = digits[2:4]
                year_str = digits[4:]
                d_masks = [f"%{day_str}.{month_str}.%{year_str}%", f"%{year_str}-{month_str}-{day_str}%"]

            d_masks = list(set(d_masks))
            date_sql = "(" + " OR ".join(['"ДатаРождения" LIKE ?'] * len(d_masks)) + ")"

            # Вариант 1A: Начало Фамилии + Дата
            low_l, cap_l, up_l = get_case_variants(letters)
            sql_fam_start = f"""
                SELECT * FROM "Клиенты"
                WHERE ("Фамилия" LIKE ? OR "Фамилия" LIKE ? OR "Фамилия" LIKE ?)
                  AND {date_sql}
                ORDER BY "Фамилия" ASC LIMIT ?
            """
            params_a = (f"{low_l}%", f"{cap_l}%", f"{up_l}%") + tuple(d_masks) + (limit,)
            cursor.execute(sql_fam_start, params_a)
            rows = [dict(r) for r in cursor.fetchall()]
            logger.info(f"[SEARCH_DEBUG] [Вариант 1A - Начало Фамилии + Дата] Найдено: {len(rows)}")
            if rows:
                return rows

            # Вариант 1B: Инициалы + Дата
            if len(letters) >= 2:
                f_low, f_cap, f_up = get_case_variants(letters[0])
                i_low, i_cap, i_up = get_case_variants(letters[1])

                if len(letters) >= 3:
                    o_low, o_cap, o_up = get_case_variants(letters[2])
                    otch_cond = '("Отчество" LIKE ? OR "Отчество" LIKE ? OR "Отчество" LIKE ? OR "Отчество" IS NULL OR "Отчество" = \'\')'
                    otch_params = (f"{o_low}%", f"{o_cap}%", f"{o_up}%")
                else:
                    otch_cond = '(1=1)'
                    otch_params = ()

                sql_inits = f"""
                    SELECT * FROM "Клиенты"
                    WHERE ("Фамилия" LIKE ? OR "Фамилия" LIKE ? OR "Фамилия" LIKE ?)
                      AND ("Имя" LIKE ? OR "Имя" LIKE ? OR "Имя" LIKE ?)
                      AND {otch_cond}
                      AND {date_sql}
                    ORDER BY "Фамилия" ASC LIMIT ?
                """
                params_b = (
                    f"{f_low}%", f"{f_cap}%", f"{f_up}%",
                    f"{i_low}%", f"{i_cap}%", f"{i_up}%",
                ) + otch_params + tuple(d_masks) + (limit,)

                cursor.execute(sql_inits, params_b)
                rows = [dict(r) for r in cursor.fetchall()]
                logger.info(f"[SEARCH_DEBUG] [Вариант 1B - Инициалы + Дата] Найдено: {len(rows)}")
                if rows:
                    return rows

        # ----------------------------------------------------------------------
        # 2. ПОИСК: ТОЛЬКО БУКВЫ (например: соля, слс)
        # ----------------------------------------------------------------------
        match_letters = re.match(r"^([a-zA-яёЁа-яА-Я]{1,10})$", q_clean)
        if match_letters:
            letters = match_letters.group(1)
            low_l, cap_l, up_l = get_case_variants(letters)

            # Вариант 2A: Начало Фамилии
            sql_fam_only = """
                SELECT * FROM "Клиенты"
                WHERE "Фамилия" LIKE ? OR "Фамилия" LIKE ? OR "Фамилия" LIKE ?
                ORDER BY "Фамилия" ASC LIMIT ?
            """
            cursor.execute(sql_fam_only, (f"{low_l}%", f"{cap_l}%", f"{up_l}%", limit))
            rows = [dict(r) for r in cursor.fetchall()]
            logger.info(f"[SEARCH_DEBUG] [Вариант 2A - Начало Фамилии] Найдено: {len(rows)}")
            if rows:
                return rows

            # Вариант 2B: Инициалы (для 2 или 3 букв)
            if len(letters) in (2, 3):
                f_low, f_cap, f_up = get_case_variants(letters[0])
                i_low, i_cap, i_up = get_case_variants(letters[1])

                if len(letters) == 3:
                    o_low, o_cap, o_up = get_case_variants(letters[2])
                    otch_cond = '("Отчество" LIKE ? OR "Отчество" LIKE ? OR "Отчество" LIKE ? OR "Отчество" IS NULL OR "Отчество" = \'\')'
                    otch_params = (f"{o_low}%", f"{o_cap}%", f"{o_up}%")
                else:
                    otch_cond = '(1=1)'
                    otch_params = ()

                sql_inits_only = f"""
                    SELECT * FROM "Клиенты"
                    WHERE ("Фамилия" LIKE ? OR "Фамилия" LIKE ? OR "Фамилия" LIKE ?)
                      AND ("Имя" LIKE ? OR "Имя" LIKE ? OR "Имя" LIKE ?)
                      AND {otch_cond}
                    ORDER BY "Фамилия" ASC LIMIT ?
                """
                params_inits = (
                    f"{f_low}%", f"{f_cap}%", f"{f_up}%",
                    f"{i_low}%", f"{i_cap}%", f"{i_up}%",
                ) + otch_params + (limit,)

                cursor.execute(sql_inits_only, params_inits)
                rows = [dict(r) for r in cursor.fetchall()]
                logger.info(f"[SEARCH_DEBUG] [Вариант 2B - Инициалы] Найдено: {len(rows)}")
                if rows:
                    return rows

        # ----------------------------------------------------------------------
        # 3. ОБЩИЙ СКВОЗНОЙ ПОИСК
        # ----------------------------------------------------------------------
        logger.info("[SEARCH_DEBUG] Переход к Варианту 3: Общий сквозной поиск по всем полям...")
        low_q, cap_q, up_q = get_case_variants(raw_q)
        any_low, any_cap = f"%{low_q}%", f"%{cap_q}%"

        sql_global = """
            SELECT *,
                   CASE
                       WHEN "Фамилия" LIKE ? OR "Фамилия" LIKE ? THEN 1
                       WHEN "Имя" LIKE ? OR "Имя" LIKE ? THEN 2
                       ELSE 3
                   END AS match_rank
            FROM "Клиенты"
            WHERE "Фамилия" LIKE ? OR "Фамилия" LIKE ?
               OR "Имя" LIKE ? OR "Имя" LIKE ?
               OR "Отчество" LIKE ? OR "Отчество" LIKE ?
               OR "ДатаРождения" LIKE ?
               OR REPLACE(COALESCE("СерПасп", '') || COALESCE("ПспНом", ''), ' ', '') LIKE ?
               OR "СерПасп" LIKE ? OR "ПспНом" LIKE ?
               OR "id" IN (
                   SELECT "КлиентID" FROM "Сделки" WHERE "ВыданаСправка№" LIKE ? OR "Выдана справкаСер" LIKE ?
                   UNION
                   SELECT "КлиентID" FROM "Справки_Оружие" WHERE "Справка№" LIKE ?
               )
            ORDER BY match_rank ASC, "Фамилия" ASC LIMIT ?
        """
        params_global = (
            f"{low_q}%", f"{cap_q}%",
            f"{low_q}%", f"{cap_q}%",
            any_low, any_cap,
            any_low, any_cap,
            any_low, any_cap,
            f"%{q_clean}%", f"%{q_clean}%",
            any_low, any_low,
            any_low, any_low, any_low,
            limit
        )

        cursor.execute(sql_global, params_global)
        rows = [dict(row) for row in cursor.fetchall()]
        logger.info(f"[SEARCH_DEBUG] [Вариант 3 - Сквозной поиск] Найдено: {len(rows)}")
        return rows

    except Exception as e:
        logger.error(f"[SEARCH_DEBUG] Ошибка при выполнении поиска клиентов: {e}", exc_info=True)
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
        logger.error(f"Ошибка обновления карточки пациента: {e}", exc_info=True)
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
# 5. СДЕЛКИ И СТАТИСТИКА
# ==============================================================================


def get_next_deal_number(table_name: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f'SELECT MAX(CAST("НомДоговора" AS INTEGER)) FROM "{table_name}"'
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
            f'SELECT *, ROWID as deal_id FROM "{table_name}" WHERE "КлиентID" = ?'
            " ORDER BY ROWID DESC LIMIT 1",
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


def get_statistics_for_period(start_date: str, end_date: str) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    def normalize_to_iso(d_str: str) -> str:
        if not d_str:
            return ""
        s = d_str.strip()
        if "." in s:
            parts = s.split(".")
            if len(parts) == 3:
                return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        return s

    start_iso = normalize_to_iso(start_date)
    end_iso = normalize_to_iso(end_date)

    try:
        sql_date_conv = """
            CASE 
                WHEN "Дата" LIKE '__.__.____' THEN 
                    SUBSTR("Дата", 7, 4) || '-' || SUBSTR("Дата", 4, 2) || '-' || SUBSTR("Дата", 1, 2)
                ELSE "Дата"
            END
        """

        query_gibdd = f"""
            SELECT COUNT(*) as cnt, SUM(CAST("СуммаДоговора" AS REAL)) as total
            FROM "Сделки"
            WHERE {sql_date_conv} >= ? AND {sql_date_conv} <= ?
        """
        cursor.execute(query_gibdd, (start_iso, end_iso))
        gibdd_row = cursor.fetchone()
        gibdd_cnt = gibdd_row["cnt"] if gibdd_row else 0
        gibdd_sum = gibdd_row["total"] if (gibdd_row and gibdd_row["total"]) else 0.0

        weapon_cnt, weapon_sum = 0, 0.0
        try:
            query_weapon = f"""
                SELECT COUNT(*) as cnt, SUM(CAST("СуммаДоговора" AS REAL)) as total
                FROM "Справки_Оружие"
                WHERE {sql_date_conv} >= ? AND {sql_date_conv} <= ?
            """
            cursor.execute(query_weapon, (start_iso, end_iso))
            weapon_row = cursor.fetchone()
            if weapon_row:
                weapon_cnt = weapon_row["cnt"] or 0
                weapon_sum = weapon_row["total"] or 0.0
        except Exception:
            pass

        return {
            "gibdd_count": gibdd_cnt,
            "gibdd_sum": gibdd_sum,
            "gibdd_total": gibdd_sum,
            "weapon_count": weapon_cnt,
            "weapon_sum": weapon_sum,
            "weapon_total": weapon_sum,
            "total_count": gibdd_cnt + weapon_cnt,
            "total_sum": gibdd_sum + weapon_sum,
        }
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}", exc_info=True)
        return {
            "gibdd_count": 0,
            "gibdd_sum": 0.0,
            "gibdd_total": 0.0,
            "weapon_count": 0,
            "weapon_sum": 0.0,
            "weapon_total": 0.0,
            "total_count": 0,
            "total_sum": 0.0,
        }
    finally:
        conn.close()


def get_client_deals(client_id: int) -> list:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN"
            " ('Сделки', 'deals')"
        )
        table_row = cursor.fetchone()
        if not table_row:
            return []

        table_name = table_row[0]

        cursor.execute(f"PRAGMA table_info([{table_name}])")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]

        client_col_candidates = ["КлиентID", "клиент_id", "client_id", "IDКлиента"]
        client_col = next(
            (col for col in client_col_candidates if col in column_names), None
        )

        if not client_col:
            client_col = next(
                (
                    col
                    for col in column_names
                    if "клиент" in col.lower() or "client" in col.lower()
                ),
                None,
            )

        if not client_col:
            return []

        sort_col = "rowid"
        for candidate in ["id", "ID", "Код", "НомДоговора"]:
            if candidate in column_names:
                sort_col = candidate
                break

        query = (
            f"SELECT * FROM [{table_name}] WHERE [{client_col}] = ? ORDER BY"
            f" [{sort_col}] DESC"
        )
        cursor.execute(query, (client_id,))

        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        deals = [dict(zip(columns, row)) for row in rows]
        return deals

    except Exception as e:
        print(f"Ошибка при получении сделок клиента: {e}")
        return []
    finally:
        conn.close()


def get_districts_list() -> List[str]:
    return [
        "Автозаводский",
        "Сормовский",
        "Нижегородский",
        "Советский",
        "Приокский",
    ]


def get_uvd_list() -> List[str]:
    return [
        "УВД Нижегородского района",
        "УВД Автозаводского района",
        "УВД Сормовского района",
    ]