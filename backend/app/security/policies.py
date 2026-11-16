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


def can_edit_ticket(user: AppUser, ticket: Any) -> bool:
    """Kiểm tra quyền chỉnh sửa ticket (tiêu đề, nội dung, danh mục, ưu tiên):
    - ADMIN: Toàn quyền.
    - Người gửi yêu cầu (requester - sinh viên): Có quyền sửa phiếu do chính mình tạo.
    """
    if not user.is_active:
        return False

    if user.role == UserRole.ADMIN:
        return True

    requester_id = getattr(ticket, "requester_id", None)
    return bool(requester_id and user.id and str(requester_id) == str(user.id))


def can_delete_ticket(user: AppUser, ticket: Any) -> bool:
    """Kiểm tra quyền xóa ticket:
    - ADMIN: Toàn quyền.
    - Người gửi yêu cầu (requester - sinh viên): Có quyền xóa phiếu do chính mình tạo.
    """
    if not user.is_active:
        return False

    if user.role == UserRole.ADMIN:
        return True

    requester_id = getattr(ticket, "requester_id", None)
    return bool(requester_id and user.id and str(requester_id) == str(user.id))


def can_cancel_ticket(user: AppUser, ticket: Any) -> bool:
    """Kiểm tra quyền hủy ticket:
    - ADMIN, DEPT_MANAGER, TECHNICIAN có quyền cập nhật ticket.
    - Người gửi yêu cầu (requester - sinh viên) có quyền hủy phiếu do mình tạo.
    """
    if not user.is_active:
        return False

    if can_accept_or_update_ticket(user, ticket):
        return True

    requester_id = getattr(ticket, "requester_id", None)
    return bool(requester_id and user.id and str(requester_id) == str(user.id))


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


def can_manage_categories(
    user: AppUser, target_dept_id: Optional[uuid.UUID | str] = None
) -> bool:
    """Kiểm tra quyền quản lý danh mục:
    - ADMIN: Toàn quyền trên mọi phòng ban.
    - DEPT_MANAGER: Có quyền thêm/sửa/xóa danh mục trong phòng ban của mình.
    - Các vai trò khác: Không có quyền.
    """
    if not user.is_active:
        return False

    if user.role == UserRole.ADMIN:
        return True

    if user.role == UserRole.DEPT_MANAGER:
        if target_dept_id is None:
            return True
        if user.department_id is None:
            return False
        return str(user.department_id) == str(target_dept_id)

    return False


def can_manage_knowledge(
    user: AppUser, target_dept_id: Optional[uuid.UUID | str] = None
) -> bool:
    """Kiểm tra quyền quản lý kho tri thức (Knowledge Base):
    - ADMIN: Toàn quyền trên mọi tài liệu/danh mục.
    - DEPT_MANAGER: Có quyền thêm/sửa tài liệu. Nếu chỉ định target_dept_id,
      chỉ được phép khi target_dept_id trùng với department_id của mình.
    - Các vai trò khác: Không có quyền.
    """
    if not user.is_active:
        return False

    if user.role == UserRole.ADMIN:
        return True

    if user.role == UserRole.DEPT_MANAGER:
        if target_dept_id is None:
            return True
        if user.department_id is None:
            return False
        return str(user.department_id) == str(target_dept_id)

    return False


def is_hr_department(department: Any) -> bool:
    """Kiểm tra phòng ban có phải là bộ phận Nhân sự / Tổ chức cán bộ hay không."""
    if department is None:
        return False
    name = getattr(department, "name", "") or ""
    name_clean = name.strip().lower()
    keywords = ["nhân sự", "nhan su", "tổ chức", "to chuc", "tccb", "hr", "human resource"]
    return any(kw in name_clean for kw in keywords)


def is_hr_manager(user: AppUser) -> bool:
    """Kiểm tra người dùng có phải là Trưởng bộ phận Nhân sự hay không."""
    if not user.is_active or user.role != UserRole.DEPT_MANAGER:
        return False
    return is_hr_department(user.department)


def can_manage_users(user: AppUser) -> bool:
    """Kiểm tra quyền quản trị người dùng: ADMIN hoặc Trưởng bộ phận nhân sự."""
    return bool(user.is_active and (user.role == UserRole.ADMIN or is_hr_manager(user)))


def can_edit_user_role(
    actor: AppUser,
    target_user: Any,
    new_role: Optional[UserRole] = None,
) -> bool:
    """Kiểm tra quyền thay đổi chức vụ / vai trò của người dùng:
    - ADMIN: Toàn quyền sửa chức vụ của mọi người dùng.
    - Trưởng bộ phận nhân sự (HR Manager): Được phép sửa chức vụ của người dùng khác.
      (Ràng buộc an toàn: Không được sửa tài khoản ADMIN, không được phong ADMIN).
    """
    if not actor.is_active:
        return False

    if actor.role == UserRole.ADMIN:
        return True

    if is_hr_manager(actor):
        target_role = getattr(target_user, "role", None)
        # Không được phép hạ quyền hoặc sửa tài khoản ADMIN
        if target_role == UserRole.ADMIN:
            return False
        # Không được phép nâng người dùng lên quyền ADMIN
        if new_role == UserRole.ADMIN:
            return False
        return True

    return False


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


# can_manage_category alias cho can_manage_categories
can_manage_category = can_manage_categories


def can_access_chat_session(user: AppUser, session: Any) -> bool:
    """Người dùng chỉ truy cập phiên chat của chính mình; ADMIN có quyền truy cập tất cả."""
    if not user.is_active:
        return False
    if user.role == UserRole.ADMIN:
        return True
    session_user_id = getattr(session, "user_id", None)
    return bool(session_user_id and str(session_user_id) == str(user.id))
