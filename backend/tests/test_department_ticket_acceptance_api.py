import io
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.fake_client import FakeLLMClient
from app.api.deps import get_llm_client
from app.main import app
from app.models.category import Category
from app.models.department import Department
from app.models.user import AppUser
from tests.conftest import auth_headers_for

fake_llm = FakeLLMClient()


@pytest.fixture(autouse=True)
def override_llm() -> None:
    fake_llm.preset_json_responses.clear()
    fake_llm.preset_text_responses.clear()
    fake_llm.calls.clear()
    app.dependency_overrides[get_llm_client] = lambda: fake_llm
    yield
    app.dependency_overrides.pop(get_llm_client, None)


@pytest.fixture
async def sample_cat_a(db: AsyncSession, dept_a: Department) -> Category:
    cat = Category(
        name="Hỗ trợ Kỹ thuật CNTT",
        description="Mạng, máy tính, tài khoản",
        department_id=dept_a.id,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@pytest.fixture
async def sample_cat_b(db: AsyncSession, dept_b: Department) -> Category:
    cat = Category(
        name="Phòng CTSV Học Bổng",
        description="Thủ tục học bổng",
        department_id=dept_b.id,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@pytest.mark.asyncio
async def test_technician_accept_ticket_flow(
    client: AsyncClient,
    student_user: AppUser,
    tech_user_a: AppUser,
    sample_cat_a: Category,
) -> None:
    # 1. Sinh viên tạo phiếu hỗ trợ gửi tới phòng ban A
    create_res = await client.post(
        "/api/v1/tickets",
        json={
            "title": "Mất kết nối mạng tại KTX",
            "description": "Không kết nối được wifi phòng 302",
            "category_id": str(sample_cat_a.id),
        },
        headers=auth_headers_for(student_user),
    )
    assert create_res.status_code == 201
    ticket_id = create_res.json()["id"]
    assert create_res.json()["status"] == "TRIAGED"
    assert create_res.json()["assignee_id"] is None

    # 2. Kỹ thuật viên Phòng A tiếp nhận phiếu
    tech_headers = auth_headers_for(tech_user_a)
    accept_res = await client.post(
        f"/api/v1/tickets/{ticket_id}/accept",
        json={"note": "Kỹ thuật viên đã nhận xử lý"},
        headers=tech_headers,
    )
    assert accept_res.status_code == 200
    accept_data = accept_res.json()
    assert accept_data["assignee_id"] == str(tech_user_a.id)
    assert accept_data["assignee_name"] == tech_user_a.full_name
    assert accept_data["status"] == "IN_PROGRESS"

    # Kiểm tra lịch sử
    histories = accept_data["histories"]
    latest_hist = histories[-1]
    assert latest_hist["new_status"] == "IN_PROGRESS"
    assert latest_hist["changed_by"] == str(tech_user_a.id)
    assert "tiếp nhận" in latest_hist["note"].lower() or "xử lý" in latest_hist["note"].lower()


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_accept_ticket(
    client: AsyncClient,
    student_user: AppUser,
    dept_manager_b: AppUser,
    sample_cat_a: Category,
) -> None:
    # Tạo ticket phòng A
    create_res = await client.post(
        "/api/v1/tickets",
        json={
            "title": "Sự cố phòng máy A",
            "description": "Màn hình xanh",
            "category_id": str(sample_cat_a.id),
        },
        headers=auth_headers_for(student_user),
    )
    ticket_id = create_res.json()["id"]

    # Student không được quyền accept ticket
    st_res = await client.post(
        f"/api/v1/tickets/{ticket_id}/accept",
        headers=auth_headers_for(student_user),
    )
    assert st_res.status_code == 403

    # Manager phòng B không được quyền accept ticket phòng A
    mgr_b_res = await client.post(
        f"/api/v1/tickets/{ticket_id}/accept",
        headers=auth_headers_for(dept_manager_b),
    )
    assert mgr_b_res.status_code == 403


@pytest.mark.asyncio
async def test_dept_manager_assign_technician_flow(
    client: AsyncClient,
    student_user: AppUser,
    dept_manager_a: AppUser,
    tech_user_a: AppUser,
    dept_manager_b: AppUser,
    sample_cat_a: Category,
) -> None:
    # Tạo ticket phòng A
    create_res = await client.post(
        "/api/v1/tickets",
        json={
            "title": "Cần cấu hình router",
            "description": "Thiết bị mới nhập về",
            "category_id": str(sample_cat_a.id),
        },
        headers=auth_headers_for(student_user),
    )
    ticket_id = create_res.json()["id"]

    # Manager phòng A phân công cho Tech A
    assign_res = await client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={
            "assignee_id": str(tech_user_a.id),
            "note": "Giao đồng chí A xử lý trước 16h",
        },
        headers=auth_headers_for(dept_manager_a),
    )
    assert assign_res.status_code == 200
    assign_data = assign_res.json()
    assert assign_data["assignee_id"] == str(tech_user_a.id)
    assert assign_data["status"] == "ASSIGNED"

    # Manager cố phân công cho người thuộc phòng ban khác -> 400 Bad Request
    invalid_assign = await client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={"assignee_id": str(dept_manager_b.id)},
        headers=auth_headers_for(dept_manager_a),
    )
    assert invalid_assign.status_code == 400


