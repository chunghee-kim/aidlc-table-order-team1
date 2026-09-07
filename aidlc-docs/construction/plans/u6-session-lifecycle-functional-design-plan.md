# U6 Session Lifecycle & History — Functional Design Plan (Part 1: Planning)

**단계**: CONSTRUCTION — **Phase 1 · Stream E** [U6] — Functional Design
**유닛**: U6 Session Lifecycle & History
**책임**: 세션 시작(첫 주문 트리거), 이용 완료(주문→이력 무손실 이관 + 리셋), 과거 이력 조회·날짜 필터.
**소유 파일(1파일=1스트림)**:
- 백엔드: `services/table_session/lifecycle.py`(신규), `services/history_service.py`(신규), `routers/table_close.py`(신규), `routers/history.py`(신규), `repositories/order_history.py`(Protocol → 실구현)
- 프론트: `features/admin/history/`(OrderHistoryView + routes.tsx), 이용 완료 플로우
- 테스트: `tests/` PBT(활성 세션 ≤1, 무손실 이관)
**계약 소비(동결 스텁)**: `SessionRepo`(U2/A), `OrderRepo`(U4/C), `order_event_broker.broker`(U5/D), `AuthDependency.get_current_admin`, `schemas/{history,table,common}.py`.
**입력**: `component-methods.md §1.2/1.5/2/3`, `parallel-execution.md §4·§5`, `stories.md US-A-11~15`, U1 Functional Design 산출물, Phase 0 계약 스텁.

> **U6 특성**: PBT 대상 상태 규칙(활성 세션 ≤1, 무손실 이관)을 포함하는 **stateful 라이프사이클** 유닛. 동결 계약과 충돌하지 않도록 **세션 주입·이벤트 통지** 두 교차 지점은 소유자+소비자 합의가 필요 → 아래 Q1·Q5에서 확정.

---

## 배경: Phase 0에서 이미 확정·동결된 사항

- **모델**: `TableSession`(status `active|closed`, index `ix_session_table_status(table_id,status)`, 불변식 "테이블당 active ≤1" 명시), `Order`(order_number `YYYYMMDD-###`, status `대기중|준비중|완료`, total_amount, created_at), `OrderItem`(menu_name/unit_price/quantity 스냅샷), `OrderHistory`(self-contained, 비-FK `table_id`/`session_id`, JSON `items_snapshot`, ordered_at, closed_at).
- **Repo Protocol**: `OrderHistoryRepo.move_session_orders(session_id)->int`, `.list(store_id, table_filter, date_range: tuple|None)->list[OrderHistory]`; `SessionRepo.{find_active_by_table, create, close(session_id, closed_at)}`; `OrderRepo.{list_by_session, sum_total_by_table, delete, ...}`.
- **파사드 스텁**(`services/table_session/__init__.py`): `get_or_start_active_session(table_id:int)->Any`, `close_table(table_id:int, actor:Any)->CloseResult`, `@dataclass CloseResult{moved_order_count, closed_at}`. **둘 다 `db` 파라미터 없음**(→ Q1).
- **스키마**: `CloseResponse{moved_order_count, closed_at}`(table.py), `OrderHistoryView{order_number, items:[OrderItemView], total_amount, ordered_at, closed_at}`(history.py), `OrderItemView{menu_name, unit_price, quantity}`(common.py).
- **엔드포인트 계약**: `POST /api/admin/tables/{id}/close`→close_table(관리자), `GET /api/admin/history?table=&date=`→list_history(관리자).
- **인프라**: `db.get_db()` 요청 스코프, "**서비스 메서드가 commit/rollback 소유**". `order_event_broker.broker` 싱글턴, **커밋 이후 publish**, 이벤트 타입은 `order_created|order_updated|order_deleted`만 존재(**close 전용 이벤트 없음** → Q5). `AuthDependency.get_current_admin`→`AdminContext{admin_id, store_id}`(Phase 0 dev 통과 스텁 store_id=1).
- **타임스탬프**: UTC ISO-8601 저장, 표시 변환은 프론트(U1 Q2).
- **이관 정책**: close 시 원본 Order/OrderItem **물리 삭제** + OrderHistory 스냅샷 보존(U1 Q4).

