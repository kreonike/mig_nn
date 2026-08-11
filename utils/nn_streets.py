import json
import os
import re
from typing import List, Tuple
from rapidfuzz import fuzz, process

JSON_FILE = "nn_streets.json"


def strip_street_prefix(street_name: str) -> str:
    """Удаляет слова 'улица', 'ул.', 'ул' и лишние пробелы из названия улицы."""
    if not street_name:
        return ""

    s = street_name.strip()
    # Удаляем слова "улица", "ул.", "ул" с учетом регистра и возможных точек/пробелов
    s = re.sub(r"^(улица|ул\.|ул)\s+", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+(улица|ул\.|ул)$", "", s, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", s).strip()


def load_official_streets() -> List[str]:
    """Загружает список официальных улиц с очищенными от 'улица/ул' названиями."""
    raw_streets = []
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                raw_streets = json.load(f)
        except Exception as e:
            print(f"Ошибка чтения {JSON_FILE}: {e}")

    # Чистим весь эталонный справочник от слов "улица/ул."
    cleaned_streets = set()
    for st in raw_streets:
        clean = strip_street_prefix(st)
        if clean:
            cleaned_streets.add(clean)

    return sorted(list(cleaned_streets))


OFFICIAL_NN_STREETS = load_official_streets()


def find_best_street_match(
    user_street: str, threshold: int = 75
) -> Tuple[str, int]:
    """Находит наиболее похожую улицу из очищенного справочника."""
    if not user_street or not user_street.strip():
        return ("", 0)

    clean_str = strip_street_prefix(user_street)

    if not OFFICIAL_NN_STREETS:
        return (clean_str, 100)

    match = process.extractOne(
        clean_str, OFFICIAL_NN_STREETS, scorer=fuzz.token_sort_ratio
    )

    if match and match[1] >= threshold:
        return (match[0], match[1])

    return (clean_str, 0)