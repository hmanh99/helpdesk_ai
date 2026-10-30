import uuid
from typing import Any, Optional, Protocol, runtime_checkable

from app.models.user import AppUser, UserRole


@runtime_checkable
class TicketLike(Protocol):
    id: Any
    requester_id: Any
    assignee_id: Optional[Any]
    department_id: Optional[Any]


@runtime_checkable
class AgentActionLike(Protocol):
    department_id: Optional[Any]


def can_create_ticket(user: AppUser) -> bool:
    """Kiểm tra quyền tạo ticket: STUDENT, STAFF, TECHNICIAN, DEPT_MANAGER, ADMIN đều có quyền."""
    if not user.is_active:
        return False
    return user.role in {
        UserRole.STUDENT,
        UserRole.STAFF,
        UserRole.TECHNICIAN,
        UserRole.DEPT_MANAGER,
        UserRole.ADMIN,
    }


def can_view_ticket(user: AppUser, ticket: Any) -> bool:
    """Kiểm tra người dùng có quyền xem/theo dõi ticket theo quy tắc dữ liệu:
    - Người dùng xem được ticket do chính mình tạo (requester_id).
    - TECHNICIAN xem được ticket được phân công hoặc thuộc phòng ban của mình.
    - DEPT_MANAGER xem được ticket thuộc phòng ban của mình hoặc do mình tạo.
    - ADMIN có quyền xem tất cả ticket.
    """
    if not user.is_active:
        return False

    if user.role == UserRole.ADMIN:
        return True

    requester_id = getattr(ticket, "requester_id", None)
    assignee_id = getattr(ticket, "assignee_id", None)
    ticket_dept_id = getattr(ticket, "department_id", None)

    u_id_str = str(user.id) if user.id else None
    u_dept_str = str(user.department_id) if user.department_id else None

    if requester_id is not None and str(requester_id) == u_id_str:
        return True

    if user.role == UserRole.TECHNICIAN:
        if assignee_id is not None and str(assignee_id) == u_id_str:
            return True
        if (
            ticket_dept_id is not None
            and u_dept_str is not None
            and str(ticket_dept_id) == u_dept_str
        ):
            return True
        return False

    if user.role == UserRole.DEPT_MANAGER:
        if (
            ticket_dept_id is not None
            and u_dept_str is not None
            and str(ticket_dept_id) == u_dept_str
        ):
            return True
        return False

    return False


# can_track_ticket đồng nghĩa với can_view_ticket
can_track_ticket = can_view_ticket


def can_accept_or_update_ticket(user: AppUser, ticket: Any) -> bool:
    """Kiểm tra quyền tiếp nhận hoặc cập nhật trạng thái ticket:
    - ADMIN: Toàn quyền.
    - DEPT_MANAGER: Ticket thuộc phòng ban của mình.
    - TECHNICIAN: Ticket được phân công hoặc thuộc phòng ban của mình.
    """
    if not user.is_active:
        return False

    if user.role == UserRole.ADMIN:
        return True

    if user.role not in {UserRole.TECHNICIAN, UserRole.DEPT_MANAGER}:
        return False

    assignee_id = getattr(ticket, "assignee_id", None)
    ticket_dept_id = getattr(ticket, "department_id", None)

    u_id_str = str(user.id) if user.id else None
    u_dept_str = str(user.department_id) if user.department_id else None

    if user.role == UserRole.DEPT_MANAGER:
        return (
            ticket_dept_id is not None
            and u_dept_str is not None
            and str(ticket_dept_id) == u_dept_str
        )

    if user.role == UserRole.TECHNICIAN:
        if assignee_id is not None and str(assignee_id) == u_id_str:
            return True
        if (
            ticket_dept_id is not None
            and u_dept_str is not None
            and str(ticket_dept_id) == u_dept_str
        ):
            return True
        return False

    return False


def can_reassign_ticket(user: AppUser, ticket: Any) -> bool:
    """Kiểm tra quyền phân công lại ticket: DEPT_MANAGER (trong phòng ban mình) hoặc ADMIN."""
    if not user.is_active:
        return False

    if user.role == UserRole.ADMIN:
        return True

    if user.role != UserRole.DEPT_MANAGER:
        return False

    ticket_dept_id = getattr(ticket, "department_id", None)
    u_dept_str = str(user.department_id) if user.department_id else None

    return (
        ticket_dept_id is not None
        and u_dept_str is not None
        and str(ticket_dept_id) == u_dept_str
    )


