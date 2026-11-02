from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole
from app.schemas.department import DepartmentResponse


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=150)


class UserCreate(UserBase):
    role: UserRole
    department_id: Optional[uuid.UUID] = None
    password: str = Field(
        ...,
        min_length=8,
        description="Mật khẩu phải có ít nhất 8 ký tự",
    )


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=150)
    role: Optional[UserRole] = None
    department_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class UserResetPasswordRequest(BaseModel):
    new_password: str = Field(
        ...,
        min_length=8,
        description="Mật khẩu mới phải có ít nhất 8 ký tự",
    )


class UserResponse(UserBase):
    id: uuid.UUID
    role: UserRole
    department_id: Optional[uuid.UUID] = None
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    department: Optional[DepartmentResponse] = None

    model_config = ConfigDict(from_attributes=True)
