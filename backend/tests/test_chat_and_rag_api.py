import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.fake_client import FakeLLMClient
from app.ai.schemas import IntentResult, RagAnswerResult, TicketDraft
from app.api.deps import get_llm_client
from app.main import app
from app.models.category import Category
from app.models.department import Department
from app.models.enums import Intent, Priority
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, ProcessingStatus
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
async def published_kb_doc(db: AsyncSession, dept_a: Department) -> KnowledgeDocument:
    cat = Category(name="Mạng KTX", department_id=dept_a.id)
    db.add(cat)
    await db.flush()

    doc = KnowledgeDocument(
        title="Hướng dẫn Wifi KTX",
        content="Đăng nhập mạng KTX_SinhVien với mật khẩu sinhvien2026.",
        is_published=True,
        processing_status=ProcessingStatus.READY,
        category_id=cat.id,
    )
    db.add(doc)
    await db.flush()

    vec = fake_llm._deterministic_vector("Wifi KTX")
    chunk = KnowledgeChunk(
        document_id=doc.id,
        chunk_index=0,
        content=doc.content,
        embedding=vec,
    )
    db.add(chunk)
    await db.commit()
    await db.refresh(doc)
    return doc


@pytest.mark.asyncio
async def test_create_and_list_chat_sessions(
    client: AsyncClient,
    student_user: AppUser,
    staff_user: AppUser,
) -> None:
    headers_student = auth_headers_for(student_user)
    # 1. Tạo session
    res = await client.post("/api/v1/chat/sessions", headers=headers_student)
    assert res.status_code == 201
    session_id = res.json()["id"]

    # 2. List sessions
    list_res = await client.get("/api/v1/chat/sessions", headers=headers_student)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["id"] == session_id

    # 3. Staff không được xem session của student
    headers_staff = auth_headers_for(staff_user)
    get_res = await client.get(f"/api/v1/chat/sessions/{session_id}", headers=headers_staff)
    assert get_res.status_code == 403


@pytest.mark.asyncio
async def test_chat_flow_kb_question_with_rag(
    client: AsyncClient,
    student_user: AppUser,
    published_kb_doc: KnowledgeDocument,
) -> None:
    headers = auth_headers_for(student_user)
    sess_res = await client.post("/api/v1/chat/sessions", headers=headers)
    session_id = sess_res.json()["id"]

    # Thiết lập mock responses:
    # 1st call to generate_json -> IntentResult (KB_QUESTION)
    fake_llm.queue_json(IntentResult(
        intent=Intent.KB_QUESTION,
        category_id=str(published_kb_doc.category_id),
        confidence=0.95,
        reason="Hỏi về wifi KTX",
    ))
    # 2nd call to generate_json -> RagAnswerResult
    fake_llm.queue_json(RagAnswerResult(
        answer="Bạn kết nối vào mạng KTX_SinhVien và dùng mật khẩu sinhvien2026 [1].",
        used_chunk_indices=[1],
        can_resolve=True,
    ))

    send_res = await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "Làm sao để kết nối wifi KTX vậy bạn?"},
        headers=headers,
    )
    assert send_res.status_code == 200
    reply = send_res.json()
    assert reply["message"]["sender"] == "BOT"
    assert "sinhvien2026" in reply["message"]["content"]
    assert reply["suggest_ticket"] is False
    assert len(reply["message"]["sources"]) >= 1
    assert reply["message"]["sources"][0]["knowledge_document_id"] == str(published_kb_doc.id)


@pytest.mark.asyncio
async def test_chat_flow_needs_department_drafts_ticket(
    client: AsyncClient,
    student_user: AppUser,
    published_kb_doc: KnowledgeDocument,
) -> None:
    headers = auth_headers_for(student_user)
    sess_res = await client.post("/api/v1/chat/sessions", headers=headers)
    session_id = sess_res.json()["id"]

    # 1. Intent: NEEDS_DEPARTMENT
    fake_llm.queue_json(IntentResult(
        intent=Intent.NEEDS_DEPARTMENT,
        category_id=str(published_kb_doc.category_id),
        priority=Priority.HIGH,
        confidence=0.9,
        reason="Dây mạng KTX bị đứt cần thợ sửa",
    ))
    # 2. TicketDraft
    fake_llm.queue_json(TicketDraft(
        title="Đứt dây mạng phòng 302 KTX",
        description="Dây mạng bị chuột cắn đứt hoàn toàn, không có tín hiệu internet",
        category_id=str(published_kb_doc.category_id),
        priority=Priority.HIGH,
        reason="Sự cố vật lý cần kỹ thuật viên sửa chữa",
    ))

    send_res = await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "Dây mạng phòng mình bị đứt rồi, cần anh kỹ thuật qua nối lại giúp"},
        headers=headers,
    )
    assert send_res.status_code == 200
    reply = send_res.json()
    assert reply["suggest_ticket"] is True
    assert reply["ticket_draft"] is not None
    assert reply["ticket_draft"]["title"] == "Đứt dây mạng phòng 302 KTX"
    assert reply["ticket_draft"]["priority"] == "HIGH"

    # Người dùng xác nhận tạo ticket
    confirm_res = await client.post(
        f"/api/v1/chat/sessions/{session_id}/ticket",
        headers=headers,
    )
    assert confirm_res.status_code == 201
    ticket_data = confirm_res.json()
    assert ticket_data["title"] == "Đứt dây mạng phòng 302 KTX"
    assert ticket_data["channel"] == "CHATBOT"
    assert ticket_data["status"] == "TRIAGED"
    assert ticket_data["chat_session_id"] == session_id

    # Bấm xác nhận lần 2 -> 409 Conflict
    confirm_again = await client.post(
        f"/api/v1/chat/sessions/{session_id}/ticket",
        headers=headers,
    )
    assert confirm_again.status_code == 409


@pytest.mark.asyncio
async def test_feedback_unresolved_drafts_ticket(
    client: AsyncClient,
    student_user: AppUser,
    published_kb_doc: KnowledgeDocument,
) -> None:
    headers = auth_headers_for(student_user)
    sess_res = await client.post("/api/v1/chat/sessions", headers=headers)
    session_id = sess_res.json()["id"]

    fake_llm.queue_json(TicketDraft(
        title="Chưa kết nối được wifi sau khi làm theo hướng dẫn",
        description="Đã nhập mật khẩu sinhvien2026 nhưng vẫn báo lỗi IP",
        category_id=str(published_kb_doc.category_id),
        priority=Priority.MEDIUM,
    ))

    fb_res = await client.post(
        f"/api/v1/chat/sessions/{session_id}/feedback",
        json={"resolved": False},
        headers=headers,
    )
    assert fb_res.status_code == 200
    fb_data = fb_res.json()
    assert fb_data["suggest_ticket"] is True
    assert fb_data["ticket_draft"]["title"] == "Chưa kết nối được wifi sau khi làm theo hướng dẫn"