---

## 결정이 필요한 질문 (Questions) — 토픽별

> 각 `[Answer]:`에 답을 채워 주세요. 권장안대로면 `A` 또는 "권장". **전부 권장**도 가능. Q1·Q5는 동결 계약 교차 지점이라 특히 확인 요망.

### ── 토픽 T1. 세션 시작 (`get_or_start_active_session`, US-A-11 🔬) ──

#### Q1. DB 세션 주입 방식 (동결 계약 교차 — 핵심)
동결된 파사드 시그니처 `get_or_start_active_session(table_id:int)`·`close_table(table_id:int, actor)`에는 `db: Session`이 없습니다. 요청 스코프 세션을 서비스가 어떻게 확보할지, 그리고 이것이 계약 갱신을 요구하는지?
- **A (권장)**: **계약 갱신 — 두 파사드/실구현에 `db: Session` 파라미터 추가**. `parallel-execution.md §5.2`가 "C·E는 세션 계약을 초반 페어로 합의", `§6` "동결 계약 변경 시 스텁 먼저 갱신"을 허용. U4/C의 `create_order`가 자기 트랜잭션 안에서 `get_or_start_active_session(db, table_id)`를 호출해야 **세션 시작+주문 삽입 원자성**이 보장됨. → 파사드 스텁을 `(db, ...)`로 먼저 갱신(A/E 합의 기록), 라우터는 `Depends(get_db)`로 `db` 주입.
- B: 서비스가 내부에서 `SessionLocal()` 생성·독립 커밋 — 시그니처 무변경. 단, create_order와 다른 트랜잭션이라 세션 시작과 주문 삽입이 분리(주문 실패 시 빈 세션 잔존 가능; MVP엔 자가 치유되나 원자성 약함).
- C: contextvar/미들웨어로 요청 세션 주입 — 시그니처 무변경이나 암묵 결합·테스트 난이도 증가.

[Answer]: **B** — 스트림 간 실시간 통신 부재로 동결 계약 변경(합의) 불가. `lifecycle.py`가 내부에서 `SessionLocal()`로 세션 확보·커밋. 파사드 시그니처 무변경 → U4/C는 기존 계약 그대로 호출(변경 0). 트랜잭션 원자성만 소폭 양보(MVP 허용).

#### Q2. 활성 세션 판정·생성 로직 (불변식 ≤1)
`get_or_start_active_session`의 동작 규칙?
- **A (권장)**: `SessionRepo.find_active_by_table(table_id)`로 active 조회 → 있으면 그대로 반환, 없으면 `SessionRepo.create(table_id)`(status='active', started_at=utcnow). 불변식 "테이블당 active ≤1"은 **조회-후-생성**으로 유지(단일 프로세스/SQLite MVP, 동시성 경합 무시). PBT로 "반복 호출해도 active 세션 수 ≤1·동일 세션 반환" 검증.
- B: DB unique 부분 인덱스(partial unique on `table_id where status='active'`)로 강제 — SQLite 지원하나 U1 동결 스키마 변경 필요(비권장).

[Answer]:

### ── 토픽 T2. 이용 완료 (`close_table`, US-A-12 🔬) ──

#### Q3. 이관 로직 위치 (서비스 vs 리포)
세션 주문 → OrderHistory 스냅샷 이관을 어디서?
- **A (권장)**: **`OrderHistoryRepo.move_session_orders(session_id)->int` 내부에서 완결** — 세션 주문 read → `items_snapshot`(menu_name/unit_price/quantity) 구성 → OrderHistory insert(ordered_at=Order.created_at, closed_at는 서비스가 전달 or repo가 utcnow) → 원본 Order/OrderItem 물리삭제 → 이관 건수 반환. `close_table`가 이 repo + `SessionRepo.close`를 **단일 트랜잭션**으로 조립. Protocol 시그니처(`(session_id)->int`)와 정합. closed_at 일관성 위해 A안 보강: `move_session_orders(session_id, closed_at)`로 갱신(리포 소유자=E 본인이라 자유롭게 확정 가능).
- B: 서비스가 `OrderRepo.list_by_session`으로 읽어 스냅샷 만들고 repo는 insert/delete만 — 관심사 분산, 트랜잭션 조립 복잡.

