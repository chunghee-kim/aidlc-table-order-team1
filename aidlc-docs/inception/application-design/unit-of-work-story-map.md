# Unit of Work — 스토리 매핑 (Story Map)

**단계**: INCEPTION — Units Generation (Part 2: Generation)
**범위**: 32개 사용자 스토리 + SD 시드 태스크의 유닛 배정 및 커버리지 검증.
**근거**: `user-stories/stories.md`, `workflow/workflow.md §1`, `components.md §4`.

---

## 1. 스토리 → 유닛 매핑 (Story → Unit)

### U1 — Foundation & Data
| ID | 스토리 | 우선순위 |
|---|---|---|
| SD-1 | 프로젝트 스캐폴딩(Vite+React `/customer`·`/admin`, FastAPI) | Must |
| SD-2 | SQLite 스키마(9개 모델) + DB 세션/에러 규약 | Must |
| SD-3 | 시드 스크립트(매장1 + 관리자 + 카테고리/메뉴 + 테이블 10~20) | Must |

> SD-1~3은 사용자 스토리가 아닌 **기반 개발 태스크**로, workflow.md에서 U1에 귀속.

### U2 — Auth & Session
| ID | 스토리 | 우선순위 | PBT |
|---|---|---|:--:|
| US-A-01 | 관리자 로그인 | Must | |
| US-A-02 | 16시간 세션 유지 | Must | |
| US-A-03 | 로그인 시도 제한 | Should | |
| US-A-04 | 테이블 태블릿 초기 설정 | Must | |
| US-C-01 | 테이블 태블릿 자동 로그인 | Must | |
| US-C-02 | 테이블 세션 식별 유지 | Must | |

### U3 — Menu 🔬
| ID | 스토리 | 우선순위 | PBT |
|---|---|---|:--:|
| US-C-03 | 기본 메뉴 화면 표시 | Must | |
| US-C-04 | 카테고리별 메뉴 분류·이동 | Must | |
| US-C-05 | 메뉴 상세 정보 표시 | Must | |
| US-C-06 | 터치 친화적 메뉴 UI | Should | |
| US-A-16 | 메뉴 등록 | Must | 🔬 |
| US-A-17 | 메뉴 수정·삭제 | Must | |
| US-A-18 | 메뉴 노출 순서 조정 | Should | |

### U4 — Cart & Order 🔬
| ID | 스토리 | 우선순위 | PBT |
|---|---|---|:--:|
| US-C-07 | 장바구니에 메뉴 추가 | Must | |
| US-C-08 | 장바구니 항목 수량 조절 | Must | 🔬 |
| US-C-09 | 장바구니 항목 삭제 | Must | |
| US-C-10 | 장바구니 비우기 | Should | |
| US-C-11 | 장바구니 로컬 지속성 | Must | 🔬 |
| US-C-12 | 주문 최종 확인·확정 | Must | 🔬 |
| US-C-13 | 주문 성공 플로우 | Must | |
| US-C-14 | 현재 세션 주문 내역 조회 | Must | |

### U5 — Order Monitoring (SSE) 🔬
| ID | 스토리 | 우선순위 | PBT |
|---|---|---|:--:|
| US-A-05 | 테이블별 그리드 대시보드 | Must | |
| US-A-06 | SSE 실시간 신규 주문 반영 | Must | |
| US-A-07 | 주문 카드 상세 보기 | Must | |
| US-A-08 | 테이블별 필터링 | Should | |
| US-A-09 | 주문 상태 변경 | Must | 🔬 |
| US-A-10 | 주문 삭제(직권 수정) | Must | 🔬 |

### U6 — Session Lifecycle & History 🔬
| ID | 스토리 | 우선순위 | PBT |
|---|---|---|:--:|
| US-A-11 | 테이블 세션 시작 | Must | 🔬 |
| US-A-12 | 테이블 이용 완료 처리 | Must | 🔬 |
| US-A-13 | 테이블별 과거 내역 조회 | Must | |
| US-A-14 | 과거 내역 날짜 필터 | Should | |
| US-A-15 | 과거 내역 닫기 | Could | |

---

## 2. 커버리지 검증 (Coverage Verification)

### 2.1 유닛별 스토리 수
| 유닛 | 스토리 수 | Must | Should | Could |
|---|:--:|:--:|:--:|:--:|
| U1 | 3 (SD) | 3 | — | — |
| U2 | 6 | 5 | 1 | — |
| U3 | 7 | 5 | 2 | — |
| U4 | 8 | 7 | 1 | — |
| U5 | 6 | 5 | 1 | — |
| U6 | 5 | 3 | 1 | 1 |
| **합계** | **32 (+3 SD)** | **23** | **6** | **1** |

> stories.md 요약과 일치: 32 스토리 (Must 23 / Should 8 / Could 1). 여기서 Should는 유닛 분산상 U2·U3(2)·U4·U5·U6 + C-06 등으로, 총 8개(C-06, C-10, A-03, A-08, A-14, A-18)가 각 유닛에 포함됨.

### 2.2 전체 스토리 배정 확인
- 고객 스토리 US-C-01 ~ US-C-14 → **14개 전부 배정** (U2:2, U3:4, U4:8)
- 관리자 스토리 US-A-01 ~ US-A-18 → **18개 전부 배정** (U2:4, U3:3, U5:6, U6:5)
- ✅ **32/32 커버**, 미배정·중복 배정 없음.
- ✅ SD-1~3 시드 태스크 → U1 배정.

---

## 3. PBT 대상 규칙 → 유닛 매핑 (PBT Rules)

| 규칙 | 유형 | 유닛 | 스토리 |
|---|---|:--:|---|
| 장바구니 총액 = Σ(단가×수량), 수량≥1 | Invariant | U4 | US-C-08, US-C-12 |
| 장바구니 로컬 저장 라운드트립 | Round-trip | U4 | US-C-11 |
| 주문 상태 전이(대기중→준비중→완료) | Invariant/Stateful | U5 | US-A-09 |
| 삭제 후 테이블 총액 = 남은 주문 합 | Invariant | U5 | US-A-10 |
| 활성 세션 최대 1개 + 완료 무손실 이관 | Stateful | U6 | US-A-11, US-A-12 |
| 메뉴 가격(>0)·필수 필드 검증 | Invariant | U3 | US-A-16 |

> 6개 PBT 규칙이 U3·U4·U5·U6에 명시적 산출물로 배정됨. CONSTRUCTION Functional Design(PBT-01)에서 테스트 가능한 속성으로 상세화.

---

## 4. 요약

- ✅ 32개 사용자 스토리 + 3개 시드 태스크 전부 유닛에 배정 (미배정/중복 없음).
- ✅ 6개 PBT 규칙이 해당 유닛에 명시.
- ✅ workflow.md·components.md의 유닛 매핑과 일관.
