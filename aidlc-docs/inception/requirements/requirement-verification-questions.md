# 요구사항 명확화 질문 (Requirements Clarification Questions)

아래 질문에 답해 주세요. 각 질문의 `[Answer]:` 태그 뒤에 선택한 **문자(A, B, C ...)**를 적어주시면 됩니다.
보기 중 맞는 것이 없으면 마지막 **"Other"** 옵션을 고르고 `[Answer]:` 태그 뒤에 직접 설명을 적어주세요.

요구사항 문서(`requirements/table-order-requirements.md`)에 이미 명시된 항목(JWT 16시간 세션, bcrypt, SSE 실시간, 로컬 장바구니 등)은 그대로 채택합니다. 아래는 구현에 필요한 **미결정 사항**입니다.

---

## Question 1
프론트엔드(고객용 + 관리자용 웹 UI)는 어떤 기술로 구현할까요?

A) React (예: Vite + React)

B) Vue 3

C) 순수 HTML/CSS/JavaScript (프레임워크 없음)

D) Next.js (React 기반 풀스택)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 2
백엔드 서버 시스템은 어떤 언어/프레임워크로 구현할까요?

A) Python + FastAPI

B) Node.js + Express

C) Java + Spring Boot

D) Python + Django

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 3
데이터 저장소(매장/메뉴/주문/과거 이력)는 무엇을 사용할까요?

A) PostgreSQL (관계형)

B) MySQL / MariaDB (관계형)

C) SQLite (파일 기반, 로컬 개발/데모에 간편)

D) MongoDB (NoSQL 문서)

X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 4
이 애플리케이션의 실행/배포 대상 환경은 어디인가요?

A) 로컬 개발 환경만 (내 PC에서 실행, 데모/학습 목적)

B) AWS 클라우드 (예: ECS/EC2/Lambda 등)

C) Docker 컨테이너 (로컬 또는 어디서든 실행 가능하게)

D) 기타 클라우드 (Azure, GCP 등)

X) Other (please describe after [Answer]: tag below)

[Answer]: A(Docker 없는 환경)

---

## Question 5
매장(Store)과 관리자 계정은 어떻게 생성되나요? (요구사항의 "매장 인증"은 계정이 이미 있다고 가정)

A) 초기 시드 데이터로 미리 생성 (샘플 매장 1개 + 관리자 계정, 코드/스크립트로 주입)

B) 관리자 회원가입 화면을 별도로 구현 (매장/계정 자체 등록)

C) 시드 데이터로 생성하되, 매장 정보 수정 기능만 추가

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 6
초기 메뉴 데이터와 메뉴 이미지는 어떻게 처리할까요? (제약사항상 이미지 리사이징/업로드 처리는 제외)

A) 샘플 메뉴 시드 데이터 제공 + 이미지는 외부 URL 참조만 (업로드 없음)

B) 빈 상태로 시작하고 관리자가 메뉴 관리 화면에서 직접 등록

C) 샘플 시드 데이터 제공 + 이미지 없이 플레이스홀더 사용

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 7
예상 사용 규모(동시성)는 어느 정도로 설계할까요? (아키텍처/기술 선택에 영향)

A) 소규모 — 매장 1개, 테이블 10~20개 수준 (데모/MVP)

B) 중규모 — 매장 수십 개, 테이블 수백 개

C) 대규모 — 멀티테넌트, 수천 테이블 동시 운영

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 8
관리자/고객 UI를 하나의 앱으로 만들지, 분리할지 결정해 주세요.

A) 단일 프로젝트에 두 화면(경로 분리, 예: /customer, /admin)

B) 고객용/관리자용 프론트엔드를 별도 앱으로 분리

C) 상관없음 — 권장안으로 진행

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 9: Security Extensions
Should security extension rules be enforced for this project?
(이 프로젝트에 보안 확장 규칙을 적용할까요?)

A) Yes — 모든 SECURITY 규칙을 차단성(blocking) 제약으로 적용 (프로덕션급 애플리케이션 권장)

B) No — SECURITY 규칙 생략 (PoC, 프로토타입, 실험적 프로젝트에 적합)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 10: Resiliency Extensions
Should the resiliency baseline be applied to this project?
(복원력 베이스라인을 적용할까요? — AWS Well-Architected 신뢰성 기둥 기반의 설계 시점 모범사례 가이드. 프로덕션 인증이 아니라 좋은 출발점을 제공)

A) Yes — 복원력 베이스라인을 설계 시점 지침으로 적용 (비즈니스 크리티컬 워크로드 권장)

B) No — 복원력 베이스라인 생략 (빠른 반복이 중요한 PoC/프로토타입/실험 프로젝트에 적합)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 11: Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?
(속성 기반 테스트 규칙을 적용할까요?)

A) Yes — 모든 PBT 규칙을 차단성 제약으로 적용 (비즈니스 로직, 데이터 변환, 직렬화, 상태 컴포넌트가 있는 프로젝트 권장)

B) Partial — 순수 함수와 직렬화 왕복(round-trip)에만 PBT 적용 (알고리즘 복잡도가 제한적인 프로젝트에 적합)

C) No — PBT 규칙 생략 (단순 CRUD, UI 전용, 얇은 통합 계층에 적합)

X) Other (please describe after [Answer]: tag below)

[Answer]: A
