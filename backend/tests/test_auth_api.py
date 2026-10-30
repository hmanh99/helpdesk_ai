from datetime import timedelta
import uuid

from httpx import AsyncClient
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.audit import AuditEvent, AuthAuditLog
from app.models.user import AppUser, UserRole
from tests.conftest import auth_headers_for


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user: AppUser, db: AsyncSession) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Password123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@example.com"
    assert data["user"]["role"] == "ADMIN"

    # Verify last_login_at is updated
    await db.refresh(admin_user)
    assert admin_user.last_login_at is not None

    # Verify audit log recorded LOGIN_SUCCESS
    audit_res = await db.execute(
        select(AuthAuditLog).where(
            AuthAuditLog.user_id == admin_user.id,
            AuthAuditLog.event == AuditEvent.LOGIN_SUCCESS.value,
        )
    )
    audit_entry = audit_res.scalar_one_or_none()
    assert audit_entry is not None
    assert audit_entry.email_attempted == admin_user.email


@pytest.mark.asyncio
async def test_login_case_insensitive(client: AsyncClient, admin_user: AppUser) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "ADMIN@EXAMPLE.COM", "password": "Password123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "admin@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user: AppUser, db: AsyncSession) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Email hoặc mật khẩu không chính xác"

    # Verify audit log recorded LOGIN_FAILED
    audit_res = await db.execute(
        select(AuthAuditLog).where(
            AuthAuditLog.user_id == admin_user.id,
            AuthAuditLog.event == AuditEvent.LOGIN_FAILED.value,
        )
    )
    audit_entry = audit_res.scalar_one_or_none()
    assert audit_entry is not None


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient, db: AsyncSession) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "Password123!"},
    )
    assert response.status_code == 401
    data = response.json()
    # Must return identical generic message
    assert data["detail"] == "Email hoặc mật khẩu không chính xác"

    # Verify audit log recorded LOGIN_FAILED with email_attempted
    audit_res = await db.execute(
        select(AuthAuditLog).where(
            AuthAuditLog.email_attempted == "nonexistent@example.com",
            AuthAuditLog.event == AuditEvent.LOGIN_FAILED.value,
        )
    )
    audit_entry = audit_res.scalar_one_or_none()
    assert audit_entry is not None
    assert audit_entry.user_id is None


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, student_user: AppUser, db: AsyncSession) -> None:
    student_user.is_active = False
    await db.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": student_user.email, "password": "Password123!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email hoặc mật khẩu không chính xác"

    audit_res = await db.execute(
        select(AuthAuditLog).where(
            AuthAuditLog.user_id == student_user.id,
            AuthAuditLog.event == AuditEvent.LOGIN_FAILED.value,
        )
    )
    assert audit_res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient, admin_user: AppUser) -> None:
    headers = auth_headers_for(admin_user)
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(admin_user.id)
    assert data["email"] == admin_user.email
    assert data["role"] == "ADMIN"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_deactivated_user_revoked_on_next_request(
    client: AsyncClient, student_user: AppUser, db: AsyncSession
) -> None:
    headers = auth_headers_for(student_user)

    # Initial request works
    res1 = await client.get("/api/v1/auth/me", headers=headers)
    assert res1.status_code == 200

    # User is deactivated in DB
    student_user.is_active = False
    await db.commit()

    # Next request with the same token must fail with 401
    res2 = await client.get("/api/v1/auth/me", headers=headers)
    assert res2.status_code == 401
    assert "vô hiệu hóa" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_expired_token_returns_401(client: AsyncClient, student_user: AppUser) -> None:
    expired_token = create_access_token(
        subject=student_user.id,
        role=student_user.role.value,
        expires_delta=timedelta(seconds=-5),
    )
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_tampered_token_returns_401(client: AsyncClient, student_user: AppUser) -> None:
    valid_token = create_access_token(subject=student_user.id, role=student_user.role.value)
    parts = valid_token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.bad_sig_{parts[2][8:]}"

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_role_change_takes_effect_immediately(
    client: AsyncClient, student_user: AppUser, db: AsyncSession
) -> None:
    # Token was issued when user had STUDENT role
    headers = auth_headers_for(student_user)

    # STUDENT cannot access /users
    res1 = await client.get("/api/v1/users", headers=headers)
    assert res1.status_code == 403

    # Promote user to ADMIN directly in DB
    student_user.role = UserRole.ADMIN
    await db.commit()

    # Next request with the SAME token should now succeed because role is loaded from DB
    res2 = await client.get("/api/v1/users", headers=headers)
    assert res2.status_code == 200


@pytest.mark.asyncio
async def test_change_password_flow(
    client: AsyncClient, student_user: AppUser, db: AsyncSession
) -> None:
    headers = auth_headers_for(student_user)

    # 1. Wrong current password -> 400
    res_fail = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "WrongPassword!", "new_password": "BrandNewPassword123!"},
    )
    assert res_fail.status_code == 400

    # 2. Correct current password -> 200
    res_ok = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "Password123!", "new_password": "BrandNewPassword123!"},
    )
    assert res_ok.status_code == 200

    # 3. Old password no longer works for login
    res_login_old = await client.post(
        "/api/v1/auth/login",
        json={"email": student_user.email, "password": "Password123!"},
    )
    assert res_login_old.status_code == 401

    # 4. New password works for login
    res_login_new = await client.post(
        "/api/v1/auth/login",
        json={"email": student_user.email, "password": "BrandNewPassword123!"},
    )
    assert res_login_new.status_code == 200

    # 5. Audit log check
    audit_res = await db.execute(
        select(AuthAuditLog).where(
            AuthAuditLog.user_id == student_user.id,
            AuthAuditLog.event == AuditEvent.PASSWORD_CHANGED.value,
        )
    )
    assert audit_res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_register_flow(client: AsyncClient, db: AsyncSession) -> None:
    # 1. Register a new user
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newbie@example.com",
            "full_name": "New User",
            "password": "Password123!",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "newbie@example.com"
    assert data["full_name"] == "New User"
    assert data["role"] == "STUDENT"
    assert data["is_active"] is True

    # 2. Register duplicate email fails with 409
    res_dup = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "NEWBIE@EXAMPLE.COM",
            "full_name": "Another User",
            "password": "Password123!",
        },
    )
    assert res_dup.status_code == 409

    # 3. Log in with newly registered account
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "newbie@example.com", "password": "Password123!"},
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()


