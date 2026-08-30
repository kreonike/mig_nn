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
    # timeout=10.0 предотвращает блокировки базы при частых запросах живого поиска
    conn = sqlite3.connect(DB_NAME, timeout=10.0)
    conn.row_factory = sqlite3.Row

    # Включаем WAL-режим для ускорения работы при параллельном чтении/записи
    try:
        conn.execute('PRAGMA journal_mode=WAL;')
    except Exception:
        pass

    # Регистрируем нижний регистр для кириллицы
    conn.create_function(
        "LOWER", 1, lambda val: str(val).lower() if val is not None else None
    )
    return conn


# ==============================================================================
# 1. ИНИЦИАЛИЗАЦИЯ И ТАБЛИЦЫ СПРАВОЧНИКОВ
# ==============================================================================


def init_reference_tables():
    """Создает таблицы и индексы в базе данных (вызывается при старте приложения)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Добавляем нормализованные поля для поиска, если их нет
        try:
            cursor.execute('ALTER TABLE "Клиенты" ADD COLUMN "search_fio" TEXT;')
            logger.info("Добавлено поле search_fio для ускоренного поиска")
        except sqlite3.OperationalError:
            pass  # Поле уже существует
        
        try:
            cursor.execute('ALTER TABLE "Клиенты" ADD COLUMN "search_passport" TEXT;')
            logger.info("Добавлено поле search_passport для ускоренного поиска")
        except sqlite3.OperationalError:
            pass  # Поле уже существует
        
        # Создаем индексы для нормализованных полей
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS "idx_клиенты_фио" ON "Клиенты" ("Фамилия", "Имя", "Отчество");'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS "idx_клиенты_паспорт" ON "Клиенты" ("СерПасп", "ПспНом");'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS "idx_клиенты_рождение" ON "Клиенты" ("ДатаРождения");'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS "idx_клиенты_search_fio" ON "Клиенты" ("search_fio");'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS "idx_клиенты_search_passport" ON "Клиенты" ("search_passport");'
        )

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "Пресеты_ГИБДД" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "Тип" TEXT DEFAULT 'ГИБДД',
                "Название" TEXT NOT NULL,
                "Категории" TEXT,
                "Сумма" REAL DEFAULT 0
            );
        """)

        # Авто-миграция: если таблица создана ранее без колонки "Тип"
        try:
            cursor.execute('ALTER TABLE "Пресеты_ГИБДД" ADD COLUMN "Тип" TEXT DEFAULT "ГИБДД";')
        except sqlite3.OperationalError:
            pass  # Колонка уже существует

        cursor.execute('SELECT COUNT(*) FROM "Пресеты_ГИБДД"')
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                'INSERT INTO "Пресеты_ГИБДД" ("Тип", "Название", "Категории", "Сумма") VALUES (?, ?, ?, ?)',
                [
                    ("ГИБДД", "Легковые (A, B)", "A, B", 500.0),
                    ("ГИБДД", "Грузовые / Автобусы (C, D)", "C, D, CE, DE", 1000.0),
                    ("ГИБДД", "Медосмотр с наркологом и психиатром", "A, B, C, D", 1500.0),
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "УВД" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "Название" TEXT NOT NULL
            );
        """)

        cursor.execute('SELECT COUNT(*) FROM "УВД"')
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                'INSERT INTO "УВД" ("Название") VALUES (?)',
                [
                    ("УВД Нижегородского района",),
                    ("УВД Автозаводского района",),
                    ("УВД Сормовского района",),
                ],
            )

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "Районы_НН" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "НазРайона" TEXT NOT NULL
            );
        """)

        cursor.execute('SELECT COUNT(*) FROM "Районы_НН"')
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                'INSERT INTO "Районы_НН" ("НазРайона") VALUES (?)',
                [
                    ("Автозаводский",),
                    ("Сормовский",),
                    ("Нижегородский",),
                    ("Советский",),
                    ("Приокский",),
                ],
            )

        conn.commit()
    except Exception as e:
        logger.error(f"Ошибка инициализации справочников и индексов: {e}", exc_info=True)
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


