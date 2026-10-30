from fastapi import APIRouter, Request, status

from app.api.deps import AuthServiceDep, CurrentUserDep
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản",
    description="Đăng ký tài khoản người dùng mới với vai trò mặc định là STUDENT.",
    responses={
        201: {"description": "Đăng ký tài khoản thành công"},
        400: {"description": "Dữ liệu đầu vào không hợp lệ"},
        409: {"description": "Email này đã được đăng ký"},
    },
)
async def register(
    request: Request,
    body: RegisterRequest,
    auth_service: AuthServiceDep,
) -> UserResponse:
    return await auth_service.register(body=body, request=request)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Đăng nhập người dùng",
    description="Xác thực bằng email và mật khẩu. Trả về JWT access token và thông tin người dùng.",
    responses={
        401: {
            "description": "Email hoặc mật khẩu không chính xác",
            "content": {"application/json": {"example": {"detail": "Email hoặc mật khẩu không chính xác"}}},
        }
    },
)
async def login(
    request: Request,
    body: LoginRequest,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    return await auth_service.login(body=body, request=request)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Lấy thông tin tài khoản hiện tại",
    description="Trả về thông tin hồ sơ, vai trò và phòng ban của người dùng hiện đang xác thực.",
    responses={
        401: {
            "description": "Yêu cầu xác thực hoặc token không hợp lệ",
            "content": {"application/json": {"example": {"detail": "Yêu cầu xác thực"}}},
        }
    },
)
async def get_me(current_user: CurrentUserDep) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post(
    "/change-password",
    summary="Đổi mật khẩu người dùng hiện tại",
    description="Cho phép người dùng hiện đang đăng nhập đổi mật khẩu bằng cách cung cấp mật khẩu cũ và mới.",
    responses={
        400: {"description": "Mật khẩu hiện tại không đúng hoặc lỗi dữ liệu"},
        401: {"description": "Yêu cầu xác thực"},
    },
)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: CurrentUserDep,
    auth_service: AuthServiceDep,
) -> dict[str, str]:
    return await auth_service.change_password(
        current_user=current_user,
        body=body,
        request=request,
    )
