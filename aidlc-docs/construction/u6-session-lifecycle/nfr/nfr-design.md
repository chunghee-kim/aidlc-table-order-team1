# U6 Session Lifecycle & History — NFR Design (설계)

**단계**: CONSTRUCTION — Phase 1 · 스트림 E (U6) — **NFR Design (Part 2: 설계)**
**목적**: `nfr-requirements.md`의 각 목표(SES/DAT/TST/USA/POR)를 **어떤 메커니즘·구성 요소로 충족**하는지 설계로 확정하고, 구현 위치와 검증 지점을 매핑한다.
**입력**: `nfr-requirements.md`, `functional-design/*`, 구현 파일(§ 매핑).
**소유 파일**: `backend/app/services/table_session/lifecycle.py`, `services/history_service.py`, `repositories/order_history.py`, `routers/{table_close,history}.py`, `services/table_session/__init__.py`(U6 구역), `main.py`(U6 라인), `frontend/src/features/admin/{table-close,history}/*`. **동결 계약은 미변경.**

> 표기: 🔬 = PBT 대상 불변식. no-escalation 전략상 U6는 다른 스트림의 미구현 Repo(SessionRepo/OrderRepo)에 의존하지 않고 **모델 직접 조회**로 충족한다.

---

## 1. 세션 라이프사이클 설계 (NFR-3)

### 1.1 활성 세션 단일성 + 멱등 (SES-1, SES-2) 🔬
- **조회-생성 흐름**(`lifecycle.get_or_start_active_session`): `SELECT ... WHERE table_id=? AND status='active'` 최신 1건 조회 → 있으면 그대로 반환(멱등), 없으면 `TableSession(status='active', started_at=utcnow())` insert + `commit`.
- **인덱스**: `TableSession.__table_args__ = Index("ix_session_table_status", table_id, status)` (U1 스키마, **비유니크** — 조회 최적화용). 활성 세션 ≤1은 **애플리케이션 조회-생성 로직**으로 보장(단일 프로세스 전제). → 한계는 §6.
- **detached 반환**: `_open_session()`은 `expire_on_commit=False`로 세션을 열어, commit 이후에도 반환된 `TableSession`의 스칼라 속성(`.id` 등)을 호출자(U4/C)가 안전하게 읽는다.
- **세션 소스**: `from app import db as _db` 후 `_db.SessionLocal()` — 모듈 경유 참조라 테스트가 `SessionLocal`을 in-memory DB로 재바인딩 가능(격리, §3).

### 1.2 이용 완료 종료 (SES-3, SES-4)
- **`lifecycle.close_table`**: active 세션 조회 → **없으면** `AppError(ErrorCode.CONFLICT, "활성 세션이 없습니다.", {table_id})`. 있으면 `move_session_orders(session.id, closed_at)` 호출 → `session.status='closed'`·`session.closed_at=closed_at` → `commit`. `except` 시 `rollback` 후 재-raise.
- **SES-4**: close가 세션을 `closed`로 전이하므로, 다음 `get_or_start`는 active가 없다고 보고 **새 세션을 시작** → 새 고객은 이전 주문 없이 시작. 반환 `CloseResult{moved_order_count, closed_at}`(동결 계약).

---

## 2. 데이터 지속성·이력 보존 설계 (NFR-5)

### 2.1 무손실 이관 + 원자적 리셋 (DAT-1, DAT-2) 🔬
- **`OrderHistoryRepoImpl.move_session_orders(session_id, closed_at)`**: 세션의 각 `Order`에 대해
  - `items_snapshot = [{menu_name, unit_price, quantity} for it in order.items]` 구성(이관 시점 값 **고정** → 이후 메뉴 변경에 불변, 이력 보존 의도),
  - `OrderHistory(table_id, session_id, order_number, items_snapshot, total_amount, ordered_at=order.created_at, closed_at)` insert,
  - 원본 `Order` **delete**(cascade로 `OrderItem` 제거),
  - `moved += 1`. 마지막에 `flush()` 후 `moved` 반환.
- **원자성**: 위 insert/delete/상태전이가 `close_table`의 **단일 `commit`** 안에서 실행. 예외 시 `rollback` → 이관·삭제·전이 **모두 취소**(무손실·정합).

### 2.2 이력 조회 + KST 경계 (DAT-3, DAT-4)
- **`history_service.list_history(store_id, table_filter, date_range)`**: `OrderHistoryRepoImpl.list(...)`가 `JOIN Table ON Table.id=OrderHistory.table_id`로 **매장 스코프**(`Table.store_id==store_id`), `table_filter` 있으면 `table_id` 조건, `date_range` 있으면 `closed_at >= start AND < end`, `ORDER BY closed_at DESC, id DESC`(최신순·안정). 행 → `OrderHistoryView`(items는 `OrderItemView`로 매핑, 동결 계약).
- **KST 변환**(`routers/history._date_range`): `start = parse(date_from) - 9h`, `end = (parse(date_to) + 1일) - 9h`. 둘 다 비면 `None`(무필터). 형식 오류 → `AppError(VALIDATION_ERROR)`(422). 저장 UTC(naive)와 비교 정합.

