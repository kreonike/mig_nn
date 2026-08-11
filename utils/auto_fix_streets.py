import os
import re
import sqlite3
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict
import pandas as pd
from rapidfuzz import process, fuzz
from tqdm import tqdm


# ==========================================
# КОНФИГУРАЦИЯ ДЛЯ MIG_DATABASE.DB
# ==========================================
@dataclass
class Config:
    # Файл базы данных SQLite
    DB_PATH: str = "/Users/kreonike/PycharmProjects/mig_nn/mig_database.db"

    # Таблица и колонка с улицами
    TABLE_NAME: str = "Клиенты"
    STREET_COLUMN: str = "Улица"

    # Режим работы:
    # True = только проверка и выгрузка отчетов (база НЕ перезаписывается)
    # False = замена значений и запись изменений в БД SQLite!
    DRY_RUN: bool = True

    # Дефолтный префикс для улиц без указанного типа
    DEFAULT_PREFIX: str = "ул."

    # Порог для исправления нечетких опечаток
    TYPO_THRESHOLD: float = 88.0

    # Файлы отчетов
    CHANGES_LOG_CSV: str = "changes_applied.csv"
    CHANGES_SUMMARY_TXT: str = "all_changes_summary.txt"
    REFERENCE_LOG_CSV: str = "official_streets_reference.csv"


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("auto_fix_streets.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# ==========================================
# ОФИЦИАЛЬНЫЙ СЛОВАРЬ ЭТАЛОНОВ УЛИЦ НН И ОБЛАСТИ
# ==========================================
OFFICIAL_NN_STREETS = [
    "ул. 60 лет Октября",
    "ул. 40 лет Победы",
    "ул. Коминтерна",
    "ул. Чаадаева",
    "ул. Академика Сахарова",
    "ул. Академика Макарова",
    "ул. Светлоярская",
    "ул. Светлогорская",
    "ул. Белинского",
    "ул. Ванеева",
    "ул. Родионова",
    "ул. Гаугеля",
    "ул. Зайцева",
    "ул. Пермякова",
    "ул. Баренца",
    "ул. Казанская",
    "ул. Клинкерная",
    "ул. Механизаторов",
    "ул. Алебастровая",
    "ул. Березовская",
    "ул. Красноармейская",
    "ул. Краснодарская",
    "пр-кт Кораблестроителей",
    "пр-кт Гагарина",
    "пр-кт Ленина",
    "пр-кт Героев",
    "пр-кт Союзный",
    "пр-кт Ильича",
    "пр-кт Молодежный",
    "пр-кт Октября",
    "пр-кт Бусыгина",
    "б-р Юбилейный",
    "б-р Мира",
    "б-р Заречный",
    "пер. Котельный",
    "пер. Кровельный",
    "пер. Союзный",
    "пер. Райниса",
    "пер. Парковый",
    "ул. Московское шоссе",
]

# ==========================================
# НОРМАЛИЗАЦИЯ И РАЗБОР ТОПОНИМОВ
# ==========================================
PREFIX_PATTERNS = [
    (r"\b(пр-кт|проспект|пр)\b\.?", "пр-кт"),
    (r"\b(ул|улица)\b\.?", "ул."),
    (r"\b(пер|переулок)\b\.?", "пер."),
    (r"\b(б-р|бульвар|бул)\b\.?", "б-р"),
    (r"\b(пр-д|проезд)\b\.?", "пр-д"),
    (r"\b(ш|шоссе)\b\.?", "ш."),
    (r"\b(пл|площадь)\b\.?", "пл."),
    (r"\b(наб|набережная)\b\.?", "наб."),
    (r"\b(ал|аллея)\b\.?", "аллея"),
    (r"\b(снт|днт|тсн)\b\.?", "СНТ"),
    (r"\b(поселок|пос|п)\b\.?", "пос."),
    (r"\b(деревня|д)\b\.?", "д."),
    (r"\b(микрорайон|мкр|м-н)\b\.?", "мкр."),
    (r"\b(тракт)\b\.?", "тракт"),
]


def parse_street(raw_name: str) -> Tuple[str, str]:
    """Разделяет строку на тип топонима и собственное имя, исправляя пропущенные пробелы."""
    if not isinstance(raw_name, str) or not raw_name.strip():
        return "", ""

    text = raw_name.strip()
    text = text.replace("ё", "е").replace("Ё", "Е")

    # 1. Исправление опечаток со склеенными словами и цифрами
    # 'летОктября' -> 'лет Октября'
    text = re.sub(r"([а-яяа-я])([А-ЯЁ])", r"\1 \2", text)
    # '60лет' -> '60 лет'
    text = re.sub(r"(\d+)([а-яА-Яa-zA-Z])", r"\1 \2", text)
    # 'лет60' -> 'лет 60'
    text = re.sub(r"([а-яА-Яa-zA-Z])(\d+)", r"\1 \2", text)

    # Убираем повторные пробелы
    text = re.sub(r"\s+", " ", text)

    found_type = ""

    # Выделяем тип топонима
    for pattern, normalized_type in PREFIX_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            found_type = normalized_type
            text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
            break

    # Очищаем имя от точек и запятых по краям
    clean_name = re.sub(r"^[.,\s\-]+|[.,\s\-]+$", "", text)

    # Корректируем регистр (Title Case)
    if clean_name.isupper():
        clean_name = clean_name.title()
    elif len(clean_name) > 0:
        clean_name = clean_name[0].upper() + clean_name[1:]

    return found_type, clean_name


def format_street_fullname(prefix: str, name: str, default_prefix: str = "ул.") -> str:
    """Собирает полное наименование, подставляя 'ул.' при отсутствии типа."""
    name = name.strip()
    if not name:
        return ""

    actual_prefix = prefix if prefix else default_prefix
    return f"{actual_prefix} {name}".strip()


# ==========================================
# ОСНОВНОЙ АЛГОРИТМ ОЧИСТКИ И ИСПРАВЛЕНИЯ ОПЕЧАТОК
# ==========================================
class StreetFixer:
    def __init__(self, reference_streets: List[str] = None, typo_threshold: float = 88.0, default_prefix: str = "ул."):
        self.typo_threshold = typo_threshold
        self.default_prefix = default_prefix

        self.reference_streets = reference_streets if reference_streets else OFFICIAL_NN_STREETS

        self.parsed_references: Dict[str, List[Tuple[str, str]]] = {}
        for ref in self.reference_streets:
            pfx, name = parse_street(ref)
            ref_type = pfx if pfx else default_prefix
            if ref_type not in self.parsed_references:
                self.parsed_references[ref_type] = []
            self.parsed_references[ref_type].append((name, ref))

    def fix(self, raw_street: str) -> Tuple[str, float, str, Optional[str]]:
        if not isinstance(raw_street, str) or not raw_street.strip():
            return raw_street, 100.0, "Empty", None

        pfx, name = parse_street(raw_street)
        if not name:
            return raw_street, 100.0, "Empty", None

        current_type = pfx if pfx else self.default_prefix
        formatted_raw = format_street_fullname(pfx, name, self.default_prefix)

        candidate_pool = self.parsed_references.get(current_type, [])
        if candidate_pool:
            names_only = [item[0] for item in candidate_pool]
            match = process.extractOne(name, names_only, scorer=fuzz.ratio)

            if match:
                best_name, score, idx = match
                best_full_ref = candidate_pool[idx][1]

                if score >= self.typo_threshold and name.lower() != best_name.lower():
                    if len(name) > 5:
                        return best_full_ref, score, f"Typo Fixed ({score:.1f}%)", best_full_ref

        return formatted_raw, 100.0, "Formatted (Cleaned)", None


# ==========================================
# ТОЧКА ВХОДА (MAIN)
# ==========================================
def main():
    config = Config()

    print("\n" + "=" * 65)
    print("      ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ mig_database.db")
    print(
        f"  Режим работы: {'[DRY RUN] Только проверка (Без записи)' if config.DRY_RUN else '[LIVE] Запись изменений в БД'}")
    print(f"  Порог исправления опечаток: {config.TYPO_THRESHOLD}%")
    print("=" * 65 + "\n")

    if not os.path.exists(config.DB_PATH):
        logging.error(f"Файл базы данных {config.DB_PATH} не найден!")
        return

    conn = sqlite3.connect(config.DB_PATH)

    try:
        logging.info(f"Подключено к БД: {config.DB_PATH}")
        logging.info(f"Выбрана таблица: '{config.TABLE_NAME}', колонка: '{config.STREET_COLUMN}'")

        df = pd.read_sql_query(f"SELECT rowid, [{config.STREET_COLUMN}] FROM [{config.TABLE_NAME}]", conn)
    except Exception as e:
        logging.error(f"Ошибка при чтении из базы данных: {e}")
        conn.close()
        return

    logging.info(f"Загружено записей клиентов: {len(df)}")

    # Подгружаем эталонный список
    reference_list = OFFICIAL_NN_STREETS
    if os.path.exists("streets_reference.csv"):
        ref_df = pd.read_csv("streets_reference.csv")
        reference_list = list(set(OFFICIAL_NN_STREETS + ref_df.iloc[:, 0].dropna().astype(str).tolist()))

    pd.DataFrame({"official_street": reference_list}).to_csv(
        config.REFERENCE_LOG_CSV, index=False, encoding="utf-8-sig"
    )

    fixer = StreetFixer(
        reference_streets=reference_list,
        typo_threshold=config.TYPO_THRESHOLD,
        default_prefix=config.DEFAULT_PREFIX
    )

    results = []
    applied_changes = []
    typos_count = 0

    logging.info("Старт нормализации и исправления опечаток...")

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Обработка БД"):
        raw_val = str(row.get(config.STREET_COLUMN, "")) if pd.notna(row.get(config.STREET_COLUMN)) else ""
        db_rowid = row.get("rowid")

        fixed_val, score, status, suggested_ref = fixer.fix(raw_val)
        results.append(fixed_val)

        if raw_val != fixed_val:
            if "Typo Fixed" in status:
                typos_count += 1

            applied_changes.append({
                "db_rowid": db_rowid,
                "original": raw_val,
                "fixed": fixed_val,
                "status": status,
                "similarity_score": round(score, 2)
            })

    print("\n" + "-" * 65)
    logging.info(f"Всего строк в БД обработано: {len(df)}")
    logging.info(f"Всего изменено/нормализовано улиц: {len(applied_changes)}")
    logging.info(f"Из них исправлено явных опечаток: {typos_count}")
    print("-" * 65)

    if applied_changes:
        df_changes = pd.DataFrame(applied_changes)
        df_changes.to_csv(config.CHANGES_LOG_CSV, index=False, encoding="utf-8-sig")

        with open(config.CHANGES_SUMMARY_TXT, "w", encoding="utf-8") as f:
            f.write("=================================================================\n")
            f.write(f"     ПОЛНЫЙ СПИСОК ВСЕХ ЗАМЕН УЛИЦ (Всего: {len(applied_changes)} | Опечаток: {typos_count})\n")
            f.write("=================================================================\n\n")
            for item in applied_changes:
                f.write(f"[ID {item['db_rowid']}] ({item['status']}): '{item['original']}'  ==>  '{item['fixed']}'\n")

        logging.info(f"✅ Отчет о заменах сохранен в: {config.CHANGES_SUMMARY_TXT}")

    # Запись результатов в БД SQLite при DRY_RUN = False
    if not config.DRY_RUN:
        logging.info("Запись обновленных улиц в базу данных SQLite...")
        cursor = conn.cursor()
        for change in applied_changes:
            cursor.execute(
                f"UPDATE [{config.TABLE_NAME}] SET [{config.STREET_COLUMN}] = ? WHERE rowid = ?",
                (change["fixed"], change["db_rowid"])
            )
        conn.commit()
        logging.info("✅ Все изменения успешно записаны в mig_database.db!")
    else:
        logging.info("ℹ️  Запуск завершен в режиме DRY_RUN. Изменения в БД НЕ внесены.")
        logging.info("    Для записи в БД установите DRY_RUN = False в Config.")

    conn.close()


if __name__ == "__main__":
    main()