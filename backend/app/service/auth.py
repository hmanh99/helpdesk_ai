from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, Request, status

from app.core.security import (
    create_access_token,
    hash_password,
    verify_dummy_password,
    verify_password,
)
from app.models.audit import AuditEvent
from app.models.user import AppUser, UserRole
from app.repo.user import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.service.audit import AuditService


class AuthService:
    """Service xử lý quy trình xác thực người dùng."""

    def __init__(self, user_repo: UserRepository, audit_service: AuditService) -> None:
        self.user_repo = user_repo
        self.audit_service = audit_service

    async def register(
        self,
        body: RegisterRequest,
        request: Optional[Request] = None,
    ) -> UserResponse:
        """Đăng ký tài khoản người dùng mới với vai trò mặc định là STUDENT."""
        normalized_email = body.email.strip().lower()

        existing = await self.user_repo.get_by_email(normalized_email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email này đã được đăng ký",
            )

        new_user = AppUser(
            email=normalized_email,
            full_name=body.full_name.strip(),
            role=UserRole.STUDENT,
            department_id=None,
            password_hash=hash_password(body.password),
            is_active=True,
        )
        await self.user_repo.create(new_user)
        await self.user_repo.flush()

        await self.audit_service.log_auth_event(
            event=AuditEvent.USER_ACTIVATED,
            user_id=new_user.id,
            email_attempted=new_user.email,
            request=request,
            commit=False,
        )
        await self.user_repo.commit()
        await self.user_repo.refresh(new_user)

        return UserResponse.model_validate(new_user)

    async def login(
        self,
        body: LoginRequest,
        request: Optional[Request] = None,
    ) -> TokenResponse:
        """Xác thực thông tin đăng nhập của người dùng và cấp JWT access token."""
        generic_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác",
            headers={"WWW-Authenticate": "Bearer"},
        )

        user = await self.user_repo.get_by_email(body.email)
        if user is None:
            verify_dummy_password(body.password)
            await self.audit_service.log_auth_event(
                event=AuditEvent.LOGIN_FAILED,
                email_attempted=body.email,
                request=request,
            )
            raise generic_error

        if not verify_password(body.password, user.password_hash) or not user.is_active:
            await self.audit_service.log_auth_event(
                event=AuditEvent.LOGIN_FAILED,
                user_id=user.id,
                email_attempted=body.email,
                request=request,
            )
            raise generic_error

        user.last_login_at = datetime.now(timezone.utc)
        await self.audit_service.log_auth_event(
            event=AuditEvent.LOGIN_SUCCESS,
            user_id=user.id,
            email_attempted=user.email,
            request=request,
            commit=False,
        )
        await self.user_repo.commit()
        await self.user_repo.refresh(user)

        token = create_access_token(
            subject=user.id,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    async def change_password(
        self,
        current_user: AppUser,
        body: ChangePasswordRequest,
        request: Optional[Request] = None,
    ) -> dict[str, str]:
        """Đổi mật khẩu cho người dùng hiện tại đang đăng nhập."""
        if not verify_password(body.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mật khẩu hiện tại không chính xác",
            )

        current_user.password_hash = hash_password(body.new_password)
        await self.audit_service.log_auth_event(
            event=AuditEvent.PASSWORD_CHANGED,
            user_id=current_user.id,
            email_attempted=current_user.email,
            request=request,
            commit=False,
        )
        await self.user_repo.commit()

        return {"message": "Đổi mật khẩu thành công"}
