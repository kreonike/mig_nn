import os
import re
import sqlite3
import sys
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MIG_NN")

# Импортируем модуль ежедневного бэкапа
from backup import make_daily_backup


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
    conn.execute(
        'CREATE INDEX IF NOT EXISTS "idx_клиенты_рождение" ON "Клиенты" ("ДатаРождения");'
    )
    return conn


# ==============================================================================
# 1. ИНИЦИАЛИЗАЦИЯ И ТАБЛИЦЫ СПРАВОЧНИКОВ
# ==============================================================================

def init_reference_tables():
    """Создает таблицы справочников, пресетов и тарифов, если они отсутствуют."""
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
                'INSERT INTO "Пресеты_ГИБДД" ("Название", "Категории", "Сумма") VALUES (?, ?, ?)',
                [
                    ("Легковые (A, B)", "A, B", 500.0),
                    ("Грузовые / Автобусы (C, D)", "C, D, CE, DE", 1000.0),
                    ("Медосмотр с наркологом и психиатром", "A, B, C, D", 1500.0),
                ]
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
                ]
            )

        conn.commit()
    except Exception as e:
        logger.error(f"Ошибка инициализации справочников: {e}", exc_info=True)
    finally:
        conn.close()


def get_reference_table(table_name: str) -> List[Dict[str, Any]]:
    """Возвращает таблицу справочника с безопасной обработкой типов."""
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
    """Добавляет новую запись в произвольный справочник."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        keys = list(item_data.keys())
        cols = ", ".join([f'"{k}"' for k in keys])
        placeholders = ", ".join(["?"] * len(keys))
        values = [item_data[k] for k in keys]

        cursor.execute(f'INSERT INTO "{table_name}" ({cols}) VALUES ({placeholders})', values)
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка добавления записи в '{table_name}': {e}", exc_info=True)
        return False
    finally:
        conn.close()


def delete_reference_item(table_name: str, item_id: int) -> bool:
    """Удаляет запись из справочника по ID."""
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


def update_reference_item(table_name: str, item_id: int, item_data: Dict[str, Any]) -> bool:
    """Универсальное обновление записи в любом справочнике."""
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
        logger.error(f"Ошибка обновления справочника '{table_name}' ID {item_id}: {e}", exc_info=True)
        return False
    finally:
        conn.close()


# ==============================================================================
# 2. УПРАВЛЕНИЕ ТАРИФАМИ И ПРЕСЕТАМИ (УМНАЯ ОБРАБОТКА СДВИГА АРГУМЕНТОВ)
# ==============================================================================

def _parse_price_value(val: Any) -> float:
    """Безопасно преобразует любое значение цены в float."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    s_val = str(val).strip().replace(',', '.')
    s_val = re.sub(r'[^\d.]', '', s_val)
    try:
        return float(s_val) if s_val else 0.0
    except ValueError:
        return 0.0


