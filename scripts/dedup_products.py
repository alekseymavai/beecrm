"""
Дедупликация товаров в beecrm.
Dry run по умолчанию. Добавьте --delete для удаления.

typeId=18 (Товары в beecrm), Название = value поля объекта.
"""
import sys
from collections import defaultdict

import requests

IAM = "https://ai2o.online/api/v2/iam"
LOGIN = "alekseymavai@gmail.com"
PASSWORD = "alekseymavai"

BEECRM_BASE = "https://ai2o.online/api/v2/beecrm"
TYPE_PRODUCTS = 18


def get_token() -> str:
    r = requests.post(f"{IAM}/login", json={"email": LOGIN, "password": PASSWORD}, timeout=15)
    r.raise_for_status()
    return r.json()["accessToken"]


def list_all(token: str, type_id: int) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    all_rows = []
    page = 1
    while True:
        r = requests.get(
            f"{BEECRM_BASE}/objects",
            headers=headers,
            params={"typeId": type_id, "page": page, "pageSize": 100},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        # Ответ: {"ok":true,"data":[...]}  или {"ok":true,"data":{"rows":[...]}}
        raw = data.get("data", data) if isinstance(data, dict) else data
        rows = raw if isinstance(raw, list) else raw.get("rows", raw.get("items", []))
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < 100:
            break
        page += 1
    return all_rows


def delete_obj(token: str, obj_id: int) -> bool:
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.delete(f"{BEECRM_BASE}/objects/{obj_id}", headers=headers, timeout=15)
    return r.ok


def get_name(obj: dict) -> str:
    return (obj.get("value") or "").strip()


def main():
    do_delete = "--delete" in sys.argv

    print("=== Аутентификация ===")
    token = get_token()
    print("OK")

    print(f"\n=== Загрузка товаров beecrm (typeId={TYPE_PRODUCTS}) ===")
    products = list_all(token, TYPE_PRODUCTS)
    print(f"Всего записей: {len(products)}")

    # Группируем по имени
    by_name: dict[str, list[dict]] = defaultdict(list)
    for p in products:
        by_name[get_name(p)].append(p)

    # Дубликаты
    to_delete: list[dict] = []
    dups = {name: items for name, items in by_name.items() if len(items) > 1}

    print(f"\n=== Дубликаты: {len(dups)} уникальных имён, {sum(len(v)-1 for v in dups.values())} лишних ===")
    for i, (name, items) in enumerate(sorted(dups.items()), 1):
        ids = [p["id"] for p in items]
        print(f"  [{i}] {name!r}: {len(items)}x → keep id={ids[0]}, delete {ids[1:]}")
        to_delete.extend(items[1:])

    if not dups:
        print("  (дублей не найдено)")

    # Пустые имена
    empty = [p for p in products if not get_name(p)]
    if empty:
        print(f"\n  ВНИМАНИЕ: {len(empty)} записей с пустым именем: ids={[p['id'] for p in empty]}")

    print(f"\n=== Итог ===")
    print(f"  Сейчас в beecrm:     {len(products)}")
    print(f"  Лишних дублей:       {len(to_delete)}")
    print(f"  После очистки будет: {len(products) - len(to_delete)}")

    if not do_delete:
        print("\n[DRY RUN] Добавьте --delete для удаления.")
        return

    # Удаление
    print(f"\n=== Удаление {len(to_delete)} записей ===")
    ok = 0
    fail = 0
    for p in to_delete:
        if delete_obj(token, p["id"]):
            ok += 1
            print(f"  ✓ id={p['id']} {get_name(p)!r}")
        else:
            fail += 1
            print(f"  ✗ ОШИБКА id={p['id']} {get_name(p)!r}")

    print(f"\nГотово: удалено {ok}, ошибок {fail}")
    final = list_all(token, TYPE_PRODUCTS)
    print(f"Итого в beecrm после удаления: {len(final)}")


if __name__ == "__main__":
    main()
