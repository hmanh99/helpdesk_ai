import uuid

from httpx import AsyncClient
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.audit import AuditEvent, AuthAuditLog
from app.models.department import Department
from app.models.user import AppUser, UserRole
from tests.conftest import auth_headers_for


@pytest.mark.asyncio
async def test_admin_create_user_success(
    client: AsyncClient, admin_user: AppUser, dept_a: Department
) -> None:
    headers = auth_headers_for(admin_user)

    response = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "new.tech@example.com",
            "full_name": "New Technician",
            "role": "TECHNICIAN",
            "department_id": str(dept_a.id),
            "password": "Password123!",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new.tech@example.com"
    assert data["role"] == "TECHNICIAN"
    assert data["department_id"] == str(dept_a.id)


@pytest.mark.asyncio
async def test_create_user_role_requires_department(
    client: AsyncClient, admin_user: AppUser
) -> None:
    headers = auth_headers_for(admin_user)

    # TECHNICIAN without department_id -> 400
    res1 = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "tech.nodept@example.com",
            "full_name": "No Dept Tech",
            "role": "TECHNICIAN",
            "password": "Password123!",
        },
    )
    assert res1.status_code == 400

    # DEPT_MANAGER without department_id -> 400
    res2 = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "mgr.nodept@example.com",
            "full_name": "No Dept Mgr",
            "role": "DEPT_MANAGER",
            "password": "Password123!",
        },
    )
    assert res2.status_code == 400

    # STUDENT without department_id -> allowed 201
    res3 = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "student.nodept@example.com",
            "full_name": "No Dept Student",
            "role": "STUDENT",
            "password": "Password123!",
        },
    )
    assert res3.status_code == 201


@pytest.mark.asyncio
async def test_create_user_duplicate_email(
    client: AsyncClient, admin_user: AppUser
) -> None:
    headers = auth_headers_for(admin_user)

    response = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": admin_user.email,
            "full_name": "Duplicate Admin",
            "role": "ADMIN",
            "password": "Password123!",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_self_deactivation_guard(
    client: AsyncClient, admin_user: AppUser
) -> None:
    headers = auth_headers_for(admin_user)

    response = await client.patch(
        f"/api/v1/users/{admin_user.id}",
        headers=headers,
        json={"is_active": False},
    )
    assert response.status_code == 400
    assert "không thể tự vô hiệu hóa" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_last_admin_protection(
    client: AsyncClient, admin_user: AppUser, student_user: AppUser, db: AsyncSession
) -> None:
    headers = auth_headers_for(admin_user)

    # 1. Only admin_user is active admin. Attempting to demote admin_user should fail
    # (Since admin cannot deactivate themselves, let's create a second admin, deactivate the first, then try to deactivate the second)
    admin_2 = AppUser(
        email="admin2@example.com",
        full_name="Admin Two",
        role=UserRole.ADMIN,
        password_hash=hash_password("Password123!"),
        is_active=True,
    )
    db.add(admin_2)
    await db.commit()
    await db.refresh(admin_2)

    # admin_user deactivates admin_2 -> Allowed because admin_user is still active admin
    res_deact_2 = await client.patch(
        f"/api/v1/users/{admin_2.id}",
        headers=headers,
        json={"is_active": False},
    )
    assert res_deact_2.status_code == 200

    # Now admin_2 logs in? admin_2 is inactive. admin_user is the ONLY active admin left.
    # Reactivate admin_2
    res_react_2 = await client.patch(
        f"/api/v1/users/{admin_2.id}",
        headers=headers,
        json={"is_active": True},
    )
    assert res_react_2.status_code == 200

    # Now admin_2 acts as the current user, tries to demote admin_user
    headers_2 = auth_headers_for(admin_2)
    res_demote_1 = await client.patch(
        f"/api/v1/users/{admin_user.id}",
        headers=headers_2,
        json={"role": "STUDENT"},
    )
    assert res_demote_1.status_code == 200

    # Now admin_2 is the LAST active admin!
    # Try to demote admin_2:
    res_demote_last = await client.patch(
        f"/api/v1/users/{admin_2.id}",
        headers=headers_2,
        json={"role": "STUDENT"},
    )
    assert res_demote_last.status_code == 400
    assert "admin đang hoạt động cuối cùng" in res_demote_last.json()["detail"].lower()


