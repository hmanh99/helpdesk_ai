from dataclasses import dataclass
from typing import Optional
import uuid

from httpx import AsyncClient
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.department import Department
from app.models.user import AppUser, UserRole
from app.security import policies
from tests.conftest import auth_headers_for


@dataclass
class MockTicket:
    id: uuid.UUID
    requester_id: uuid.UUID
    assignee_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None


@dataclass
class MockAction:
    department_id: uuid.UUID


# ---------------------------------------------------------------------------
# 1. Permission Matrix Unit Tests (Parameterized over all roles and actions)
# ---------------------------------------------------------------------------

POLICY_MATRIX = [
    # (action_name, STUDENT, STAFF, TECHNICIAN, DEPT_MANAGER, ADMIN)
    ("create_ticket", True, True, True, True, True),
    ("accept_ticket", False, False, True, True, True),
    ("reassign_ticket", False, False, False, True, True),
    ("approve_agent_action", False, False, False, True, True),
    ("manage_categories", False, False, False, False, True),
    ("manage_knowledge", False, False, False, False, True),
    ("manage_users", False, False, False, False, True),
    ("view_internal_comments", False, False, True, True, True),
]


@pytest.mark.parametrize(
    "action_name,student_exp,staff_exp,tech_exp,mgr_exp,admin_exp",
    POLICY_MATRIX,
)
def test_policy_permission_matrix(
    action_name: str,
    student_exp: bool,
    staff_exp: bool,
    tech_exp: bool,
    mgr_exp: bool,
    admin_exp: bool,
) -> None:
    dept_id = uuid.uuid4()
    users = {
        UserRole.STUDENT: AppUser(
            id=uuid.uuid4(), email="s@test.com", full_name="Student", role=UserRole.STUDENT, is_active=True
        ),
        UserRole.STAFF: AppUser(
            id=uuid.uuid4(), email="st@test.com", full_name="Staff", role=UserRole.STAFF, is_active=True
        ),
        UserRole.TECHNICIAN: AppUser(
            id=uuid.uuid4(), email="t@test.com", full_name="Tech", role=UserRole.TECHNICIAN, department_id=dept_id, is_active=True
        ),
        UserRole.DEPT_MANAGER: AppUser(
            id=uuid.uuid4(), email="m@test.com", full_name="Manager", role=UserRole.DEPT_MANAGER, department_id=dept_id, is_active=True
        ),
        UserRole.ADMIN: AppUser(
            id=uuid.uuid4(), email="a@test.com", full_name="Admin", role=UserRole.ADMIN, is_active=True
        ),
    }

    expected = {
        UserRole.STUDENT: student_exp,
        UserRole.STAFF: staff_exp,
        UserRole.TECHNICIAN: tech_exp,
        UserRole.DEPT_MANAGER: mgr_exp,
        UserRole.ADMIN: admin_exp,
    }

    ticket_in_dept = MockTicket(id=uuid.uuid4(), requester_id=uuid.uuid4(), department_id=dept_id)
    action_in_dept = MockAction(department_id=dept_id)

    for role, user in users.items():
        exp = expected[role]
        if action_name == "create_ticket":
            assert policies.can_create_ticket(user) is exp
        elif action_name == "accept_ticket":
            # For tech, ticket in own dept is allowed
            assert policies.can_accept_or_update_ticket(user, ticket_in_dept) is exp
        elif action_name == "reassign_ticket":
            assert policies.can_reassign_ticket(user, ticket_in_dept) is exp
        elif action_name == "approve_agent_action":
            assert policies.can_approve_agent_action(user, action_in_dept) is exp
        elif action_name == "manage_categories":
            assert policies.can_manage_categories(user) is exp
        elif action_name == "manage_knowledge":
            assert policies.can_manage_knowledge(user) is exp
        elif action_name == "manage_users":
            assert policies.can_manage_users(user) is exp
        elif action_name == "view_internal_comments":
            assert policies.can_view_internal_comments(user, ticket_in_dept) is exp


# ---------------------------------------------------------------------------
# 2. Endpoint Authorization Matrix Tests (Parameterized across all roles)
# ---------------------------------------------------------------------------

