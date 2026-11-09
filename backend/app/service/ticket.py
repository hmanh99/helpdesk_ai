from datetime import datetime, timezone
import logging
from typing import Optional
import uuid

from fastapi import HTTPException, status

from app.core.config import settings
from app.models.category import Category
from app.models.enums import Channel, Priority, TicketStatus
from app.models.ticket import AIClassification, Ticket, TicketComment, TicketHistory
from app.models.user import AppUser, UserRole
from app.repo.category import CategoryRepository
from app.repo.department import DepartmentRepository
from app.repo.ticket import TicketRepository
from app.repo.user import UserRepository
from app.schemas.ticket import (
    AIClassificationResponse,
    TicketAcceptRequest,
    TicketAssignRequest,
    TicketCommentCreate,
    TicketCommentResponse,
    TicketCreate,
    TicketHistoryResponse,
    TicketResponse,
    TicketStatusUpdateRequest,
)
from app.security.policies import (
    can_accept_or_update_ticket,
    can_create_ticket,
    can_reassign_ticket,
    can_view_internal_comments,
    can_view_ticket,
)
from app.service.classifier import ClassifierService, RoutingService

logger = logging.getLogger(__name__)


class TicketService:
    """Service xử lý nghiệp vụ tạo phiếu hỗ trợ, phân loại AI, tiếp nhận và xử lý sự cố phòng ban."""

    def __init__(
        self,
        ticket_repo: TicketRepository,
        category_repo: CategoryRepository,
        dept_repo: DepartmentRepository,
        classifier_service: ClassifierService,
        user_repo: Optional[UserRepository] = None,
    ) -> None:
        self.ticket_repo = ticket_repo
        self.category_repo = category_repo
        self.dept_repo = dept_repo
        self.classifier_service = classifier_service
        self.user_repo = user_repo or UserRepository(self.ticket_repo.db)

    def _to_response(
        self, ticket: Ticket, current_user: Optional[AppUser] = None
    ) -> TicketResponse:
        histories_resp = [
            TicketHistoryResponse(
                id=h.id,
                old_status=h.old_status,
                new_status=h.new_status,
                note=h.note,
                changed_by=h.changed_by,
                changed_by_name=h.actor.full_name if h.actor else "Hệ thống AI",
                changed_at=h.changed_at,
            )
            for h in ticket.histories
        ]

        include_internal = False
        if current_user is not None:
            include_internal = can_view_internal_comments(current_user, ticket)

        comments_resp = [
            TicketCommentResponse(
                id=c.id,
                ticket_id=c.ticket_id,
                author_id=c.author_id,
                author_name=c.author.full_name if c.author else None,
                author_role=c.author.role.value if c.author else None,
                content=c.content,
                is_internal=c.is_internal,
                created_at=c.created_at,
            )
            for c in (ticket.comments or [])
            if (not c.is_internal or include_internal)
        ]

        latest_clf = ticket.classifications[0] if ticket.classifications else None
        clf_resp = None
        if latest_clf:
            clf_resp = AIClassificationResponse(
                id=latest_clf.id,
                predicted_category_id=latest_clf.predicted_category_id,
                predicted_category_name=latest_clf.predicted_category.name
                if latest_clf.predicted_category
                else None,
                suggested_priority=latest_clf.suggested_priority,
                confidence_score=latest_clf.confidence_score,
                model_version=latest_clf.model_version,
                created_at=latest_clf.created_at,
            )

        return TicketResponse(
            id=ticket.id,
            title=ticket.title,
            description=ticket.description,
            requester_id=ticket.requester_id,
            requester_name=ticket.requester.full_name if ticket.requester else None,
            assignee_id=ticket.assignee_id,
            assignee_name=ticket.assignee.full_name if ticket.assignee else None,
            category_id=ticket.category_id,
            category_name=ticket.category.name if ticket.category else None,
            department_id=ticket.department_id,
            department_name=ticket.department.name if ticket.department else None,
            chat_session_id=ticket.chat_session_id,
            priority=ticket.priority,
            status=ticket.status,
            channel=ticket.channel,
            created_at=ticket.created_at,
            resolved_at=ticket.resolved_at,
            histories=histories_resp,
            comments=comments_resp,
            classification=clf_resp,
        )

    async def create_ticket(
        self, body: TicketCreate, current_user: AppUser
    ) -> TicketResponse:
        if not can_create_ticket(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản không có quyền tạo phiếu hỗ trợ",
            )

        # Tránh tạo trùng ticket từ cùng một phiên chat
        if body.chat_session_id:
            existing = await self.ticket_repo.get_by_chat_session_id(body.chat_session_id)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Phiên chat này đã được tạo Ticket trước đó (ID: {existing.id})",
                )

        ticket_id = uuid.uuid4()
        ticket = Ticket(
            id=ticket_id,
            title=body.title.strip(),
            description=body.description.strip(),
            requester_id=current_user.id,
            priority=body.priority,
            status=TicketStatus.NEW,
            channel=body.channel,
            chat_session_id=body.chat_session_id,
        )
        await self.ticket_repo.create_ticket(ticket)

        # Lịch sử khởi tạo
        init_history = TicketHistory(
            ticket_id=ticket.id,
            changed_by=current_user.id,
            old_status=None,
            new_status=TicketStatus.NEW.value,
            note=f"Khởi tạo phiếu hỗ trợ qua kênh {body.channel.value}",
        )
        await self.ticket_repo.add_history(init_history)

        categories = await self.category_repo.list_categories(active_only=True)

        # TH1: Người dùng đã chủ động chọn hoặc xác nhận danh mục
        if body.category_id:
            cat = next((c for c in categories if c.id == body.category_id), None)
            if cat is not None:
                ticket.category_id = cat.id
                ticket.department_id = cat.department_id
                ticket.status = TicketStatus.TRIAGED

                clf = AIClassification(
                    ticket_id=ticket.id,
                    predicted_category_id=cat.id,
                    suggested_priority=ticket.priority,
                    confidence_score=1.0,
                    model_version="user_selection",
                )
                await self.ticket_repo.add_classification(clf)

                routed_history = TicketHistory(
                    ticket_id=ticket.id,
                    changed_by=None,
                    old_status=TicketStatus.NEW.value,
                    new_status=TicketStatus.TRIAGED.value,
                    note=f"Đã định tuyến theo danh mục người dùng chọn: {cat.name} -> {cat.department.name if cat.department else ''}",
                )
                await self.ticket_repo.add_history(routed_history)
        else:
            # TH2: Phân loại và định tuyến tự động bằng AI
            clf_result = await self.classifier_service.classify_ticket(ticket, categories)
            cat_id_uuid = uuid.UUID(clf_result.category_id) if clf_result.category_id else None

            clf = AIClassification(
                ticket_id=ticket.id,
                predicted_category_id=cat_id_uuid,
                suggested_priority=clf_result.priority,
                confidence_score=clf_result.confidence,
                model_version=settings.GEMINI_CHAT_MODEL,
                raw_output=clf_result.model_dump(),
            )
            await self.ticket_repo.add_classification(clf)

            # Thực hiện định tuyến
            is_routed = RoutingService.route_ticket(
                ticket=ticket,
                classification=clf,
                categories=categories,
                confidence_threshold=settings.INTENT_CONFIDENCE_THRESHOLD,
            )

            if is_routed:
                ticket.status = TicketStatus.TRIAGED
                dept_name = ticket.department.name if ticket.department else "Phòng ban phụ trách"
                cat_name = ticket.category.name if ticket.category else ""
                routed_history = TicketHistory(
                    ticket_id=ticket.id,
                    changed_by=None,
                    old_status=TicketStatus.NEW.value,
                    new_status=TicketStatus.TRIAGED.value,
                    note=f"AI tự động định tuyến tới {dept_name} (Danh mục: {cat_name}, Độ tin cậy: {clf.confidence_score:.0%})",
                )
                await self.ticket_repo.add_history(routed_history)
            else:
                ticket.status = TicketStatus.NEW
                low_conf_history = TicketHistory(
                    ticket_id=ticket.id,
                    changed_by=None,
                    old_status=TicketStatus.NEW.value,
                    new_status=TicketStatus.NEW.value,
                    note=f"AI độ tin cậy thấp ({clf.confidence_score:.0%}). Chờ nhân viên phân loại thủ công.",
                )
                await self.ticket_repo.add_history(low_conf_history)

        await self.ticket_repo.commit()
        refreshed = await self.ticket_repo.get_by_id(ticket.id)
        assert refreshed is not None
        return self._to_response(refreshed, current_user)

    async def get_ticket(
        self, ticket_id: uuid.UUID, current_user: AppUser
    ) -> TicketResponse:
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiếu hỗ trợ",
            )

        if not can_view_ticket(current_user, ticket):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền xem thông tin phiếu hỗ trợ này",
            )

        return self._to_response(ticket, current_user)

    async def list_tickets(
        self,
        current_user: AppUser,
        status: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        unassigned_only: bool = False,
        assigned_to_me: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TicketResponse]:
        tickets = await self.ticket_repo.list_tickets_for_user(
            user=current_user,
            status=status,
            category_id=category_id,
            department_id=department_id,
            unassigned_only=unassigned_only,
            assigned_to_me=assigned_to_me,
            skip=skip,
            limit=limit,
        )
        return [self._to_response(t, current_user) for t in tickets]

    async def accept_ticket(
        self, ticket_id: uuid.UUID, current_user: AppUser, note: Optional[str] = None
    ) -> TicketResponse:
        """Cán bộ / Kỹ thuật viên phòng ban tiếp nhận phiếu hỗ trợ để bắt đầu xử lý."""
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiếu hỗ trợ",
            )

        if not can_accept_or_update_ticket(current_user, ticket):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền tiếp nhận phiếu hỗ trợ này (chỉ dành cho cán bộ/kỹ thuật viên thuộc phòng ban phụ trách)",
            )

        old_status = ticket.status.value
        ticket.assignee = current_user
        ticket.assignee_id = current_user.id
        if ticket.status in (TicketStatus.NEW, TicketStatus.TRIAGED, TicketStatus.ASSIGNED):
            ticket.status = TicketStatus.IN_PROGRESS

        history = TicketHistory(
            ticket_id=ticket.id,
            changed_by=current_user.id,
            actor=current_user,
            old_status=old_status,
            new_status=ticket.status.value,
            note=note or f"Cán bộ/Kỹ thuật viên {current_user.full_name} đã tiếp nhận phiếu hỗ trợ",
        )
        ticket.histories.append(history)
        await self.ticket_repo.add_history(history)
        await self.ticket_repo.commit()

        refreshed = await self.ticket_repo.get_by_id(ticket.id)
        assert refreshed is not None
        return self._to_response(refreshed, current_user)

    async def assign_ticket(
        self, ticket_id: uuid.UUID, body: TicketAssignRequest, current_user: AppUser
    ) -> TicketResponse:
        """Trưởng phòng ban (DEPT_MANAGER) hoặc ADMIN điều phối/phân công phiếu cho kỹ thuật viên."""
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiếu hỗ trợ",
            )

        if not can_reassign_ticket(current_user, ticket):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Quản trị viên hoặc Trưởng phòng ban phụ trách mới có quyền phân công phiếu hỗ trợ",
            )

        tech = await self.user_repo.get_by_id(body.assignee_id)
        if tech is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy tài khoản kỹ thuật viên được chỉ định",
            )

        if current_user.role == UserRole.DEPT_MANAGER:
            if tech.department_id != current_user.department_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Kỹ thuật viên được phân công phải thuộc cùng phòng ban với bạn",
                )

        old_status = ticket.status.value
        ticket.assignee = tech
        ticket.assignee_id = tech.id
        if ticket.status in (TicketStatus.NEW, TicketStatus.TRIAGED):
            ticket.status = TicketStatus.ASSIGNED

        history = TicketHistory(
            ticket_id=ticket.id,
            changed_by=current_user.id,
            actor=current_user,
            old_status=old_status,
            new_status=ticket.status.value,
            note=body.note or f"Trưởng phòng {current_user.full_name} đã phân công xử lý cho kỹ thuật viên {tech.full_name}",
        )
        ticket.histories.append(history)
        await self.ticket_repo.add_history(history)
        await self.ticket_repo.commit()

        refreshed = await self.ticket_repo.get_by_id(ticket.id)
        assert refreshed is not None
        return self._to_response(refreshed, current_user)

    async def update_status(
        self, ticket_id: uuid.UUID, body: TicketStatusUpdateRequest, current_user: AppUser
    ) -> TicketResponse:
        """Cán bộ phòng ban cập nhật trạng thái phiếu hỗ trợ (Đang xử lý, Chờ SV phản hồi, Đã giải quyết, Đóng, Hủy)."""
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiếu hỗ trợ",
            )

        if not can_accept_or_update_ticket(current_user, ticket):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền cập nhật trạng thái phiếu hỗ trợ này",
            )

        old_status = ticket.status.value
        ticket.status = body.status

        if body.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
            ticket.resolved_at = datetime.now(timezone.utc)
        elif body.status in (TicketStatus.IN_PROGRESS, TicketStatus.PENDING_USER, TicketStatus.ASSIGNED):
            ticket.resolved_at = None

        history = TicketHistory(
            ticket_id=ticket.id,
            changed_by=current_user.id,
            actor=current_user,
            old_status=old_status,
            new_status=body.status.value,
            note=body.note or f"Cập nhật trạng thái phiếu sang {body.status.value}",
        )
        ticket.histories.append(history)
        await self.ticket_repo.add_history(history)
        await self.ticket_repo.commit()

        refreshed = await self.ticket_repo.get_by_id(ticket.id)
        assert refreshed is not None
        return self._to_response(refreshed, current_user)

    async def add_comment(
        self, ticket_id: uuid.UUID, body: TicketCommentCreate, current_user: AppUser
    ) -> TicketCommentResponse:
        """Gửi phản hồi, hướng dẫn xử lý cho sinh viên hoặc ghi chú nội bộ phòng ban."""
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiếu hỗ trợ",
            )

        if not can_view_ticket(current_user, ticket):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền trao đổi trên phiếu hỗ trợ này",
            )

        if body.is_internal and not can_view_internal_comments(current_user, ticket):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sinh viên không có quyền tạo ghi chú nội bộ phòng ban",
            )

        comment = TicketComment(
            ticket_id=ticket.id,
            author_id=current_user.id,
            content=body.content.strip(),
            is_internal=body.is_internal,
        )
        await self.ticket_repo.add_comment(comment)
        await self.ticket_repo.commit()

        return TicketCommentResponse(
            id=comment.id,
            ticket_id=comment.ticket_id,
            author_id=comment.author_id,
            author_name=current_user.full_name,
            author_role=current_user.role.value,
            content=comment.content,
            is_internal=comment.is_internal,
            created_at=comment.created_at,
        )

    async def list_comments(
        self, ticket_id: uuid.UUID, current_user: AppUser
    ) -> list[TicketCommentResponse]:
        """Xem toàn bộ trao đổi / hướng dẫn xử lý trên phiếu hỗ trợ (tự động ẩn ghi chú nội bộ đối với sinh viên)."""
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiếu hỗ trợ",
            )

        if not can_view_ticket(current_user, ticket):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền xem thông tin phiếu hỗ trợ này",
            )

        include_internal = can_view_internal_comments(current_user, ticket)
        comments = await self.ticket_repo.list_comments(ticket_id, include_internal=include_internal)
        return [
            TicketCommentResponse(
                id=c.id,
                ticket_id=c.ticket_id,
                author_id=c.author_id,
                author_name=c.author.full_name if c.author else None,
                author_role=c.author.role.value if c.author else None,
                content=c.content,
                is_internal=c.is_internal,
                created_at=c.created_at,
            )
            for c in comments
        ]