---

## 3. 검증(PBT) 설계 (NFR-6)
- **P1**(`test_lifecycle_pbt.py`): `@given(calls, table_id)` 임의 반복 호출 후 active count=1·반환 id 단일. `test_p1_independent_per_table`로 테이블 독립 확인.
- **P2**(`test_close_pbt.py`): `@given(orders=list[list[(price,qty)]])` 임의 주문 생성 → `close_table` → `moved==len(orders)`, `OrderHistory` 합계=원본, 이후 테이블 총액 0·active 0. `test_close_without_active_session_conflicts`로 CONFLICT 확인.
- **격리**: 각 예제가 `new_memory_db()`(StaticPool in-memory SQLite)로 `SessionLocal` 재바인딩 — Hypothesis가 함수 스코프 fixture를 예제 간 리셋하지 않는 문제를 회피.
- **프론트 PBT**(`query.pbt.test.ts`): fast-check로 `buildHistoryQuery`가 설정된 필터만 포함하고 값이 라운드트립됨을 검증.
- **결과**: `pytest` 9 pass, `vitest` 2 pass.

---

## 4. 사용성·이식성 설계 (NFR-4/7)
- **USA-1**: `CloseConfirmModal`·`CloseTableView`·`OrderHistoryView`가 공유 `shared/ui/Button`(min 44×44). 오류 `role="alert"`, 성공/상태 `role="status"`. 시각은 서버 UTC ISO → `new Date(...).toLocaleString()` 로컬 변환(파싱 실패 시 원문 fallback).
- **POR-1**: U6는 기존 `app.db.SessionLocal`·FastAPI 앱을 재사용. 백엔드 라우터는 `main.py`의 U6 라인으로 등록, 프론트는 라우트 레지스트리(`features/admin/*/routes.tsx` 자동 수집, `main.tsx` 미편집). 추가 인프라/외부 서비스/Docker 없음.

---

## 5. 요구사항 → 구현/검증 매핑

| 요구 | 구현 위치 | 검증 |
|---|---|---|
| SES-1, SES-2 | `lifecycle.get_or_start_active_session`, `_open_session` | `test_lifecycle_pbt`(P1) |
| SES-3, SES-4 | `lifecycle.close_table` | `test_close_pbt`(CONFLICT·총액 0) |
| DAT-1, DAT-2 | `repositories/order_history.move_session_orders` + `close_table` 단일 트랜잭션 | `test_close_pbt`(P2) |
| DAT-3, DAT-4 | `history_service.list_history`, `OrderHistoryRepoImpl.list`, `routers/history._date_range` | `test_history`(스코프·필터·KST·형식오류) |
| TST-1~4 | `tests/{test_lifecycle_pbt,test_close_pbt,test_history}.py`, `query.pbt.test.ts` | pytest 9 / vitest 2 |
| USA-1 | `features/admin/{table-close,history}/*` + `shared/ui/Button` | `npm run typecheck`/`build` |
| POR-1 | `main.py`(U6 라인), `features/admin/*/routes.tsx` | 로컬 기동 스모크 |

---

## 6. 잔여 리스크·후속 (Overconfidence 방지)
- **세션 경합(동시성)**: 활성 세션 ≤1은 **조회-생성 로직 + 단일 프로세스** 전제로 보장한다. 다중 워커·고동시성에서는 두 요청이 동시에 "active 없음"을 관측해 **이중 active 세션**을 만들 수 있다. `ix_session_table_status`는 **비유니크**라 DB가 막지 못한다. 완화: 배포를 단일 프로세스로 제약(NFR-7 로컬 전제와 정합). 근본 해결(부분 UNIQUE 인덱스 `(table_id) WHERE status='active'`)은 **U1 스키마(동결) 변경**이라 no-escalation 범위 밖 → Infrastructure/후속 단계 과제.
- **이벤트 유실**: close의 `order_deleted` 발행은 **best-effort**(broker 미구현 시 `NotImplementedError` 흡수, 통합 후 U5 브로커가 소비). 실시간 반영·재연결 누락 복구 보장은 U5 소유.
- **타임존 하드코딩**: 날짜 경계는 **KST(UTC+9) 고정**. 다중 타임존·DST는 범위 밖(국내 단일 매장 전제).
- **스냅샷 비정규화**: `items_snapshot`은 이관 시점 값으로 고정 — 이후 메뉴 가격/명칭 변경에 영향받지 않는 **의도된 이력 보존**. 원본 메뉴 참조 무결성은 이관 이후 요구하지 않는다.
- **커밋 후 이벤트 발행 순서**: 알림은 `commit` **이후** 발행하므로, 커밋 성공했으나 발행 직전 프로세스가 죽으면 알림만 누락될 수 있다(데이터는 이미 영속·정합). 실시간 정합은 U5 재연결 복구로 수렴.