@pytest.mark.asyncio
async def test_update_ticket_status_and_resolution(
    client: AsyncClient,
    student_user: AppUser,
    tech_user_a: AppUser,
    sample_cat_a: Category,
) -> None:
    # 1. Tạo ticket
    create_res = await client.post(
        "/api/v1/tickets",
        json={
            "title": "Cần mở port firewall",
            "description": "Port 8000 bị chặn",
            "category_id": str(sample_cat_a.id),
        },
        headers=auth_headers_for(student_user),
    )
    ticket_id = create_res.json()["id"]

    # 2. Cập nhật sang RESOLVED
    tech_headers = auth_headers_for(tech_user_a)
    res_status = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={
            "status": "RESOLVED",
            "note": "Đã mở rule firewall cho IP phòng lab, sinh viên kiểm tra lại.",
        },
        headers=tech_headers,
    )
    assert res_status.status_code == 200
    data = res_status.json()
    assert data["status"] == "RESOLVED"
    assert data["resolved_at"] is not None


@pytest.mark.asyncio
async def test_ticket_comments_public_and_internal(
    client: AsyncClient,
    student_user: AppUser,
    tech_user_a: AppUser,
    dept_manager_a: AppUser,
    sample_cat_a: Category,
) -> None:
    # 1. Tạo ticket
    create_res = await client.post(
        "/api/v1/tickets",
        json={
            "title": "Quên mật khẩu cổng sinh viên",
            "description": "Em không đăng nhập được",
            "category_id": str(sample_cat_a.id),
        },
        headers=auth_headers_for(student_user),
    )
    ticket_id = create_res.json()["id"]

    # 2. Kỹ thuật viên gửi phản hồi công khai cho sinh viên
    tech_headers = auth_headers_for(tech_user_a)
    pub_res = await client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "content": "Chào em, mật khẩu tạm thời đã được reset về ngày sinh của em. Em đăng nhập và đổi lại nhé.",
            "is_internal": False,
        },
        headers=tech_headers,
    )
    assert pub_res.status_code == 201
    assert pub_res.json()["is_internal"] is False
    assert pub_res.json()["author_name"] == tech_user_a.full_name

    # 3. Kỹ thuật viên lưu ghi chú nội bộ (sinh viên không thấy)
    internal_res = await client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "content": "Ghi chú nội bộ: Tài khoản này đã reset 2 lần trong tuần.",
            "is_internal": True,
        },
        headers=tech_headers,
    )
    assert internal_res.status_code == 201

    # 4. Sinh viên xem danh sách comments -> CHỈ thấy 1 comment công khai
    st_headers = auth_headers_for(student_user)
    st_comments = await client.get(f"/api/v1/tickets/{ticket_id}/comments", headers=st_headers)
    assert st_comments.status_code == 200
    st_list = st_comments.json()
    assert len(st_list) == 1
    assert st_list[0]["is_internal"] is False
    assert "reset về ngày sinh" in st_list[0]["content"]

    # 5. Trưởng phòng / KTV xem danh sách comments -> thấy cả 2 comments
    mgr_comments = await client.get(
        f"/api/v1/tickets/{ticket_id}/comments", headers=auth_headers_for(dept_manager_a)
    )
    assert mgr_comments.status_code == 200
    assert len(mgr_comments.json()) == 2

    # 6. Sinh viên cố gắng tạo comment nội bộ -> 403 Forbidden
    st_forbidden = await client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={"content": "Hacker cố tạo note nội bộ", "is_internal": True},
        headers=st_headers,
    )
    assert st_forbidden.status_code == 403

