from typing import Optional
import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models.audit import AuditEvent
from app.models.user import AppUser, UserRole
from app.repo.department import DepartmentRepository
from app.repo.user import UserRepository
from app.schemas.user import (
    UserCreate,
    UserResetPasswordRequest,
    UserResponse,
    UserUpdate,
)
from app.security.policies import can_access_user_data
from app.service.audit import AuditService


class UserService:
    """Service xử lý vòng đời người dùng và quyền quản trị."""

    def __init__(
        self,
        user_repo: UserRepository,
        dept_repo: DepartmentRepository,
        audit_service: AuditService,
    ) -> None:
        self.user_repo = user_repo
        self.dept_repo = dept_repo
        self.audit_service = audit_service

    async def list_users(
        self,
        current_user: AppUser,
        skip: int = 0,
        limit: int = 50,
        role: Optional[UserRole] = None,
        department_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
    ) -> list[UserResponse]:
        """Xem danh sách người dùng. Chỉ dành cho quyền ADMIN."""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không đủ quyền truy cập",
            )

        users = await self.user_repo.list_users(
            skip=skip,
            limit=limit,
            department_id=department_id,
            role=role,
            is_active=is_active,
        )
        return [UserResponse.model_validate(u) for u in users]

    async def get_user_by_id(
        self,
        user_id: uuid.UUID,
        current_user: AppUser,
    ) -> UserResponse:
        """Lấy thông tin người dùng theo ID. Chỉ chính người dùng đó hoặc ADMIN mới có quyền truy cập."""
        if not can_access_user_data(current_user, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không đủ quyền truy cập",
            )

        target_user = await self.user_repo.get_by_id(user_id)
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy người dùng",
            )

        return UserResponse.model_validate(target_user)

    async def create_user(
        self,
        body: UserCreate,
        current_user: AppUser,
        request: Optional[Request] = None,
    ) -> UserResponse:
        """Tạo người dùng mới với vai trò chỉ định. Chỉ dành cho ADMIN."""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Yêu cầu quyền ADMIN",
            )

        normalized_email = body.email.lower().strip()

        existing = await self.user_repo.get_by_email(normalized_email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email này đã được đăng ký",
            )

        if (
            body.role in {UserRole.TECHNICIAN, UserRole.DEPT_MANAGER}
            and body.department_id is None
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phòng ban là bắt buộc đối với vai trò Kỹ thuật viên (TECHNICIAN) và Trưởng phòng (DEPT_MANAGER)",
            )

        if body.department_id is not None:
            dept = await self.dept_repo.get_by_id(body.department_id)
            if dept is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Không tìm thấy phòng ban",
                )

        new_user = AppUser(
            email=normalized_email,
            full_name=body.full_name.strip(),
            role=body.role,
            department_id=body.department_id,
            password_hash=hash_password(body.password),
            is_active=True,
        )
        await self.user_repo.create(new_user)
        try:
            await self.user_repo.flush()
            await self.audit_service.log_auth_event(
                event=AuditEvent.USER_ACTIVATED,
                user_id=new_user.id,
                email_attempted=new_user.email,
                request=request,
                commit=False,
            )
            await self.user_repo.commit()
        except IntegrityError:
            await self.user_repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email này đã được đăng ký",
            )

        await self.user_repo.refresh(new_user)
        return UserResponse.model_validate(new_user)

    async def update_user(
        self,
        user_id: uuid.UUID,
        body: UserUpdate,
        current_user: AppUser,
        request: Optional[Request] = None,
    ) -> UserResponse:
        """Cập nhật thông tin người dùng. Chỉ chính người dùng hoặc ADMIN mới có quyền."""
        if not can_access_user_data(current_user, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không đủ quyền truy cập",
            )

        target_user = await self.user_repo.get_by_id(user_id)
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy người dùng",
            )

        fields_set = body.model_fields_set

        # Nếu người dùng hiện tại không phải ADMIN, chỉ được phép sửa họ tên của mình
        if current_user.role != UserRole.ADMIN:
            if "role" in fields_set or "department_id" in fields_set or "is_active" in fields_set:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Người dùng chỉ có thể chỉnh sửa họ tên của mình",
                )

        # Ràng buộc 1: ADMIN không thể tự vô hiệu hóa tài khoản của chính mình
        if target_user.id == current_user.id and body.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin không thể tự vô hiệu hóa chính mình",
            )

        # Ràng buộc 2: Không cho phép vô hiệu hóa hoặc hạ quyền ADMIN đang hoạt động cuối cùng
        will_deactivate = body.is_active is False
        will_demote = body.role is not None and body.role != UserRole.ADMIN
        if (
            target_user.role == UserRole.ADMIN
            and target_user.is_active
            and (will_deactivate or will_demote)
        ):
            active_admin_count = await self.user_repo.count_other_active_admins(
                target_user.id
            )
            if active_admin_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Không thể vô hiệu hóa hoặc hạ quyền admin đang hoạt động cuối cùng",
                )

        # Ràng buộc 3: Yêu cầu phòng ban đối với vai trò TECHNICIAN / DEPT_MANAGER
        effective_role = body.role if body.role is not None else target_user.role
        effective_dept = (
            body.department_id
            if "department_id" in fields_set
            else target_user.department_id
        )
        if (
            effective_role in {UserRole.TECHNICIAN, UserRole.DEPT_MANAGER}
            and effective_dept is None
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phòng ban là bắt buộc đối với vai trò Kỹ thuật viên (TECHNICIAN) và Trưởng phòng (DEPT_MANAGER)",
            )

        # Kiểm tra sự tồn tại của phòng ban nếu có truyền department_id mới
        if "department_id" in fields_set and body.department_id is not None:
            dept = await self.dept_repo.get_by_id(body.department_id)
            if dept is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Không tìm thấy phòng ban",
                )

        events_to_log: list[AuditEvent] = []

        if body.full_name is not None:
            target_user.full_name = body.full_name.strip()

        if body.role is not None and body.role != target_user.role:
            target_user.role = body.role
            events_to_log.append(AuditEvent.ROLE_CHANGED)

        if "department_id" in fields_set:
            target_user.department_id = body.department_id

        if body.is_active is not None and body.is_active != target_user.is_active:
            target_user.is_active = body.is_active
            events_to_log.append(
                AuditEvent.USER_ACTIVATED
                if body.is_active
                else AuditEvent.USER_DEACTIVATED
            )

        for ev in events_to_log:
            await self.audit_service.log_auth_event(
                event=ev,
                user_id=target_user.id,
                email_attempted=target_user.email,
                request=request,
                commit=False,
            )

        await self.user_repo.commit()
        await self.user_repo.refresh(target_user)
        return UserResponse.model_validate(target_user)

    async def delete_user(
        self,
        user_id: uuid.UUID,
        current_user: AppUser,
        request: Optional[Request] = None,
    ) -> dict[str, str]:
        """Xóa tài khoản người dùng. Chỉ cho phép chính người dùng đó hoặc ADMIN."""
        if not can_access_user_data(current_user, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không đủ quyền truy cập",
            )

        target_user = await self.user_repo.get_by_id(user_id)
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy người dùng",
            )

        # Bảo vệ ADMIN đang hoạt động cuối cùng của hệ thống
        if target_user.role == UserRole.ADMIN and target_user.is_active:
            active_admin_count = await self.user_repo.count_other_active_admins(
                target_user.id
            )
            if active_admin_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Không thể xóa admin đang hoạt động cuối cùng",
                )

        target_email = target_user.email
        await self.user_repo.delete(target_user)
        await self.audit_service.log_auth_event(
            event=AuditEvent.USER_DEACTIVATED,
            user_id=None,
            email_attempted=target_email,
            request=request,
            commit=False,
        )
        await self.user_repo.commit()

        return {"message": "Xóa người dùng thành công"}

    async def reset_password(
        self,
        user_id: uuid.UUID,
        body: UserResetPasswordRequest,
        current_user: AppUser,
        request: Optional[Request] = None,
    ) -> dict[str, str]:
        """Đặt lại mật khẩu cho người dùng. Chỉ dành cho ADMIN."""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Yêu cầu quyền ADMIN",
            )

        target_user = await self.user_repo.get_by_id(user_id)
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy người dùng",
            )

        target_user.password_hash = hash_password(body.new_password)
        await self.audit_service.log_auth_event(
            event=AuditEvent.PASSWORD_CHANGED,
            user_id=target_user.id,
            email_attempted=target_user.email,
            request=request,
            commit=False,
        )
        await self.user_repo.commit()

        return {"message": "Đặt lại mật khẩu người dùng thành công"}
