from typing import Optional
import uuid

from fastapi import APIRouter, Body, Query, status

from app.api.deps import CurrentUserDep, TicketServiceDep
from app.schemas.ticket import (
    TicketAcceptRequest,
    TicketAssignRequest,
    TicketCommentCreate,
    TicketCommentResponse,
    TicketCreate,
    TicketResponse,
    TicketStatusUpdateRequest,
)

router = APIRouter()


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    current_user: CurrentUserDep,
    body: TicketCreate,
    ticket_service: TicketServiceDep,
) -> TicketResponse:
    """Tạo mới Phiếu hỗ trợ (Ticket) qua web form: AI tự động phân loại danh mục và định tuyến tới phòng ban."""
    return await ticket_service.create_ticket(body, current_user)


@router.get("", response_model=list[TicketResponse])
async def list_tickets(
    current_user: CurrentUserDep,
    ticket_service: TicketServiceDep,
    status: Optional[str] = Query(None, description="Lọc theo trạng thái ticket"),
    category_id: Optional[uuid.UUID] = Query(None, description="Lọc theo danh mục"),
    department_id: Optional[uuid.UUID] = Query(None, description="Lọc theo phòng ban"),
    unassigned_only: bool = Query(False, description="Chỉ lấy phiếu chưa có người tiếp nhận"),
    assigned_to_me: bool = Query(False, description="Chỉ lấy phiếu phân công cho bản thân"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[TicketResponse]:
    """Xem danh sách phiếu hỗ trợ theo quyền hạn người dùng."""
    return await ticket_service.list_tickets(
        current_user=current_user,
        status=status,
        category_id=category_id,
        department_id=department_id,
        unassigned_only=unassigned_only,
        assigned_to_me=assigned_to_me,
        skip=skip,
        limit=limit,
    )


@router.get("/{id}", response_model=TicketResponse)
async def get_ticket(
    current_user: CurrentUserDep,
    id: uuid.UUID,
    ticket_service: TicketServiceDep,
) -> TicketResponse:
    """Xem chi tiết phiếu hỗ trợ kèm toàn bộ lịch sử trạng thái, thảo luận và kết quả phân loại AI."""
    return await ticket_service.get_ticket(id, current_user)


@router.post("/{id}/accept", response_model=TicketResponse)
async def accept_ticket(
    id: uuid.UUID,
    current_user: CurrentUserDep,
    ticket_service: TicketServiceDep,
    body: TicketAcceptRequest = Body(default_factory=TicketAcceptRequest),
) -> TicketResponse:
    """Cán bộ / Kỹ thuật viên phòng ban phụ trách tiếp nhận phiếu hỗ trợ."""
    return await ticket_service.accept_ticket(id, current_user, note=body.note)


@router.post("/{id}/assign", response_model=TicketResponse)
async def assign_ticket(
    id: uuid.UUID,
    body: TicketAssignRequest,
    current_user: CurrentUserDep,
    ticket_service: TicketServiceDep,
) -> TicketResponse:
    """Trưởng phòng ban (DEPT_MANAGER) hoặc ADMIN điều phối/phân công phiếu cho kỹ thuật viên trong phòng ban."""
    return await ticket_service.assign_ticket(id, body, current_user)


@router.patch("/{id}/status", response_model=TicketResponse)
async def update_ticket_status(
    id: uuid.UUID,
    body: TicketStatusUpdateRequest,
    current_user: CurrentUserDep,
    ticket_service: TicketServiceDep,
) -> TicketResponse:
    """Cập nhật trạng thái phiếu hỗ trợ (IN_PROGRESS, PENDING_USER, RESOLVED, CLOSED, CANCELLED)."""
    return await ticket_service.update_status(id, body, current_user)


@router.get("/{id}/comments", response_model=list[TicketCommentResponse])
async def list_ticket_comments(
    id: uuid.UUID,
    current_user: CurrentUserDep,
    ticket_service: TicketServiceDep,
) -> list[TicketCommentResponse]:
    """Xem danh sách trao đổi / hướng dẫn xử lý trên phiếu hỗ trợ."""
    return await ticket_service.list_comments(id, current_user)


@router.post("/{id}/comments", response_model=TicketCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket_comment(
    id: uuid.UUID,
    body: TicketCommentCreate,
    current_user: CurrentUserDep,
    ticket_service: TicketServiceDep,
) -> TicketCommentResponse:
    """Gửi phản hồi, hướng dẫn xử lý cho sinh viên hoặc tạo ghi chú kỹ thuật nội bộ phòng ban."""
    return await ticket_service.add_comment(id, body, current_user)

