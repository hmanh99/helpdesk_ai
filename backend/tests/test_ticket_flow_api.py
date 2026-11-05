import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.fake_client import FakeLLMClient
from app.ai.schemas import ClassificationResult
from app.api.deps import get_llm_client
from app.main import app
from app.models.category import Category
from app.models.department import Department
from app.models.enums import Priority
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
async def cat_it(db: AsyncSession, dept_a: Department) -> Category:
    cat = Category(
        name="Hạ tầng CNTT",
        description="Sự cố mạng, máy tính, wifi",
        department_id=dept_a.id,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@pytest.fixture
async def cat_hr(db: AsyncSession, dept_b: Department) -> Category:
    cat = Category(
        name="Hồ sơ nhân sự",
        description="Hồ sơ tuyển dụng, bảo hiểm",
        department_id=dept_b.id,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@pytest.mark.asyncio
async def test_user_create_ticket_with_explicit_category(
    client: AsyncClient,
    student_user: AppUser,
    cat_it: Category,
    dept_a: Department,
) -> None:
    headers = auth_headers_for(student_user)
    payload = {
        "title": "Hỏng chuột máy tính phòng lab 4",
        "description": "Chuột quang bị đứt dây không sáng đèn",
        "category_id": str(cat_it.id),
        "priority": "LOW",
    }
    response = await client.post("/api/v1/tickets", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["category_id"] == str(cat_it.id)
    assert data["department_id"] == str(dept_a.id)
    assert data["department_name"] == dept_a.name
    assert data["status"] == "TRIAGED"
    assert len(data["histories"]) >= 2
    assert data["classification"]["confidence_score"] == 1.0


@pytest.mark.asyncio
async def test_user_create_ticket_auto_routed_high_confidence(
    client: AsyncClient,
    student_user: AppUser,
    cat_it: Category,
    dept_a: Department,
) -> None:
    headers = auth_headers_for(student_user)
    fake_llm.queue_json(ClassificationResult(
        category_id=str(cat_it.id),
        priority=Priority.HIGH,
        confidence=0.92,
        reason="Sự cố liên quan hạ tầng mạng phòng máy",
    ))

    payload = {
        "title": "Mất mạng toàn bộ dãy nhà C",
        "description": "Switch tầng 2 không sáng đèn cổng uplink",
    }
    response = await client.post("/api/v1/tickets", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["category_id"] == str(cat_it.id)
    assert data["department_id"] == str(dept_a.id)
    assert data["status"] == "TRIAGED"
    assert data["classification"]["confidence_score"] == 0.92


@pytest.mark.asyncio
async def test_user_create_ticket_low_confidence_remains_new(
    client: AsyncClient,
    student_user: AppUser,
    cat_it: Category,
) -> None:
    headers = auth_headers_for(student_user)
    fake_llm.queue_json(ClassificationResult(
        category_id=str(cat_it.id),
        priority=Priority.LOW,
        confidence=0.45,  # Dưới ngưỡng 0.6
        reason="Nội dung không rõ ràng",
    ))

    payload = {
        "title": "Em muốn hỏi chút",
        "description": "Thầy cho em hỏi lịch làm việc hôm nay thế nào",
    }
    response = await client.post("/api/v1/tickets", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "NEW"
    assert data["department_id"] is None


@pytest.mark.asyncio
async def test_ticket_visibility_by_role(
    client: AsyncClient,
    student_user: AppUser,
    staff_user: AppUser,
    admin_user: AppUser,
    tech_user_a: AppUser,
    cat_it: Category,
    cat_hr: Category,
) -> None:
    # 1. Student tạo ticket CNTT (Dept A)
    res1 = await client.post(
        "/api/v1/tickets",
        json={"title": "Ticket Student", "description": "Desc 1", "category_id": str(cat_it.id)},
        headers=auth_headers_for(student_user),
    )
    t1_id = res1.json()["id"]

    # 2. Staff tạo ticket Nhân sự (Dept B)
    res2 = await client.post(
        "/api/v1/tickets",
        json={"title": "Ticket Staff", "description": "Desc 2", "category_id": str(cat_hr.id)},
        headers=auth_headers_for(staff_user),
    )
    t2_id = res2.json()["id"]

    # Student chỉ thấy Ticket của mình
    st_list = await client.get("/api/v1/tickets", headers=auth_headers_for(student_user))
    assert st_list.status_code == 200
    st_ids = [t["id"] for t in st_list.json()]
    assert t1_id in st_ids
    assert t2_id not in st_ids

    # Technician Dept A chỉ thấy Ticket thuộc Dept A
    tech_list = await client.get("/api/v1/tickets", headers=auth_headers_for(tech_user_a))
    assert tech_list.status_code == 200
    tech_ids = [t["id"] for t in tech_list.json()]
    assert t1_id in tech_ids
    assert t2_id not in tech_ids

    # Admin thấy tất cả
    admin_list = await client.get("/api/v1/tickets", headers=auth_headers_for(admin_user))
    assert admin_list.status_code == 200
    adm_ids = [t["id"] for t in admin_list.json()]
    assert t1_id in adm_ids
    assert t2_id in adm_ids

