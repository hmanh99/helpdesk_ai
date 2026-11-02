# Helpdesk AI

Hệ thống **Helpdesk AI** full-stack sử dụng **FastAPI** (Backend), **PostgreSQL + pgvector** (Cơ sở dữ liệu & Vector Search), **React + Vite** (Frontend) và **Docker Compose**.

---

## Cấu trúc thư mục

```text
helpdesk_ai/
├── docker-compose.yml          # Khởi chạy đồng bộ PostgreSQL (pgvector), Backend và Frontend
├── .env.example                # File mẫu cấu hình biến môi trường
├── backend/
│   ├── Dockerfile              # Docker image cho FastAPI backend
│   ├── requirements.txt        # Danh sách thư viện Python
│   ├── pyproject.toml          # Cấu hình project & pytest
│   ├── alembic.ini             # Cấu hình Alembic migration
│   ├── alembic/                # Môi trường migration bất đồng bộ (Async SQLAlchemy)
│   ├── scripts/
│   │   └── init-db.sql         # Tự động kích hoạt extension pgvector & uuid-ossp
│   ├── app/
│   │   ├── main.py             # Khởi tạo FastAPI app, CORS, lifespan
│   │   ├── core/
│   │   │   └── config.py       # Quản lý cấu hình với Pydantic v2 Settings
│   │   ├── db/
│   │   │   ├── base.py         # DeclarativeBase & TimestampMixin
│   │   │   └── session.py      # AsyncEngine, AsyncSessionLocal, dependency get_db
│   │   ├── models/             # Các bảng dữ liệu SQLAlchemy 2.0 ORM
│   │   ├── schemas/            # Các schema dữ liệu Pydantic v2 (request/response)
│   │   └── api/
│   │       ├── deps.py         # Dependency dùng chung (SessionDep)
│   │       └── v1/
│   │           ├── router.py   # Gom nhóm các route API v1
│   │           └── endpoints/
│   │               └── health.py # API kiểm tra trạng thái hệ thống & database
│   └── tests/                  # Bộ kiểm thử tự động với Pytest
└── frontend/
    ├── Dockerfile              # Multi-stage Dockerfile (dev với Vite HMR & production với Nginx)
    ├── vite.config.js          # Cấu hình Vite server & hot-reload trong Docker
    ├── package.json            # Dependencies cho React 19 + Vite 8
    └── src/                    # Mã nguồn giao diện người dùng
```

---

## Hướng dẫn cài đặt và chạy dự án

### Cách 1: Chạy toàn bộ hệ thống bằng Docker Compose (Khuyên dùng)

1. Kiểm tra hoặc tạo file `.env` ở thư mục gốc từ file mẫu (nếu chưa có):
   ```powershell
   Copy-Item .env.example .env
   ```

2. Khởi chạy cả 3 dịch vụ (`db`, `backend`, `frontend`):
   ```powershell
   docker compose up --build
   ```

3. Truy cập các dịch vụ:
   - **Frontend (React + Vite)**: http://localhost:5173
   - **Backend API Root**: http://localhost:8000
   - **Tài liệu API (Swagger UI)**: http://localhost:8000/docs
   - **Kiểm tra trạng thái (Health Check)**: http://localhost:8000/api/v1/health
   - **PostgreSQL (`pgvector`)**: `localhost:5432`

4. Xem log hoặc dừng các container:
   ```powershell
   # Xem log trực tiếp
   docker compose logs -f

   # Dừng các container
   docker compose down
   ```

---

### Cách 2: Chạy môi trường phát triển trực tiếp trên máy (Local Development)

#### 1. Khởi chạy Database PostgreSQL bằng Docker
```powershell
docker compose up -d db
```

#### 2. Chạy Backend (FastAPI) với `.venv`
```powershell
cd backend
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

#### 3. Chạy Frontend (React + Vite)
```powershell
cd frontend
npm install
npm run dev
```

---

## Quản lý Database Migration (Alembic)

Khi thêm hoặc chỉnh sửa các model trong `backend/app/models/` (nhớ import model vào `backend/app/models/__init__.py`):

```powershell
cd backend

# Tạo file migration mới tự động từ model
.\.venv\Scripts\alembic revision --autogenerate -m "Mo ta thay doi"

# Áp dụng migration lên cơ sở dữ liệu
.\.venv\Scripts\alembic upgrade head

# Hoàn tác 1 bước migration (nếu cần)
.\.venv\Scripts\alembic downgrade -1
```

---

## Chạy kiểm thử (Testing)

### Kiểm thử Backend (Pytest)
```powershell
cd backend
.\.venv\Scripts\pytest -v
```

### Kiểm tra mã nguồn Frontend (Oxlint)
```powershell
cd frontend
npm run dev
```
