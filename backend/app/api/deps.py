from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.fake_client import FakeLLMClient
from app.ai.gemini_client import GeminiClient
from app.ai.llm import LLMClient
from app.core.config import settings
from app.db.session import get_db
from app.models.user import AppUser
from app.repo.audit import AuditRepository
from app.repo.category import CategoryRepository
from app.repo.chat import ChatRepository
from app.repo.department import DepartmentRepository
from app.repo.health import HealthRepository
from app.repo.knowledge import KnowledgeRepository
from app.repo.ticket import TicketRepository
from app.repo.user import UserRepository
from app.security.deps import CurrentUserDep, get_current_user, require_roles
from app.service.audit import AuditService
from app.service.auth import AuthService
from app.service.category import CategoryService
from app.service.chat import ChatService
from app.service.classifier import ClassifierService, IntentClassifier
from app.service.department import DepartmentService
from app.service.health import HealthService
from app.service.knowledge import KnowledgeService
from app.service.rag import RagService
from app.service.ticket import TicketService
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


def get_category_service(db: SessionDep) -> CategoryService:
    return CategoryService(CategoryRepository(db), DepartmentRepository(db))


def get_llm_client() -> LLMClient:
    if settings.GOOGLE_API_KEY:
        return GeminiClient(settings.GOOGLE_API_KEY)
    return FakeLLMClient(embedding_dim=settings.EMBEDDING_DIM)


def get_knowledge_service(
    db: SessionDep,
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
) -> KnowledgeService:
    return KnowledgeService(KnowledgeRepository(db), CategoryRepository(db), llm_client)


def get_intent_classifier(
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
) -> IntentClassifier:
    return IntentClassifier(llm_client)


def get_classifier_service(
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
) -> ClassifierService:
    return ClassifierService(llm_client)


def get_rag_service(
    db: SessionDep,
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
) -> RagService:
    return RagService(KnowledgeRepository(db), llm_client)


def get_ticket_service(
    db: SessionDep,
    classifier_service: Annotated[ClassifierService, Depends(get_classifier_service)],
) -> TicketService:
    return TicketService(
        TicketRepository(db),
        CategoryRepository(db),
        DepartmentRepository(db),
        classifier_service,
        UserRepository(db),
    )


def get_chat_service(
    db: SessionDep,
    intent_classifier: Annotated[IntentClassifier, Depends(get_intent_classifier)],
    rag_service: Annotated[RagService, Depends(get_rag_service)],
    classifier_service: Annotated[ClassifierService, Depends(get_classifier_service)],
    ticket_service: Annotated[TicketService, Depends(get_ticket_service)],
) -> ChatService:
    return ChatService(
        ChatRepository(db),
        CategoryRepository(db),
        intent_classifier,
        rag_service,
        classifier_service,
        ticket_service,
    )


AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
DepartmentServiceDep = Annotated[DepartmentService, Depends(get_department_service)]
CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]
KnowledgeServiceDep = Annotated[KnowledgeService, Depends(get_knowledge_service)]
LLMClientDep = Annotated[LLMClient, Depends(get_llm_client)]
TicketServiceDep = Annotated[TicketService, Depends(get_ticket_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
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
