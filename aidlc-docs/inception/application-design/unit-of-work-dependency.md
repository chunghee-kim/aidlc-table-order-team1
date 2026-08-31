# Unit of Work — 의존성 매트릭스 및 빌드 순서

**단계**: INCEPTION — Units Generation (Part 2: Generation)
**범위**: 유닛 간 의존성 매트릭스, 계약 의존, 빌드 순서, 검증.
**근거**: `component-dependency.md §7`, `services.md §4`, `unit-of-work.md`.

---

## 1. 유닛 의존성 매트릭스 (Unit Dependency Matrix)

행(의존하는 유닛) → 열(의존 대상). ✔ = 직접 의존, ⓒ = 계약 의존(런타임 위임).

| 유닛 \ 대상 | U1 | U2 | U3 | U4 | U5 | U6 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| **U1** Foundation | — | | | | | |
| **U2** Auth & Session | ✔ | — | | | | |
| **U3** Menu | ✔ | ✔ | — | | | |
| **U4** Cart & Order | ✔ | ✔ | ✔ | — | | ⓒ |
| **U5** Monitoring (SSE) | ✔ | ✔ | | ✔ | — | |
| **U6** Session & History | ✔ | ✔ | | ✔ | ✔ | — |

- **순환 없음**: U4→U6은 **계약 의존(ⓒ)**으로, U6이 소유한 `get_or_start_active_session`을 U4가 호출하는 런타임 위임입니다. U6은 U4의 Order/Session 데이터에 구조적으로 의존(✔)하므로, 빌드 순서상 U4가 먼저 완성되고 U6이 라이프사이클을 완성합니다 → **빌드 DAG는 선형 유지**.

### 1.1 의존성 근거 (Why)
| 유닛 | 의존 대상 | 이유 |
|---|---|---|
| U2 | U1 | 데이터 모델(AdminUser/Table/Session), DB 세션, 에러 규약 |
| U3 | U1, U2 | 모델(Menu/Category) + 관리자 보호 엔드포인트(AuthDependency) |
| U4 | U1, U2, U3 | 모델(Order/OrderItem), 세션 컨텍스트, 단가 확정(MenuRepo) |
| U5 | U1, U2, U4 | 주문 데이터·상태, 관리자 인증, 주문 생성이 이벤트 소스 |
| U6 | U1, U2, U4, U5 | 세션·주문 데이터, 관리자 인증, 이용 완료가 대시보드(U5) 총액 리셋 유발 |

---

## 2. 계약 의존 상세 (Contract Dependencies)

### 2.1 U4 ↔ U6 — 세션 시작 (Session Start)
```
[U4] OrderService.create_order(session_ctx, items)
        │
        └──ⓒ위임──▶ [U6] TableSessionService.get_or_start_active_session(table_id)
                        # 🔬 활성 세션 ≤ 1, 없으면 시작
                     ◀── session_id 반환
```
- **소유**: 규칙·구현 = U6. **호출**: U4 OrderService.
- **계약 안정성**: `get_or_start_active_session(table_id) -> session_id` 시그니처는 U4/U6 공통 계약. 변경 시 양측 갱신.

### 2.2 U5 ← U4 — 이벤트 소스 (Event Source)
```
[U4] OrderService.create_order → (커밋 후) [U5] OrderEventBroker.publish('order_created')
```
- U4의 주문 생성이 U5 SSE 스트림의 소스. U5는 U4 완성 후 실시간 계층을 얹음.

### 2.3 U6 → U5 — 총액 리셋 전파
```
[U6] close_table → [U5] OrderEventBroker.publish('order_deleted'/'table_reset') → 대시보드 총액 0
```

---

## 3. 빌드 순서 (Build Sequencing)

```
U1 Foundation & Data      (의존성 없음 · 최우선)
  └─▶ U2 Auth & Session
        └─▶ U3 Menu
              └─▶ U4 Cart & Order  🔬        ◀─┐ 계약 의존(ⓒ)
                    └─▶ U5 Monitoring 🔬       │
                          └─▶ U6 Session & History 🔬 ─┘
```

**권장 순서(논리 DAG)**: U1 → U2 → U3 → U4 → U5 → U6 (Foundation-First 선형)

- U1은 전 유닛의 공유 기반(모델·인프라).
- U2는 전 관리자 보호 엔드포인트의 인증 의존성.
- U5·U6는 U4의 주문/세션 데이터에 의존 → 반드시 U4 이후.
- U6은 U4의 세션 시작 계약을 완성하고 U5의 이벤트 채널을 재사용 → 마지막.

### 3.1 병렬 빌드 모델 (5인 · 2-Phase)
논리 의존은 선형이지만, **계약 우선(Contract-First)**으로 실행을 병렬화한다.

```
Phase 0 (1인 선행 · 유일 직렬 구간)
  U1 실구현 + 전 교차 계약 스텁 동결
   (AuthDependency · TableSessionService · OrderEventBroker · MenuRepo · schemas · 프론트 Context/SseClient)
        │  머지 → 착수 신호
        ▼
Phase 1 (5인 병렬 · 스텁 대상 개발)
  A(U2) ─┐
  B(U3) ─┤
  C(U4) ─┼─▶ 통합 PR(파사드/DI 조립) ─▶ 종단 검증
  D(U5) ─┤
  E(U6) ─┘
```

- **직렬 구간은 Phase 0뿐**(크리티컬 패스). 이후 U2~U6는 계약 스텁에 대고 병렬 개발.
- 하드 의존(U4의 MenuRepo 단가, U5의 주문 데이터, U6의 세션/이벤트 계약)은 Phase 0 스텁 동결로 "빌드 타임 하드 의존" → "머지 타임 통합"으로 완화.
- **권장 머지 순서**: A → B → C → (D,E 병렬) → 조립 PR. 남는 통합 지점은 `services/order/__init__.py`·`services/table_session/__init__.py` 파사드와 DI 조립뿐(스텁 동결로 1~2줄).

> 병렬 스트림 소유·파일 분리 상세는 `unit-of-work.md §3·§5`, 실행/검증 절차는 `parallel-execution.md` 참조.

---

## 4. 공통 인프라 → 유닛 (Cross-Cutting Reference)

| 공통 관심사 | 소유 | 참조 유닛 |
|---|---|---|
| 데이터 모델·시드·DB 세션·에러 규약 | U1 | 전 유닛 |
| JWT 인증(AuthDependency) | U2 | U3, U5, U6 (보호 엔드포인트) |
| 테이블 세션 컨텍스트 | U2(식별)+U6(라이프사이클) | U4 (주문 시 주입) |
| 실시간 SSE(EventBroker/SseClient) | U5 | U4(이벤트 소스), U6(리셋 전파) |
| ApiClient(REST) | U1 스켈레톤 | 전 유닛 확장 |

---

## 5. 검증 (Validation)

- ✅ **순환 없음**: 빌드 DAG 선형(U1→U6). U4↔U6은 계약 의존(런타임)이며 빌드상 U4→U6 단방향.
- ✅ **모든 의존 대상 선행**: 각 유닛의 의존 대상이 빌드 순서상 앞에 위치.
- ✅ **공통 관심사 단일 소유**: 각 cross-cutting 자산에 단일 소유 유닛 존재(중복 없음).
- ✅ **회귀 안전**: 후행 유닛의 선행 API 계약 변경 시 명시적 갱신 규칙(unit-of-work.md §5).