def can_approve_agent_action(user: AppUser, action_or_dept_id: Any) -> bool:
    """Kiểm tra quyền phê duyệt hành động của AI Agent: DEPT_MANAGER (cho phòng ban mình) hoặc ADMIN."""
    if not user.is_active:
        return False

    if user.role == UserRole.ADMIN:
        return True

    if user.role != UserRole.DEPT_MANAGER:
        return False

    dept_id = (
        getattr(action_or_dept_id, "department_id", None)
        if hasattr(action_or_dept_id, "department_id")
        else action_or_dept_id
    )
    u_dept_str = str(user.department_id) if user.department_id else None

    return dept_id is not None and u_dept_str is not None and str(dept_id) == u_dept_str


def can_manage_categories(user: AppUser) -> bool:
    """Kiểm tra quyền quản lý danh mục: Chỉ ADMIN."""
    return bool(user.is_active and user.role == UserRole.ADMIN)


def can_manage_knowledge(user: AppUser) -> bool:
    """Kiểm tra quyền quản lý cơ sở tri thức (Knowledge Base): Chỉ ADMIN."""
    return bool(user.is_active and user.role == UserRole.ADMIN)


def can_manage_users(user: AppUser) -> bool:
    """Kiểm tra quyền quản trị người dùng: Chỉ ADMIN."""
    return bool(user.is_active and user.role == UserRole.ADMIN)


def can_view_internal_comments(user: AppUser, ticket: Any = None) -> bool:
    """Kiểm tra quyền xem bình luận nội bộ: TECHNICIAN, DEPT_MANAGER, ADMIN.
    Nếu có ticket cụ thể thì người dùng cũng phải có quyền xem ticket đó.
    """
    if not user.is_active:
        return False

    if user.role not in {UserRole.TECHNICIAN, UserRole.DEPT_MANAGER, UserRole.ADMIN}:
        return False

    if ticket is not None:
        return can_view_ticket(user, ticket)

    return True


def can_manage_department(user: AppUser, department_id: uuid.UUID | str) -> bool:
    """Kiểm tra quyền quản lý hoặc xem danh sách thành viên phòng ban:
    - ADMIN: Toàn quyền với mọi phòng ban.
    - DEPT_MANAGER: Chỉ xem/quản lý phòng ban của mình.
    """
    if not user.is_active:
        return False

    if user.role == UserRole.ADMIN:
        return True

    if user.role == UserRole.DEPT_MANAGER:
        return bool(
            user.department_id
            and str(user.department_id) == str(department_id)
        )

    return False


can_view_department_members = can_manage_department


def can_view_user(current_user: AppUser, target_user: Any) -> bool:
    """Kiểm tra quyền xem hoặc thao tác với thông tin người dùng:
    - ADMIN: Toàn quyền.
    - Người dùng hiện tại: Chỉ được xem/thao tác trên tài khoản của chính mình.
    - Các trường hợp khác: Bị từ chối.
    """
    if not current_user.is_active:
        return False

    if current_user.role == UserRole.ADMIN:
        return True

    target_id = getattr(target_user, "id", target_user)
    if current_user.id is not None and target_id is not None:
        return str(current_user.id) == str(target_id)

    return False


can_modify_user = can_view_user
can_access_user_data = can_view_user
can_delete_user = can_view_user


def resolve_user_list_department_scope(
    current_user: AppUser,
    requested_department_id: Optional[uuid.UUID],
) -> tuple[bool, Optional[uuid.UUID]]:
    """Xác định phạm vi lọc phòng ban khi xem danh sách:
    - ADMIN: Không giới hạn, sử dụng requested_department_id.
    - DEPT_MANAGER: Chỉ được xem phòng ban của mình.
    - Khác: Không có quyền.
    """
    if not current_user.is_active:
        return False, None

    if current_user.role == UserRole.ADMIN:
        return True, requested_department_id

    if current_user.role == UserRole.DEPT_MANAGER:
        if current_user.department_id is None:
            return False, None
        if (
            requested_department_id is not None
            and requested_department_id != current_user.department_id
        ):
            return False, None
        return True, current_user.department_id

    return False, None
