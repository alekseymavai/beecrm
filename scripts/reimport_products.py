"""
Вариант B: полная перезагрузка товаров beecrm из alekseymavai.

READ ONLY на alekseymavai — ни одного write-запроса!
Только чтение источника, удаление и создание в beecrm.

Запуск: python3 reimport_products.py          # dry run
        python3 reimport_products.py --go      # выполнить
"""
import sys
import time
import requests

IAM = "https://ai2o.online/api/v2/iam"
LOGIN = "alekseymavai@gmail.com"
PASSWORD = "alekseymavai"

SRC_BASE = "https://ai2o.online/api/v2/alekseymavai"
DST_BASE = "https://ai2o.online/api/v2/beecrm"

TYPE_SRC = 2163   # Товары в alekseymavai
TYPE_DST = 18     # Товары в beecrm

# Маппинг категорий: alekseymavai_id → beecrm_id
CAT_MAP = {
    157: 78,  # Продукты пчеловодства
    159: 79,  # Настойки
    161: 80,  # Программы здоровья
    163: 81,  # Мёд
    165: 82,  # Наборы
    167: 83,  # Упаковка
    169: 84,  # Свечи
    171: 85,  # Чаи и травы
}

# Колонки alekseymavai → beecrm
COL_PRICE    = "2180"   # Цена
COL_INSTOCK  = "2183"   # В наличии
COL_STOCK    = "2186"   # Остаток
COL_CATEGORY = "85846"  # Категория (ссылка)

DST_COL_NAME     = "23"
DST_COL_PRICE    = "24"
DST_COL_INSTOCK  = "27"
DST_COL_STOCK    = "30"
DST_COL_CATEGORY = "56"


def auth() -> str:
    r = requests.post(f"{IAM}/login",
                      json={"email": LOGIN, "password": PASSWORD}, timeout=15)
    r.raise_for_status()
    token = r.json().get("accessToken")
    if not token:
        raise RuntimeError(f"Auth failed: {r.text}")
    return token


def list_all(base: str, token: str, type_id: int) -> list[dict]:
    """Загрузить ВСЕ объекты типа type_id постранично. READ ONLY."""
    h = {"Authorization": f"Bearer {token}"}
    all_rows = []
    page = 1
    while True:
        r = requests.get(f"{base}/objects", headers=h,
                         params={"typeId": type_id, "page": page, "pageSize": 100},
                         timeout=30)
        r.raise_for_status()
        raw = r.json().get("data", [])
        rows = raw if isinstance(raw, list) else raw.get("rows", [])
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < 100:
            break
        page += 1
    return all_rows


def get_detail(base: str, token: str, obj_id: int) -> dict:
    """Получить объект с requisites. READ ONLY."""
    h = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{base}/objects/{obj_id}", headers=h, timeout=15)
    r.raise_for_status()
    return r.json().get("data", {})


def is_valid_product(obj: dict) -> bool:
    """Валидный товар: непустое имя, не технический объект."""
    name = (obj.get("value") or "").strip()
    if not name:
        return False
    if name.lower() in ("true", "false", "null"):
        return False
    return True


def map_to_beecrm(src_obj: dict) -> dict:
    """Преобразовать объект alekseymavai в requisites для beecrm."""
    reqs = src_obj.get("requisites") or {}
    name = (src_obj.get("value") or "").strip()

    dst_reqs = {DST_COL_NAME: name}

    if COL_PRICE in reqs and reqs[COL_PRICE]:
        dst_reqs[DST_COL_PRICE] = reqs[COL_PRICE]

    if COL_INSTOCK in reqs and reqs[COL_INSTOCK]:
        dst_reqs[DST_COL_INSTOCK] = reqs[COL_INSTOCK]

    if COL_STOCK in reqs and reqs[COL_STOCK]:
        dst_reqs[DST_COL_STOCK] = reqs[COL_STOCK]

    cat_src = reqs.get(COL_CATEGORY)
    if cat_src:
        cat_dst = CAT_MAP.get(int(cat_src))
        if cat_dst:
            dst_reqs[DST_COL_CATEGORY] = str(cat_dst)

    return {"value": name, "requisites": dst_reqs}


def delete_obj(token: str, obj_id: int) -> bool:
    h = {"Authorization": f"Bearer {token}"}
    r = requests.delete(f"{DST_BASE}/objects/{obj_id}", headers=h, timeout=15)
    return r.ok


