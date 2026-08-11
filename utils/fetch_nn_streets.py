import pandas as pd
import requests


def fetch_all_nn_streets():
  print("Загрузка полного списка улиц Нижнего Новгорода из OpenStreetMap...")

  # Overpass API запрос на получение всех улиц Нижнего Новгорода
  overpass_url = "http://overpass-api.de/api/interpreter"
  overpass_query = """
    [out:json];
    area["name"="Нижний Новгород"]->.searchArea;
    way["highway"]["name"](area.searchArea);
    out tags;
    """

  response = requests.get(overpass_url, params={"data": overpass_query})
  data = response.json()

  streets = set()
  for element in data.get("elements", []):
    name = element.get("tags", {}).get("name")
    if name:
      streets.add(name)

  sorted_streets = sorted(list(streets))
  print(f"Успешно загружено {len(sorted_streets)} уникальных улиц!")

  # Сохраняем в CSV
  df = pd.DataFrame({"street_name": sorted_streets})
  df.to_csv("streets_reference.csv", index=False, encoding="utf-8-sig")
  print("Справочник сохранен в файл 'streets_reference.csv'")


if __name__ == "__main__":
  fetch_all_nn_streets()