def get_presets_list(preset_type: str = "ГИБДД") -> List[Dict[str, Any]]:
    """Возвращает пресеты/тарифы ГИБДД с четкими ключами и типами."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        init_reference_tables()
        cursor.execute('SELECT "id", "Название", "Категории", "Сумма" FROM "Пресеты_ГИБДД"')
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
    """
    Разбирает вызовы любой сигнатуры из ui_references.py:
    1. update_preset_item(preset_id, item_dict)
    2. update_preset_item(preset_id, 'ГИБДД', name, categories, price)
    3. update_preset_item(preset_id, name, categories, price)
    """
    logger.info(f"[PRESET_UPDATE] Сырые аргументы: args={args}, kwargs={kwargs}")

    preset_id = None
    preset_name = ""
    preset_cats = ""
    preset_price = 0.0

    # 1. Распаковка kwargs
    if "preset_id" in kwargs:
        preset_id = kwargs["preset_id"]
    if "id" in kwargs:
        preset_id = kwargs["id"]

    # 2. Распаковка позиционных args
    all_args = list(args)

    if all_args:
        # Второй аргумент может быть словарем
        if len(all_args) >= 2 and isinstance(all_args[1], dict):
            preset_id = all_args[0]
            d = all_args[1]
            preset_name = d.get("Название") or d.get("title") or d.get("name") or ""
            preset_cats = d.get("Категории") or d.get("categories") or ""
            preset_price = _parse_price_value(d.get("Сумма") if "Сумма" in d else d.get("price"))
        else:
            # Отфильтровываем строковый тип 'ГИБДД', если он передан в аргументах
            clean_args = [a for a in all_args if str(a).strip().upper() != 'ГИБДД']

            if clean_args:
                preset_id = clean_args[0]

            # Если остались позиционные значения для названия, категорий и цены
            if len(clean_args) >= 2:
                preset_name = clean_args[1]
            if len(clean_args) >= 3:
                preset_cats = clean_args[2]
            if len(clean_args) >= 4:
                preset_price = _parse_price_value(clean_args[3])

    # Проверяем kwargs если значения не найдены в args
    if not preset_name and ("title" in kwargs or "Название" in kwargs or "name" in kwargs):
        preset_name = kwargs.get("title") or kwargs.get("Название") or kwargs.get("name")
    if not preset_cats and ("categories" in kwargs or "Категории" in kwargs):
        preset_cats = kwargs.get("categories") or kwargs.get("Категории")
    if preset_price == 0.0 and ("price" in kwargs or "Сумма" in kwargs):
        preset_price = _parse_price_value(kwargs.get("price") if "price" in kwargs else kwargs.get("Сумма"))

    if preset_id is None:
        logger.error("[PRESET_UPDATE] Не удалось определить preset_id!")
        return False

    logger.info(f"[PRESET_UPDATE] Итоговые распарсенные данные: id={preset_id}, name='{preset_name}', categories='{preset_cats}', price={preset_price}")

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
        logger.info(f"[PRESET_UPDATE] Обновление успешно выполнено. Затронуто строк: {cursor.rowcount}")
        return True
    except Exception as e:
        logger.error(f"[PRESET_UPDATE] Ошибка записи пресета в БД: {e}", exc_info=True)
        return False
    finally:
        conn.close()


def add_preset_item(*args, **kwargs) -> bool:
    """Добавляет новый пресет ГИБДД с гибким разбором аргументов."""
    logger.info(f"[PRESET_ADD] Сырые аргументы: args={args}, kwargs={kwargs}")

    preset_name = ""
    preset_cats = ""
    preset_price = 0.0

    all_args = list(args)
    clean_args = [a for a in all_args if str(a).strip().upper() != 'ГИБДД']

    if clean_args and isinstance(clean_args[0], dict):
        d = clean_args[0]
        preset_name = d.get("Название") or d.get("title") or d.get("name") or ""
        preset_cats = d.get("Категории") or d.get("categories") or ""
        preset_price = _parse_price_value(d.get("Сумма") if "Сумма" in d else d.get("price"))
    else:
        if len(clean_args) >= 1:
            preset_name = clean_args[0]
        if len(clean_args) >= 2:
            preset_cats = clean_args[1]
        if len(clean_args) >= 3:
            preset_price = _parse_price_value(clean_args[2])

    if not preset_name and ("title" in kwargs or "Название" in kwargs or "name" in kwargs):
        preset_name = kwargs.get("title") or kwargs.get("Название") or kwargs.get("name")
    if not preset_cats and ("categories" in kwargs or "Категории" in kwargs):
        preset_cats = kwargs.get("categories") or kwargs.get("Категории")
    if preset_price == 0.0 and ("price" in kwargs or "Сумма" in kwargs):
        preset_price = _parse_price_value(kwargs.get("price") if "price" in kwargs else kwargs.get("Сумма"))

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
        logger.info(f"[PRESET_ADD] Пресет успешно добавлен. ID: {cursor.lastrowid}")
        return True
    except Exception as e:
        logger.error(f"[PRESET_ADD] Ошибка добавления пресета: {e}", exc_info=True)
        return False
    finally:
        conn.close()


def delete_preset_item(preset_id: int) -> bool:
    """Удаляет пресет ГИБДД по ID."""
    logger.info(f"[PRESET_DELETE] Удаление пресета ID: {preset_id}")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM "Пресеты_ГИБДД" WHERE "id" = ?', (int(preset_id),))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"[PRESET_DELETE] Ошибка удаления пресета ID {preset_id}: {e}", exc_info=True)
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


def merge_multiple_streets_in_db(old_streets: List[str], target_street: str) -> int:
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
# 4. РАБОТА С ПАЦИЕНТАМИ (КЛИЕНТАМИ)
# ==============================================================================

def search_clients_for_completer(
        query: str, limit: int = 100
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        raw_q = str(query or "").strip()
        clean_q = raw_q.lower()

        if not clean_q:
            cursor.execute('SELECT * FROM "Клиенты" LIMIT ?', (limit,))
            return [dict(row) for row in cursor.fetchall()]

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
        logger.error(f"Ошибка поиска клиентов: {e}", exc_info=True)
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


def get_statistics_for_period(start_date: str, end_date: str) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT COUNT(*) as cnt, SUM(CAST("СуммаДоговора" AS REAL)) as total
            FROM "Сделки"
            WHERE "Дата" >= ? AND "Дата" <= ?
            """,
            (start_date, end_date),
        )
        gibdd_row = cursor.fetchone()

        weapon_cnt, weapon_total = 0, 0.0
        try:
            cursor.execute(
                """
                SELECT COUNT(*) as cnt, SUM(CAST("СуммаДоговора" AS REAL)) as total
                FROM "Справки_Оружие"
                WHERE "Дата" >= ? AND "Дата" <= ?
                """,
                (start_date, end_date),
            )
            weapon_row = cursor.fetchone()
            if weapon_row:
                weapon_cnt = weapon_row["cnt"] or 0
                weapon_total = weapon_row["total"] or 0.0
        except Exception:
            pass

        gibdd_cnt = gibdd_row["cnt"] if gibdd_row else 0
        gibdd_total = gibdd_row["total"] if (gibdd_row and gibdd_row["total"]) else 0.0

        return {
            "gibdd_count": gibdd_cnt,
            "gibdd_total": gibdd_total,
            "weapon_count": weapon_cnt,
            "weapon_total": weapon_total,
            "total_count": gibdd_cnt + weapon_cnt,
            "total_sum": gibdd_total + weapon_total,
        }
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}", exc_info=True)
        return {
            "gibdd_count": 0, "gibdd_total": 0.0,
            "weapon_count": 0, "weapon_total": 0.0,
            "total_count": 0, "total_sum": 0.0
        }
    finally:
        conn.close()


def get_districts_list() -> List[str]:
    return ["Автозаводский", "Сормовский", "Нижегородский", "Советский", "Приокский"]


def get_uvd_list() -> List[str]:
    return ["УВД Нижегородского района", "УВД Автозаводского района", "УВД Сормовского района"]