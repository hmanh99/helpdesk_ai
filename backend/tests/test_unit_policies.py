from dataclasses import dataclass
from typing import Optional
import uuid

import pytest

from app.models.user import AppUser, UserRole
from app.security.policies import (
    can_accept_or_update_ticket,
    can_approve_agent_action,
    can_create_ticket,
    can_manage_categories,
    can_manage_department,
    can_manage_knowledge,
    can_manage_users,
    can_reassign_ticket,
    can_track_ticket,
    can_view_department_members,
    can_view_internal_comments,
    can_view_ticket,
    can_view_user,
)


@dataclass
class MockTicket:
    id: uuid.UUID
    requester_id: uuid.UUID
    assignee_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None


@dataclass
class MockAgentAction:
    department_id: uuid.UUID


def create_user(
    role: UserRole,
    department_id: Optional[uuid.UUID] = None,
    is_active: bool = True,
) -> AppUser:
    return AppUser(
        id=uuid.uuid4(),
        email=f"{role.value.lower()}@example.com",
        full_name=f"User {role.value}",
        role=role,
        department_id=department_id,
        is_active=is_active,
        password_hash="mock_hash",
    )


def test_can_create_ticket() -> None:
    dept = uuid.uuid4()
    for role in UserRole:
        user = create_user(role=role, department_id=dept)
        assert can_create_ticket(user) is True

    inactive_user = create_user(role=UserRole.STUDENT, is_active=False)
    assert can_create_ticket(inactive_user) is False


def test_can_view_ticket_requester_rules() -> None:
    dept_a = uuid.uuid4()
    student = create_user(UserRole.STUDENT)
    other_student = create_user(UserRole.STUDENT)

    own_ticket = MockTicket(id=uuid.uuid4(), requester_id=student.id, department_id=dept_a)
    other_ticket = MockTicket(id=uuid.uuid4(), requester_id=other_student.id, department_id=dept_a)

    assert can_view_ticket(student, own_ticket) is True
    assert can_track_ticket(student, own_ticket) is True
    assert can_view_ticket(student, other_ticket) is False


def test_can_view_ticket_technician_rules() -> None:
    dept_a = uuid.uuid4()
    dept_b = uuid.uuid4()

    tech = create_user(UserRole.TECHNICIAN, department_id=dept_a)
    other_user = create_user(UserRole.STUDENT)

    # 1. Tech's own department ticket
    dept_ticket = MockTicket(id=uuid.uuid4(), requester_id=other_user.id, department_id=dept_a)
    assert can_view_ticket(tech, dept_ticket) is True

    # 2. Ticket assigned directly to tech (even if outside dept)
    assigned_ticket = MockTicket(
        id=uuid.uuid4(), requester_id=other_user.id, assignee_id=tech.id, department_id=dept_b
    )
    assert can_view_ticket(tech, assigned_ticket) is True

    # 3. Ticket requested by tech
    tech_requested = MockTicket(id=uuid.uuid4(), requester_id=tech.id, department_id=dept_b)
    assert can_view_ticket(tech, tech_requested) is True

    # 4. Other department, not assigned, not requested
    unrelated_ticket = MockTicket(id=uuid.uuid4(), requester_id=other_user.id, department_id=dept_b)
    assert can_view_ticket(tech, unrelated_ticket) is False


def test_can_view_ticket_dept_manager_and_admin_rules() -> None:
    dept_a = uuid.uuid4()
    dept_b = uuid.uuid4()
    manager = create_user(UserRole.DEPT_MANAGER, department_id=dept_a)
    admin = create_user(UserRole.ADMIN)
    other_user = create_user(UserRole.STUDENT)

    ticket_a = MockTicket(id=uuid.uuid4(), requester_id=other_user.id, department_id=dept_a)
    ticket_b = MockTicket(id=uuid.uuid4(), requester_id=other_user.id, department_id=dept_b)

    # DEPT_MANAGER can only view own department tickets
    assert can_view_ticket(manager, ticket_a) is True
    assert can_view_ticket(manager, ticket_b) is False

    # ADMIN can view all tickets unconditionally
    assert can_view_ticket(admin, ticket_a) is True
    assert can_view_ticket(admin, ticket_b) is True


def test_can_accept_or_update_ticket() -> None:
    dept_a = uuid.uuid4()
    dept_b = uuid.uuid4()

    student = create_user(UserRole.STUDENT)
    staff = create_user(UserRole.STAFF)
    tech = create_user(UserRole.TECHNICIAN, department_id=dept_a)
    manager = create_user(UserRole.DEPT_MANAGER, department_id=dept_a)
    admin = create_user(UserRole.ADMIN)

    ticket_a = MockTicket(id=uuid.uuid4(), requester_id=student.id, department_id=dept_a)
    ticket_b = MockTicket(id=uuid.uuid4(), requester_id=student.id, department_id=dept_b)

    # Student / Staff cannot accept/update tickets
    assert can_accept_or_update_ticket(student, ticket_a) is False
    assert can_accept_or_update_ticket(staff, ticket_a) is False

    # Tech can accept/update own dept tickets or assigned
    assert can_accept_or_update_ticket(tech, ticket_a) is True
    assert can_accept_or_update_ticket(tech, ticket_b) is False

    assigned_to_tech = MockTicket(
        id=uuid.uuid4(), requester_id=student.id, assignee_id=tech.id, department_id=dept_b
    )
    assert can_accept_or_update_ticket(tech, assigned_to_tech) is True

    # Manager can update own dept tickets
    assert can_accept_or_update_ticket(manager, ticket_a) is True
    assert can_accept_or_update_ticket(manager, ticket_b) is False

    # Admin is unrestricted
    assert can_accept_or_update_ticket(admin, ticket_a) is True
    assert can_accept_or_update_ticket(admin, ticket_b) is True


