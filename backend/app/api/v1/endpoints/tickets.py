from typing import Optional
import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUserDep, TicketServiceDep
from app.schemas.ticket import TicketCreate, TicketResponse

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
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[TicketResponse]:
    """Xem danh sách phiếu hỗ trợ theo quyền hạn người dùng."""
    return await ticket_service.list_tickets(
        current_user=current_user,
        status=status,
        category_id=category_id,
        department_id=department_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{id}", response_model=TicketResponse)
async def get_ticket(
    current_user: CurrentUserDep,
    id: uuid.UUID,
    ticket_service: TicketServiceDep,
) -> TicketResponse:
    """Xem chi tiết phiếu hỗ trợ kèm toàn bộ lịch sử trạng thái và kết quả phân loại AI."""
    return await ticket_service.get_ticket(id, current_user)

