# U5 Order Monitoring — Frontend Components (Functional Design)

**단계**: CONSTRUCTION — Phase 1 · 스트림 D [U5] — Functional Design
**범위**: `MonitoringDashboardView`, `OrderDetailModal`, `SseClient` 실구현의 컴포넌트 구조·props/state·상호작용·API 연동. `main.tsx` 미편집(라우트는 `features/admin/monitoring/routes.tsx`로 등록).
**근거**: 승인된 계획(Q1~Q12), `component-methods.md §4.5/5`, `business-logic-model.md`, `sse-client.ts`(동결 인터페이스).

---

## 1. 컴포넌트 계층

```
features/admin/monitoring/
├── routes.tsx                 # /admin/monitoring 라우트 export (레지스트리가 수집)
├── MonitoringDashboardView.tsx
│    ├── TableCardGrid          # 테이블별 카드 그리드
│    │    └── TableCard         # 번호·총액·최신 3개 미리보기·unseen 강조
│    ├── TableFilterBar         # 전체/테이블별 필터 (클라이언트 사이드, Q6)
│    └── OrderDetailModal       # 단일 주문 상세 (조건부 렌더)
└── useOrderStream.ts           # SSE 구독 훅 (SseClient 래핑)
```

`SseClient` 실구현은 소유 파일 `shared/api/sse-client.ts`(동결 인터페이스 유지).

---

## 2. 컴포넌트별 명세

### 2.1 MonitoringDashboardView
- **역할**: 대시보드 진입점. 초기 스냅샷 로드 + SSE 구독 라이프사이클 관리 + 상태 소유.
- **State**:
  | 상태 | 타입 | 설명 |
  |---|---|---|
  | `ordersById` | `Map<orderId, OrderView>` | 활성 주문 로컬 맵(§domain §2) |
  | `unseen` | `Set<orderId>` | 미확인(강조 대상), Q7-B |
  | `tableTotals` | `Map<tableId, number>` | 카드 총액(로컬 재합산 or 이벤트 갱신) |
  | `filterTableId` | `number \| null` | 필터(클라이언트 사이드) |
  | `selectedOrderId` | `number \| null` | 상세 모달 대상 |
  | `connState` | `'connecting'\|'open'\|'reconnecting'` | 연결 표시 |
- **핸들러** (component-methods.md §5):
  - `subscribeStream()`: mount 시 `useOrderStream`으로 connect. `snapshot` 프레임 → 상태 replace, 증분 이벤트 → 패치(§logic §2).
  - `applyTableFilter(n)`: `filterTableId=n`(클라이언트 필터, 재구독 없음).
  - `openDetail(orderId)`: `selectedOrderId=orderId`, `unseen`에서 제거(열람 처리, Q7-B).
- **이벤트 리듀서**:
  - `order_created` → upsert + `unseen.add` + 총액 재합산.
  - `order_updated` → 해당 항목 교체(상태 배지 갱신).
  - `order_deleted` → 항목 제거 + `tableTotals[table_id]=table_total`.
  - `snapshot` → 전체 replace(삭제/이관분 제거, unseen 교집합만 유지).
- **언마운트**: `SseClient.disconnect()`.

### 2.2 TableCard
- **Props**: `tableNumber`, `total`, `previews: OrderPreview[3]`, `hasUnseen: boolean`, `onOpen(orderId)`.
- **표시**: 테이블 번호, 총 주문액(KST/원화 포맷), 최신 3개(주문번호·대표 메뉴·상태 배지). unseen 있으면 카드 강조(테두리/펄스), Q7-B — 관리자가 열람 전까지 유지.
- **상호작용**: 미리보기 항목/카드 클릭 → `onOpen(orderId)`.

