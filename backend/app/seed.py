"""SeedScript (U1) — idempotent demo seed. Run: `python -m app.seed`.

Seeds: 1 store (STORE01 / 데모 카페), 1 admin (admin/admin1234), 4 categories,
4~6 menus per category (external image URL placeholders), 12 tables (password = number).
Re-running skips anything that already exists.
"""
from app.db import SessionLocal, create_all
from app.models import AdminUser, Category, Menu, Store, Table
from app.security import hash_password

STORE_CODE = "STORE01"
STORE_NAME = "데모 카페"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin1234"
TABLE_COUNT = 12

_IMG = "https://placehold.co/300x200?text="

# (category_name, display_order, [(menu_name, price), ...])
CATEGORIES: list[tuple[str, int, list[tuple[str, int]]]] = [
    ("커피", 0, [("아메리카노", 4000), ("카페라떼", 4500), ("카푸치노", 4500),
                 ("바닐라라떼", 5000), ("에스프레소", 3500)]),
    ("음료", 1, [("아이스티", 4000), ("레몬에이드", 5000), ("자몽에이드", 5000),
                 ("생수", 1500), ("콜라", 2500)]),
    ("디저트", 2, [("치즈케이크", 6000), ("티라미수", 6500), ("초코브라우니", 5500),
                   ("마카롱", 3000)]),
    ("식사", 3, [("클럽샌드위치", 8000), ("BLT샌드위치", 7500), ("샐러드볼", 9000),
                 ("파니니", 8500), ("수프세트", 7000)]),
]


def seed() -> None:
    create_all()
    db = SessionLocal()
    try:
        # Store (idempotent by store_code)
        store = db.query(Store).filter_by(store_code=STORE_CODE).one_or_none()
        if store is None:
            store = Store(store_code=STORE_CODE, name=STORE_NAME)
            db.add(store)
            db.flush()
            print(f"+ store {STORE_CODE}")

        # Admin (idempotent by store_id + username)
        if db.query(AdminUser).filter_by(store_id=store.id, username=ADMIN_USERNAME).one_or_none() is None:
            db.add(AdminUser(store_id=store.id, username=ADMIN_USERNAME,
                             password_hash=hash_password(ADMIN_PASSWORD)))
            print(f"+ admin {ADMIN_USERNAME}")

        # Categories + menus (idempotent by name)
        for cat_name, order, menus in CATEGORIES:
            category = db.query(Category).filter_by(store_id=store.id, name=cat_name).one_or_none()
            if category is None:
                category = Category(store_id=store.id, name=cat_name, display_order=order)
                db.add(category)
                db.flush()
                print(f"+ category {cat_name}")
            for idx, (menu_name, price) in enumerate(menus):
                exists = db.query(Menu).filter_by(store_id=store.id, category_id=category.id,
                                                  name=menu_name).one_or_none()
                if exists is None:
                    db.add(Menu(store_id=store.id, category_id=category.id, name=menu_name,
                                price=price, description=f"{menu_name} 설명",
                                image_url=f"{_IMG}{menu_name}", display_order=idx))
                    print(f"  + menu {menu_name}")

        # Tables 1..N (idempotent by store_id + table_number); password = number string
        for n in range(1, TABLE_COUNT + 1):
            if db.query(Table).filter_by(store_id=store.id, table_number=n).one_or_none() is None:
                db.add(Table(store_id=store.id, table_number=n,
                             table_password_hash=hash_password(str(n))))
                print(f"+ table {n}")

        db.commit()
        print("seed complete (idempotent).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
