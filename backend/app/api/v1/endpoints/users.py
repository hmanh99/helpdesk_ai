from typing import Annotated, Optional
import uuid

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import CurrentUserDep, UserServiceDep, require_roles
from app.models.user import AppUser, UserRole
from app.schemas.user import (
    UserCreate,
    UserResetPasswordRequest,
    UserResponse,
    UserUpdate,
)

router = APIRouter()

AdminOnlyDep = Annotated[AppUser, Depends(require_roles(UserRole.ADMIN))]


@router.get(
    "",
    response_model=list[UserResponse],
    summary="Danh sách người dùng",
    description="Lấy danh sách người dùng có phân trang và bộ lọc. Chỉ dành cho quyền ADMIN.",
    responses={
        401: {"description": "Yêu cầu xác thực"},
        403: {"description": "Yêu cầu quyền ADMIN"},
    },
)
async def list_users(
    current_user: AdminOnlyDep,
    user_service: UserServiceDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[UserRole] = None,
    department_id: Optional[uuid.UUID] = None,
    is_active: Optional[bool] = None,
) -> list[UserResponse]:
    return await user_service.list_users(
        current_user=current_user,
        skip=skip,
        limit=limit,
        role=role,
        department_id=department_id,
        is_active=is_active,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo người dùng mới",
    description="Tạo người dùng mới. Chỉ dành cho quyền ADMIN. Yêu cầu phòng ban đối với vai trò Kỹ thuật viên và Trưởng phòng.",
    responses={
        400: {"description": "Dữ liệu không hợp lệ hoặc thiếu phòng ban bắt buộc"},
        401: {"description": "Yêu cầu xác thực"},
        403: {"description": "Yêu cầu quyền ADMIN"},
        409: {"description": "Email đã tồn tại"},
    },
)
async def create_user(
    request: Request,
    body: UserCreate,
    current_user: AdminOnlyDep,
    user_service: UserServiceDep,
) -> UserResponse:
    return await user_service.create_user(
        body=body,
        current_user=current_user,
        request=request,
    )


@router.get(
    "/{id}",
    response_model=UserResponse,
    summary="Xem chi tiết người dùng theo ID",
    description="Lấy thông tin người dùng theo ID. Chỉ chính người dùng đó hoặc ADMIN mới có quyền xem.",
    responses={
        401: {"description": "Yêu cầu xác thực"},
        403: {"description": "Không đủ quyền truy cập"},
        404: {"description": "Không tìm thấy người dùng"},
    },
)
async def get_user_by_id(
    id: uuid.UUID,
    current_user: CurrentUserDep,
    user_service: UserServiceDep,
) -> UserResponse:
    return await user_service.get_user_by_id(
        user_id=id,
        current_user=current_user,
    )


@router.patch(
    "/{id}",
    response_model=UserResponse,
    summary="Cập nhật thông tin người dùng",
    description="Cập nhật thông tin người dùng. Chỉ chính người dùng đó hoặc ADMIN mới có quyền. Người dùng thường chỉ được đổi họ tên.",
    responses={
        400: {"description": "Vi phạm ràng buộc dữ liệu"},
        401: {"description": "Yêu cầu xác thực"},
        403: {"description": "Không đủ quyền truy cập"},
        404: {"description": "Không tìm thấy người dùng hoặc phòng ban"},
    },
)
async def update_user(
    id: uuid.UUID,
    body: UserUpdate,
    request: Request,
    current_user: CurrentUserDep,
    user_service: UserServiceDep,
) -> UserResponse:
    return await user_service.update_user(
        user_id=id,
        body=body,
        current_user=current_user,
        request=request,
    )


@router.delete(
    "/delete/{id}",
    summary="Xóa tài khoản người dùng",
    description="Xóa tài khoản người dùng. Chỉ chính người dùng đó hoặc ADMIN mới có quyền thực hiện.",
    responses={
        400: {"description": "Không thể xóa admin đang hoạt động cuối cùng"},
        401: {"description": "Yêu cầu xác thực"},
        403: {"description": "Không đủ quyền truy cập"},
        404: {"description": "Không tìm thấy người dùng"},
    },
)
async def delete_user(
    id: uuid.UUID,
    request: Request,
    current_user: CurrentUserDep,
    user_service: UserServiceDep,
) -> dict[str, str]:
    return await user_service.delete_user(
        user_id=id,
        current_user=current_user,
        request=request,
    )


@router.post(
    "/{id}/reset-password",
    summary="Đặt lại mật khẩu người dùng",
    description="Đặt lại mật khẩu cho người dùng. Chỉ dành cho quyền ADMIN.",
    responses={
        401: {"description": "Yêu cầu xác thực"},
        403: {"description": "Yêu cầu quyền ADMIN"},
        404: {"description": "Không tìm thấy người dùng"},
    },
)
async def reset_password(
    id: uuid.UUID,
    body: UserResetPasswordRequest,
    request: Request,
    current_user: AdminOnlyDep,
    user_service: UserServiceDep,
) -> dict[str, str]:
    return await user_service.reset_password(
        user_id=id,
        body=body,
        current_user=current_user,
        request=request,
    )