### 2.3 OrderDetailModal (US-A-07/09/10)
- **Props**: `order: OrderView & {orderId}`, `onClose()`, `onChanged()`, `onDeleted()`.
- **표시**: 전체 메뉴 목록(메뉴명·수량·단가), 총액, 현재 상태, `created_at`(KST 표시).
- **핸들러**:
  - `changeStatus(next)`: `PATCH /api/admin/orders/{orderId}/status {status:next}`. 성공 시 낙관적 UI는 이벤트로 자동 정합(별도 setState 불필요), 실패 409/404 → 에러 토스트(Q10).
    - 버튼 노출: 현재 상태 기준 **허용 전이만** 활성화(대기중→[준비중], 준비중→[완료], 완료→없음). BR-U5-1과 UI 일치.
  - `deleteOrder()`: **확인 팝업** 표시 → 확정 시 `DELETE /api/admin/orders/{orderId}`. 성공 피드백, `order_deleted` 이벤트로 그리드 자동 갱신.
- **접근성/터치**: 액션 버튼 최소 44×44px.

### 2.4 TableFilterBar (US-A-08)
- **Props**: `tables: number[]`, `active: number|null`, `onSelect(n|null)`.
- **동작**: 전체/특정 테이블 토글. 클라이언트 사이드 필터만(Q6). 재구독·재조회 없음.

### 2.5 SseClient (shared/api/sse-client.ts 실구현)
- **인터페이스(동결)**: `connect(url, onEvent)`, `disconnect()`.
- **구현 요구**:
  - `EventSource(url)` 생성. URL에 `?token=<JWT>` 포함(Q5-A). JWT는 `AuthContext`(U2)에서 취득.
  - `onmessage` → JSON 파싱 → `onEvent({type, payload})`. `type='snapshot'` 프레임 별도 처리(orders 배열).
  - `onerror` → 지수 백오프 재연결(1→2→4s, 상한 10s, 지터). 재연결 성공 시 서버 스냅샷으로 자동 복구(BR-U5-14/15).
  - `disconnect()` → `EventSource.close()` + 재연결 타이머 취소.
- **주의**: `SseEvent.payload`는 `unknown`(동결). 모니터링 훅에서 타입 가드로 좁힘.

---

## 3. API 연동 지점

| 컴포넌트/훅 | 호출 | 계약 |
|---|---|---|
| MonitoringDashboardView (초기) | `GET /api/admin/orders[?table=n]` | `list[OrderView+order_id]` |
| useOrderStream / SseClient | `GET /api/admin/orders/stream?token=` | SSE: snapshot/created/updated/deleted |
| OrderDetailModal.changeStatus | `PATCH /api/admin/orders/{id}/status` | `ChangeStatusRequest{status}` → `OrderView` |
| OrderDetailModal.deleteOrder | `DELETE /api/admin/orders/{id}` | → `TableTotals` |

- 인증: 관리자 JWT. REST는 `ApiClient`(U1)가 Authorization 헤더 주입, SSE는 쿼리 토큰(Q5).
- 에러: `ApiClient`가 구조화 바디 → `ApiError{code,message,details}` throw. 401→로그인 유도, 404/409→토스트 후 이벤트로 자동 정합.

---

## 4. UX 규칙

- **강조(Q7-B)**: unseen 주문은 관리자가 열람(카드/미리보기 클릭 → 상세 오픈)하기 전까지 강조 유지. 열람 즉시 해제. 페이드 타이머 없음.
- **실시간성(NFR-1)**: 신규 주문 2초 이내 카드 반영(인메모리 fan-out).
- **연결 상태 표시**: `reconnecting` 중 배너/인디케이터로 사용자에게 표시, 복구 시 자동 사라짐.
- **포맷**: 금액 원화, 시간 KST(서버 UTC → 프론트 변환, U1 규칙).
- **터치 타깃**: 상태 변경·삭제 등 액션 44×44px 이상.

---

## 5. 라우팅 등록 (main.tsx 미편집)

```
// features/admin/monitoring/routes.tsx
export default [{ path: "/admin/monitoring", element: <MonitoringDashboardView /> }];
```
`route-registry.ts`(U1)의 `import.meta.glob('features/*/routes.tsx')`가 자동 수집 → `main.tsx` 편집 불필요(parallel-execution §5.4).
