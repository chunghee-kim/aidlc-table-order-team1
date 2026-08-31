# U1 Foundation — Business Rules (Functional Design)

**단계**: CONSTRUCTION — Phase 0 (U1 Foundation & Data) — Functional Design
**범위**: U1이 소유하는 기반 규칙(비즈니스 로직 아님). 근거: 승인된 Q1~Q9(전부 권장안 A).

## 1. 타임스탬프 (Q2)
- 모든 시간 컬럼은 **UTC** ISO-8601 저장. 서버는 `datetime.utcnow()` 사용, 응답도 UTC(ISO 8601, `Z`). 로컬(KST) 변환·표시는 프론트 책임.

## 2. 주문 번호 생성 규칙 (Q3) — `order_number`
- 형식: **`YYYYMMDD-###`** (예 `20260831-001`). 매장 전역 **일별 순번**, 자정(UTC 기준일) 리셋.
- 생성 로직(주문 생성 시, U4 소유이나 규칙은 U1 확정): 당일 날짜 프리픽스로 시작하는 `order_number` 중 최대 순번 +1, `001`부터 3자리 zero-pad. 동시성은 SQLite 단일 프로세스 + `order_number` UNIQUE 제약 + 트랜잭션으로 보장.

## 3. 참조 무결성 / 삭제·이관 (Q4)
- **이용 완료(세션 close)**: 활성 세션의 Order/OrderItem → OrderHistory 스냅샷으로 **무손실 이관** 후 원본 **물리 삭제**, 세션 `status='closed'`, `closed_at` 기록. 전 과정 **단일 트랜잭션**(U6 소유).
- **메뉴 삭제**: 물리 삭제 허용. OrderItem 이 `menu_name`/`unit_price` **스냅샷**을 보유하므로 과거 주문 무결성 유지.
- **FK 정책**: DB `ON DELETE` 제약에 의존하지 않고 **서비스 계층 트랜잭션**으로 제어(MVP·단일 프로세스 전제).

## 4. `OrderHistory.items_snapshot` 형식 (Q5)
- **JSON 컬럼**: `[{ "menu_name": str, "unit_price": int, "quantity": int }]`. 이력 조회는 단일 레코드로 완결, 메뉴 변경과 디커플.

## 5. 시드 데이터 규칙 (Q6) — 멱등
- 매장 1: `store_code="STORE01"`, `name="데모 카페"`.
- 관리자 1: `username="admin"`, `password="admin1234"` → bcrypt(cost 12) 해시 저장.
- 카테고리 4: 커피 / 음료 / 디저트 / 식사 (`display_order` 0~3).
- 메뉴: 카테고리당 4~6개, `price>0`, 외부 이미지 URL 플레이스홀더.
- 테이블 12: 번호 1~12, 초기 `table_password`는 테이블 번호 문자열(예 "1") → bcrypt 해시.
- **멱등성**: 시드 재실행 시 `store_code`/`(store_id,username)`/`(store_id,table_number)`/카테고리·메뉴 이름 존재 여부로 스킵. 이미 있으면 생성하지 않음.

## 6. 비밀번호·시크릿 (Q7)
- bcrypt **cost 12** (관리자·테이블 비밀번호 공통).
- `JWT_SECRET`, `DATABASE_URL`, `BCRYPT_COST` 는 `.env`/환경변수. 로컬 fallback 기본값 제공하되 실 시크릿은 커밋 금지(`.env.example` 만 커밋).

## 7. 스키마 생성 (Q8)
- 앱 부팅/시드 시 `Base.metadata.create_all(engine)`. Alembic 마이그레이션 미도입(MVP).

## 8. 공통 에러 코드 체계 (Q9)
구조화 에러 바디: `{ "error": { "code": <ErrorCode>, "message": <str>, "details": <obj|null> } }` + 적절한 HTTP 상태.

| ErrorCode | HTTP | 의미 |
|---|---|---|
| VALIDATION_ERROR | 422 | 요청 검증 실패(필드 오류 details) |
| UNAUTHORIZED | 401 | 인증 실패/토큰 무효·만료 |
| FORBIDDEN | 403 | 권한 없음 |
| NOT_FOUND | 404 | 리소스 없음 |
| CONFLICT | 409 | 중복/상태 충돌 |
| TOO_MANY_ATTEMPTS | 429 | 로그인 시도 제한 |
| INTERNAL | 500 | 서버 내부 오류 |

- `ErrorHandler`(U1)가 `AppError`(code 보유) 및 미처리 예외 → 위 바디로 매핑. 각 유닛은 `AppError(ErrorCode.X, ...)` 를 raise하여 재사용.