ROLES_ENDPOINT_ACCESS = [
    # (role, exp_me, exp_get_users, exp_get_user_by_id, exp_create_user, exp_patch_user, exp_reset_pwd, exp_dept_members)
    (UserRole.STUDENT, 200, 403, 403, 403, 403, 403, 403),
    (UserRole.STAFF, 200, 403, 403, 403, 403, 403, 403),
    (UserRole.TECHNICIAN, 200, 403, 403, 403, 403, 403, 403),
    (UserRole.DEPT_MANAGER, 200, 403, 403, 403, 403, 403, 200),
    (UserRole.ADMIN, 200, 200, 200, 201, 200, 200, 200),
]


@pytest.mark.parametrize(
    "role,exp_me,exp_get_users,exp_get_user_by_id,exp_create_user,exp_patch_user,exp_reset_pwd,exp_dept_members",
    ROLES_ENDPOINT_ACCESS,
)
@pytest.mark.asyncio
async def test_endpoint_role_permissions_matrix(
    client: AsyncClient,
    db: AsyncSession,
    dept_a: Department,
    role: UserRole,
    exp_me: int,
    exp_get_users: int,
    exp_get_user_by_id: int,
    exp_create_user: int,
    exp_patch_user: int,
    exp_reset_pwd: int,
    exp_dept_members: int,
) -> None:
    # Setup test user for this role
    user = AppUser(
        email=f"user.{role.value.lower()}@example.com",
        full_name=f"Role {role.value}",
        role=role,
        department_id=dept_a.id if role in {UserRole.TECHNICIAN, UserRole.DEPT_MANAGER} else None,
        password_hash=hash_password("Password123!"),
        is_active=True,
    )
    # Target user in dept_a for get_by_id, patch, and reset-password
    target = AppUser(
        email=f"target.{role.value.lower()}@example.com",
        full_name="Target User",
        role=UserRole.STUDENT,
        department_id=dept_a.id,
        password_hash=hash_password("Password123!"),
        is_active=True,
    )
    db.add_all([user, target])
    await db.commit()
    await db.refresh(user)
    await db.refresh(target)

    headers = auth_headers_for(user)

    # 1. GET /api/v1/auth/me
    res_me = await client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == exp_me

    # 2. GET /api/v1/users
    res_get_users = await client.get("/api/v1/users", headers=headers)
    assert res_get_users.status_code == exp_get_users, f"GET /users for {role} expected {exp_get_users}, got {res_get_users.status_code}"

    # 3. GET /api/v1/users/{target.id}
    res_get_by_id = await client.get(f"/api/v1/users/{target.id}", headers=headers)
    assert res_get_by_id.status_code == exp_get_user_by_id, f"GET /users/{{id}} for {role} expected {exp_get_user_by_id}, got {res_get_by_id.status_code}"

    # 4. POST /api/v1/users
    res_create = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": f"created.by.{role.value.lower()}@example.com",
            "full_name": "Created User",
            "role": "STUDENT",
            "password": "Password123!",
        },
    )
    assert res_create.status_code == exp_create_user, f"POST /users for {role} expected {exp_create_user}, got {res_create.status_code}"

    # 5. PATCH /api/v1/users/{target.id}
    res_patch = await client.patch(
        f"/api/v1/users/{target.id}",
        headers=headers,
        json={"full_name": "Updated Name"},
    )
    assert res_patch.status_code == exp_patch_user, f"PATCH /users/{{id}} for {role} expected {exp_patch_user}, got {res_patch.status_code}"

    # 6. POST /api/v1/users/{target.id}/reset-password
    res_reset = await client.post(
        f"/api/v1/users/{target.id}/reset-password",
        headers=headers,
        json={"new_password": "NewResetPassword123!"},
    )
    assert res_reset.status_code == exp_reset_pwd, f"POST /users/{{id}}/reset-password for {role} expected {exp_reset_pwd}, got {res_reset.status_code}"

    # 7. GET /api/v1/departments/{dept_a.id}/members
    res_members = await client.get(
        f"/api/v1/departments/{dept_a.id}/members",
        headers=headers,
    )
    assert res_members.status_code == exp_dept_members, f"GET /departments/{{id}}/members for {role} expected {exp_dept_members}, got {res_members.status_code}"

