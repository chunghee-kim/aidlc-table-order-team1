# U6 — Frontend Components (Functional Design)

라우트 등록은 레지스트리 규약(`features/<name>/routes.tsx` default export `FeatureRoutes`). `main.tsx` 미편집. 모든 API는 `apiClient`(Bearer 자동 주입).

## 1. 이용 완료 플로우 — `features/admin/table-close/` (US-A-12, Q10=A)
- **`useCloseTable()` 훅**: `closeTable(tableId): Promise<CloseResult>` — 확인 후 `apiClient.post('/api/admin/tables/{tableId}/close')`. 상태 `{loading, error, result}` 노출. U5/D 대시보드가 이 훅/버튼을 import해 테이블 카드에 배치(통합 시).
- **`CloseConfirmModal`**: "이용 완료" 확인 팝업(A-12 "확인 팝업"). 확정 시 훅 호출 → 성공 시 "이관 N건·리셋 완료" 토스트.
- **`CloseTableView`**(독립 admin 라우트 `/admin/table-close`): U5/D 미구축 상황에서 시연용 진입점 — 테이블 번호(=table_id) 입력 → 완료 버튼 → 모달. 통합 후 대시보드로 흡수.
- `routes.tsx`: `scope:"admin"`, `{ path: "table-close", element: <CloseTableView/> }`.

## 2. 과거 내역 — `features/admin/history/` (US-A-13~15)
- **`OrderHistoryView`**(admin 라우트 `/admin/history`):
  - 필터바: 테이블 드롭다운(옵션: 전체 + 1~N) + 날짜 `date_from`/`date_to`(`<input type=date>`), "조회" 버튼.
  - 목록: `apiClient.get('/api/admin/history?table=&date_from=&date_to=')` → `OrderHistoryView[]`, 시간 역순 카드. 카드: 주문번호·주문시각(로컬 변환)·메뉴목록(name×qty, 단가)·총액·이용완료시각.
  - 상태: 로딩 스피너/빈 상태("이력이 없습니다")/에러(ApiError.message).
  - "닫기" 버튼(A-15): `/admin`으로 navigate.
- `routes.tsx`: `scope:"admin"`, `{ path: "history", element: <OrderHistoryView/> }`.

## 3. 타입 (프론트 로컬)
```ts
interface OrderItemView { menu_name: string; unit_price: number; quantity: number }
interface OrderHistoryItem { order_number: string; items: OrderItemView[]; total_amount: number; ordered_at: string; closed_at: string }
interface CloseResult { moved_order_count: number; closed_at: string }
```
- 시각은 서버 UTC ISO → `new Date(...).toLocaleString()`로 표시(U1 Q2: 표시 변환은 프론트).

## 4. 공통
- 버튼은 `shared/ui/Button`(44×44 최소). 인증 토큰은 ApiClient가 localStorage에서 자동 주입(관리자 화면 전제).
