from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import AppUser
from app.repo.audit import AuditRepository
from app.repo.department import DepartmentRepository
from app.repo.health import HealthRepository
from app.repo.user import UserRepository
from app.security.deps import CurrentUserDep, get_current_user, require_roles
from app.service.audit import AuditService
from app.service.auth import AuthService
from app.service.department import DepartmentService
from app.service.health import HealthService
from app.service.user import UserService

SessionDep = Annotated[AsyncSession, Depends(get_db)]


def get_audit_service(db: SessionDep) -> AuditService:
    return AuditService(AuditRepository(db))


def get_auth_service(
    db: SessionDep,
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> AuthService:
    return AuthService(UserRepository(db), audit_service)


def get_department_service(db: SessionDep) -> DepartmentService:
    return DepartmentService(DepartmentRepository(db), UserRepository(db))


def get_user_service(
    db: SessionDep,
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> UserService:
    return UserService(UserRepository(db), DepartmentRepository(db), audit_service)


def get_health_service(db: SessionDep) -> HealthService:
    return HealthService(HealthRepository(db))


AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
DepartmentServiceDep = Annotated[DepartmentService, Depends(get_department_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]

__all__ = [
    "SessionDep",
    "CurrentUserDep",
    "get_current_user",
    "require_roles",
    "get_audit_service",
    "get_auth_service",
    "get_department_service",
    "get_user_service",
    "get_health_service",
    "AuditServiceDep",
    "AuthServiceDep",
    "DepartmentServiceDep",
    "UserServiceDep",
    "HealthServiceDep",
]