[Answer]:

#### Q4. close_table 트랜잭션·리셋 순서·반환
단일 트랜잭션 내 연산 순서와 "총액 0 리셋" 달성 방식?
- **A (권장)**: 한 트랜잭션에서 ① active 세션 확인(없으면 `AppError(CONFLICT, "활성 세션 없음")`) → ② `move_session_orders`(이관+원본 삭제, 건수 n) → ③ `SessionRepo.close(session_id, closed_at)` → ④ commit → ⑤ **커밋 후** 이벤트 발행(Q5). "현재 총액 0"은 원본 주문 삭제로 `sum_total_by_table→0` 자동 달성. `CloseResult(moved_order_count=n, closed_at)` 반환 → 라우터가 `CloseResponse`로 매핑. 이관 건수 = 원 주문 건수(무손실, PBT 대상).
- B: 리셋을 별도 상태 필드로 표현(원본 유지) — U1 Q4(물리삭제) 정책 위배(비권장).

[Answer]:

#### Q5. 이용 완료 시 대시보드(U5) 통지 (동결 계약 교차)
`OrderEventBroker`에 close 전용 이벤트가 없습니다(`order_created|updated|deleted`만). 실시간 대시보드에서 완료된 테이블 주문이 사라지도록 통지하는 방법?
- **A (권장)**: **이관 대상 주문마다 `order_deleted` 이벤트를 커밋 후 발행**(payload `{order_id}`) — 기존 이벤트 타입 재사용이라 **동결 계약 무변경**. U5/D 대시보드가 이미 `order_deleted`로 카드 제거 → 테이블 총액 0 반영. 발행은 삭제 전 order_id 목록을 확보해 커밋 후 순차 publish.
- B: 새 이벤트 타입 `table_closed{table_id, session_id}` 추가 — 대시보드가 테이블 카드 일괄 제거. **`order_event_broker.py`(U5/D 소유) 계약 변경 → D+E 합의·스텁 우선 갱신 필요**. 의미론적으론 더 깔끔하나 교차 계약 변경 비용.
- C: 통지 안 함(대시보드는 다음 스냅샷/재연결 때 반영) — 실시간성 저하(비권장).

[Answer]: **A** — 기존 `order_deleted` 재사용, broker 계약 무변경.

### ── 토픽 T3. 과거 이력 조회·날짜 필터 (`HistoryService.list_history`, US-A-13/14) ──

#### Q6. HistoryService 배치 위치
`list_history`를 어디에?
- **A (권장)**: 독립 파일 **`services/history_service.py`** — `component-methods.md §1.5`·`parallel-execution.md §4` 표기와 일치. 파사드 스텁 없음(lifecycle과 달리) → E가 신규 생성. 함수형 `list_history(db, store_id, table_filter, date_range)->list[OrderHistoryView]`.
- B: `table_session/` 패키지 하위 서브모듈 — 라이프사이클과 응집되나 문서 표기와 불일치.

[Answer]:

#### Q7. 날짜 필터 파라미터·타임존 (US-A-14)
`GET /api/admin/history?table=&date=` 및 repo `date_range: tuple|None`의 구체 형식?
- **A (권장)**: 쿼리 `?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`(둘 다 선택, 포함 범위). 저장은 UTC지만 **필터 기준일은 매장 로컬(KST) 자정~자정**으로 해석 → repo에 `date_range=(start_utc, end_utc)` tuple로 전달(프론트가 로컬일→UTC 경계 변환, 또는 서버가 고정 KST 오프셋 적용). MVP는 단일 매장이므로 **서버에서 KST(+09:00) 경계 계산** 권장. `table_filter`는 `?table=<int>` 옵션.
- B: 단일 `?date=YYYY-MM-DD`(하루) + UTC 그대로 비교 — 범위 지정(A-14 "날짜 범위") 미충족.

