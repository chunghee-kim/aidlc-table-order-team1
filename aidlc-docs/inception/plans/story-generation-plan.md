# 사용자 스토리 생성 계획서 (Story Generation Plan)

**역할**: Product Owner
**목적**: 요구사항(`requirements.md`)을 페르소나 기반 사용자 스토리와 수용 기준으로 변환

이 계획서는 (1) 스토리 생성 방법론 체크리스트와 (2) 방향 결정을 위한 질문으로 구성됩니다.
아래 **질문 섹션**의 각 `[Answer]:` 태그 뒤에 문자를 채워주세요. 맞는 보기가 없으면 마지막 **Other**를 선택하고 직접 기술해 주세요.

---

## A. 스토리 생성 방법론 체크리스트 (실행 단계)

- [x] 페르소나 정의 (`personas.md`) — 고객, 관리자 등 사용자 아키타입
- [x] 요구사항(FR/NFR)을 사용자 스토리로 변환 (`stories.md`)
- [x] 각 스토리를 INVEST 기준(Independent, Negotiable, Valuable, Estimable, Small, Testable) 충족하도록 작성
- [x] 각 스토리에 수용 기준(Acceptance Criteria) 포함
- [x] 페르소나를 관련 스토리에 매핑
- [x] 승인 대상이 되는 비즈니스 규칙(주문 금액 계산, 세션 전이 등) 명시

---

## B. 스토리 분해 접근법 (Story Breakdown Options)

아래는 스토리를 조직하는 방식입니다. 트레이드오프를 참고해 Q4에서 선택해 주세요.

- **User Journey-Based**: 사용자 워크플로우(주문 여정)를 따라 스토리 구성 — 흐름 이해에 강점
- **Feature-Based**: 시스템 기능(메뉴 관리, 주문 모니터링 등) 중심 — 기능 완결성에 강점
- **Persona-Based**: 사용자 유형(고객/관리자)별 그룹화 — 역할별 책임 명확
- **Epic-Based**: 상위 에픽 아래 하위 스토리로 계층 구성 — 대규모 범위 관리에 강점
- **Hybrid**: 위 방식 조합 (예: 페르소나로 최상위 그룹 + 각 그룹 내 여정순)

---

## C. 질문 (Questions)

## Question 1
스토리 문서에 사용할 **스토리 작성 형식**은 무엇을 선호하시나요?

A) 표준 형식: "As a [역할], I want [기능], so that [가치]" + 수용 기준

B) 표준 형식 + Gherkin 스타일 수용 기준 (Given/When/Then)

C) 간결 형식: 제목 + 한 줄 설명 + 수용 기준 목록

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 2
**수용 기준(Acceptance Criteria)의 상세 수준**은 어느 정도가 적절할까요?

A) 상세 — 각 스토리마다 정상/예외/경계 시나리오까지 명시 (테스트 근거로 활용)

B) 표준 — 핵심 정상 흐름 + 주요 예외 위주

C) 간략 — 핵심 확인 항목만 불릿으로

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 3
**페르소나 범위**를 어떻게 정의할까요? (요구사항상 기본은 고객 + 관리자)

A) 2개: 고객(주문자) + 매장 관리자

B) 3개: 고객(주문자) + 매장 관리자 + 시스템 설치자(태블릿 초기 설정 담당) 분리

C) 2개 + 각 페르소나에 세부 상황(예: 첫 방문 고객 vs 추가 주문 고객) 서술

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4
**스토리 분해 접근법**(위 B 섹션 참고)은 무엇으로 할까요?

A) Persona-Based (고객/관리자별 그룹화)

B) User Journey-Based (주문 여정 흐름 중심)

C) Feature-Based (기능 중심)

D) Hybrid — 페르소나로 최상위 그룹 + 각 그룹 내 기능/여정순 (권장)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 5
**스토리 세분화 수준(granularity)**은 어느 정도가 좋을까요?

A) 세분화 — 기능을 작은 단위 스토리로 쪼갬 (예: "장바구니 수량 증가" / "장바구니 항목 삭제" 별도)

B) 중간 — 응집된 기능 단위로 묶음 (예: "장바구니 관리" 하나에 수용 기준으로 세부 명시)

C) 큰 단위 — 에픽 수준 스토리 위주

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
**MVP 범위 우선순위 표기**를 스토리에 포함할까요? (요구사항 문서의 MVP 필수 기능 기준)

A) 예 — 각 스토리에 우선순위(Must/Should/Could) 태그 표기

B) 아니오 — 우선순위 없이 스토리만 작성 (MVP 필수 기능은 모두 포함)

X) Other (please describe after [Answer]: tag below)

[Answer]: A