@pytest.mark.asyncio
async def test_user_self_access_and_isolation(
    client: AsyncClient,
    student_user: AppUser,
    tech_user_a: AppUser,
    dept_manager_a: AppUser,
    dept_a: Department,
    dept_b: Department,
) -> None:
    headers_student = auth_headers_for(student_user)
    headers_tech = auth_headers_for(tech_user_a)
    headers_manager = auth_headers_for(dept_manager_a)

    # 1. Non-admin users cannot list all users
    res_list_student = await client.get("/api/v1/users", headers=headers_student)
    assert res_list_student.status_code == 403
    res_list_mgr = await client.get("/api/v1/users", headers=headers_manager)
    assert res_list_mgr.status_code == 403

    # 2. Users can view their own profile by ID
    res_self = await client.get(f"/api/v1/users/{student_user.id}", headers=headers_student)
    assert res_self.status_code == 200
    assert res_self.json()["email"] == student_user.email

    # 3. Users cannot view other users by ID
    res_other = await client.get(f"/api/v1/users/{tech_user_a.id}", headers=headers_student)
    assert res_other.status_code == 403

    # 4. Department managers cannot view user by ID even in own department (only self or admin)
    res_mgr_view_tech = await client.get(f"/api/v1/users/{tech_user_a.id}", headers=headers_manager)
    assert res_mgr_view_tech.status_code == 403

    # 5. Department manager can view members via department members endpoint
    res_dept_members_a = await client.get(
        f"/api/v1/departments/{dept_a.id}/members",
        headers=headers_manager,
    )
    assert res_dept_members_a.status_code == 200
    members = res_dept_members_a.json()
    member_emails = [m["email"] for m in members]
    assert dept_manager_a.email in member_emails
    assert tech_user_a.email in member_emails

    # 6. Department manager viewing other dept members -> 403
    res_dept_members_b = await client.get(
        f"/api/v1/departments/{dept_b.id}/members",
        headers=headers_manager,
    )
    assert res_dept_members_b.status_code == 403

    # 7. User updating their own full name -> 200
    res_update_self = await client.patch(
        f"/api/v1/users/{student_user.id}",
        headers=headers_student,
        json={"full_name": "Updated Self Name"},
    )
    assert res_update_self.status_code == 200
    assert res_update_self.json()["full_name"] == "Updated Self Name"

    # 8. User attempting to escalate role on self -> 403
    res_escalate = await client.patch(
        f"/api/v1/users/{student_user.id}",
        headers=headers_student,
        json={"role": "ADMIN"},
    )
    assert res_escalate.status_code == 403

    # 9. User attempting to update another user -> 403
    res_update_other = await client.patch(
        f"/api/v1/users/{tech_user_a.id}",
        headers=headers_student,
        json={"full_name": "Hacked Name"},
    )
    assert res_update_other.status_code == 403


@pytest.mark.asyncio
async def test_user_delete_endpoints(
    client: AsyncClient,
    admin_user: AppUser,
    student_user: AppUser,
    tech_user_a: AppUser,
    db: AsyncSession,
) -> None:
    headers_student = auth_headers_for(student_user)
    headers_admin = auth_headers_for(admin_user)

    # 1. Student attempts to delete another user (tech_user_a) -> 403
    res_del_forbidden = await client.delete(
        f"/api/v1/users/delete/{tech_user_a.id}",
        headers=headers_student,
    )
    assert res_del_forbidden.status_code == 403

    # 2. Student deletes themselves -> 200
    res_del_self = await client.delete(
        f"/api/v1/users/delete/{student_user.id}",
        headers=headers_student,
    )
    assert res_del_self.status_code == 200
    assert res_del_self.json()["message"] == "Xóa người dùng thành công"

    # Deleted student can no longer login
    res_login = await client.post(
        "/api/v1/auth/login",
        json={"email": student_user.email, "password": "Password123!"},
    )
    assert res_login.status_code == 401

    # 3. Admin deletes tech_user_a -> 200
    res_admin_del = await client.delete(
        f"/api/v1/users/delete/{tech_user_a.id}",
        headers=headers_admin,
    )
    assert res_admin_del.status_code == 200

    # 4. Cannot delete last active admin
    res_last_admin = await client.delete(
        f"/api/v1/users/delete/{admin_user.id}",
        headers=headers_admin,
    )
    assert res_last_admin.status_code == 400
    assert "admin đang hoạt động cuối cùng" in res_last_admin.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_reset_password(
    client: AsyncClient,
    admin_user: AppUser,
    student_user: AppUser,
    db: AsyncSession,
) -> None:
    headers = auth_headers_for(admin_user)

    response = await client.post(
        f"/api/v1/users/{student_user.id}/reset-password",
        headers=headers,
        json={"new_password": "NewResetPassword123!"},
    )
    assert response.status_code == 200

    # Target user can now login with new password
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": student_user.email, "password": "NewResetPassword123!"},
    )
    assert login_res.status_code == 200

    # Verify audit log
    audit_res = await db.execute(
        select(AuthAuditLog).where(
            AuthAuditLog.user_id == student_user.id,
            AuthAuditLog.event == AuditEvent.PASSWORD_CHANGED.value,
        )
    )
    assert audit_res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_patch_user_department_null_handling(
    client: AsyncClient,
    admin_user: AppUser,
    tech_user_a: AppUser,
) -> None:
    headers = auth_headers_for(admin_user)

    # 1. Attempting to explicitly set department_id=null on a TECHNICIAN must fail with 400
    res_fail = await client.patch(
        f"/api/v1/users/{tech_user_a.id}",
        headers=headers,
        json={"department_id": None},
    )
    assert res_fail.status_code == 400

    # 2. Changing role to STAFF while explicitly clearing department_id=null succeeds
    res_ok = await client.patch(
        f"/api/v1/users/{tech_user_a.id}",
        headers=headers,
        json={"role": "STAFF", "department_id": None},
    )
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["role"] == "STAFF"
    assert data["department_id"] is None