[Answer]:

#### Q8. 정렬·그룹핑·페이지네이션
이력 목록 표현?
- **A (권장)**: **시간 역순**(closed_at desc, tie-break ordered_at desc) **평면 리스트** `list[OrderHistoryView]`(component-methods 계약 그대로). 테이블별 표시는 프론트가 `table` 필터/그룹 렌더. MVP 규모(테이블 12, 소량)라 **페이지네이션 없음**(전량 반환). 향후 필요 시 cursor 확장.
- B: 서버에서 테이블/세션별 그룹 구조로 반환 — 스키마(`OrderHistoryView` 평면) 변경 필요(비권장).

[Answer]:

### ── 토픽 T4. 라우터 (`routers/table_close.py`, `routers/history.py`) ──

#### Q9. 라우터 조립·인증·main 등록
- **A (권장)**: 두 라우터 모두 `APIRouter` + `Depends(get_current_admin)`. `table_close`: `POST /api/admin/tables/{table_id}/close` → `close_table(db, table_id, actor)` → `CloseResponse`. `history`: `GET /api/admin/history` → `list_history(...)` → `list[OrderHistoryView]`, `store_id`는 `actor.store_id`에서. `main.py`의 표시된 Phase 1 섹션에서 해당 2줄(`include_router(table_close.router)`·`include_router(history.router)`) 주석 해제(다른 편집 없음). 서비스가 `AppError`(CONFLICT/NOT_FOUND) throw → 기존 ErrorHandler가 구조화 바디 매핑.

[Answer]:

### ── 토픽 T5/T6. 프론트 (이용 완료 플로우 + OrderHistoryView, US-A-12~15) ──

#### Q10. 이용 완료 트리거 UI 소유 경계 (교차 UI)
"이용 완료" 버튼은 자연히 대시보드/테이블 카드(U5/D 소유)에 위치. U6는 "이용완료 플로우" 소유. 경계 처리?
- **A (권장)**: U6가 **재사용 컴포넌트+훅을 `features/admin/table-close/`에 소유·export**(`useCloseTable()` 훅 = 확인 팝업→`POST .../close`→성공 토스트; `CloseTableButton`/`CloseConfirmModal`). U5/D 대시보드가 이를 import해 카드에 배치(통합 시점). U5/D 미구축이므로 지금은 **독립 admin 라우트에서 시연 가능한 진입점**(테이블 선택→완료)도 함께 제공, 통합 후 대시보드로 흡수. `main.tsx` 미편집 — `features/admin/table-close/routes.tsx`로 등록.
- B: 이용 완료 버튼까지 U5/D가 소유하고 U6는 API만 제공 — 플로우 소유(§4) 배정과 불일치.

[Answer]:

#### Q11. OrderHistoryView 화면 구성 (US-A-13~15)
- **A (권장)**: `features/admin/history/` 하위 `OrderHistoryView`(admin 라우트, `scope:"admin"`, `routes.tsx` 등록). 구성: 상단 필터바(테이블 드롭다운 + 날짜 from/to), 목록(시간 역순 카드: 주문번호·주문시각·메뉴목록·총액·완료시각), "닫기"→대시보드 복귀(A-15). `apiClient.get` + `AuthContext` 토큰 사용. 로딩/빈 상태/에러 처리. 시각은 프론트가 로컬 변환 표시.

[Answer]:

### ── 토픽 T7. PBT · 파사드/DI 조립 ──

#### Q12. PBT 속성 정의 (Hypothesis) 🔬
- **A (권장)**: 두 속성 — ① **활성 세션 ≤1 & 멱등**(US-A-11): 임의 횟수·순서로 `get_or_start_active_session` 반복 호출 후에도 테이블당 active 세션 ≤1이고 close 전까지 동일 세션 id 반환. ② **무손실 이관**(US-A-12): 임의 개수/구성의 세션 주문 생성 후 `close_table` → `moved_order_count == 원 주문 수`, OrderHistory `items_snapshot` 합계·건수 = 원본, 이후 `sum_total_by_table==0` & active 세션 없음. 인메모리 SQLite 픽스처 위에서 실행.