def test_can_reassign_ticket() -> None:
    dept_a = uuid.uuid4()
    dept_b = uuid.uuid4()

    student = create_user(UserRole.STUDENT)
    tech = create_user(UserRole.TECHNICIAN, department_id=dept_a)
    manager = create_user(UserRole.DEPT_MANAGER, department_id=dept_a)
    admin = create_user(UserRole.ADMIN)

    ticket_a = MockTicket(id=uuid.uuid4(), requester_id=student.id, department_id=dept_a)
    ticket_b = MockTicket(id=uuid.uuid4(), requester_id=student.id, department_id=dept_b)

    assert can_reassign_ticket(student, ticket_a) is False
    assert can_reassign_ticket(tech, ticket_a) is False

    # DEPT_MANAGER can only reassign own department tickets
    assert can_reassign_ticket(manager, ticket_a) is True
    assert can_reassign_ticket(manager, ticket_b) is False

    # ADMIN can reassign any ticket
    assert can_reassign_ticket(admin, ticket_a) is True
    assert can_reassign_ticket(admin, ticket_b) is True


def test_can_approve_agent_action() -> None:
    dept_a = uuid.uuid4()
    dept_b = uuid.uuid4()

    manager = create_user(UserRole.DEPT_MANAGER, department_id=dept_a)
    admin = create_user(UserRole.ADMIN)
    tech = create_user(UserRole.TECHNICIAN, department_id=dept_a)

    action_a = MockAgentAction(department_id=dept_a)
    action_b = MockAgentAction(department_id=dept_b)

    assert can_approve_agent_action(tech, action_a) is False

    assert can_approve_agent_action(manager, action_a) is True
    assert can_approve_agent_action(manager, action_b) is False

    assert can_approve_agent_action(admin, action_a) is True
    assert can_approve_agent_action(admin, action_b) is True


def test_admin_only_management_policies() -> None:
    admin = create_user(UserRole.ADMIN)
    for role in [UserRole.STUDENT, UserRole.STAFF, UserRole.TECHNICIAN, UserRole.DEPT_MANAGER]:
        other = create_user(role, department_id=uuid.uuid4())
        assert can_manage_categories(other) is False
        assert can_manage_knowledge(other) is False
        assert can_manage_users(other) is False

    assert can_manage_categories(admin) is True
    assert can_manage_knowledge(admin) is True
    assert can_manage_users(admin) is True


def test_can_view_internal_comments() -> None:
    dept_a = uuid.uuid4()
    dept_b = uuid.uuid4()

    student = create_user(UserRole.STUDENT)
    staff = create_user(UserRole.STAFF)
    tech = create_user(UserRole.TECHNICIAN, department_id=dept_a)
    manager = create_user(UserRole.DEPT_MANAGER, department_id=dept_a)
    admin = create_user(UserRole.ADMIN)

    ticket_a = MockTicket(id=uuid.uuid4(), requester_id=student.id, department_id=dept_a)
    ticket_b = MockTicket(id=uuid.uuid4(), requester_id=student.id, department_id=dept_b)

    # General check without ticket
    assert can_view_internal_comments(student) is False
    assert can_view_internal_comments(staff) is False
    assert can_view_internal_comments(tech) is True
    assert can_view_internal_comments(manager) is True
    assert can_view_internal_comments(admin) is True

    # With ticket context
    assert can_view_internal_comments(tech, ticket_a) is True
    assert can_view_internal_comments(tech, ticket_b) is False
    assert can_view_internal_comments(manager, ticket_a) is True
    assert can_view_internal_comments(manager, ticket_b) is False
    assert can_view_internal_comments(admin, ticket_b) is True


def test_can_manage_department_and_view_members() -> None:
    dept_a = uuid.uuid4()
    dept_b = uuid.uuid4()

    manager = create_user(UserRole.DEPT_MANAGER, department_id=dept_a)
    admin = create_user(UserRole.ADMIN)
    student = create_user(UserRole.STUDENT)

    assert can_manage_department(student, dept_a) is False
    assert can_view_department_members(student, dept_a) is False

    assert can_manage_department(manager, dept_a) is True
    assert can_manage_department(manager, dept_b) is False

    assert can_manage_department(admin, dept_a) is True
    assert can_manage_department(admin, dept_b) is True


def test_can_view_user_and_access_data() -> None:
    admin = create_user(UserRole.ADMIN)
    student1 = create_user(UserRole.STUDENT)
    student2 = create_user(UserRole.STUDENT)

    # Admin can view any user
    assert can_view_user(admin, student1) is True
    assert can_view_user(admin, student2) is True

    # User can view/access themselves
    assert can_view_user(student1, student1) is True
    assert can_view_user(student2, student2) is True

    # User cannot view/access other users
    assert can_view_user(student1, student2) is False
    assert can_view_user(student2, student1) is False


