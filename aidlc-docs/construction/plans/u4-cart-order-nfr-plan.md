# U4 Cart & Order — NFR Plan (Part 1: Planning)

**단계**: CONSTRUCTION — **Phase 1 (5인 병렬)** [U4 / 스트림 C] — **NFR (비기능 요구사항 정의 → 설계)**
**유닛**: U4 Cart & Order (장바구니 · 주문 생성 · 현재 세션 주문 조회)
**책임 파일(스트림 C 소유)**: `services/order/create.py`, `routers/order.py`, `repositories/order.py`(`SqlOrderRepo`), 프론트 `context/cart-context.tsx`, `features/customer/cart-order/*`.
**입력**: `inception/requirements/requirements.md §5`(NFR-1~7), `aidlc-state.md`(Extension Config: Security=No, Resiliency=No, **PBT=Yes**), U4 Functional Design 산출물(`business-rules.md`, `domain-entities.md`, `frontend-components.md`).

> **범위 주의(병렬 규칙)**: 본 단계는 U4에 해당하는 NFR만 다룬다. 전역 NFR 중 U4 책임이 아닌 항목(NFR-2 인증·NFR-3 세션 라이프사이클·SSE 브로커 구현 등)은 소관 스트림(U2/A, U5/D, U6/E)의 NFR로 넘긴다. 동결 계약(`schemas/`, 서비스 파사드, `OrderEventBroker`, 리포 Protocol, 프론트 컨텍스트 인터페이스)은 변경하지 않는다.

---

## 배경: 전역 NFR 중 U4 관련 항목 (requirements.md §5)

| # | 분류 | 요구 | U4 관련성 |
|---|---|---|---|
| NFR-1 | 성능 | 실시간 주문 표시 2초 이내(SSE) | **부분** — U4는 이벤트 *발행측*(주문 생성 후 `order_created` publish). 채번/생성 응답성도 여기서 확보. |
| NFR-2 | 보안 | bcrypt·JWT·시도제한 (Security 확장 미적용) | **간접** — U4 고객 API는 비인증(테이블 세션 스코프). 인증 자체는 U2/A. |
| NFR-3 | 세션 | 테이블 세션 라이프사이클 | **간접** — U4는 `get_or_start_active_session`(U6/E) 계약에 위임. |
| NFR-4 | 사용성 | 터치 친화적(최소 44×44px), 카드 레이아웃 | **직접** — 장바구니/주문 UI. 수량 입력 한도 정의 포함. |
| NFR-5 | 데이터 지속성 | 장바구니 로컬 저장(새로고침 유지) | **직접** — `localStorage` 라운드트립. 지속 기간 정책 필요. |
| NFR-6 | 테스트 | PBT 전체 적용 + 예제 기반 병행 | **직접** — 총액/수량/라운드트립/채번 불변식. |
| NFR-7 | 이식성 | 로컬 실행(Docker 불필요) | **직접** — 추가 인프라 의존 금지. |

---

## 결정이 필요한 질문 (Questions) — 승인 완료

> 아래 3개 질문은 사용자 승인 완료. 결정 사항은 `nfr-design.md`에 반영·구현됨.

### Q1. 장바구니 지속성 정책 (NFR-5)
`localStorage`에 저장된 장바구니를 언제까지 유지할까?
- **A (권장·채택)**: **무기한 유지** — 사용자가 직접 비우거나(비우기 버튼) 주문 성공 시에만 삭제. 새로고침·재방문에도 보존. TTL 없음.
- B: TTL(예: 24h) 후 만료.
- C: 세션 종료 시 삭제.

[Answer]: **A (채택)** — 무기한 유지, 명시적 비우기/주문 성공 시에만 삭제. (현재 구현과 일치)

### Q2. 주문번호 채번 동시성 (NFR-1)
`order_number`(`YYYYMMDD-###`, UNIQUE)를 동시 주문에서 어떻게 안전하게 발급할까?
- **A (권장·채택)**: **UNIQUE 제약 + 재시도 루프** — 단일 프로세스 전제에서 `max(today)+1` 채번, 커밋 시 UNIQUE 충돌이면 롤백 후 재채번(최대 N회). 목표 응답 <300ms.
- B: 애플리케이션 전역 락(Lock) 직렬화.
- C: DB 시퀀스/트리거.

[Answer]: **A (채택)** — UNIQUE + 재시도 루프(N=5), 초과 시 `CONFLICT` 반환.

### Q3. 장바구니 한도 (NFR-4)
과도 입력 방지를 위한 수량/항목 한도?
- **A (권장·채택)**: **항목당 수량 1~99, 항목(메뉴) 종류 수 무제한.** 초과 입력은 백엔드 검증 거부 + 프론트 클램프.
- B: 수량·항목 모두 무제한(방어 없음).
- C: 더 엄격한 한도(예: 수량 1~20).

[Answer]: **A (채택)** — 수량 1~99 클램프/검증, 항목 종류 무제한.

---

## 계획 실행 체크리스트 (Part 2 = NFR 산출물 생성)

- [x] `construction/u4-cart-order/nfr/nfr-requirements.md` — U4 NFR 정의(측정 가능한 목표·수용 기준으로 구체화)
- [x] `construction/u4-cart-order/nfr/nfr-design.md` — 설계 결정(지속성·채번·한도)과 코드 반영 지점, 검증(PBT) 매핑
- [x] 코드 반영: 채번 재시도 루프(`create.py`), 수량 상한 1~99(`create.py` `_validate_items`, `cart-logic.ts`)
- [x] 테스트 반영: `test_order_pbt.py`(수량 상한 거부/수용), `cart-logic.test.ts`(99 클램프)

---

## 승인 요청

Q1~Q3는 승인 완료 상태로 기록합니다. 산출물(정의·설계)과 그에 따른 코드/테스트 반영은 본 계획대로 완료했습니다.
