# Frame Science

React 학생·학부모·조교 공통 Frontend와 FastAPI Backend입니다. 현재 구현 범위는 **로그인/Auth**입니다. 계정 Profile, 사용자 관리, 강의·클리닉 및 실제 메인 UI는 포함하지 않습니다. 도메인 경계가 확정된 기능만 추가하며 미래 서비스를 미리 생성하지 않습니다.

## 구조

```text
Backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI, Origin 검사, no-store
│   ├── config.py            # .env, 설정 검증
│   ├── database.py          # 동기 SQLAlchemy engine/session/base
│   ├── errors.py            # 공통 오류 응답
│   ├── redis_store.py       # Redis 연결, 계정 세션 폐기
│   └── auth/
│       ├── __init__.py
│       ├── models.py       # user_account만 정의
│       ├── schemas.py
│       ├── repository.py
│       ├── service.py
│       ├── security.py     # Argon2, JWT, 비밀번호 정책
│       ├── dependencies.py # current_account, require_roles
│       ├── sender.py       # 로컬 콘솔 Sender 교체 지점
│       └── router.py
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/0001_user_account.py
├── scripts/{seed_test_accounts.py,smoke_auth.py}
├── tests/test_auth.py
├── alembic.ini
├── .env.example
└── requirements.txt
Frontend/
├── src/
│   ├── admin/              # 아직 기능 없음
│   ├── student/            # 아직 기능 없음
│   ├── app/{router.tsx,queryClient.ts,PlaceholderPage.module.css}
│   ├── common/auth/
│   │   ├── AuthPage.module.css
│   │   ├── MessageModal.module.css
│   │   ├── AuthField.tsx
│   │   ├── validation.ts
│   │   ├── LoginPage.tsx
│   │   ├── ResetPage.tsx
│   │   ├── MessageModal.tsx
│   │   └── useAuth.ts
│   ├── services/api.ts
│   ├── styles/global.css
│   ├── App.tsx
│   └── main.tsx
├── tests/auth.test.mjs
├── vite.config.ts
└── package.json
```

## 실행

PostgreSQL localhost:5432, Redis localhost:6379가 실행 중이어야 합니다. 기존 가상환경과 프로젝트를 그대로 사용합니다.

```bash
cd Backend
# 최초 설정 시에만 실행. 기존 .env를 덮어쓰지 않습니다.
test -f .env || cp .env.example .env
# .env의 DATABASE_URL과 서로 다른 32자 이상 Secret 두 개를 설정합니다.
# Secret 생성 예: .venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))'
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m scripts.seed_test_accounts
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

다른 터미널에서:

```bash
cd Frontend
npm ci
npm run dev -- --host 127.0.0.1
```

- 화면: http://127.0.0.1:5173/login
- API 문서: http://127.0.0.1:8000/docs
- Vite `/api` 프록시가 FastAPI로 전달하므로 개발 쿠키는 Frontend와 동일 출처입니다.
- 서버 시작 시 설정을 읽습니다. `.env` 변경 후 Backend를 재시작합니다.

## 개발 계정

`APP_ENV=local`에서만 Seed를 실행할 수 있습니다. 같은 번호가 있으면 비밀번호·역할·활성 상태를 수정하지 않습니다.

| 역할 | 휴대폰 번호 | 최초 비밀번호 |
|---|---|---|
| STUDENT | 01012345678 | 5678 |
| PARENT | 01023456789 | 6789 |
| STAFF | 01034567890 | 7890 |

DB에는 Argon2id 해시만 저장합니다. 새 비밀번호에는 8자 이상, ASCII 영문·숫자·특수문자(`string.punctuation`)를 요구합니다. 초기 4자리 비밀번호는 Seed의 초기 계정 정책입니다. 가입 API는 없습니다.

## 환경변수

`Backend/.env`를 사용하며 환경에 이미 설정된 값이 우선합니다. `.env`, `.venv`, Python 캐시 파일은 Git에서 제외합니다.

| 항목 | 기본값/설명 |
|---|---|
| DATABASE_URL | 필수, `postgresql+psycopg://frame_science:YOUR_PASSWORD@localhost:5432/frame_science` |
| REDIS_URL | `redis://localhost:6379/0` |
| REDIS_PREFIX | `frame:auth:` |
| ACCESS_TOKEN_SECRET | 필수, 32자 이상 무작위 값 |
| REFRESH_TOKEN_SECRET | 필수, Access와 다른 32자 이상 무작위 값 |
| ACCESS_TOKEN_EXPIRE_MINUTES | 15 |
| REFRESH_TOKEN_EXPIRE_DAYS | 14 |
| RESET_CODE_TTL_SECONDS | 300 |
| RESET_TOKEN_TTL_SECONDS | 600 |
| RESET_REQUEST_COOLDOWN_SECONDS | 60 |
| RESET_CODE_MAX_ATTEMPTS | 5 |
| COOKIE_SECURE | local 기본 false, 비로컬 환경은 강제로 true |
| COOKIE_SAMESITE | lax (strict/none 지원, none은 Secure 필요) |
| APP_ENV | local |
| ALLOWED_ORIGINS | `http://localhost:5173,http://127.0.0.1:5173` |

