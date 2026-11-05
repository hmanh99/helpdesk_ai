from pathlib import Path
from typing import Optional


def extract_text_from_txt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def extract_text_from_pdf(path: Path) -> str:
    import pypdf

    reader = pypdf.PdfReader(str(path))
    pages_text: list[str] = []
    for page_idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages_text.append(f"--- Trang {page_idx + 1} ---\n{text.strip()}")

    full_text = "\n\n".join(pages_text).strip()
    if len(full_text) < 20:
        raise ValueError(
            "Tài liệu PDF không chứa văn bản có thể trích xuất (có thể là file scan dạng hình ảnh)."
        )
    return full_text


def extract_text_from_docx(path: Path) -> str:
    import docx

    doc = docx.Document(str(path))
    paragraphs: list[str] = []
    for p in doc.paragraphs:
        if p.text.strip():
            paragraphs.append(p.text.strip())

    # Trích xuất thêm nội dung trong bảng
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                paragraphs.append(row_text)

    full_text = "\n\n".join(paragraphs).strip()
    if not full_text:
        raise ValueError("Tài liệu Word (DOCX) trống hoặc không có nội dung văn bản.")
    return full_text


def extract_text_from_file(file_path: Path | str, mime_type: Optional[str] = None) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    ext = path.suffix.lower()

    if ext in (".txt", ".md"):
        text = extract_text_from_txt(path)
    elif ext == ".pdf":
        text = extract_text_from_pdf(path)
    elif ext in (".docx", ".doc"):
        if ext == ".doc":
            raise ValueError(
                "Định dạng .doc cũ không được hỗ trợ trực tiếp. Vui lòng chuyển đổi sang .docx hoặc .pdf."
            )
        text = extract_text_from_docx(path)
    else:
        raise ValueError(f"Định dạng file {ext} không được hỗ trợ. Chỉ hỗ trợ .txt, .md, .pdf, .docx.")

    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Nội dung tài liệu trống sau khi trích xuất.")
    return cleaned

