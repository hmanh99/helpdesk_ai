import io
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


@pytest.fixture(autouse=True)
def override_llm() -> None:
    fake = FakeLLMClient()
    app.dependency_overrides[get_llm_client] = lambda: fake
    yield
    app.dependency_overrides.pop(get_llm_client, None)


@pytest.fixture
async def sample_category(db: AsyncSession, dept_a: Department) -> Category:
    cat = Category(name="Mạng Wifi KTX", department_id=dept_a.id)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@pytest.mark.asyncio
async def test_student_cannot_access_knowledge_api(
    client: AsyncClient,
    student_user: AppUser,
) -> None:
    headers = auth_headers_for(student_user)
    res = await client.get("/api/v1/knowledge", headers=headers)
    assert res.status_code == 403

    post_res = await client.post(
        "/api/v1/knowledge",
        json={"title": "Test", "content": "Sample"},
        headers=headers,
    )
    assert post_res.status_code == 403


@pytest.mark.asyncio
async def test_admin_create_text_and_publish(
    client: AsyncClient,
    admin_user: AppUser,
    sample_category: Category,
) -> None:
    headers = auth_headers_for(admin_user)
    payload = {
        "title": "Hướng dẫn kết nối Wifi KTX",
        "category_id": str(sample_category.id),
        "content": "Để kết nối wifi KTX, sinh viên chọn mạng KTX_SinhVien, nhập mật khẩu chung và đăng nhập bằng email trường.",
        "source_url": "https://helpdesk.edu.vn/wifi",
    }
    create_res = await client.post("/api/v1/knowledge", json=payload, headers=headers)
    assert create_res.status_code == 201
    doc_data = create_res.json()
    doc_id = doc_data["id"]
    assert doc_data["title"] == "Hướng dẫn kết nối Wifi KTX"
    assert doc_data["processing_status"] == "READY"
    assert doc_data["is_published"] is False
    assert doc_data["chunk_count"] >= 1

    # Publish
    pub_res = await client.post(f"/api/v1/knowledge/{doc_id}/publish", headers=headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["is_published"] is True

    # Unpublish
    unpub_res = await client.post(f"/api/v1/knowledge/{doc_id}/unpublish", headers=headers)
    assert unpub_res.status_code == 200
    assert unpub_res.json()["is_published"] is False

    # Delete
    del_res = await client.delete(f"/api/v1/knowledge/{doc_id}", headers=headers)
    assert del_res.status_code == 204


@pytest.mark.asyncio
async def test_admin_upload_file(
    client: AsyncClient,
    admin_user: AppUser,
    sample_category: Category,
) -> None:
    headers = auth_headers_for(admin_user)
    file_content = b"# Quy che cap hoc bong\n\nSinh vien can dat diem GPA >= 3.2 de xet hoc bong."
    files = {"file": ("hoc_bong.md", io.BytesIO(file_content), "text/markdown")}
    data = {
        "title": "Tài liệu học bổng",
        "category_id": str(sample_category.id),
    }
    upload_res = await client.post(
        "/api/v1/knowledge/upload",
        files=files,
        data=data,
        headers=headers,
    )
    assert upload_res.status_code == 201
    res_data = upload_res.json()
    assert res_data["title"] == "Tài liệu học bổng"
    assert res_data["processing_status"] == "READY"
    assert "GPA >= 3.2" in res_data["content"]
    assert res_data["chunk_count"] >= 1


@pytest.mark.asyncio
async def test_admin_upload_unsupported_extension_fails(
    client: AsyncClient,
    admin_user: AppUser,
) -> None:
    headers = auth_headers_for(admin_user)
    files = {"file": ("malicious.exe", io.BytesIO(b"MZ..."), "application/octet-stream")}
    upload_res = await client.post(
        "/api/v1/knowledge/upload",
        files=files,
        headers=headers,
    )
    assert upload_res.status_code == 400


@pytest.mark.asyncio
async def test_technician_and_staff_cannot_manage_knowledge(
    client: AsyncClient,
    staff_user: AppUser,
    tech_user_a: AppUser,
    sample_category: Category,
) -> None:
    for user in [staff_user, tech_user_a]:
        headers = auth_headers_for(user)
        list_res = await client.get("/api/v1/knowledge", headers=headers)
        assert list_res.status_code == 403

        files = {"file": ("guide.md", io.BytesIO(b"# Guide\n\nContent"), "text/markdown")}
        data = {"title": "Forbidden Upload", "category_id": str(sample_category.id)}
        upload_res = await client.post(
            "/api/v1/knowledge/upload",
            files=files,
            data=data,
            headers=headers,
        )
        assert upload_res.status_code == 403


@pytest.mark.asyncio
async def test_dept_manager_upload_file_auto_chunking_and_chunks_endpoints(
    client: AsyncClient,
    dept_manager_a: AppUser,
    sample_category: Category,
) -> None:
    headers = auth_headers_for(dept_manager_a)
    markdown_content = (
        "# Hướng dẫn cấu hình VPN trường đại học\n\n"
        "Bước 1: Tải phần mềm OpenVPN Client từ trang chủ.\n\n"
        "Bước 2: Import file cấu hình vpn_config.ovpn do trung tâm CNTT cung cấp.\n\n"
        "Bước 3: Nhập tài khoản và mật khẩu email của trường để kết nối."
    ).encode("utf-8")

    files = {"file": ("vpn_guide.md", io.BytesIO(markdown_content), "text/markdown")}
    data = {
        "title": "Hướng dẫn VPN Nội bộ",
        "category_id": str(sample_category.id),
        "source_url": "https://helpdesk.edu.vn/vpn",
        "is_published": "true",
    }

    upload_res = await client.post(
        "/api/v1/knowledge/upload",
        files=files,
        data=data,
        headers=headers,
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    assert doc_data["title"] == "Hướng dẫn VPN Nội bộ"
    assert doc_data["processing_status"] == "READY"
    assert doc_data["is_published"] is True
    assert doc_data["chunk_count"] >= 1
    assert doc_data["created_by"] == str(dept_manager_a.id)
    doc_id = doc_data["id"]

    # 1. Kiểm tra GET /api/v1/knowledge/{id} trả về tài liệu kèm danh sách chunks
    detail_res = await client.get(f"/api/v1/knowledge/{doc_id}", headers=headers)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert "chunks" in detail_data
    assert len(detail_data["chunks"]) >= 1
    first_chunk = detail_data["chunks"][0]
    assert first_chunk["chunk_index"] == 0
    assert "Hướng dẫn cấu hình VPN" in first_chunk["content"]
    assert first_chunk["token_count"] is not None and first_chunk["token_count"] > 0

    # 2. Kiểm tra GET /api/v1/knowledge/{id}/chunks
    chunks_res = await client.get(f"/api/v1/knowledge/{doc_id}/chunks", headers=headers)
    assert chunks_res.status_code == 200
    chunks_list = chunks_res.json()
    assert isinstance(chunks_list, list)
    assert len(chunks_list) == len(detail_data["chunks"])
    assert chunks_list[0]["content"] == first_chunk["content"]


@pytest.mark.asyncio
async def test_dept_manager_scoped_to_own_department_category(
    client: AsyncClient,
    dept_b: Department,
    dept_manager_a: AppUser,
    admin_user: AppUser,
    db: AsyncSession,
) -> None:
    # Tạo danh mục thuộc Dept B
    cat_b = Category(name="Quy chế nhân sự", department_id=dept_b.id)
    db.add(cat_b)
    await db.commit()
    await db.refresh(cat_b)

    # Manager A (thuộc Dept A) cố gắng upload tài liệu vào danh mục Dept B -> 403
    mgr_headers = auth_headers_for(dept_manager_a)
    files = {"file": ("nhan_su.txt", io.BytesIO(b"Noi dung quy che"), "text/plain")}
    data = {"title": "Quy che", "category_id": str(cat_b.id)}
    mgr_upload_res = await client.post(
        "/api/v1/knowledge/upload",
        files=files,
        data=data,
        headers=mgr_headers,
    )
    assert mgr_upload_res.status_code == 403
    assert "phòng ban" in mgr_upload_res.json()["detail"].lower() or "bộ phận" in mgr_upload_res.json()["detail"].lower()

    # Admin tải lên cùng danh mục Dept B -> Thành công 201
    admin_headers = auth_headers_for(admin_user)
    files_admin = {"file": ("nhan_su_admin.txt", io.BytesIO(b"Noi dung quy che hop le"), "text/plain")}
    admin_upload_res = await client.post(
        "/api/v1/knowledge/upload",
        files=files_admin,
        data=data,
        headers=admin_headers,
    )
    assert admin_upload_res.status_code == 201


@pytest.mark.asyncio
async def test_docx_upload_auto_chunking(
    client: AsyncClient,
    dept_manager_a: AppUser,
    sample_category: Category,
) -> None:
    import docx

    doc = docx.Document()
    doc.add_heading("Sổ tay sinh viên năm nhất", level=1)
    doc.add_paragraph("Chào mừng tân sinh viên đến với trường đại học.")
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Khoản mục"
    table.rows[0].cells[1].text = "Thời hạn"
    table.rows[1].cells[0].text = "Đăng ký học phần"
    table.rows[1].cells[1].text = "Tuần 1 học kỳ"

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)

    headers = auth_headers_for(dept_manager_a)
    files = {
        "file": (
            "so_tay.docx",
            bio,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    data = {
        "title": "Sổ tay sinh viên",
        "category_id": str(sample_category.id),
    }

    res = await client.post(
        "/api/v1/knowledge/upload",
        files=files,
        data=data,
        headers=headers,
    )
    assert res.status_code == 201
    data_res = res.json()
    assert data_res["processing_status"] == "READY"
    assert "Sổ tay sinh viên" in data_res["content"]
    assert "Đăng ký học phần" in data_res["content"]
    assert data_res["chunk_count"] >= 1


@pytest.mark.asyncio
async def test_upload_empty_file_fails_with_400(
    client: AsyncClient,
    admin_user: AppUser,
    sample_category: Category,
) -> None:
    headers = auth_headers_for(admin_user)
    files = {"file": ("empty.txt", io.BytesIO(b"   "), "text/plain")}
    data = {"title": "Empty", "category_id": str(sample_category.id)}
    res = await client.post(
        "/api/v1/knowledge/upload",
        files=files,
        data=data,
        headers=headers,
    )
    assert res.status_code == 400
    assert "Lỗi khi xử lý tài liệu" in res.json()["detail"]