Frontend의 `VITE_API_BASE_URL`은 기본 `/api`입니다. 현 구성은 동일 출처 프록시를 사용합니다. 운영에서는 실제 HTTPS 출처를 `ALLOWED_ORIGINS`에 설정하고 SMS Sender를 구현해야 합니다. 운영 Nginx/CORS 배포 구성은 이번 범위에 포함하지 않습니다.

## DB와 Migration

PostgreSQL `user_account`:

- `id BIGINT` PK
- `phone VARCHAR(11)` UNIQUE NOT NULL
- `password_hash VARCHAR(255)` NOT NULL
- `role VARCHAR(10)` NOT NULL, STUDENT/PARENT/STAFF CHECK
- `is_active BOOLEAN` NOT NULL

PostgreSQL 관례에 맞춰 물리 테이블명은 소문자입니다. Profile 필드는 없습니다. 최초 리비전은 `0001_user_account`, Alembic 내부 테이블은 `alembic_version`입니다. `alembic check`로 모델과 DB 차이를 확인할 수 있습니다.

## Auth API

모든 경로의 접두사는 `/api/auth`, 메서드는 POST입니다. 전화번호는 `010`으로 시작하는 숫자 11자리입니다. 프론트엔드는 입력의 하이픈을 제거합니다.

| 경로 | JSON Request | 성공 Response |
|---|---|---|
| `/login` | `{"phone":"01012345678","password":"5678"}` | 200 `{"accessToken":"…","role":"STUDENT"}` + Refresh Cookie |
| `/refresh` | 없음, Refresh Cookie | 200 `{"accessToken":"…","role":"STUDENT"}` + 새 Refresh Cookie |
| `/logout` | 없음, Refresh Cookie | 204, Cookie 삭제 |
| `/password-reset/request` | `{"phone":"01012345678"}` | 204, 코드 반환 안 함 |
| `/password-reset/verify` | `{"phone":"01012345678","code":"123456"}` | 200 `{"resetToken":"…"}` |
| `/password-reset/confirm` | `{"resetToken":"…","newPassword":"Frame123!","newPasswordConfirm":"Frame123!"}` | 204, 자동 로그인 안 함 |

오류는 모두 `{"code":"ERROR_CODE","message":"사용자 안내"}` 형식입니다.

- 로그인: 401 `AUTH_INVALID_CREDENTIALS`, 403 `ACCOUNT_INACTIVE`
- Refresh: 401 `AUTH_REFRESH_TOKEN_INVALID`, 403 `ACCOUNT_INACTIVE`
- 코드 확인: 400 `PASSWORD_RESET_CODE_INVALID` / `PASSWORD_RESET_CODE_EXPIRED` / `PASSWORD_RESET_CODE_ATTEMPTS_EXCEEDED`
- 비밀번호 변경: 400 `PASSWORD_RESET_TOKEN_INVALID` / `PASSWORD_RESET_TOKEN_EXPIRED`, 422 `PASSWORD_POLICY_VIOLATION` / `PASSWORD_CONFIRM_MISMATCH`
- 공통: 422 `VALIDATION_ERROR`, 503 `SERVICE_UNAVAILABLE`, 500 `INTERNAL_SERVER_ERROR`
- 비로컬 SMS 미설정: 503 `SMS_PROVIDER_UNAVAILABLE` (계정 존재와 무관)
- 허용되지 않은 Origin: 403 `AUTH_ORIGIN_INVALID`

