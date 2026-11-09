import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.department import Department
from app.models.user import AppUser, UserRole
from scripts.seed_data import DEFAULT_SEED_PASSWORD, seed_users


@pytest.mark.asyncio
async def test_seed_users_creates_all_roles_for_departments(
    db: AsyncSession,
    dept_a: Department,
    dept_b: Department,
) -> None:
    # 1. Chạy seed users
    users = await seed_users(db, password="CustomTestPassword123!")
    assert len(users) >= 20

    # 2. Kiểm tra tính hợp lệ của mật khẩu
    for u in users:
        assert verify_password("CustomTestPassword123!", u.password_hash) is True
        assert u.is_active is True

    # 3. Kiểm tra các vai trò cốt lõi
    roles = {u.role for u in users}
    assert UserRole.ADMIN in roles
    assert UserRole.DEPT_MANAGER in roles
    assert UserRole.TECHNICIAN in roles
    assert UserRole.STAFF in roles
    assert UserRole.STUDENT in roles

    # 4. Kiểm tra từng phòng ban trong hệ thống đều có đầy đủ 4 role chuyên trách
    depts = (await db.execute(select(Department))).scalars().all()
    for dept in depts:
        dept_users = (
            await db.execute(
                select(AppUser).where(AppUser.department_id == dept.id)
            )
        ).scalars().all()

        dept_roles = {u.role for u in dept_users}
        assert UserRole.DEPT_MANAGER in dept_roles, f"Phòng {dept.name} thiếu DEPT_MANAGER"
        assert UserRole.TECHNICIAN in dept_roles, f"Phòng {dept.name} thiếu TECHNICIAN"
        assert UserRole.STAFF in dept_roles, f"Phòng {dept.name} thiếu STAFF"
        assert UserRole.STUDENT in dept_roles, f"Phòng {dept.name} thiếu STUDENT"

    # 5. Kiểm tra tính Idempotent: chạy lại lần 2 không gây lỗi và bảo toàn dữ liệu
    users_round_2 = await seed_users(db, password="CustomTestPassword123!")
    assert len(users_round_2) >= len(users)

