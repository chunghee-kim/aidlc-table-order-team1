# U3 Menu — 비기능 요구사항 (NFR Requirements)

**단계**: CONSTRUCTION — Phase 1 (스트림 B) [U3 Menu] — NFR Requirements
**유닛**: U3 Menu
**입력**: `inception/requirements/requirements.md §5`(글로벌 NFR-1~7), U3 구현물, `aidlc-state.md`(Extension 설정)
**계획/결정 근거**: `construction/plans/u3-menu-nfr-requirements-plan.md` (Q1~Q7 전부 권장안)

> 본 문서는 글로벌 NFR을 **U3 범위로 국소화**하여 측정 가능한 목표로 상세화합니다. ID 접두사 `U3-NFR-*`. 각 항목은 글로벌 NFR / 스토리로 추적됩니다.

---

## 1. 요약 (Scope of NFR for U3)

| 분류 | 적용 | U3에서의 초점 |
|---|:--:|---|
| Performance | ✅ | 메뉴/카테고리 조회 지연·초기 렌더 |
| Scalability | ➖(제한적) | 단일 매장·메뉴 ~20건 — 스케일 트리거 없음(경계만 명시) |
| Availability | ➖(제한적) | 로컬 단일 프로세스 — 가용성 SLA 없음(우아한 실패만) |
| Security | ✅ | 읽기 공개 / 쓰기 JWT 보호 / 매장 스코프 격리 / 최소 노출 |
| Reliability | ✅ | 서버 권위 검증(불변식)·트랜잭션 일관성·오류 처리 |
| Maintainability | ✅ | 3계층·구조화 에러·테스트 회귀 방어 |
| Usability | ✅ | 44×44px 터치·카드·이미지 폴백·검증 피드백 |
| Testability | ✅ | PBT 3속성 + 예제/통합 테스트 |

---

## 2. 성능 (Performance)

| ID | 요구사항 | 목표(측정) | 측정 방법 | 추적 |
|---|---|---|---|---|
| U3-NFR-P1 | 메뉴/카테고리 조회 응답 | `GET /api/menus`·`GET /api/categories` **p95 < 300ms**(로컬) | 로컬 부하 없는 상태에서 응답시간 관찰(수동/스크립트) | NFR-1(파생) |
| U3-NFR-P2 | 고객 메뉴 화면 초기 상호작용 | 진입 후 **< 1s** 내 카테고리 탭·카드 렌더 | 브라우저 로드 관찰(로컬 dev) | US-C-03 |
| U3-NFR-P3 | 쿼리 효율(N+1 금지) | 메뉴 목록은 **단일 쿼리**(카테고리 조인 정렬), 항목 수 무관 상수 쿼리 수 | 코드 리뷰(레포지토리 쿼리) | — |
| U3-NFR-P4 | 데이터 규모 전제 | 메뉴 ~20·카테고리 4 기준 **페이지네이션 불필요**, 전량 반환 | 시드 규모 기준 | 규모(소규모) |

**근거**: 단일 매장·소량 데이터·로컬 실행 → 캐시/페이지네이션 도입은 과설계(Q1·Q2=A).

---

## 3. 확장성 (Scalability) — 제한적 적용

| ID | 요구사항 | 목표 | 비고 |
|---|---|---|---|
| U3-NFR-SC1 | 부하 경계 명시 | 동시 사용자 ≤ 테이블 수(10~20) + 관리자 1 | MVP 범위. 스케일아웃 트리거·자동확장 **없음** |
| U3-NFR-SC2 | 성장 시 확장 지점(문서화) | 메뉴 급증 시 ①목록 페이지네이션 ②카테고리별 lazy fetch ③읽기 캐시 도입 여지 | 현재 미구현(향후 옵션) |

**정당화**: 규모 고정(1 매장). 확장 패턴은 **경계와 향후 지점만 기록**하고 구현하지 않음.

---

## 4. 가용성 (Availability) — 제한적 적용

| ID | 요구사항 | 목표 | 비고 |
|---|---|---|---|
| U3-NFR-A1 | 우아한 실패 | 조회 실패 시 고객 화면은 **에러 메시지/빈 상태** 렌더(크래시 없음) | Resiliency Baseline=No → 재시도·서킷브레이커 미도입 |
| U3-NFR-A2 | 빈 데이터 안전 | 미시드/빈 매장에서 조회는 **빈 배열** 반환(예외 아님) | `default_store_id() is None` → `[]` |

---

## 5. 보안 (Security)

| ID | 요구사항 | 목표 | 추적 |
|---|---|---|---|
| U3-NFR-S1 | 읽기 공개 | `GET /api/menus`·`/api/categories`는 **무인증 공개** | 설계(공개 엔드포인트) |
| U3-NFR-S2 | 쓰기 보호 | `POST/PUT/DELETE /api/admin/menus[/{id}]`·`PATCH .../menu-order`는 **`AuthDependency`(JWT) 필수** | NFR-2, US-A-16~18 |
| U3-NFR-S3 | 매장 스코프 격리 | 관리자 작업은 **`actor.store_id`로 스코프** — 타 매장 카테고리/메뉴 접근 시 검증 오류/NOT_FOUND | 멀티테넌시 안전(단일 매장이나 규칙 유지) |
| U3-NFR-S4 | 최소 노출 | `MenuView`는 표시용 필드만(내부 타임스탬프/원가 등 미노출) | 계약(schemas) |
| U3-NFR-S5 | 이미지 URL 신뢰 경계 | 외부 URL은 **표시 전용**, 서버는 fetch/프록시하지 않음(SSRF 표면 없음) | Q5=A |