def add_reference_item(table_name: str, column_name: str, value: str) -> bool:
    """Добавляет новую запись в одноколоночный справочник (напр. "УВД", "Районы_НН")."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f'INSERT INTO "{table_name}" ("{column_name}") VALUES (?)', (value,)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка добавления записи в '{table_name}': {e}", exc_info=True)
        return False
    finally:
        conn.close()


def delete_reference_item(table_name: str, column_name: str, value: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f'DELETE FROM "{table_name}" WHERE "{column_name}" = ?', (value,)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления записи из '{table_name}': {e}", exc_info=True)
        return False
    finally:
        conn.close()


def update_reference_item(
    table_name: str, column_name: str, old_value: str, new_value: str
) -> bool:
    """Обновляет значение в одноколоночном справочнике."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f'UPDATE "{table_name}" SET "{column_name}" = ? WHERE "{column_name}" = ?',
            (new_value, old_value),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(
            f"Ошибка обновления справочника '{table_name}' ({old_value} -> {new_value}): {e}",
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


def get_presets_list(preset_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Загружает список пресетов. При передаче preset_type (напр. 'ГИБДД') фильтрует результаты."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        init_reference_tables()
        if preset_type:
            cursor.execute(
                'SELECT "id", "Тип", "Название", "Категории", "Сумма" FROM "Пресеты_ГИБДД" WHERE "Тип" = ?',
                (preset_type,)
            )
        else:
            cursor.execute(
                'SELECT "id", "Тип", "Название", "Категории", "Сумма" FROM "Пресеты_ГИБДД"'
            )
        rows = cursor.fetchall()

        result = []
        for r in rows:
            try:
                preset_id = int(r["id"])
            except (ValueError, TypeError):
                preset_id = 0

            type_val = str(r["Тип"] or "ГИБДД")
            title_val = str(r["Название"] or "")
            cats_val = str(r["Категории"] or "")
            price_val = _parse_price_value(r["Сумма"])

            result.append({
                "id": preset_id,
                "Тип": type_val,
                "type": type_val,
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


def update_preset_item(
    preset_id: int, preset_type: str, name: str, categories: str, price: float
) -> bool:
    """Обновление пресета тарифного плана."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        price_val = _parse_price_value(price)
        cursor.execute(
            """
            UPDATE "Пресеты_ГИБДД"
            SET "Тип"       = ?,
                "Название"  = ?,
                "Категории" = ?,
                "Сумма"     = ?
            WHERE "id" = ?
            """,
            (str(preset_type), str(name), str(categories), price_val, int(preset_id)),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(
            f"[PRESET_UPDATE] Ошибка записи пресета ID {preset_id}: {e}",
            exc_info=True,
        )
        return False
    finally:
        conn.close()


def add_preset_item(
    preset_type: str, name: str, categories: str, price: float
) -> bool:
    """Добавление нового пресета тарифного плана."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        price_val = _parse_price_value(price)
        cursor.execute(
            """
            INSERT INTO "Пресеты_ГИБДД" ("Тип", "Название", "Категории", "Сумма")
            VALUES (?, ?, ?, ?)
            """,
            (str(preset_type), str(name), str(categories), price_val),
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


def get_streets_list(query: str = "", limit: Optional[int] = None) -> List[str]:
    """
    Возвращает список уникальных улиц.
    Если query пустой — отдает ВСЕ улицы базы данных без урезания.
    Если передан query — ищет подстроку.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        clean_q = str(query or "").strip()
        if clean_q:
            if limit:
                cursor.execute(
                    'SELECT DISTINCT "Улица" FROM "Клиенты" WHERE "Улица" LIKE ? AND "Улица" IS NOT NULL AND "Улица" != "" ORDER BY "Улица" ASC LIMIT ?',
                    (f"%{clean_q}%", limit),
                )
            else:
                cursor.execute(
                    'SELECT DISTINCT "Улица" FROM "Клиенты" WHERE "Улица" LIKE ? AND "Улица" IS NOT NULL AND "Улица" != "" ORDER BY "Улица" ASC',
                    (f"%{clean_q}%",),
                )
        else:
            # Возвращаем 100% улиц базы данных
            cursor.execute(
                'SELECT DISTINCT "Улица" FROM "Клиенты" WHERE "Улица" IS NOT NULL AND "Улица" != "" ORDER BY "Улица" ASC'
            )

        raw_streets = cursor.fetchall()
        result_set = set()
        for r in raw_streets:
            if r[0]:
                norm = normalize_street_name(r[0])
                if norm:
                    result_set.add(norm)

        return sorted(list(result_set))
    except Exception as e:
        logger.error(f"Ошибка получения списка улиц: {e}", exc_info=True)
        return []
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
        # 1. ПОИСК: БУКВЫ + ЦИФРЫ (например: сдг23, сдг11, слс13, сдг11121981)
        # ----------------------------------------------------------------------
        match_letters_digits = re.match(
            r"^([а-яА-ЯёЁa-zA-Z]{1,10})(\d{1,8})$", q_clean
        )
        if match_letters_digits:
            letters = match_letters_digits.group(1)
            digits = match_letters_digits.group(2)
            

            date_norm_expr = (
                'CASE '
                'WHEN "ДатаРождения" LIKE \'__.__.____\' THEN '
                'SUBSTR("ДатаРождения", 7, 4) || \'-\' || SUBSTR("ДатаРождения", 4, 2) '
                '|| \'-\' || SUBSTR("ДатаРождения", 1, 2) '
                'ELSE SUBSTR("ДатаРождения", 1, 10) '
                'END'
            )

            d_params: tuple = ()

            # А) 1 или 2 цифры -> ДЕНЬ РОЖДЕНИЯ (день 1..31)
            if len(digits) in (1, 2):
                day_padded = digits.zfill(2)
                date_sql = f'(SUBSTR({date_norm_expr}, 9, 2) = ?)'
                d_params = (day_padded,)

            # Б) 3 или 4 цифры -> ДЕНЬ (первые 2) + МЕСЯЦ (следующие 2)
            elif len(digits) in (3, 4):
                day_str = digits[:2].zfill(2)
                month_str = digits[2:].zfill(2)
                date_sql = (
                    f'(SUBSTR({date_norm_expr}, 9, 2) = ? '
                    f'AND SUBSTR({date_norm_expr}, 6, 2) = ?)'
                )
                d_params = (day_str, month_str)

            # В) 5+ цифр -> ДЕНЬ + МЕСЯЦ + ГОД
            else:
                day_str = digits[:2]
                month_str = digits[2:4]
                year_str = digits[4:]
                date_sql = (
                    f'(SUBSTR({date_norm_expr}, 9, 2) = ? '
                    f'AND SUBSTR({date_norm_expr}, 6, 2) = ? '
                    f'AND SUBSTR({date_norm_expr}, 1, 4) LIKE ?)'
                )
                d_params = (day_str, month_str, f"%{year_str}%")

            # Вариант 1A: Начало Фамилии + Дата
            low_l, cap_l, up_l = get_case_variants(letters)
            sql_fam_start = f"""
                SELECT * FROM "Клиенты"
                WHERE ("Фамилия" LIKE ? OR "Фамилия" LIKE ? OR "Фамилия" LIKE ?)
                  AND {date_sql}
                ORDER BY "Фамилия" ASC LIMIT ?
            """
            params_a = (f"{low_l}%", f"{cap_l}%", f"{up_l}%") + d_params + (limit,)
            cursor.execute(sql_fam_start, params_a)
            rows = [dict(r) for r in cursor.fetchall()]
            
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
                ) + otch_params + d_params + (limit,)

                cursor.execute(sql_inits, params_b)
                rows = [dict(r) for r in cursor.fetchall()]
                
                if rows:
                    return rows

        # ----------------------------------------------------------------------
        # 2. ПОИСК: ТОЛЬКО БУКВЫ (например: соля, слс, сдг)
        # ----------------------------------------------------------------------
        match_letters = re.match(r"^([а-яА-ЯёЁa-zA-Z]{1,10})$", q_clean)
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
                if rows:
                    return rows

        # ----------------------------------------------------------------------
        # 3. ОБЩИЙ СКВОЗНОЙ ПОИСК
        # ----------------------------------------------------------------------
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
        return rows

    except Exception as e:
        logger.error(f"Ошибка при выполнении поиска клиентов: {e}", exc_info=True)
        return []
    finally:
        conn.close()


def search_clients(query: str, limit: int = 200) -> List[Dict[str, Any]]:
    return search_clients_for_completer(query, limit=limit)


# ==============================================================================
# 5. СОХРАНЕНИЕ И ОБНОВЛЕНИЕ КЛИЕНТОВ
# ==============================================================================


def normalize_date_for_storage(value: Any) -> Optional[str]:
    """Приводит дату к единому формату хранения YYYY-MM-DD."""
    if value is None:
        return None

    s = str(value).strip()
    if not s or "_" in s:
        return None

    s = s.split(" ")[0].split("T")[0]

    if "." in s:
        parts = s.split(".")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            day, month, year = parts
            if len(year) == 4:
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        return s

    if "-" in s:
        parts = s.split("-")
        if len(parts) == 3 and len(parts[0]) == 4 and all(p.isdigit() for p in parts):
            year, month, day = parts
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        return s

    return s


def save_client(client_data: Dict[str, Any]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        client_id = client_data.get("id")
        street_clean = normalize_street_name(client_data.get("Улица", ""))
        birth_clean = normalize_date_for_storage(client_data.get("ДатаРождения"))
        issued_clean = normalize_date_for_storage(client_data.get("ДатаВыдачи"))
        
        # Нормализуем ФИО и паспорт для ускоренного поиска
        surname = client_data.get("Фамилия") or ""
        name = client_data.get("Имя") or ""
        patronymic = client_data.get("Отчество") or ""
        search_fio = f"{surname.lower()} {name.lower()} {patronymic.lower()}".strip()
        
        ser_pas = client_data.get("СерПасп") or ""
        psp_nom = client_data.get("ПспНом") or ""
        search_passport = f"{ser_pas}{psp_nom}".replace(" ", "").lower()

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
                    "Квартира"          = ?,
                    "search_fio"        = ?,
                    "search_passport"   = ?
                WHERE "id" = ?
                """,
                (
                    client_data.get("Фамилия"),
                    client_data.get("Имя"),
                    client_data.get("Отчество"),
                    client_data.get("Пол"),
                    birth_clean,
                    client_data.get("СерПасп"),
                    client_data.get("ПспНом"),
                    client_data.get("ПаспортВыданМесто"),
                    issued_clean,
                    client_data.get("Область"),
                    client_data.get("Город"),
                    client_data.get("Район"),
                    street_clean,
                    client_data.get("Дом"),
                    client_data.get("Квартира"),
                    search_fio,
                    search_passport,
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
                                       "Область", "Город", "Район", "Улица", "Дом", "Квартира",
                                       "search_fio", "search_passport")
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_data.get("Фамилия"),
                    client_data.get("Имя"),
                    client_data.get("Отчество"),
                    client_data.get("Пол"),
                    birth_clean,
                    client_data.get("СерПасп"),
                    client_data.get("ПспНом"),
                    client_data.get("ПаспортВыданМесто"),
                    issued_clean,
                    client_data.get("Область"),
                    client_data.get("Город"),
                    client_data.get("Район"),
                    street_clean,
                    client_data.get("Дом"),
                    client_data.get("Квартира"),
                    search_fio,
                    search_passport,
                ),
            )
            conn.commit()
            return cursor.lastrowid
    finally:
        conn.close()


def update_client(client_data: Dict[str, Any]) -> bool:
    return bool(save_client(client_data))


def get_client_by_id(client_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM "Клиенты" WHERE "id" = ?', (client_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def check_duplicate_client(client_data: Dict[str, Any], exclude_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Проверяет наличие дубликата клиента по ФИО + дата рождения или паспорт.
    Возвращает найденного дубликата или None.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        surname = (client_data.get("Фамилия") or "").strip().lower()
        name = (client_data.get("Имя") or "").strip().lower()
        patronymic = (client_data.get("Отчество") or "").strip().lower()
        birth_date = normalize_date_for_storage(client_data.get("ДатаРождения"))
        ser_pas = (client_data.get("СерПасп") or "").strip()
        psp_nom = (client_data.get("ПспНом") or "").strip()
        
        if not surname or not name or not birth_date:
            return None
        
        # Формируем условия поиска
        conditions = []
        params = []
        
        # Поиск по ФИО + дата рождения
        fio_birth_cond = """
            (LOWER("Фамилия") = ? AND LOWER("Имя") = ? 
             AND (LOWER(COALESCE("Отчество", "")) = ? OR (? = '' AND "Отчество" IS NULL))
             AND "ДатаРождения" = ?)
        """
        conditions.append(fio_birth_cond)
        params.extend([surname, name, patronymic, patronymic, birth_date])
        
        # Поиск по паспорту (если заполнен)
        if ser_pas and psp_nom:
            passport_cond = '(COALESCE("СерПасп", "") = ? AND COALESCE("ПспНом", "") = ?)'
            conditions.append(passport_cond)
            params.extend([ser_pas, psp_nom])
        
        # Объединяем условия через OR
        where_clause = " OR ".join(conditions)
        
        # Исключаем текущего клиента при обновлении
        if exclude_id:
            where_clause += f' AND "id" != ?'
            params.append(exclude_id)
        
        sql = f'SELECT * FROM "Клиенты" WHERE {where_clause} LIMIT 1'
        cursor.execute(sql, params)
        row = cursor.fetchone()
        
        if row:
            duplicate = dict(row)
            logger.warning(
                f"Найден возможный дубликат клиента: ID={duplicate['id']}, "
                f"ФИО={duplicate['Фамилия']} {duplicate['Имя']} {duplicate.get('Отчество', '')}"
            )
            return duplicate
        
        return None
    except Exception as e:
        logger.error(f"Ошибка при проверке дубликата клиента: {e}", exc_info=True)
        return None
    finally:
        conn.close()


# ==============================================================================
# 6. СДЕЛКИ И СТАТИСТИКА
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


def get_spreadsheet_data_for_period(start_date: str, end_date: str) -> List[List[str]]:
    """
    Получает данные для экспорта в Excel за указанный период.
    Возвращает список строк с данными:
    [Номер справки, Дата выдачи, Действительна до, Фамилия, Имя, Отчество, 
     Дата рождения, Адрес, Заключение, Примечание]
    """
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
    
    sql_date_conv = """
        CASE 
            WHEN "Дата" LIKE '__.__.____' THEN 
                SUBSTR("Дата", 7, 4) || '-' || SUBSTR("Дата", 4, 2) || '-' || SUBSTR("Дата", 1, 2)
            ELSE "Дата"
        END
    """
    
    try:
        # Запрос для ГИБДД
        query_gibdd = f"""
            SELECT 
                s."ВыданаСправка№" AS "НомерСправки",
                s."Дата" AS "ДатаВыдачи",
                s."Сроком" AS "ДействительнаДо",
                c."Фамилия",
                c."Имя",
                c."Отчество",
                c."ДатаРождения",
                COALESCE(c."Улица", '') || ', д. ' || COALESCE(c."Дом", '') || 
                    CASE WHEN c."Квартира" IS NOT NULL AND c."Квартира" != '' THEN ', кв. ' || c."Квартира" ELSE '' END AS "Адрес",
                'Годен' AS "Заключение",
                COALESCE(s."Примечание", '') AS "Примечание"
            FROM "Сделки" s
            JOIN "Клиенты" c ON s."КлиентID" = c."rowid"
            WHERE {sql_date_conv} >= ? AND {sql_date_conv} <= ?
        """
        cursor.execute(query_gibdd, (start_iso, end_iso))
        rows_gibdd = cursor.fetchall()
        
        # Запрос для Оружия
        query_weapon = f"""
            SELECT 
                w."Справка№" AS "НомерСправки",
                w."Дата" AS "ДатаВыдачи",
                '' AS "ДействительнаДо",
                c."Фамилия",
                c."Имя",
                c."Отчество",
                c."ДатаРождения",
                COALESCE(c."Улица", '') || ', д. ' || COALESCE(c."Дом", '') || 
                    CASE WHEN c."Квартира" IS NOT NULL AND c."Квартира" != '' THEN ', кв. ' || c."Квартира" ELSE '' END AS "Адрес",
                'Годен' AS "Заключение",
                COALESCE(w."Примечание", '') AS "Примечание"
            FROM "Справки_Оружие" w
            JOIN "Клиенты" c ON w."КлиентID" = c."rowid"
            WHERE {sql_date_conv} >= ? AND {sql_date_conv} <= ?
        """
        cursor.execute(query_weapon, (start_iso, end_iso))
        rows_weapon = cursor.fetchall()
        
        # Объединяем результаты
        all_rows = []
        for row in rows_gibdd:
            all_rows.append([
                str(row["НомерСправки"] or ""),
                row["ДатаВыдачи"] or "",
                row["ДействительнаДо"] or "",
                row["Фамилия"] or "",
                row["Имя"] or "",
                row["Отчество"] or "",
                row["ДатаРождения"] or "",
                row["Адрес"] or "",
                row["Заключение"] or "",
                row["Примечание"] or ""
            ])
        
        for row in rows_weapon:
            all_rows.append([
                str(row["НомерСправки"] or ""),
                row["ДатаВыдачи"] or "",
                row["ДействительнаДо"] or "",
                row["Фамилия"] or "",
                row["Имя"] or "",
                row["Отчество"] or "",
                row["ДатаРождения"] or "",
                row["Адрес"] or "",
                row["Заключение"] or "",
                row["Примечание"] or ""
            ])
        
        # Сортируем по дате выдачи
        all_rows.sort(key=lambda x: x[1], reverse=True)
        
        return all_rows
        
    except Exception as e:
        logger.error(f"Ошибка получения данных для экспорта: {e}", exc_info=True)
        return []
    finally:
        conn.close()


def get_client_deals(client_id: int) -> List[Dict[str, Any]]:
    """
    Возвращает объединенную историю всех справок пациента
    (ГИБДД и Оружие), отсортированную по убыванию даты/ID.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT 
                "НомДоговора",
                'ГИБДД' AS "Тип",
                "Дата",
                "ВыданаСправка№" AS "НомерСправки",
                "СуммаДоговора",
                "rowid" AS "sort_id"
            FROM "Сделки"
            WHERE "КлиентID" = ?

            UNION ALL

            SELECT 
                "НомДоговора",
                'Оружие' AS "Тип",
                "Дата",
                "Справка№" AS "НомерСправки",
                "СуммаДоговора",
                "rowid" AS "sort_id"
            FROM "Справки_Оружие"
            WHERE "КлиентID" = ?

            ORDER BY "sort_id" DESC
        """
        cursor.execute(query, (client_id, client_id))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f"Ошибка при получении сделок клиента ID {client_id}: {e}", exc_info=True)
        return []
    finally:
        conn.close()


def get_districts_list() -> List[str]:
    init_reference_tables()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT "НазРайона" FROM "Районы_НН" ORDER BY "НазРайона" ASC')
        rows = [r["НазРайона"] for r in cursor.fetchall() if r["НазРайона"]]
        return rows
    except Exception as e:
        logger.error(f"Ошибка чтения справочника 'Районы_НН': {e}", exc_info=True)
        return []
    finally:
        conn.close()


def get_uvd_list() -> List[str]:
    init_reference_tables()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT "Название" FROM "УВД" ORDER BY "Название" ASC')
        rows = [r["Название"] for r in cursor.fetchall() if r["Название"]]
        return rows
    except Exception as e:
        logger.error(f"Ошибка чтения справочника 'УВД': {e}", exc_info=True)
        return []
    finally:
        conn.close()