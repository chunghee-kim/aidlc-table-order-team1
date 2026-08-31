# U6 — Domain Entities (Functional Design)

**유닛**: U6 Session Lifecycle & History · **범위**: U6가 읽고/쓰는 엔티티의 상태·매핑 규칙(스키마는 U1 동결, 여기선 U6 관점의 제약·전이만).

## 1. TableSession (U6가 상태 전이 소유)
| 컬럼 | 타입 | U6 규칙 |
|---|---|---|
| id | int PK | — |
| table_id | FK table.id | 조회 키 |
| status | str(10) `active|closed` | **불변식: 테이블당 `active` ≤ 1** (index `ix_session_table_status(table_id,status)`로 조회) |
| started_at | datetime(UTC) | `get_or_start`가 신규 생성 시 `utcnow` |
| closed_at | datetime|null | `close_table`가 완료 시각 기록(그전엔 null) |

**상태 전이**: `(none) → active`(첫 주문/get_or_start) → `closed`(close_table). closed는 종단(재활성 없음). 새 이용은 새 세션 row.

## 2. OrderHistory (U6 소유 · self-contained 스냅샷)
| 컬럼 | 타입 | 매핑 원천 |
|---|---|---|
| id | int PK | — |
| table_id | int (비-FK, indexed) | Order.table_id |
| session_id | int (비-FK, indexed) | 닫힌 TableSession.id |
| order_number | str(20) | Order.order_number |
| items_snapshot | JSON `[{menu_name,unit_price,quantity}]` | OrderItem 목록 스냅샷 |
| total_amount | int | Order.total_amount |
| ordered_at | datetime(UTC) | **Order.created_at** |
| closed_at | datetime(UTC) | close 트랜잭션의 단일 `closed_at` |

- **비-FK 의도**: 메뉴/주문 물리삭제(U1 Q4)와 디커플. 이력은 스냅샷으로 완결.
- **store 소속**: OrderHistory엔 store_id 없음 → 이력 조회 시 `table_id`를 `Table`에 조인해 `store_id` 필터.

## 3. Order / OrderItem (U4 소유 · U6는 읽고→이관 후 삭제)
- close 시 세션의 Order 전량을 OrderHistory로 스냅샷 후 **물리 삭제**(OrderItem은 `cascade="all, delete-orphan"`로 함께 삭제).
- 삭제 전 `Order.id` 목록을 확보해 커밋 후 `order_deleted` 이벤트 발행에 사용.

## 4. 참조/무결성 요약
- close는 **단일 트랜잭션**: 스냅샷 insert + 원본 delete + session.status=closed. 부분 실패 시 전체 롤백 → 무손실 보장.
- "현재 총액 0"은 원본 Order 삭제의 부수효과(`sum_total_by_table→0`).

> 관련: [PBT] 활성 세션 ≤1(§TableSession), 무손실 이관(§OrderHistory) → `business-rules.md §PBT`.
