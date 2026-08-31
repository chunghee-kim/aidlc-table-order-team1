# 서비스 정의 및 오케스트레이션 (Services)

**단계**: INCEPTION — Application Design (Standard depth)
**범위**: 서비스 정의·책임·**오케스트레이션 패턴**(유즈케이스 흐름). 상세 규칙·엣지 케이스는 Functional Design.

**아키텍처**: 3계층(Router → **Service** → Repository). 서비스는 유즈케이스의 **오케스트레이터이자 트랜잭션 경계·비즈니스 규칙의 소유자**입니다.

---

## 1. 서비스 목록 (Service Catalog)

| 서비스 | 유형 | 주 책임 | 의존(Repo/서비스) | 유닛 |
|---|---|---|---|---|
| **AuthService** | 도메인 | 관리자 인증·JWT·시도 제한 | AdminUserRepo, StoreRepo | U2 |
| **TableSessionService** | 도메인 | 태블릿 설정·세션 식별·라이프사이클(시작/완료) | TableRepo, SessionRepo, OrderRepo, OrderHistoryRepo | U2, U6 |
| **MenuService** | 도메인 | 메뉴 조회·CRUD·순서·검증(🔬) | MenuRepo, CategoryRepo | U3 |
| **OrderService** | 도메인 | 주문 생성·조회·상태전이(🔬)·직권삭제(🔬) | OrderRepo, SessionRepo, MenuRepo, TableSessionService, OrderEventBroker | U4, U5 |
| **HistoryService** | 도메인 | 과거 이력 조회·필터 | OrderHistoryRepo | U6 |
| **OrderEventBroker** | 인프라 | 실시간 이벤트 pub/sub(SSE) | (인메모리 상태) | U5 |

---

## 2. 오케스트레이션 패턴 (Orchestration Flows)

### 2.1 관리자 로그인 (U2 · US-A-01/02/03)
```
AuthRouter.POST /api/admin/login
  → AuthService.authenticate(store_code, username, password)
      → StoreRepo.find_by_code  → AdminUserRepo.find_by_store_and_username
      → 시도제한 확인(register_login_attempt) → bcrypt 검증
      → issue_token(admin)  # JWT 16h
  → 200 { token, admin }  |  401 구조화 에러(+시도제한 429)
```

### 2.2 태블릿 설정 & 고객 자동 로그인 (U2 · US-A-04, US-C-01/02)
```
[관리자] TableRouter.POST /api/admin/tables/{id}/setup  (AuthDependency)
  → TableSessionService.setup_table(...)  → TableRepo.upsert (번호/비번 해시)
  → 200 { table, auto_login_enabled: true }  (중복 시 409/확인 플래그)

[고객]  TableRouter.POST /api/customer/table-login
  → TableSessionService.resolve_session_context(store_code, table_number, table_password)
      → StoreRepo/TableRepo 조회 + 비번 검증
  → 200 { storeId, tableId }  # 프론트 TableSessionContext에 저장(localStorage), 새로고침 유지
```

### 2.3 메뉴 조회/관리 (U3 · US-C-03~06, US-A-16~18)
```
[고객] MenuRouter.GET /api/menus → MenuService.list_menus_for_customer → 카테고리·순서 정렬
[관리자] POST/PUT/DELETE /api/admin/menus → MenuService.create/update/delete
      → 🔬 검증: 필수 필드, price > 0 (실패 시 422 구조화 에러)
[관리자] PATCH /api/admin/categories/{id}/menu-order → MenuService.reorder_menus
  # 관리자 변경은 고객 GET /api/menus에 즉시 반영(단일 SQLite 소스)
```

### 2.4 주문 생성 — 세션 시작 트리거 (U4↔U6 · US-C-12/13, US-A-11)
```
OrderRouter.POST /api/orders  (TableSessionContext)
  → OrderService.create_order(session_ctx, items)
      → 빈 항목 차단
      → TableSessionService.get_or_start_active_session(table_id)   # 🔬 활성 세션 ≤1, 없으면 시작
      → MenuRepo로 단가 확정 → total = Σ(unit_price × qty)          # 🔬 총액 불변식
      → OrderRepo.create(order+items, order_number, status=대기중)
      → OrderEventBroker.publish('order_created', OrderView)         # → SSE 실시간 전파
  → 201 { order_number, ... }  (실패 시 4xx/5xx, 프론트는 장바구니 유지)
```
> **계약 노트**: "세션 시작"은 U6 라이프사이클 규칙이지만 **트리거는 U4 주문 생성**. OrderService가 TableSessionService에 위임하여 경계를 명확히 유지.

