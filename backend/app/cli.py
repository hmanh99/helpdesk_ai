import argparse
import asyncio
import os
from pathlib import Path
import sys

# Đảm bảo đường dẫn gốc backend có trong sys.path khi chạy trực tiếp bằng python app/cli.py
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.audit import AuditEvent
from app.models.user import AppUser, UserRole
from app.repo.audit import AuditRepository
from app.repo.user import UserRepository
from app.service.audit import AuditService


async def create_admin(email: str | None, password: str | None, full_name: str | None) -> int:
    """Tạo mới hoặc cập nhật tài khoản quản trị viên (ADMIN) hệ thống ban đầu."""
    admin_email = email or settings.ADMIN_EMAIL or os.getenv("ADMIN_EMAIL")
    admin_password = password or settings.ADMIN_PASSWORD or os.getenv("ADMIN_PASSWORD")
    admin_name = full_name or settings.ADMIN_FULL_NAME or os.getenv("ADMIN_FULL_NAME") or "System Administrator"

    if not admin_email:
        print(
            "Lỗi: Email admin phải được cung cấp qua --email hoặc biến môi trường ADMIN_EMAIL.",
            file=sys.stderr,
        )
        return 1

    if not admin_password or len(admin_password) < 8:
        print(
            "Lỗi: Mật khẩu admin phải có ít nhất 8 ký tự (qua --password hoặc ADMIN_PASSWORD).",
            file=sys.stderr,
        )
        return 1

    admin_email = admin_email.strip().lower()

    try:
        async with AsyncSessionLocal() as db:
            user_repo = UserRepository(db)
            audit_repo = AuditRepository(db)
            audit_service = AuditService(audit_repo)

            existing_user = await user_repo.get_by_email(admin_email)

            if existing_user is not None:
                was_inactive = not existing_user.is_active
                if existing_user.role == UserRole.ADMIN or str(existing_user.role) == "ADMIN":
                    print(
                        f"Tài khoản admin '{admin_email}' đã tồn tại (ID: {existing_user.id}). Đang cập nhật mật khẩu..."
                    )
                    existing_user.password_hash = hash_password(admin_password)
                    existing_user.is_active = True
                    await audit_service.log_auth_event(
                        event=AuditEvent.PASSWORD_CHANGED,
                        user_id=existing_user.id,
                        email_attempted=admin_email,
                        commit=False,
                    )
                    if was_inactive:
                        await audit_service.log_auth_event(
                            event=AuditEvent.USER_ACTIVATED,
                            user_id=existing_user.id,
                            email_attempted=admin_email,
                            commit=False,
                        )
                    await user_repo.commit()
                    print("Cập nhật mật khẩu admin thành công.")
                    return 0
                else:
                    current_role = (
                        existing_user.role.value
                        if hasattr(existing_user.role, "value")
                        else str(existing_user.role)
                    )
                    print(
                        f"Người dùng '{admin_email}' tồn tại với vai trò '{current_role}'. Đang nâng quyền lên ADMIN..."
                    )
                    existing_user.role = UserRole.ADMIN
                    existing_user.password_hash = hash_password(admin_password)
                    existing_user.is_active = True
                    await audit_service.log_auth_event(
                        event=AuditEvent.ROLE_CHANGED,
                        user_id=existing_user.id,
                        email_attempted=admin_email,
                        commit=False,
                    )
                    await audit_service.log_auth_event(
                        event=AuditEvent.PASSWORD_CHANGED,
                        user_id=existing_user.id,
                        email_attempted=admin_email,
                        commit=False,
                    )
                    if was_inactive:
                        await audit_service.log_auth_event(
                            event=AuditEvent.USER_ACTIVATED,
                            user_id=existing_user.id,
                            email_attempted=admin_email,
                            commit=False,
                        )
                    await user_repo.commit()
                    print(f"Đã nâng quyền người dùng '{admin_email}' lên ADMIN thành công.")
                    return 0

            # Tạo mới Admin
            new_admin = AppUser(
                email=admin_email,
                full_name=admin_name.strip(),
                role=UserRole.ADMIN,
                department_id=None,
                password_hash=hash_password(admin_password),
                is_active=True,
            )
            await user_repo.create(new_admin)
            await user_repo.flush()

            await audit_service.log_auth_event(
                event=AuditEvent.USER_ACTIVATED,
                user_id=new_admin.id,
                email_attempted=admin_email,
                commit=False,
            )
            await user_repo.commit()
            await user_repo.refresh(new_admin)

            role_display = (
                new_admin.role.value
                if hasattr(new_admin.role, "value")
                else str(new_admin.role)
            )
            print(
                f"Tạo người dùng Admin thành công:\n"
                f"  ID:      {new_admin.id}\n"
                f"  Email:   {new_admin.email}\n"
                f"  Họ tên:  {new_admin.full_name}\n"
                f"  Vai trò: {role_display}"
            )
            return 0
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Helpdesk AI CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    admin_parser = subparsers.add_parser(
        "create-admin", help="Tạo hoặc khởi tạo tài khoản quản trị viên (admin) ban đầu"
    )
    admin_parser.add_argument(
        "--email", help="Email của tài khoản admin (hoặc qua biến môi trường ADMIN_EMAIL)"
    )
    admin_parser.add_argument(
        "--password", help="Mật khẩu của tài khoản admin (hoặc qua biến môi trường ADMIN_PASSWORD)"
    )
    admin_parser.add_argument(
        "--full-name", help="Họ tên của tài khoản admin (mặc định: System Administrator)"
    )

    args = parser.parse_args()

    if args.command == "create-admin":
        code = asyncio.run(create_admin(args.email, args.password, args.full_name))
        sys.exit(code)


if __name__ == "__main__":
    main()
