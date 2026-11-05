import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.models.user import AppUser
from tests.conftest import auth_headers_for


@pytest.mark.asyncio
async def test_admin_create_category(
    client: AsyncClient,
    admin_user: AppUser,
    dept_a: Department,
) -> None:
    headers = auth_headers_for(admin_user)
    payload = {
        "name": "Mạng & Wifi",
        "department_id": str(dept_a.id),
        "description": "Hỗ trợ sự cố kết nối mạng và wifi",
        "sla_response_minutes": 30,
        "sla_resolve_minutes": 240,
        "is_active": True,
    }
    response = await client.post("/api/v1/categories", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Mạng & Wifi"
    assert data["department_id"] == str(dept_a.id)
    assert data["department_name"] == dept_a.name
    assert data["sla_response_minutes"] == 30


@pytest.mark.asyncio
async def test_student_cannot_create_category(
    client: AsyncClient,
    student_user: AppUser,
    dept_a: Department,
) -> None:
    headers = auth_headers_for(student_user)
    payload = {
        "name": "Mạng & Wifi",
        "department_id": str(dept_a.id),
    }
    response = await client.post("/api/v1/categories", json=payload, headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_category_name_fails(
    client: AsyncClient,
    admin_user: AppUser,
    dept_a: Department,
) -> None:
    headers = auth_headers_for(admin_user)
    payload = {
        "name": "Mạng & Wifi",
        "department_id": str(dept_a.id),
    }
    res1 = await client.post("/api/v1/categories", json=payload, headers=headers)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/categories", json=payload, headers=headers)
    assert res2.status_code == 400


@pytest.mark.asyncio
async def test_create_category_invalid_dept_fails(
    client: AsyncClient,
    admin_user: AppUser,
) -> None:
    headers = auth_headers_for(admin_user)
    payload = {
        "name": "Category With Fake Dept",
        "department_id": str(uuid.uuid4()),
    }
    res = await client.post("/api/v1/categories", json=payload, headers=headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_list_and_get_categories(
    client: AsyncClient,
    admin_user: AppUser,
    student_user: AppUser,
    dept_a: Department,
) -> None:
    headers_admin = auth_headers_for(admin_user)
    cat1 = await client.post(
        "/api/v1/categories",
        json={"name": "Cat 1", "department_id": str(dept_a.id)},
        headers=headers_admin,
    )
    assert cat1.status_code == 201
    cat1_id = cat1.json()["id"]

    # Student can list categories
    headers_student = auth_headers_for(student_user)
    list_res = await client.get("/api/v1/categories", headers=headers_student)
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1
    assert any(c["id"] == cat1_id for c in items)

    # Student can get specific category
    get_res = await client.get(f"/api/v1/categories/{cat1_id}", headers=headers_student)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Cat 1"


@pytest.mark.asyncio
async def test_admin_update_and_delete_category(
    client: AsyncClient,
    admin_user: AppUser,
    dept_a: Department,
) -> None:
    headers = auth_headers_for(admin_user)
    create_res = await client.post(
        "/api/v1/categories",
        json={"name": "To Update", "department_id": str(dept_a.id)},
        headers=headers,
    )
    cat_id = create_res.json()["id"]

    # Update
    update_res = await client.patch(
        f"/api/v1/categories/{cat_id}",
        json={"name": "Updated Cat", "sla_resolve_minutes": 720},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Updated Cat"
    assert update_res.json()["sla_resolve_minutes"] == 720

    # Delete
    del_res = await client.delete(f"/api/v1/categories/{cat_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify deleted
    get_res = await client.get(f"/api/v1/categories/{cat_id}", headers=headers)
    assert get_res.status_code == 404

