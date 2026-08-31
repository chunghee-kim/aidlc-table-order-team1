# U4 Cart & Order — NFR Requirements (비기능 요구사항 정의)

**단계**: CONSTRUCTION — Phase 1 [U4 / 스트림 C] — NFR 정의
**범위**: 전역 NFR(requirements.md §5) 중 **U4가 소유·검증 책임을 지는 항목**을 측정 가능한 수용 기준으로 구체화한다. 타 스트림 소관은 참조만 한다.
**근거**: `requirements.md §5`, `aidlc-state.md`(Security=No·Resiliency=No·**PBT=Yes**), 승인된 NFR 질문 Q1~Q3(`plans/u4-cart-order-nfr-plan.md`).

> **Extension 정책 반영**: Security/Resiliency 확장은 **미적용**이므로, U4는 별도 위협 모델링·서킷브레이커·리트라이 정책 등을 도입하지 않는다. 단 **채번 UNIQUE 충돌 재시도**는 정합성(데이터 무결성) 보장을 위한 최소 조치로 허용한다(요구사항 명시분 범위 내).

---

## U4-NFR-1 · 성능 / 응답성 (전역 NFR-1)

**U4 책임**: 주문 생성 API의 응답 지연과 실시간 이벤트 *발행*.

| ID | 요구 | 측정 가능한 수용 기준 |
|---|---|---|
| U4-NFR-1.1 | 주문 생성 응답 지연 | `POST /api/orders` 정상 경로 서버 처리 **p95 < 300ms**(로컬·시드 규모, SQLite). |
| U4-NFR-1.2 | 실시간 발행 지연 | 커밋 성공 후 `order_created` 이벤트를 **동기 경로 밖(post-commit)** 에서 즉시 publish → 소비측(U5) 2초 이내 표시 요건(NFR-1)에 기여. |
| U4-NFR-1.3 | 발행 실패 격리 | 브로커 publish 실패가 주문 생성 트랜잭션 결과를 **바꾸지 않음**(best-effort, 주문은 이미 커밋). |
| U4-NFR-1.4 | 채번 동시성 | 동시 주문에서도 `order_number` 중복 없음. 충돌 시 재시도로 흡수, 재시도 소진 시 명확한 `CONFLICT`(409) 반환. |

## U4-NFR-4 · 사용성 / 입력 방어 (전역 NFR-4)

**U4 책임**: 장바구니·주문 화면의 터치 접근성 및 과도 입력 방어.

| ID | 요구 | 측정 가능한 수용 기준 |
|---|---|---|
| U4-NFR-4.1 | 터치 타깃 | 장바구니 수량 ± 버튼·주문 버튼 등 상호작용 요소 **최소 44×44px**. |
| U4-NFR-4.2 | 수량 한도 | 항목당 수량 **1~99**. 하한 미만은 항목 제거(수량 0/음수 라인 없음), 상한 초과는 거부/클램프. |
| U4-NFR-4.3 | 항목 수 | 장바구니 **메뉴 종류 수 무제한**(별도 상한 없음). |
| U4-NFR-4.4 | 방어 위치 | 프론트는 클램프(UX), 백엔드는 검증 거부(권위 있는 방어) — **양측 모두** 강제. |

## U4-NFR-5 · 데이터 지속성 (전역 NFR-5)

**U4 책임**: 장바구니 로컬 지속성.

| ID | 요구 | 측정 가능한 수용 기준 |
|---|---|---|
| U4-NFR-5.1 | 새로고침 유지 | 새로고침/재방문 후에도 장바구니 내용 **완전 복원**(라운드트립 무손실). |
| U4-NFR-5.2 | 지속 기간 | **무기한 유지**. TTL 없음. |
| U4-NFR-5.3 | 삭제 트리거 | (a) 사용자 '비우기', (b) 주문 성공 시에만 삭제. 그 외 자동 삭제 없음. |
| U4-NFR-5.4 | 손상 내성 | 저장소 값이 손상/비정상이면 **예외 없이 빈 장바구니로 복구**(throw 금지). |

## U4-NFR-6 · 테스트 / PBT (전역 NFR-6)

**U4 책임**: 검증 가치가 높은 U4 불변식의 속성 기반 테스트.

| ID | 불변식(🔬 PBT) | 도구 |
|---|---|---|
| U4-NFR-6.1 | 주문 총액 = Σ(unit_price × quantity) = 장바구니 총액 | Hypothesis(백엔드) + fast-check(프론트) |
| U4-NFR-6.2 | 모든 라인 quantity ∈ [1, 99] | Hypothesis / fast-check |
| U4-NFR-6.3 | 장바구니 직렬화 라운드트립: `deserialize(serialize(x)) == x` | fast-check |
| U4-NFR-6.4 | `order_number` 순번 단조 증가(`###+1`), 001 시작 | Hypothesis |
| U4-NFR-6.5 | 손상 입력 → 빈 장바구니(무예외) | fast-check(예제 기반 병행) |

## U4-NFR-7 · 이식성 (전역 NFR-7)

| ID | 요구 | 수용 기준 |
|---|---|---|
| U4-NFR-7.1 | 무 추가 인프라 | U4는 Redis/메시지 브로커/외부 큐 등 **추가 런타임 의존 없음**. 실시간은 U1 제공 인메모리 `OrderEventBroker` 사용. |
| U4-NFR-7.2 | 로컬 실행 | `uvicorn`(백엔드)·`vite`(프론트)만으로 동작, Docker 불필요. |

---

## 타 스트림 소관 (U4 비책임 — 참조용)

| 전역 NFR | 소관 | 비고 |
|---|---|---|
| NFR-2 보안(bcrypt·JWT·시도제한) | U2/A | U4 고객 API는 테이블 세션 스코프 비인증. |
| NFR-3 세션 라이프사이클 | U6/E | U4는 `get_or_start_active_session` 계약에 위임. |
| NFR-1 소비측 2초 표시(SSE 렌더) | U5/D | U4는 발행만. |

---

## 추적성 요약

| U4-NFR | 전역 NFR | 설계 문서 절 | 검증 |
|---|---|---|---|
| U4-NFR-1.4 | NFR-1 | nfr-design §2 | (동시성은 단일 프로세스 전제, 로직 검증) |
| U4-NFR-4.2/4.3 | NFR-4 | nfr-design §3 | 🔬 U4-NFR-6.2 |
| U4-NFR-5.* | NFR-5 | nfr-design §1 | 🔬 U4-NFR-6.3/6.5 |
| U4-NFR-6.* | NFR-6 | nfr-design §4 | test_order_pbt.py / cart-logic.test.ts |
| U4-NFR-7.* | NFR-7 | nfr-design §5 | (구성 검토) |
