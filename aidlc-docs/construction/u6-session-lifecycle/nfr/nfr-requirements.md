# U6 Session Lifecycle & History — NFR Requirements (정의)

**단계**: CONSTRUCTION — Phase 1 · 스트림 E (U6) — **NFR Requirements (Part 1: 정의)**
**목적**: U6가 책임지는 비기능 요구사항을 **측정 가능한 목표(target)와 수용 기준**으로 확정한다. 설계·구현 방법은 `nfr-design.md`에서 다룬다.
**근거**: `inception/requirements/requirements.md §5`(NFR-1~7), `inception/user-stories/stories.md`(US-A-11~15), `construction/u6-session-lifecycle/functional-design/*`.

> 확장 설정(`aidlc-state.md`): Security Baseline = **미적용**, Resiliency Baseline = **미적용**, PBT = **적용(Full)** — U6는 PBT **배정 스트림**(P1·P2). no-escalation 전략상 동결 계약(schemas/AuthDependency/OrderEventBroker/repo Protocol/facade)은 미변경.

---

## 1. U6에 적용되는 NFR (매핑)

| NFR | 범주 | U6 적용 여부 | 스토리 |
|---|---|---|---|
| NFR-3 | 세션 | ✅ **주(主) 책임** — 테이블 세션 **라이프사이클**(첫 주문 시작 ~ 이용 완료), 활성 세션 ≤1 | US-A-11/12 |
| NFR-5 | 데이터 지속성 | ✅ **주 책임(일부)** — 이용 완료 시 주문 → OrderHistory **무손실 이관·보존**(SQLite). (장바구니 지속은 U4) | US-A-12~15 |
| NFR-6 | 테스트 | ✅ **주 책임** — PBT **P1**(활성세션≤1·멱등)·**P2**(무손실 이관·리셋) + 프론트 fast-check | US-A-11/12 |
| NFR-4 | 사용성 | ◐ 부분 — 이용완료 모달·이력 화면 버튼 터치 타깃 ≥44×44px, 오류/성공 시각 피드백 | US-A-12~15 |
| NFR-7 | 이식성 | ✅ 추가 인프라 없이 로컬 실행(내부 `SessionLocal` 재사용) | — |
| NFR-2 | 보안 | ◐ 부분 — 관리자 전용 엔드포인트는 `get_current_admin`(U2 계약) 필수. U6 자체 인증 로직 없음(재사용) | — |
| NFR-1 | 성능 | ✖ 해당 없음(실시간 성능·SSE는 U5). U6는 close 시 `order_deleted` 이벤트 **발행만** | — |

---

## 2. 측정 가능한 요구사항 (Targets & Acceptance)

### NFR-3 세션 라이프사이클 (Session)

**SES-1 — 활성 세션 최대 1개 (US-A-11) 🔬**
- 요구: `get_or_start_active_session(table_id)`를 **임의 순서·임의 횟수** 호출해도 테이블당 `status='active'` 세션은 **≤ 1**이고, close 전까지 **동일 `session_id`를 반환(멱등)**.
- 수용: 반복 호출 후 DB active count = 1, 반환 id 집합 크기 = 1. **PBT P1 통과**. 테이블 간 독립(한 테이블 호출이 다른 테이블 세션에 영향 없음).

**SES-2 — 세션 시작 시점**
- 요구: 세션은 **최초 `get_or_start` 호출(= 첫 주문 진입)** 시 발급. 이미 active 세션이 있으면 재사용.
- 수용: 세션 없던 테이블 호출 → 새 `active` 세션 생성(`started_at` 기록). 존재 시 신규 생성 없음.

**SES-3 — 이용 완료 = 세션 종료 (US-A-12)**
- 요구: `close_table(table_id)`는 active 세션을 `closed`로 전이하고 `closed_at`을 기록한다. active 세션이 **없으면** `AppError(CONFLICT)`.
- 수용: close 후 해당 테이블 `active` 세션 **0개**. 무세션 close → **409(CONFLICT)** 구조화 에러(`활성 세션이 없습니다.`).

**SES-4 — 새 고객이 이전 주문 없이 시작 (US-A-12 후속)**
- 요구: close 이후 동일 테이블에 `get_or_start` 호출 시 **이전 주문 없이** 새 세션이 시작된다.
- 수용: close 직후 테이블 총액 = 0, 이전 세션 주문이 신규 세션에 노출되지 않음.

### NFR-5 이력 보존·데이터 지속성 (Data)

**DAT-1 — 무손실 이관 (US-A-12) 🔬**
- 요구: close 시 세션의 **모든** 주문이 `OrderHistory`로 이관된다. `moved_order_count == 원 주문 수`, `items_snapshot`·`total_amount` 보존.
- 수용: **PBT P2 통과** — 임의 개수(≥0)·구성의 주문에 대해 이관 건수 = 원본, 스냅샷 합계 = 원본 총액.

