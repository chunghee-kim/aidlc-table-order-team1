# Table Order Service (테이블오더 서비스)

QR/태블릿 기반 매장 테이블오더 데모. **FastAPI + SQLite** 백엔드와 **React(Vite) + TypeScript** 프론트엔드로 구성된 로컬 실행용 모놀리스입니다.

- 고객(태블릿): 자동 로그인 → 메뉴 탐색 → 장바구니 → 주문 → 주문 현황
- 관리자: 로그인 → 테이블 설정 → 메뉴 관리 → 테이블 마감 → 주문 이력

## 요구 사항

- **Python 3.11+** (개발 검증: 3.12)
- **Node 18+** (개발 검증: 24)
- OS 무관 (개발 환경: Windows 11 + Git Bash)

## 빠른 시작

백엔드와 프론트엔드를 **각각 별도 터미널**에서 실행합니다.

### 1) 백엔드 (`backend/`)

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate        # Windows Git Bash
# source .venv/bin/activate          # macOS / Linux
pip install -r requirements.txt
cp .env.example .env                 # JWT_SECRET 등 확인 (.env 는 커밋 금지)
python -m app.seed                   # 초기 시드 (멱등 — 여러 번 실행해도 안전)
uvicorn app.main:app --reload        # http://localhost:8000
```

동작 확인: `GET http://localhost:8000/api/health` → `{"status":"ok","db":"ok"}`
API 문서(OpenAPI): http://localhost:8000/docs

### 2) 프론트엔드 (`frontend/`)

```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

> Vite dev 서버가 `/api` 요청을 `http://localhost:8000` 으로 프록시합니다. 백엔드를 먼저 띄워 두세요.
> Windows에서 `npm` 실행 시 esbuild 설치가 node를 못 찾으면, npm 실행 전 `export PATH="/c/Program Files/nodejs:$PATH"` 를 먼저 실행하세요.

## 시드 데이터 / 로그인 정보

`python -m app.seed` 가 아래를 생성합니다 (멱등):

| 항목 | 값 |
|---|---|
| 매장 코드 | `STORE01` (데모 카페) |
| 관리자 계정 | `admin` / `admin1234` |
| 메뉴 | 4개 카테고리 · 카테고리당 4~6개 |
| 테이블 | 1 ~ 12번 (각 테이블 비밀번호 = 테이블 번호 문자열, 예: 5번 → `5`) |

## 화면 (프론트엔드 경로)

**관리자** (`/admin`)
- `/admin/login` — 관리자 로그인
- `/admin/table-setup` — 태블릿 초기 설정(테이블 번호/비밀번호 등록, 자동 로그인 활성화)
- `/admin/menu-manage` — 메뉴 관리(CRUD·정렬)
- `/admin/table-close` — 테이블 마감(주문 이력 이관 + 세션 리셋)
- `/admin/history` — 주문 이력 조회

**고객** (`/customer`)
- `/customer/start` — 자동 로그인 부트스트랩
- `/customer/table-login` — 테이블 로그인
- `/customer/menu` — 메뉴 탐색
- `/customer/cart` — 장바구니
- `/customer/order/confirm` — 주문 확인
- `/customer/order/success` — 주문 완료
- `/customer/orders` — 현재 주문 현황

### 데모 흐름 예시

1. 관리자 로그인(`admin`/`admin1234`) → `/admin/table-setup` 에서 테이블(예: 5번) 설정
2. 고객 화면에서 매장코드 `STORE01` / 테이블 `5` / 비밀번호 `5` 로 로그인
3. 메뉴 담기 → 주문 → 관리자 `/admin/history` 및 `/admin/table-close` 에서 확인

## 테스트

### 백엔드 (pytest + Hypothesis PBT)
```bash
cd backend
pytest
```

### 프론트엔드
```bash
cd frontend
npm run typecheck    # tsc --noEmit
npm run build        # tsc --noEmit && vite build
npm run test         # vitest (fast-check PBT)
```

## 환경 변수 (`backend/.env`)

`.env.example` 참고:

| 변수 | 기본값 | 설명 |
|---|---|---|
| `JWT_SECRET` | `dev-insecure-change-me` | 관리자 JWT 서명 시크릿 (**운영 시 반드시 교체**) |
| `DATABASE_URL` | `sqlite:///./tableorder.db` | SQLite 파일 경로 |
| `BCRYPT_COST` | `12` | 비밀번호 해시 비용 |
| `CORS_ORIGINS` | `http://localhost:5173` | 허용 오리진(쉼표 구분) |

## 아키텍처 개요

- **모놀리스**: `backend/` (Router → Service → Repository 3계층) + `frontend/` (기능 단위, `/customer` · `/admin` 라우트 분리)
- **인증**: 관리자 JWT(16시간, localStorage) · 태블릿 자동 로그인 세션
- **실시간**: 인메모리 pub/sub 브로커 + SSE
- **에러 규약**: 전 구간 `{error:{code, message, details}}`
- 상세: [`CLAUDE.md`](CLAUDE.md), 설계 문서 [`aidlc-docs/`](aidlc-docs/)

## 현재 구현 상태

Phase 0(U1 기반) 완료 후 Phase 1 5개 스트림을 `develop` 브랜치에 통합했습니다.

| 유닛 | 기능 | 상태 |
|---|---|---|
| U1 | Foundation & Data (스키마·시드·계약) | ✅ 구현 |
| U2 | Auth & Session (관리자 인증·테이블 설정·자동 로그인) | ✅ 구현 |
| U3 | Menu (메뉴 탐색·관리) | ✅ 구현 |
| U4 | Cart & Order (장바구니·주문) | ✅ 구현 |
| U5 | Order Monitoring (SSE 실시간 모니터링) | 📄 설계만(코드 미구현) |
| U6 | Session Lifecycle & History (테이블 마감·주문 이력) | ✅ 구현 |

> U5(관리자 실시간 주문 모니터링)는 설계 산출물만 존재하며 코드 구현은 아직입니다. `backend/app/main.py` 의 `admin_order` 라우터는 주석 처리된 상태입니다.