def create_obj(token: str, name: str, requisites: dict) -> dict:
    h = {"Authorization": f"Bearer {token}"}
    body = {"typeId": TYPE_DST, "parentId": 1, "value": name, "requisites": requisites}
    r = requests.post(f"{DST_BASE}/objects", headers=h, json=body, timeout=15)
    r.raise_for_status()
    return r.json().get("data", r.json())


def main():
    do_go = "--go" in sys.argv

    print("=== Аутентификация ===")
    token = auth()
    print("OK")

    # ── Шаг 1: читаем источник alekseymavai (READ ONLY) ─────────────────────
    print(f"\n=== [1/3] Чтение источника alekseymavai (typeId={TYPE_SRC}) ===")
    src_list = list_all(SRC_BASE, token, TYPE_SRC)
    print(f"  Объектов в списке: {len(src_list)}")

    # Фильтруем - валидные товары. Берём только summary (без requisites)
    # для поиска деталей нужно загружать каждый объект отдельно
    valid_ids = [o["id"] for o in src_list if is_valid_product(o)]
    print(f"  Валидных товаров: {len(valid_ids)}")
    print(f"  Пропущено (пустые/технические): {len(src_list) - len(valid_ids)}")

    # Загружаем детали каждого валидного товара (requisites)
    print(f"  Загрузка requisites...")
    src_products = []
    for i, obj_id in enumerate(valid_ids, 1):
        detail = get_detail(SRC_BASE, token, obj_id)
        if is_valid_product(detail):
            src_products.append(detail)
        if i % 20 == 0:
            print(f"    {i}/{len(valid_ids)} загружено...")
        time.sleep(0.1)  # не перегружаем API

    print(f"  Итого товаров для импорта: {len(src_products)}")

    # ── Шаг 2: читаем beecrm ────────────────────────────────────────────────
    print(f"\n=== [2/3] Чтение beecrm (typeId={TYPE_DST}) ===")
    dst_list = list_all(DST_BASE, token, TYPE_DST)
    dst_ids = [o["id"] for o in dst_list]
    print(f"  Товаров в beecrm сейчас: {len(dst_ids)}")

    # ── Предпросмотр ────────────────────────────────────────────────────────
    print(f"\n=== Предпросмотр ===")
    print(f"  Будет удалено из beecrm:   {len(dst_ids)}")
    print(f"  Будет создано в beecrm:    {len(src_products)}")
    print("\n  Первые 5 товаров к импорту:")
    for p in src_products[:5]:
        mapped = map_to_beecrm(p)
        print(f"    - {p['value']!r}: {mapped['requisites']}")

    if not do_go:
        print("\n[DRY RUN] Запустите с --go для выполнения.")
        return

    # ── Шаг 3a: удаляем все товары из beecrm ────────────────────────────────
    print(f"\n=== [3a/3] Удаление {len(dst_ids)} товаров из beecrm ===")
    del_ok = 0
    del_fail = 0
    for obj_id in dst_ids:
        if delete_obj(token, obj_id):
            del_ok += 1
        else:
            del_fail += 1
            print(f"  ✗ ОШИБКА удаления id={obj_id}")
        time.sleep(0.05)

    print(f"  Удалено: {del_ok}, ошибок: {del_fail}")

    # ── Шаг 3b: создаём товары из alekseymavai ──────────────────────────────
    print(f"\n=== [3b/3] Создание {len(src_products)} товаров в beecrm ===")
    cr_ok = 0
    cr_fail = 0
    for i, src in enumerate(src_products, 1):
        mapped = map_to_beecrm(src)
        try:
            new_obj = create_obj(token, mapped["value"], mapped["requisites"])
            cr_ok += 1
            if i <= 5 or i % 20 == 0:
                print(f"  [{i}] ✓ id={new_obj.get('id')} {mapped['value']!r}")
        except Exception as e:
            cr_fail += 1
            print(f"  [{i}] ✗ ОШИБКА {src['value']!r}: {e}")
        time.sleep(0.1)

    print(f"\n  Создано: {cr_ok}, ошибок: {cr_fail}")

    # ── Финальная проверка ───────────────────────────────────────────────────
    print(f"\n=== Финальная проверка beecrm ===")
    final = list_all(DST_BASE, token, TYPE_DST)
    print(f"  Товаров в beecrm после импорта: {len(final)}")
    print(f"  Ожидалось: {len(src_products)}")
    if len(final) == len(src_products):
        print("  ✅ СОВПАДАЕТ")
    else:
        print(f"  ⚠️ РАСХОЖДЕНИЕ на {abs(len(final) - len(src_products))}")


if __name__ == "__main__":
    main()