유효 TTL이 지나 Redis에서 사라진 코드/Reset Token은 처음부터 없는 값 및 이미 사용한 값과 구별할 수 없어 EXPIRED로 응답합니다. 별도의 무기한 tombstone은 저장하지 않습니다.

인증번호 TTL 300초, Reset Token TTL 600초, 재요청 간격 60초, 최대 시도 5회는 **변경 가능한 개발 기본값**이며 확정된 서비스 정책이 아닙니다.

## 토큰·Redis 정책

Access JWT(15분): `sub`, `role`, `type=access`, `iat`, `exp`. Frontend 모듈 메모리에만 보관하며 localStorage/sessionStorage를 쓰지 않습니다.

Refresh JWT(14일): `sub`, `jti`, `type=refresh`, `iat`, `exp`. `refresh_token` HttpOnly Cookie, Path `/api/auth`, SameSite 설정, 비로컬 Secure 강제. JWT 알고리즘은 HS256으로 고정하고 필수 Claim을 검증합니다.

Redis 키 접두사는 기본 `frame:auth:`입니다.

| 키 | 저장 내용 | TTL |
|---|---|---|
| `refresh:{jti}` | 계정 ID | Refresh 만료까지 |
| `sessions:{account_id}` | 해당 계정 Refresh 키의 Set | 마지막 발급 Refresh 만료까지 |
| `code:{HMAC(phone)}` | 계정 ID, 비밀번호 해시 지문, 코드 HMAC, 시도 횟수 JSON | RESET_CODE_TTL_SECONDS |
| `reset:{HMAC(token)}` | 계정 ID, 발급 시 비밀번호 해시 지문 JSON | RESET_TOKEN_TTL_SECONDS |
| `cooldown:{HMAC(phone)}` | 재요청 제한 표식 | RESET_REQUEST_COOLDOWN_SECONDS |

- Refresh는 Redis `GETDEL`로 기존 상태를 단 한 번 소비합니다.
- 인증번호 비교·시도 횟수 증가·소비는 Lua 한 작업으로 수행합니다.
- Reset Token은 암호학적 난수이며 DB 변경 직전 원자적으로 소비합니다.
- 로그인/Refresh/Reset은 같은 계정 DB 행 잠금으로 직렬화합니다. 비밀번호 변경 전에 계정의 Refresh 키를 모두 폐기하며 Redis 실패 시 비밀번호 변경도 실패합니다.
- DB와 Redis의 분산 트랜잭션을 도입하지 않습니다. DB Commit 실패 시 토큰/세션이 먼저 폐기될 수 있으므로 새 인증 요청이 필요할 수 있습니다.
- 이전 비밀번호에서 발급된 다른 Reset Token도 비밀번호 해시 지문 비교로 무효화합니다.
- 로그아웃은 해당 Refresh만 폐기합니다. Redis 장애에도 쿠키를 지우고 204를 반환하지만 서버 토큰 폐기는 보장되지 않습니다.
- 기존 Access JWT는 로그아웃/비밀번호 변경 뒤에도 만료까지 유효합니다. 요청 범위대로 Refresh 세션을 무효화하며 Access denylist는 추가하지 않습니다.

개발 Sender는 서버 콘솔에만 6자리 인증번호를 출력합니다. 실제 SMS 업체는 선택하지 않았습니다. 비로컬 환경에서 콘솔 발송은 차단합니다.

## Frontend 흐름

- `/login`: 세 역할 공통, 오류는 네이티브 dialog Modal로 안내합니다.
- 앱 시작: Refresh 한 번 공유 호출 → 메모리 인증 복구 또는 비로그인.
- STUDENT/PARENT → `/student`, STAFF → `/admin`. 잘못된 역할 경로는 자신의 경로로 이동합니다.
- 비로그인 보호 경로 접근 → `/login`.
- 보호 API에는 Bearer 헤더를 붙이고, 401 발생 시 공유 Refresh 작업을 기다린 후 원요청을 한 번만 재시도합니다. 실패하면 인증을 제거합니다. Auth API는 재시도에서 제외합니다.
- `/password-reset`: 번호 → 코드 → 새 비밀번호/확인 → 완료 Modal → 로그인.
- 메인 경로는 개발 예정 문구와 로그아웃 버튼만 표시합니다.

