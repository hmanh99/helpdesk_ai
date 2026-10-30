import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.models.department import Department
from app.models.user import AppUser
from app.repo.department import DepartmentRepository
from app.repo.user import UserRepository
from app.schemas.department import DepartmentCreate, DepartmentResponse
from app.schemas.user import UserResponse
from app.security.policies import can_manage_department


class DepartmentService:
    """Service xử lý nghiệp vụ quản lý phòng ban và thành viên."""

    def __init__(
        self,
        dept_repo: DepartmentRepository,
        user_repo: UserRepository,
    ) -> None:
        self.dept_repo = dept_repo
        self.user_repo = user_repo

    async def create_department(self, body: DepartmentCreate) -> DepartmentResponse:
        """Tạo mới phòng ban. Kiểm tra tên phòng ban không trùng lặp."""
        existing = await self.dept_repo.get_by_name(body.name)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phòng ban với tên này đã tồn tại",
            )

        dept = Department(name=body.name.strip(), description=body.description)
        await self.dept_repo.create(dept)
        try:
            await self.dept_repo.commit()
        except IntegrityError:
            await self.dept_repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phòng ban với tên này đã tồn tại",
            )

        await self.dept_repo.refresh(dept)
        return DepartmentResponse.model_validate(dept)

    async def list_departments(
        self, skip: int = 0, limit: int = 50
    ) -> list[DepartmentResponse]:
        """Lấy danh sách các phòng ban với phân trang."""
        departments = await self.dept_repo.list_departments(skip=skip, limit=limit)
        return [DepartmentResponse.model_validate(d) for d in departments]

    async def get_department(self, dept_id: uuid.UUID) -> DepartmentResponse:
        """Lấy thông tin chi tiết một phòng ban theo ID."""
        dept = await self.dept_repo.get_by_id(dept_id)
        if dept is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phòng ban",
            )
        return DepartmentResponse.model_validate(dept)

    async def get_department_members(
        self, dept_id: uuid.UUID, current_user: AppUser
    ) -> list[UserResponse]:
        """Lấy danh sách thành viên trong phòng ban (kiểm tra quyền của Trưởng phòng hoặc ADMIN)."""
        dept = await self.dept_repo.get_by_id(dept_id)
        if dept is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phòng ban",
            )

        if not can_manage_department(current_user, dept_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Trưởng phòng chỉ có thể xem thành viên trong phòng ban của mình",
            )

        members = await self.user_repo.list_by_department(dept_id)
        return [UserResponse.model_validate(m) for m in members]
