from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUserDep, DepartmentServiceDep, require_roles
from app.models.user import AppUser, UserRole
from app.schemas.department import DepartmentCreate, DepartmentResponse
from app.schemas.user import UserResponse

router = APIRouter()

AdminOnlyDep = Annotated[AppUser, Depends(require_roles(UserRole.ADMIN))]
AdminOrManagerDep = Annotated[
    AppUser, Depends(require_roles(UserRole.ADMIN, UserRole.DEPT_MANAGER))
]


@router.post(
    "",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo phòng ban mới",
    description="Tạo một phòng ban mới. Chỉ dành cho quyền ADMIN.",
    responses={
        400: {"description": "Tên phòng ban đã tồn tại"},
        401: {"description": "Yêu cầu xác thực"},
        403: {"description": "Yêu cầu quyền ADMIN"},
    },
)
async def create_department(
    body: DepartmentCreate,
    current_user: AdminOnlyDep,
    department_service: DepartmentServiceDep,
) -> DepartmentResponse:
    return await department_service.create_department(body=body)


@router.get(
    "",
    response_model=list[DepartmentResponse],
    summary="Danh sách phòng ban",
    description="Lấy danh sách tất cả các phòng ban. Dành cho người dùng đã đăng nhập.",
    responses={
        401: {"description": "Yêu cầu xác thực"},
    },
)
async def list_departments(
    current_user: CurrentUserDep,
    department_service: DepartmentServiceDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[DepartmentResponse]:
    return await department_service.list_departments(skip=skip, limit=limit)


@router.get(
    "/{id}",
    response_model=DepartmentResponse,
    summary="Chi tiết phòng ban theo ID",
    description="Lấy thông tin chi tiết một phòng ban theo ID.",
    responses={
        401: {"description": "Yêu cầu xác thực"},
        404: {"description": "Không tìm thấy phòng ban"},
    },
)
async def get_department(
    id: uuid.UUID,
    current_user: CurrentUserDep,
    department_service: DepartmentServiceDep,
) -> DepartmentResponse:
    return await department_service.get_department(dept_id=id)


@router.get(
    "/{id}/members",
    response_model=list[UserResponse],
    summary="Danh sách thành viên phòng ban",
    description="Lấy danh sách thành viên trong phòng ban. ADMIN xem được mọi phòng ban; DEPT_MANAGER chỉ xem được phòng ban của mình.",
    responses={
        401: {"description": "Yêu cầu xác thực"},
        403: {"description": "Không đủ quyền truy cập"},
        404: {"description": "Không tìm thấy phòng ban"},
    },
)
async def get_department_members(
    id: uuid.UUID,
    current_user: AdminOrManagerDep,
    department_service: DepartmentServiceDep,
) -> list[UserResponse]:
    return await department_service.get_department_members(
        dept_id=id, current_user=current_user
    )
