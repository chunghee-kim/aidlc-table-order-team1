# U1 Foundation — Domain Entities (Functional Design)

**단계**: CONSTRUCTION — Phase 0 (U1 Foundation & Data) — Functional Design
**범위**: 9개 데이터 모델의 최종 스키마(컬럼 타입·nullable·기본값·uniq·인덱스·FK·관계). ORM=SQLAlchemy, DB=SQLite 단일 파일.
**근거**: `application-design.md §2`, `component-methods.md`, 승인된 Q1~Q9(전부 권장안 A).

## 공통 규약 (Q1·Q2·Q8)
- **PK**: 전 엔티티 `id INTEGER PRIMARY KEY AUTOINCREMENT`.
- **타임스탬프**: `created_at`/`started_at`/`closed_at` 등은 **UTC** 저장(`DateTime`, 기본값 `datetime.utcnow`). 표시 변환은 프론트.
- **스키마 생성**: `Base.metadata.create_all(engine)` (Alembic 미도입).
- **금액**: `price`/`unit_price`/`total_amount` 는 `Numeric`(SQLite에선 정수 최소단위 권장, MVP는 `Integer` 원 단위 사용).
- **비밀번호**: `password_hash`/`table_password_hash` 는 bcrypt(cost 12) 해시 문자열.

---

## ERD
```
Store 1──N AdminUser
Store 1──N Table 1──N TableSession 1──N Order 1──N OrderItem
Store 1──N Category 1──N Menu
Order ──(close 시 스냅샷 이관)──▶ OrderHistory
OrderItem.menu_id ──▶ Menu (참조, 단 menu_name/unit_price 스냅샷 보관)
```

---

## 1. Store (시드 1개)
| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | INTEGER | PK, autoincrement | |
| store_code | String(32) | **UNIQUE**, not null, index | 예 `STORE01` |
| name | String(100) | not null | 예 `데모 카페` |
| created_at | DateTime | not null, default utcnow | |

## 2. AdminUser
| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | INTEGER | PK | |
| store_id | INTEGER | FK→store.id, not null, index | |
| username | String(50) | not null | |
| password_hash | String(255) | not null | bcrypt |
| created_at | DateTime | not null, default utcnow | |
- **UNIQUE**: `(store_id, username)`.

## 3. Table
| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | INTEGER | PK | |
| store_id | INTEGER | FK→store.id, not null, index | |
| table_number | Integer | not null | |
| table_password_hash | String(255) | not null | bcrypt |
| is_active | Boolean | not null, default true | |
| created_at | DateTime | not null, default utcnow | |
- **UNIQUE**: `(store_id, table_number)`. 시드 12개(번호 1~12).

## 4. TableSession  🔬(활성 세션 ≤1 — U6 PBT)
| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | INTEGER | PK | |
| table_id | INTEGER | FK→table.id, not null, index | |
| status | String(10) | not null, default `active` | `active`/`closed` |
| started_at | DateTime | not null, default utcnow | |
| closed_at | DateTime | nullable | close 시 기록 |
- **불변식**: 테이블당 `status='active'` 세션 최대 1개(서비스 계층 트랜잭션 + `(table_id, status)` 부분 인덱스로 지원). 🔬 U6.

## 5. Category
| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | INTEGER | PK | |
| store_id | INTEGER | FK→store.id, not null, index | |
| name | String(50) | not null | |
| display_order | Integer | not null, default 0 | 노출 순서 |

## 6. Menu
| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | INTEGER | PK | |
| store_id | INTEGER | FK→store.id, not null, index | |
| category_id | INTEGER | FK→category.id, not null, index | |
| name | String(100) | not null | |
| price | Integer | not null | **> 0** (🔬 U3 검증) |
| description | Text | nullable | |
| image_url | String(500) | nullable | 외부 URL |
| display_order | Integer | not null, default 0 | |
| is_available | Boolean | not null, default true | |
| created_at | DateTime | not null, default utcnow | |
| updated_at | DateTime | not null, default utcnow, onupdate utcnow | |

## 7. Order
| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | INTEGER | PK | |
| session_id | INTEGER | FK→table_session.id, not null, index | |
| table_id | INTEGER | FK→table.id, not null, index | |
| order_number | String(20) | **UNIQUE**, not null | `YYYYMMDD-###` (Q3) |
| status | String(10) | not null, default `대기중` | `대기중`/`준비중`/`완료` |
| total_amount | Integer | not null | = Σ(unit_price×qty) (🔬 U4) |
| created_at | DateTime | not null, default utcnow | |

## 8. OrderItem
| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | INTEGER | PK | |
| order_id | INTEGER | FK→order.id, not null, index | |
| menu_id | INTEGER | FK→menu.id, not null | 참조(스냅샷 병행) |
| menu_name | String(100) | not null | **스냅샷** |
| unit_price | Integer | not null | **스냅샷** |
| quantity | Integer | not null | **≥ 1** (🔬 U4) |

## 9. OrderHistory (이용 완료 이관 스냅샷)
| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | INTEGER | PK | |
| table_id | INTEGER | not null, index | 스냅샷(FK 강제 안 함) |
| session_id | INTEGER | not null, index | |
| order_number | String(20) | not null | |
| items_snapshot | JSON | not null | `[{menu_name, unit_price, quantity}]` (Q5) |
| total_amount | Integer | not null | |
| ordered_at | DateTime | not null | 원 주문 created_at |
| closed_at | DateTime | not null | 세션 close 시각 |

---

## 관계 요약 (SQLAlchemy relationships)
- `Store` → `admin_users`, `tables`, `categories`, `menus` (1:N)
- `Table` → `sessions` (1:N); `TableSession` → `orders` (1:N); `Order` → `items` (1:N)
- `Category` → `menus` (1:N)
- `OrderHistory` 는 독립(스냅샷) — 조인 없이 단일 레코드 완결.

## 불변식(🔬 후속 유닛 PBT 대상) 참조 지점
> U1은 규칙을 **강제하지 않고 스키마로 지원**만 한다. 실제 강제/검증은 해당 유닛 서비스 + PBT.
| 불변식 | 지원 스키마 | 담당 유닛 |
|---|---|---|
| 활성 세션 ≤ 1 | `TableSession.status` + 인덱스 | U6 |
| total_amount = Σ(unit_price×qty) | `Order.total_amount`, `OrderItem` | U4 |
| 수량 ≥ 1 | `OrderItem.quantity` | U4 |
| 상태 전이(대기중→준비중→완료) | `Order.status` | U5 |
| 삭제 후 총액 = 남은 합 | `Order`/`OrderItem` | U5 |
| 무손실 이관 | `OrderHistory.items_snapshot` | U6 |
| price>0·필수필드 | `Menu.price` not null | U3 |
