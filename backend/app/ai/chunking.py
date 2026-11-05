from dataclasses import dataclass
import re


@dataclass
class TextChunk:
    chunk_index: int
    content: str
    token_count: int


def estimate_tokens(text: str) -> int:
    """Ước lượng số token cho văn bản tiếng Việt/Anh (~1 token cho 3.5 ký tự)."""
    return max(1, int(len(text) / 3.5))


def _split_into_atomic_units(text: str, max_size: int) -> list[str]:
    """Chia nhỏ văn bản thành các đoạn atomic không vượt quá max_size ký tự."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_size:
        return [text]

    # Cấp 1: Phân tách theo đoạn văn (paragraph)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) > 1:
        res: list[str] = []
        for p in paragraphs:
            res.extend(_split_into_atomic_units(p, max_size))
        return res

    # Cấp 2: Phân tách theo dòng (line)
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if len(lines) > 1:
        res = []
        for ln in lines:
            res.extend(_split_into_atomic_units(ln, max_size))
        return res

    # Cấp 3: Phân tách theo câu (sentence punctuation)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?。;])\s+", text) if s.strip()]
    if len(sentences) > 1:
        res = []
        for s in sentences:
            res.extend(_split_into_atomic_units(s, max_size))
        return res

    # Cấp 4: Phân tách theo từ (words)
    words = text.split()
    if len(words) > 1:
        parts: list[str] = []
        current = ""
        for w in words:
            if not current:
                current = w
            elif len(current) + len(w) + 1 <= max_size:
                current += " " + w
            else:
                parts.append(current)
                current = w
        if current:
            parts.append(current)
        if len(parts) > 1:
            return parts

    # Cấp 5: Cắt cứng nếu từ đơn lẻ quá dài
    return [text[i : i + max_size] for i in range(0, len(text), max_size)]


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[TextChunk]:
    """Tách văn bản thành các đoạn (chunks) có kích thước xấp xỉ `chunk_size` ký tự,
    với phần gối đầu `overlap` ký tự, ưu tiên ngắt theo đoạn văn, câu hoặc từ.
    """
    cleaned = text.strip()
    if not cleaned:
        return []

    if len(cleaned) <= chunk_size:
        return [
            TextChunk(
                chunk_index=0,
                content=cleaned,
                token_count=estimate_tokens(cleaned),
            )
        ]

    atomic_units = _split_into_atomic_units(cleaned, max_size=chunk_size)

    chunks: list[TextChunk] = []
    current_content = ""
    chunk_idx = 0

    for unit in atomic_units:
        sep = "\n\n" if ("\n" in unit or "\n" in current_content) else " "
        if not current_content:
            current_content = unit
        elif len(current_content) + len(unit) + len(sep) <= chunk_size:
            current_content += sep + unit
        else:
            chunks.append(
                TextChunk(
                    chunk_index=chunk_idx,
                    content=current_content.strip(),
                    token_count=estimate_tokens(current_content),
                )
            )
            chunk_idx += 1

            if overlap > 0 and len(current_content) > overlap:
                tail = current_content[-overlap:].lstrip()
                if len(tail) + len(unit) + len(sep) <= chunk_size:
                    current_content = tail + sep + unit
                else:
                    current_content = unit
            else:
                current_content = unit

    if current_content.strip():
        chunks.append(
            TextChunk(
                chunk_index=chunk_idx,
                content=current_content.strip(),
                token_count=estimate_tokens(current_content),
            )
        )

    return chunks