### 2.5 실시간 모니터링 (U5 · US-A-05~08)
```
AdminOrderRouter.GET /api/admin/orders/stream  (AuthDependency, text/event-stream)
  → OrderEventBroker.snapshot(store_id)  # 최초/재연결 시 현재 활성 주문 전량
  → OrderEventBroker.subscribe(store_id) → 이후 order_created/updated/deleted 스트리밍
  # 프론트 SseClient: 자동 재연결 → 재연결 시 snapshot으로 누락 복구(US-A-06)
```

### 2.6 상태 변경 / 직권 삭제 (U5 · US-A-09/10)
```
PATCH /api/admin/orders/{id}/status
  → OrderService.change_status(id, next)   # 🔬 허용 전이만 (대기중→준비중→완료)
  → OrderRepo.update_status → publish('order_updated')
  # 고객 CurrentOrdersView에도 반영(동일 데이터 소스)

DELETE /api/admin/orders/{id}
  → OrderService.delete_order(id)          # 🔬 삭제 후 total = 남은 주문 합
  → OrderRepo.delete → sum_total_by_table → publish('order_deleted', {table_totals})
```

### 2.7 이용 완료 — 세션 마감 (U6 · US-A-12)
```
TableRouter.POST /api/admin/tables/{id}/close  (AuthDependency)
  → TableSessionService.close_table(table_id)       # 🔬 트랜잭션 경계
      ┌ [단일 트랜잭션]
      │  OrderHistoryRepo.move_session_orders(session_id)  # 주문/항목 스냅샷 이관
      │  OrderRepo.delete(session orders)                  # 현재 목록에서 제거
      │  SessionRepo.close(session_id, closed_at)          # 활성 → closed
      └ (무손실: 이관 건수 == 원 주문 건수)
  → publish('order_deleted'/'table_reset')  # 대시보드 총액 0 반영
  → 200 { moved_order_count, closed_at }
  # 새 고객의 첫 주문 시 2.4 흐름으로 새 세션 시작
```

### 2.8 과거 내역 조회 (U6 · US-A-13/14/15)
```
HistoryRouter.GET /api/admin/history?table=&date=  (AuthDependency)
  → HistoryService.list_history(store_id, table_filter, date_range)
      → OrderHistoryRepo.list (테이블별 시간 역순, 날짜 필터)
  → 200 [ { order_number, items, total, ordered_at, closed_at } ]
```

---

## 3. 트랜잭션·일관성 경계 (Transaction Boundaries)

| 유즈케이스 | 트랜잭션 단위 | 불변식(🔬) |
|---|---|---|
| 주문 생성 | 세션 확보 + 주문/항목 생성 원자적 | 활성 세션 ≤1, 총액 = Σ(단가×수량) |
| 상태 변경 | 단건 갱신 | 허용 전이만(대기중→준비중→완료) |
| 직권 삭제 | 삭제 + 총액 재계산 | 삭제 후 총액 = 남은 주문 합 |
| 이용 완료 | 이관 + 삭제 + 세션 close 를 **단일 트랜잭션** | 무손실(이관 건수 = 원 건수), 완료 후 현재 총액 0 |

> SQLite 단일 파일·단일 프로세스 전제. 서비스 메서드가 트랜잭션 커밋/롤백 경계를 소유. 이벤트 발행(publish)은 **커밋 성공 후** 수행(잘못된 실시간 반영 방지).

---

## 4. 서비스 간 상호작용 원칙

- **OrderService → TableSessionService**: 주문 생성 시 세션 확보 위임(도메인 경계 유지). 역방향 의존 없음.
- **OrderService → OrderEventBroker**: 상태 변경 유즈케이스 완료 후 이벤트 발행(단방향).
- **HistoryService**: 읽기 전용. 쓰기(이관)는 TableSessionService.close_table가 소유.
- **AuthService**: 다른 도메인 서비스에 의존하지 않음. AuthDependency(인프라)가 verify_token만 사용.
- **순환 의존 금지**: 서비스 의존은 DAG(component-dependency.md의 그래프 참조).

---

## 5. 서비스 유형 요약

- **도메인 서비스**(AuthService, TableSessionService, MenuService, OrderService, HistoryService): 유즈케이스·규칙·트랜잭션.
- **인프라 서비스**(OrderEventBroker): 상태 저장형(인메모리 구독자 레지스트리 + asyncio 큐), 단일 프로세스 로컬 MVP 전제. 재시작 시 구독 상태 소실은 허용(클라이언트 자동 재연결 + 스냅샷으로 복구).