**미적용(정당화)**: 레이트리밋·WAF·입력 새니타이징(HTML) — Security Baseline=No, 로컬 MVP. 인증 실구현·시도제한은 U2 소관.

---

## 6. 신뢰성 (Reliability)

| ID | 요구사항 | 목표 | 추적 |
|---|---|---|---|
| U3-NFR-R1 | 서버 권위 검증 | `price>0`, `name` 필수(trim·≤100), `category` 동일 매장 소속을 **서버가 최종 검증** | US-A-16 불변식 |
| U3-NFR-R2 | 이중 검증 계층 | Pydantic(형식/타입) → Service(도메인 불변식) → 구조화 오류(`VALIDATION_ERROR`) | error 규약 |
| U3-NFR-R3 | 트랜잭션 일관성 | Service가 commit 소유, Repo는 flush-only. `reorder`는 **단일 트랜잭션** | Q6=A |
| U3-NFR-R4 | 삭제 무결성 | 메뉴 물리 삭제 허용 — 과거 주문은 OrderItem **스냅샷**으로 무결(U3는 스냅샷 생성 안 함, 삭제만) | business-rules §3 |
| U3-NFR-R5 | 오류 응답 표준 | 모든 실패는 `{error:{code,message,details}}` + 적정 HTTP 상태 | ErrorHandler |

---

## 7. 유지보수성 (Maintainability)

| ID | 요구사항 | 목표 |
|---|---|---|
| U3-NFR-M1 | 계층 분리 | Router(검증/매핑) → Service(규칙/트랜잭션) → Repo(영속) 준수 |
| U3-NFR-M2 | 계약 불변 준수 | 동결된 `schemas`·`MenuRepo`/`CategoryRepo` Protocol·`AuthDependency` 미변경(1파일 1스트림 소유) |
| U3-NFR-M3 | 관측성 | 전용 메트릭/트레이싱 미도입(MVP), 구조화 에러 + 기본 로깅 |
| U3-NFR-M4 | 회귀 방어 | PBT + 예제 단위 + TestClient 통합 테스트 유지 |

---

## 8. 사용성 (Usability)

| ID | 요구사항 | 목표 | 추적 |
|---|---|---|---|
| U3-NFR-U1 | 터치 타깃 | 상호작용 요소 **최소 44×44px**(공유 `Button`) | NFR-4, US-C-06 |
| U3-NFR-U2 | 카드 레이아웃 | 메뉴명·가격·설명·이미지의 카드형 표시, 카테고리 탭 이동 | US-C-04·05 |
| U3-NFR-U3 | 이미지 폴백 | 이미지 누락/실패 시 플레이스홀더, 품절(`is_available=false`) 시각 표시 | US-C-05 |
| U3-NFR-U4 | 검증 피드백 | 관리자 입력 오류를 명확한 한글 메시지로 표시(가격/필수) | US-A-16 |
| U3-NFR-U5 | 가격 표기 | 통화 로캘 표기(`ko-KR`, "원") | 사용성 |

---

## 9. 테스트 (Testability) — PBT 전면(NFR-6)

| ID | 속성/케이스 | 프레임워크 | 위치 |
|---|---|---|---|
| U3-NFR-T1 | `price ≤ 0` 입력은 항상 `VALIDATION_ERROR`(🔬) | Hypothesis | `backend/tests/test_menu_service.py` |
| U3-NFR-T2 | 공백/빈 `name`은 항상 거부(🔬) | Hypothesis | 〃 |
| U3-NFR-T3 | 유효 입력(price>0·name 비공백)은 항상 생성·라운드트립(🔬) | Hypothesis | 〃 |
| U3-NFR-T4 | CRUD·순서·소유권·NOT_FOUND 예제 | pytest | 〃 |
| U3-NFR-T5 | 공개/보호 엔드포인트·검증 422·순서 반영 통합 | pytest + TestClient | `backend/tests/test_menu_api.py` |

---

## 10. 추적 매트릭스 (글로벌 NFR → U3)

| 글로벌 NFR | U3 국소화 |
|---|---|
| NFR-1 성능(SSE 2s) | U3-NFR-P1~P4 (메뉴 조회 성능; SSE 자체는 U5) |
| NFR-2 보안 | U3-NFR-S1~S5 (읽기 공개/쓰기 JWT/스코프) |
| NFR-4 사용성 | U3-NFR-U1~U5 |
| NFR-6 테스트(PBT) | U3-NFR-T1~T5 |
| NFR-7 이식성 | 로컬 실행·추가 인프라 미도입(§3·§7) |

> NFR-3(세션)·NFR-5(장바구니 지속성)는 U3 범위 밖(U2/U6·U4).