**DAT-2 — 원자적 이관 + 리셋**
- 요구: 스냅샷 insert + 원본 Order delete(cascade OrderItem) + `session.status='closed'`가 **단일 트랜잭션**. 부분 실패 시 **전체 롤백**.
- 수용: 커밋 후 원본 `Order` 물리 삭제, 해당 테이블 잔여 총액 = 0. 예외 시 롤백으로 상태 불변(이관·삭제 모두 취소).

**DAT-3 — 이력 조회 (US-A-13~15)**
- 요구: 이력은 **매장 스코프**, `closed_at` **최신순**, **테이블/날짜 필터** 지원.
- 수용: 타 매장 이력 미포함. 테이블 필터 적용 시 해당 테이블만. 필터 없으면 매장 전체.

**DAT-4 — 시각·타임존 정합성**
- 요구: 저장은 **UTC(naive)**, 날짜 필터는 **KST(UTC+9)** 경계로 변환. 표시(로컬 시각)는 프론트 담당(U1 결정).
- 수용: `date_from`/`date_to`(YYYY-MM-DD) 하루 = UTC `[parse(from)-9h, (parse(to)+1일)-9h)`. 잘못된 형식 → **422(VALIDATION_ERROR)**.

### NFR-6 테스트 (Test) 🔬

**TST-1 — PBT P1**(Hypothesis): 활성 세션 ≤1·멱등·테이블 독립.
**TST-2 — PBT P2**(Hypothesis): 무손실 이관·원자적 리셋(총액 0·active 0).
**TST-3 — 프론트 PBT**(fast-check): `buildHistoryQuery` 라운드트립(설정된 필터만 포함).
**TST-4 — 예제 기반**: 이력 매장 스코프·최신순·테이블 필터·KST 경계, 무세션 close CONFLICT, 잘못된 날짜 VALIDATION_ERROR.
- 수용: `pytest` **9 pass**(PBT 4 + 예제 5), `vitest` **2 pass**. 각 예제는 격리된 in-memory DB에서 실행.

### NFR-4 사용성 (Usability, 부분)
**USA-1** — 이용완료 확인 모달·이력 화면의 상호작용 버튼은 공유 `Button`(≥44×44px). 오류는 `role="alert"`, 성공/상태는 `role="status"`로 노출. 시각은 서버 UTC → 로컬 표시.

### NFR-7 이식성 (Portability)
**POR-1** — 추가 인프라 없이 로컬 실행. U6는 `app.db.SessionLocal`을 **재사용**(내부 세션)하며 새 DB/외부 서비스/Docker를 도입하지 않는다. 라우터는 기존 앱에 자동 등록(백엔드 `main.py` U6 라인, 프론트 라우트 레지스트리).

---

## 3. 비목표 (Out of Scope, U6)
- **실시간 성능(NFR-1)·SSE 브로커 구현** — U5 소유. U6는 close 후 `order_deleted` 이벤트를 **best-effort 발행**만(broker 미구현 시 `NotImplementedError` 흡수).
- **관리자 인증 자체(JWT 발급/검증)** — U2 소유. U6는 `get_current_admin` 계약을 **소비**만.
- **이력 페이지네이션/무한 스크롤** — MVP 범위 밖(FD Q8=A: flat list).
- **프로세스 재시작 간 실시간 이벤트 영속성** — 세션·이력은 SQLite로 유지되나, in-memory 브로커 이벤트는 재시작 시 유실(U5 재연결 복구 소유).
- **고동시성/다중 워커 환경의 세션 경합 방지** — 내부 `SessionLocal`·단일 프로세스 전제(NFR-7 로컬 정합). 상세 리스크는 `nfr-design.md §6`.

---

## 4. 검증 방법 (요약)
- **SES-1, DAT-1**: `backend/tests/test_lifecycle_pbt.py`(P1), `test_close_pbt.py`(P2) — Hypothesis.
- **SES-3, DAT-2**: `test_close_pbt.py`(무세션 CONFLICT, 커밋 후 총액 0·원본 삭제).
- **DAT-3/4**: `test_history.py`(매장 스코프·최신순·테이블 필터·KST 경계·형식 오류).
- **TST-3**: `frontend/src/features/admin/history/query.pbt.test.ts` — fast-check.
- **USA-1**: 공유 `Button`(min 44×44) 사용, `npm run build` 통과.
- **POR-1**: 로컬 기동 스모크(라우트 등록·`/api/health`·엔드포인트 200/409/422).

> Part 2(설계) = `nfr-design.md`: 위 요구사항을 어떤 메커니즘·구성으로 충족하는지.