[Answer]:

#### Q13. 파사드/DI 와이어링 범위
- **A (권장)**: `services/table_session/__init__.py` 파사드의 `get_or_start_active_session`·`close_table`를 `lifecycle.py` 실구현으로 위임(1~2줄, Q1 시그니처 반영). `OrderHistoryRepo` 실구현 클래스는 `repositories/order_history.py`에 추가. 라우터가 repo·서비스 인스턴스를 조립(경량 DI: 함수형 + `Depends(get_db)`). 최종 `services/__init__.py` 전역 DI 조립 PR은 통합 단계(§6 머지 순서)로 미룸.

[Answer]:

---

## 계획 실행 체크리스트 (Part 2 = Functional Design 산출물 생성)

> 위 질문 승인 후 아래 산출물을 생성합니다.

- [ ] `construction/u6-session-lifecycle/functional-design/domain-entities.md` — U6 관점 엔티티(TableSession 상태전이, OrderHistory 스냅샷 매핑 규칙, 참조 무결성 비-FK)
- [ ] `construction/u6-session-lifecycle/functional-design/business-rules.md` — 활성 세션 ≤1, 무손실 이관 규칙, close 트랜잭션 순서, 날짜 필터 타임존, 이벤트 통지, 에러 매핑(CONFLICT/NOT_FOUND)
- [ ] `construction/u6-session-lifecycle/functional-design/business-logic-model.md` — get_or_start/close_table/list_history 흐름도, 트랜잭션·이벤트 경계, DB 세션 주입 경로(Q1 결정 반영)
- [ ] `construction/u6-session-lifecycle/functional-design/frontend-components.md` — 이용완료 플로우·OrderHistoryView 컴포넌트·상태·핸들러·라우트 등록
- [ ] PBT 속성 명세(PBT-01): 활성 세션 ≤1, 무손실 이관 (Q12)
- [ ] 교차 계약 변경 기록: Q1(세션 시그니처 `db` 추가, A/C/E 합의)·Q5(이벤트 통지 방식) 확정 내용

---

## 승인 결과 (Approved 2026-08-31)

**결정 원칙**: 스트림 간 실시간 통신이 없으므로 **동결 계약을 변경하지 않는(escalate 불필요) 옵션만 채택** → U6가 U2~U5 협조 없이 단독 완주·머지 가능.

| Q | 토픽 | 결정 | 계약 변경 |
|---|---|---|:--:|
| Q1 | 세션 주입 | **B** (내부 `SessionLocal()`, 파사드 시그니처 유지) | 없음 |
| Q2 | 활성 세션 ≤1 | A (조회-후-생성) | 없음 |
| Q3 | 이관 로직 위치 | A (`OrderHistoryRepo.move_session_orders` 내부, `closed_at` 인자 보강) | 없음(리포 소유=E) |
| Q4 | close 트랜잭션 | A (확인→이관+삭제→close→commit→발행) | 없음 |
| Q5 | 대시보드 통지 | **A** (기존 `order_deleted` 재사용) | 없음 |
| Q6 | HistoryService 위치 | A (`services/history_service.py`) | 없음 |
| Q7 | 날짜 필터 | A (`date_from/date_to`, 서버 KST 경계) | 없음 |
| Q8 | 정렬·페이지 | A (closed_at desc 평면 리스트, 페이지 없음) | 없음 |
| Q9 | 라우터 조립 | A (2 라우터 + `get_current_admin`, main.py 2줄 주석해제) | 없음 |
| Q10 | 완료 트리거 UI | A (`useCloseTable` 훅 + 독립 admin 라우트) | 없음 |
| Q11 | OrderHistoryView | A (`features/admin/history/`) | 없음 |
| Q12 | PBT | A (활성세션≤1·멱등 / 무손실 이관) | 없음 |
| Q13 | 파사드/DI | A (facade 1~2줄 위임, 시그니처 무변경) | 없음 |

→ **Part 2 (Functional Design 산출물 생성) 착수.**