## 패키지

기존 React 19, TypeScript, Vite, React Router, Axios, TanStack Query와 Python 3.14/FastAPI/Pydantic/SQLAlchemy/Alembic/psycopg를 유지합니다. Frontend 의존성은 추가하지 않았습니다.

주요 추가 Python 패키지:

| 패키지 | 버전 | 용도 |
|---|---|---|
| redis | 8.1.0 | Refresh/재설정 상태 |
| PyJWT | 2.15.1 | JWT 발급/검증 |
| pwdlib | 0.3.1 | 비밀번호 해시 API |
| argon2-cffi | 25.1.0 | Argon2id |
| pytest | 9.2.0 | Backend 테스트 |
| httpx | 0.28.1 | API TestClient/실제 HTTP 검증 |

간접 의존성도 `requirements.txt`에 정확한 버전으로 고정합니다: argon2-cffi-bindings 26.1.0, cffi 2.1.1, pycparser 3.12, certifi 2026.10.23, httpcore 1.0.9, iniconfig 2.3.1, packaging 26.3, pluggy 1.7.0, Pygments 2.21.0.

## 검증

```bash
cd Backend
.venv/bin/python -m compileall -q app scripts tests
.venv/bin/python -m pytest -q
.venv/bin/alembic current
.venv/bin/alembic check

cd ../Frontend
npm run test:auth
npm run build
npm run lint
```

Backend 테스트는 실제 PostgreSQL 트랜잭션을 롤백하고 실행별 Redis 접두사만 정리합니다. Seed 계정은 변경하지 않습니다. Frontend 테스트는 기존 Vite로 통신 모듈을 빌드하여 Node 내장 테스트와 Axios adapter로 Refresh 동시성/재시도를 검증합니다. 임의의 테스트용 보호 API는 제품에 추가하지 않습니다.

현재 Starlette는 httpx 기반 TestClient에 deprecation 경고 1개를 표시하지만 테스트 실행은 지원합니다.


### 실제 검증 결과

- Backend: pytest **20 passed**, compileall 성공, Alembic head 및 check 성공.
- Frontend: 인증 통신/입력 검증 테스트 **21 passed**, Build/Lint 성공.
- 두 서버 동시 실행 후 `.venv/bin/python -m scripts.smoke_auth`: Vite 프록시, 세 역할 로그인, 쿠키/Refresh/Logout, 동시 Refresh 200/401 확인.
- Seed 2회 실행 후 계정 수 3개 유지, 재실행 시 기존 계정 변경 없음.
- 브라우저 연결이 제공되지 않아 화면 클릭·모바일 외관·브라우저 새로고침 E2E는 미검증입니다. 앱 초기 인증 복구와 동시성은 자동 테스트로 검증했습니다.
- 초기 샌드박스 네트워크 제한은 승인된 실행으로 해결했습니다. 최초 테스트의 쿠키 경로 불일치는 테스트를 실제 Cookie Path에 맞춰 수정한 뒤 통과했습니다.


## Auth 마무리: DB 접속과 화면

Backend와 DBeaver 모두 PostgreSQL 사용자 `frame_science`, Database `frame_science`, Host `localhost`, Port `5432`를 사용합니다. 기존 개발 비밀번호를 사용하며 README/예제에는 실제 비밀번호를 저장하지 않습니다.

DB 및 Auth 객체(`public.user_account`, `public.alembic_version`, `public.user_account_id_seq`) 소유자는 `frame_science`입니다. 데이터와 Migration을 재작성하지 않고 Auth 객체만 소유권을 변경했습니다.

DBeaver 연결의 Database/User를 위 값으로 설정한 뒤 Refresh하면 `Databases → frame_science → Schemas → public → Tables`에서 두 테이블을 확인할 수 있습니다. DBeaver UI 자체는 자동 조작하지 않았습니다.

