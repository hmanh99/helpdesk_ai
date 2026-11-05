import math
from pathlib import Path
import pytest

from app.ai.chunking import chunk_text, estimate_tokens
from app.ai.extractors import extract_text_from_file
from app.ai.fake_client import FakeLLMClient
from app.ai.schemas import IntentResult, TicketDraft
from app.models.enums import Intent, Priority


def test_chunking_short_and_empty() -> None:
    assert chunk_text("") == []
    assert chunk_text("   ") == []

    chunks = chunk_text("Đoạn văn bản ngắn.", chunk_size=800)
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].content == "Đoạn văn bản ngắn."
    assert chunks[0].token_count >= 1


def test_chunking_long_with_overlap() -> None:
    text = "\n\n".join([f"Đoạn văn số {i}: " + "Nội dung chi tiết lặp lại để tạo độ dài. " * 8 for i in range(15)])
    chunks = chunk_text(text, chunk_size=300, overlap=50)
    assert len(chunks) > 1
    for idx, c in enumerate(chunks):
        assert c.chunk_index == idx
        assert len(c.content) > 0


def test_extractors_txt_and_md(tmp_path: Path) -> None:
    txt_file = tmp_path / "sample.txt"
    txt_file.write_text("Hướng dẫn kết nối Wifi trường.", encoding="utf-8")
    extracted = extract_text_from_file(txt_file)
    assert extracted == "Hướng dẫn kết nối Wifi trường."

    md_file = tmp_path / "guide.md"
    md_file.write_text("# Quy chế học vụ\n\nSinh viên cần hoàn thành 130 tín chỉ.", encoding="utf-8")
    assert "130 tín chỉ" in extract_text_from_file(md_file)


def test_extractors_unsupported(tmp_path: Path) -> None:
    unsupported = tmp_path / "data.xyz"
    unsupported.write_text("Test", encoding="utf-8")
    with pytest.raises(ValueError, match="không được hỗ trợ"):
        extract_text_from_file(unsupported)


@pytest.mark.asyncio
async def test_fake_llm_client_embed() -> None:
    client = FakeLLMClient(embedding_dim=768)
    vectors = await client.embed(["Câu hỏi mẫu 1", "Câu hỏi mẫu 2"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 768
    assert len(vectors[1]) == 768

    # Kiểm tra chuẩn hoá L2 ~ 1.0
    norm = math.sqrt(sum(x * x for x in vectors[0]))
    assert abs(norm - 1.0) < 1e-4


@pytest.mark.asyncio
async def test_fake_llm_client_generate_json() -> None:
    client = FakeLLMClient()
    # Default without preset
    res1 = await client.generate_json("Prompt", IntentResult)
    assert res1.intent == Intent.KB_QUESTION

    # With queued preset
    client.queue_json(IntentResult(
        intent=Intent.NEEDS_DEPARTMENT,
        category_id="cat-123",
        priority=Priority.HIGH,
        confidence=0.95,
        reason="Hỏng máy tính phòng thi",
    ))
    res2 = await client.generate_json("Prompt 2", IntentResult)
    assert res2.intent == Intent.NEEDS_DEPARTMENT
    assert res2.priority == Priority.HIGH
    assert res2.confidence == 0.95

