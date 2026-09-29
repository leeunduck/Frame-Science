# Frame Science

프레임 과학 서비스 개발 프로젝트입니다.

기존 프레임 과학 서비스의 기능과 운영 방식을 참고하되, 기존 사이트를 그대로 복제하지 않고 실제 운영에 필요한 기능을 기준으로 학생용 서비스와 조교용 관리자 서비스를 새롭게 설계하고 개발합니다.

---

## 프로젝트 구조

```text
Frame-Science/
├── Backend/
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py
│   └── requirements.txt
├── Frontend/
└── README.md
```

Frontend는 학생용과 조교용 관리자를 별도의 프로젝트로 나누지 않고 하나의 React 프로젝트로 구성합니다.

```text
Frontend/
├── src/
│   ├── admin/
│   ├── app/
│   │   ├── queryClient.ts
│   │   └── router.tsx
│   ├── assets/
│   ├── common/
│   ├── services/
│   │   └── api.ts
│   ├── student/
│   ├── styles/
│   │   └── global.css
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── package-lock.json
├── tsconfig.json
├── vite.config.ts
└── eslint.config.js
```

### Frontend 디렉터리 구성

- `admin` : 조교용 관리자 화면 및 기능
- `student` : 학생용 화면 및 기능
- `common` : 학생용과 조교용에서 함께 사용하는 공통 코드
- `app` : Router, TanStack Query 등 애플리케이션 전체 설정
- `services` : Backend API 통신 관련 공통 설정
- `styles` : 전역 스타일
- `assets` : 이미지, 아이콘 등 정적 리소스

Backend는 FastAPI 애플리케이션의 최소 실행 구조부터 시작하며, 기능별 서비스 구조는 실제 도메인과 MSA 서비스 경계가 확정되는 과정에서 추가합니다.

```text
Backend/
├── app/
│   ├── __init__.py
│   └── main.py
└── requirements.txt
```

### Backend 디렉터리 구성

- `app` : FastAPI 애플리케이션 코드
- `app/__init__.py` : `app` 디렉터리를 Python 패키지로 사용하기 위한 파일
- `app/main.py` : FastAPI 애플리케이션 시작점
- `requirements.txt` : Backend 실행에 필요한 Python 패키지와 버전 관리

로컬 Python 가상환경은 `Backend/.venv`를 사용하며 Git에는 포함하지 않습니다.

---

## 기술 스택

### Frontend

- React
- TypeScript
- Vite
- React Router
- Axios
- TanStack Query
- CSS Modules

### Backend

- Python
- FastAPI
- Pydantic
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- psycopg
- Uvicorn

Python 패키지는 `venv + pip + requirements.txt` 방식으로 관리합니다.

### 공통 인프라

- JWT
- Redis
- Kafka
- Nginx
- AWS

AWS의 구체적인 인프라 구성은 추후 인프라 설계 단계에서 확정합니다.

---

## 시작하기

### 1. Repository Clone

```bash
git clone <repository-url>
cd Frame-Science
```

### 2. Frontend 실행

Frontend 디렉터리로 이동합니다.

```bash
cd Frontend
```

의존성을 설치합니다.

```bash
npm install
```

개발 서버를 실행합니다.

```bash
npm run dev
```

빌드를 확인합니다.

```bash
npm run build
```

Lint를 확인합니다.

```bash
npm run lint
```

Frontend 초기 세팅은 완료되었으며 개발 서버 실행, Build, Lint가 정상 동작하는 것을 확인했습니다.

### 3. Backend 실행

Repository 루트에서 Backend 디렉터리로 이동합니다.

```bash
cd Backend
```

Python 가상환경을 생성합니다.

```bash
python3 -m venv .venv
```

가상환경을 활성화합니다.

```bash
source .venv/bin/activate
```

`requirements.txt`에 정의된 Backend 패키지를 설치합니다.

```bash
python -m pip install -r requirements.txt
```

FastAPI 개발 서버를 실행합니다.

```bash
uvicorn app.main:app --reload
```

서버가 정상적으로 실행되면 다음 주소에서 Backend 응답을 확인할 수 있습니다.

```text
http://127.0.0.1:8000
```

FastAPI에서 자동으로 제공하는 API 문서는 다음 주소에서 확인할 수 있습니다.

```text
http://127.0.0.1:8000/docs
```

Backend 초기 세팅은 완료되었으며 FastAPI 서버 실행과 API 문서 접근이 정상 동작하는 것을 확인했습니다.

### Backend 패키지 추가

새로운 Python 패키지가 필요한 경우 가상환경이 활성화된 상태에서 설치합니다.

```bash
python -m pip install <package-name>
```

패키지를 추가하거나 버전을 변경한 뒤 현재 환경을 `requirements.txt`에 반영합니다.

```bash
python -m pip freeze > requirements.txt
```

---

## 개발 구조

학생용과 조교용 관리자는 동일한 Frontend 프로젝트를 사용하며 영역을 분리하여 개발합니다.

```text
src/
├── student/    # 학생용
├── admin/      # 조교용 관리자
└── common/     # 공통
```

학생용과 조교용에서 공통으로 사용하는 애플리케이션 설정과 API 통신 관련 코드는 다음 위치에서 관리합니다.

```text
src/
├── app/
├── services/
└── styles/
```

Backend는 현재 최소 FastAPI 실행 구조만 구성합니다.

```text
Backend/
└── app/
    ├── __init__.py
    └── main.py
```

MSA를 기준으로 개발하지만 화면 메뉴를 기준으로 서비스를 미리 분리하지 않습니다.

학생, 강의, 클리닉 등의 실제 기능을 설계하면서 각 도메인의 책임과 데이터 관계를 확인한 뒤 필요한 서비스 구조를 추가합니다.

기능 개발 전에 불필요한 폴더나 구조를 미리 만들지 않고, 실제 기능 구현 과정에서 필요한 구조만 추가합니다.

---

## 문서 관리

프로젝트의 세부 설계와 개발 기록은 Notion에서 관리합니다.

```text
프레임 과학
├── 공통
│   ├── 기술 설계
│   └── 프로젝트 세팅
│       ├── Frontend
│       └── Backend
│
├── 학생용
│   ├── 설계
│   └── 개발
│
└── 조교용 관리자
    ├── 설계
    └── 개발
```

README는 프로젝트에 처음 접근했을 때 필요한 프로젝트 소개, 전체 구조, 기술 스택, 실행 방법을 중심으로 관리합니다.

구체적인 기능 설계, 기술 선택 이유, 실제 구현 과정, 문제 발생 원인과 해결 과정은 Notion 문서를 기준으로 관리합니다.