- `public/Logo.png`: 기존 PNG 내용은 그대로 보존하고 파일명만 변경. Login에만 적용합니다.
- `styles/global.css`: 전역 기본 설정과 지정된 8색 CSS 변수만 관리합니다.
- `AuthPage.module.css`: Login/Reset 공통 레이아웃과 필드/버튼.
- `MessageModal.module.css`: Modal만 담당합니다.
- `app/PlaceholderPage.module.css`: 임시 화면만 담당합니다.
- 모든 Form은 `noValidate`, React 필드 검증을 사용합니다. 입력 오류는 Label 오른쪽과 테두리에 표시하며 해당 입력 수정 시 해당 오류만 해제합니다.
- Label 연결, `aria-invalid`, `aria-describedby`, 오류 알림을 적용했습니다.
- 입력 검증 실패 시 API를 호출하지 않습니다. 로그인 비밀번호는 미입력만 검사하며 초기 4자리 비밀번호도 허용합니다.
- 새 비밀번호만 Backend와 동일한 영문/숫자/ASCII 특수문자 정책을 검사합니다. 서버가 반환한 정책/확인 불일치 및 잘못된 인증번호는 필드에 표시합니다. 인증 실패·비활성 계정·네트워크·서버 오류와 만료 상태는 Modal로 표시합니다.


### Phone 입력과 Logout 최종 보완

Login/Reset은 공통 `formatPhone()`으로 숫자 최대 11자리를 `010-1234-5678` 형태로 표시합니다. 붙여넣기의 공백/문자는 제거하며 API 직전에는 기존 `normalizePhone()`으로 숫자만 전달합니다. 기존 010/11자리 검증과 초기 4자리 로그인 비밀번호 허용은 유지합니다.

Logout은 진행 중인 Refresh가 끝난 뒤 서버 Logout을 호출하고, 성공한 경우에만 메모리 Session을 지웁니다. 요청 중 새 Refresh와 중복 Logout을 막으며, 이미 시작된 Refresh의 응답은 인증 세대 비교로 Session에 반영하지 않습니다. 서버/네트워크 실패 시 Session과 현재 화면을 유지해 기존 Modal로 오류를 안내하고 다시 시도할 수 있습니다.

Backend는 주석/Docstring만 정리했습니다. JWT Claim, Redis 키, Cookie, TTL, API, DB Schema는 변경하지 않았습니다. 브라우저에서 자동 하이픈 입력·붙여넣기·중간 수정과 Logout 실패 Modal은 별도 수동 확인 대상입니다.


### 커밋 전 예외처리 점검

- 없는 번호와 잘못된 비밀번호는 동일한 401 `AUTH_INVALID_CREDENTIALS` 및 “등록되지 않은 휴대폰 번호이거나 비밀번호가 올바르지 않습니다.”로 응답합니다.
- 삭제된 계정을 가리키는 Access/Refresh는 각각 401 `AUTH_ACCESS_TOKEN_INVALID` / `AUTH_REFRESH_TOKEN_INVALID`입니다. 존재하는 비활성 계정만 403 `ACCOUNT_INACTIVE`입니다.
- 인증번호 오입력, 만료, 기존 최대 시도 횟수 도달을 서로 다른 메시지로 안내합니다. 마지막 오입력은 `PASSWORD_RESET_CODE_ATTEMPTS_EXCEEDED`, 이후에는 `PASSWORD_RESET_CODE_EXPIRED`입니다. 제한 값과 Lua 원자성은 유지합니다.
- Frontend는 잘못된 인증번호를 Field Error로, 만료·횟수 초과를 Modal로 표시하며 “처음부터 다시 요청”을 유지합니다.
- 장애 로그는 traceback의 파일·행·함수와 예외 유형을 기록합니다. 민감정보가 포함될 수 있는 예외 원문, SQL/매개변수, locals, 소스 줄, 요청 본문·Cookie는 포함하지 않습니다. 예상 가능한 AuthError는 오류 traceback을 기록하지 않습니다.
- Logout Redis 장애는 경고를 기록하고 Cookie 삭제 및 204를 유지합니다. 실제 Redis 상태 폐기는 실패할 수 있습니다.
- 기존 로컬 개발용 Console SMS Sender는 별도의 개발 테스트 수단으로 유지합니다. 위 민감정보 제외 정책은 장애/예외 로그에 적용하며, 개발 Sender의 명시적인 인증번호 출력과 구분합니다.
