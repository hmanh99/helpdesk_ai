from collections.abc import AsyncGenerator
import uuid

from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app
from app.models.department import Department
from app.models.user import AppUser, UserRole

# Use NullPool for tests so asyncpg connections are never reused across closed event loops
test_engine = create_async_engine(
    settings.async_database_url,
    poolclass=NullPool,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for test operations."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def clean_db() -> AsyncGenerator[None, None]:
    """Clean all tables before each test to guarantee complete test isolation."""
    async with TestSessionLocal() as session:
        await session.execute(
            text("TRUNCATE TABLE auth_audit_log, app_user, department RESTART IDENTITY CASCADE;")
        )
        await session.commit()
    yield


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Test HTTP client with overridden get_db dependency."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def dept_a(db: AsyncSession) -> Department:
    dept = Department(name="IT Support", description="IT department")
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


@pytest_asyncio.fixture
async def dept_b(db: AsyncSession) -> Department:
    dept = Department(name="HR", description="Human Resources")
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> AppUser:
    user = AppUser(
        email="admin@example.com",
        full_name="Admin User",
        role=UserRole.ADMIN,
        password_hash=hash_password("Password123!"),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def dept_manager_a(db: AsyncSession, dept_a: Department) -> AppUser:
    user = AppUser(
        email="manager.a@example.com",
        full_name="Manager A",
        role=UserRole.DEPT_MANAGER,
        department_id=dept_a.id,
        password_hash=hash_password("Password123!"),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def dept_manager_b(db: AsyncSession, dept_b: Department) -> AppUser:
    user = AppUser(
        email="manager.b@example.com",
        full_name="Manager B",
        role=UserRole.DEPT_MANAGER,
        department_id=dept_b.id,
        password_hash=hash_password("Password123!"),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def tech_user_a(db: AsyncSession, dept_a: Department) -> AppUser:
    user = AppUser(
        email="tech.a@example.com",
        full_name="Tech A",
        role=UserRole.TECHNICIAN,
        department_id=dept_a.id,
        password_hash=hash_password("Password123!"),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def staff_user(db: AsyncSession) -> AppUser:
    user = AppUser(
        email="staff@example.com",
        full_name="Staff User",
        role=UserRole.STAFF,
        password_hash=hash_password("Password123!"),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def student_user(db: AsyncSession) -> AppUser:
    user = AppUser(
        email="student@example.com",
        full_name="Student User",
        role=UserRole.STUDENT,
        password_hash=hash_password("Password123!"),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def auth_headers_for(user: AppUser) -> dict[str, str]:
    token = create_access_token(subject=user.id, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}
