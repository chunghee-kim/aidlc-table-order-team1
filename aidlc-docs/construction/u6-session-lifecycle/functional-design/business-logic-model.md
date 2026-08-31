# U6 — Business Logic Model (Functional Design)

## 1. DB 세션 주입 경로 (Q1=B)
동결 파사드 시그니처(`db` 없음)를 유지하기 위해 U6 서비스가 **내부에서 세션을 확보**한다.
```
router (Depends(get_current_admin))
   → facade fn (table_id[, actor])          # services/table_session/__init__.py (시그니처 동결)
      → lifecycle fn                          # services/table_session/lifecycle.py
         → _open_session(): app.db.SessionLocal() (expire_on_commit=False)
         → 모델 직접 쿼리 + OrderHistoryRepoImpl(db)
         → db.commit(); db.close()
      ← 커밋 후 broker.publish(order_deleted…) (NotImplementedError 무시)
```
- `expire_on_commit=False`: 반환된 detached TableSession의 스칼라 속성(`.id` 등)을 커밋/close 후에도 U4/C가 안전하게 읽음.
- 테스트: `_open_session`이 `app.db.SessionLocal`을 **모듈 경유**로 참조 → conftest가 in-memory 엔진으로 monkeypatch.

## 2. get_or_start_active_session(table_id) → TableSession
```
db = _open_session()
s = db.query(TableSession).filter_by(table_id=table_id, status="active").first()
if s is None:
    s = TableSession(table_id=table_id, status="active", started_at=utcnow)
    db.add(s); db.commit()   # id 부여
db.close(); return s          # detached, .id 접근 가능
```
U4/C `create_order`가 이 함수로 세션 확보 후 같은 session_id로 주문 그룹화(US-A-11).

## 3. close_table(table_id, actor) → CloseResult
```
closed_at = utcnow()
db = _open_session()
try:
  s = db.query(TableSession).filter_by(table_id=table_id, status="active").first()
  if s is None: raise AppError(CONFLICT, "활성 세션이 없습니다")
  order_ids = [o.id for o in db.query(Order).filter_by(session_id=s.id).all()]
  moved = OrderHistoryRepoImpl(db).move_session_orders(s.id, closed_at)   # snapshot+delete
  s.status = "closed"; s.closed_at = closed_at
  db.commit()
except: db.rollback(); raise
finally: db.close()
for oid in order_ids: try broker.publish(order_deleted{oid}) except NotImplementedError: pass
return CloseResult(moved_order_count=moved, closed_at=closed_at)
```
라우터가 `CloseResult` → `CloseResponse`로 매핑.

## 4. OrderHistoryRepoImpl(db)
- `move_session_orders(session_id, closed_at) -> int`: 세션 Order 로드 → 각 Order를 `OrderHistory(items_snapshot=[{menu_name,unit_price,quantity}…], total_amount, ordered_at=created_at, closed_at)`로 insert → `db.delete(order)`(items cascade) → `flush`; 이관 건수 반환.
- `list(store_id, table_filter, date_range) -> list[OrderHistory]`: `select(OrderHistory).join(Table, Table.id==OrderHistory.table_id).where(Table.store_id==store_id)` (+ table_filter, + closed_at 범위) `order_by closed_at desc, id desc`.

## 5. history_service.list_history(store_id, table_filter, date_range) → list[OrderHistoryView]
`_open_session()` → `OrderHistoryRepoImpl(db).list(...)` → 각 row를 `OrderHistoryView`로 매핑(items_snapshot→OrderItemView) → close → 반환.

## 6. 라우터
- `routers/table_close.py`: `POST /api/admin/tables/{table_id}/close`, `Depends(get_current_admin)` → `close_table(table_id, actor)` → `CloseResponse`.
- `routers/history.py`: `GET /api/admin/history?table=&date_from=&date_to=`, `Depends(get_current_admin)` → 날짜 문자열→KST 경계 UTC 변환→`list_history(actor.store_id, table, date_range)` → `list[OrderHistoryView]`.
- `main.py`: `from app.routers import health, history, table_close` + 두 `include_router` 주석 해제(그 외 편집 없음).

## 7. 파사드 와이어링
`services/table_session/__init__.py`: `from . import lifecycle` 후 `get_or_start_active_session`/`close_table`를 `lifecycle.*`에 위임(시그니처 그대로). `identify.py`(U2/A) 라인 미접촉.
