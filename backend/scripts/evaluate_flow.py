import asyncio
import logging
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select

from app.api.deps import get_llm_client
from app.db.session import AsyncSessionLocal
from app.models.category import Category
from app.models.enums import Intent
from app.service.classifier import IntentClassifier

logging.basicConfig(level=logging.WARNING)

TEST_CASES = [
    # 1. KB_QUESTION & SIMPLE_TROUBLESHOOT (Tra cứu tài liệu tri thức)
    {"q": "Làm sao để kết nối vào mạng wifi sinh viên ở giảng đường?", "expected_intent": Intent.KB_QUESTION},
    {"q": "Mật khẩu mạng wifi KTX_SinhVien là gì vậy ạ?", "expected_intent": Intent.KB_QUESTION},
    {"q": "Cách lấy lại mật khẩu tài khoản Portal khi bị quên như thế nào?", "expected_intent": Intent.KB_QUESTION},
    {"q": "Tôi bị quên mật khẩu Office 365 thì làm sao để đồng bộ lại?", "expected_intent": Intent.KB_QUESTION},
    {"q": "Học kỳ chính một sinh viên được đăng ký tối thiểu và tối đa bao nhiêu tín chỉ?", "expected_intent": Intent.KB_QUESTION},
    {"q": "Muốn rút môn học trong 2 tuần đầu kỳ có được hoàn lại tiền học phí không?", "expected_intent": Intent.KB_QUESTION},
    {"q": "Thời hạn nộp đơn phúc khảo bài thi kết thúc học phần là bao nhiêu ngày?", "expected_intent": Intent.KB_QUESTION},
    {"q": "Xin cấp bảng điểm bản cứng có dấu đỏ của trường ở đâu và mất bao lâu?", "expected_intent": Intent.KB_QUESTION},
    {"q": "Thủ tục xin cấp giấy tạm hoãn nghĩa vụ quân sự cần những giấy tờ gì?", "expected_intent": Intent.KB_QUESTION},
    {"q": "Học phí học kỳ này nộp qua tài khoản ngân hàng nào và hạn chót là khi nào?", "expected_intent": Intent.KB_QUESTION},

    # 2. NEEDS_DEPARTMENT (Sự cố phức tạp, hỏng hóc vật lý, cần nhân viên xử lý)
    {"q": "Cáp mạng phòng 302 KTX bị chuột cắn đứt đôi, cần thợ qua bấm và nối lại dây mới", "expected_intent": Intent.NEEDS_DEPARTMENT},
    {"q": "Phòng học B1-204 máy chiếu bị nổ bóng đèn và bốc khói khét lẹt, cần kỹ thuật viên thay gấp", "expected_intent": Intent.NEEDS_DEPARTMENT},
    {"q": "Nhà vệ sinh tầng 3 nhà A1 bị vỡ ống nước chảy tràn ra hành lang giảng đường", "expected_intent": Intent.NEEDS_DEPARTMENT},
    {"q": "Tài khoản của em bị báo khoá vĩnh viễn do nghi ngờ gian lận, em cần gặp trực tiếp thầy cô để giải trình", "expected_intent": Intent.NEEDS_DEPARTMENT},
    {"q": "Bảng điểm trên hệ thống của em bị nhập sai từ 8.5 thành 5.0, em cần phòng Đào tạo đính chính lại", "expected_intent": Intent.NEEDS_DEPARTMENT},
    {"q": "Điều hoà phòng 501 giảng đường C bị chảy nước ướt hết bàn ghế sinh viên ngồi bên dưới", "expected_intent": Intent.NEEDS_DEPARTMENT},
    {"q": "Em đã chuyển khoản học phí 3 ngày trước nhưng tài khoản vẫn báo nợ, cần kế toán đối soát giao dịch", "expected_intent": Intent.NEEDS_DEPARTMENT},
    {"q": "Em bị mất thẻ sinh viên cứng, cần phòng công tác sinh viên in cấp lại thẻ mới", "expected_intent": Intent.NEEDS_DEPARTMENT},
    {"q": "Cầu dao điện phòng thực hành máy tính 2 bị chập cháy nhảy át liên tục", "expected_intent": Intent.NEEDS_DEPARTMENT},
    {"q": "Em muốn xin gặp trưởng phòng đào tạo để nộp đơn xin bảo lưu kết quả học tập đột xuất", "expected_intent": Intent.NEEDS_DEPARTMENT},

    # 3. SMALLTALK (Chào hỏi, cảm ơn, giao tiếp xã giao)
    {"q": "Xin chào bạn, bạn là ai thế?", "expected_intent": Intent.SMALLTALK},
    {"q": "Chào chatbot, chúc bạn một ngày tốt lành", "expected_intent": Intent.SMALLTALK},
    {"q": "Cảm ơn bot nhiều nhé, thông tin rất hữu ích", "expected_intent": Intent.SMALLTALK},
    {"q": "Cảm ơn bạn, tôi đã hiểu rồi", "expected_intent": Intent.SMALLTALK},
    {"q": "Hi bot", "expected_intent": Intent.SMALLTALK},

    # 4. UNCLEAR (Tối nghĩa, quá ngắn, mơ hồ)
    {"q": "???", "expected_intent": Intent.UNCLEAR},
    {"q": "cái đó", "expected_intent": Intent.UNCLEAR},
    {"q": "alo", "expected_intent": Intent.UNCLEAR},
    {"q": "thầy ơi cho em hỏi với", "expected_intent": Intent.UNCLEAR},
    {"q": "giúp", "expected_intent": Intent.UNCLEAR},
]


async def run_evaluation() -> None:
    print(f"\n{'='*70}")
    print("BẮT ĐẦU ĐÁNH GIÁ ĐỘ CHÍNH XÁC PHÂN LOẠI Ý ĐỊNH (INTENT CLASSIFICATION)")
    print(f"{'='*70}\n")

    llm = get_llm_client()
    classifier = IntentClassifier(llm)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Category).where(Category.is_active.is_(True))
        )
        categories = result.scalars().all()

    correct_count = 0
    total_count = len(TEST_CASES)

    for idx, case in enumerate(TEST_CASES, start=1):
        q = case["q"]
        expected = case["expected_intent"]

        res = await classifier.classify(message=q, history=[], categories=categories)
        is_correct = (res.intent == expected)
        # SIMPLE_TROUBLESHOOT và KB_QUESTION cùng nằm trong nhánh tra cứu tài liệu
        if expected == Intent.KB_QUESTION and res.intent in (Intent.KB_QUESTION, Intent.SIMPLE_TROUBLESHOOT):
            is_correct = True

        if is_correct:
            correct_count += 1
            status_symbol = "[OK]"
        else:
            status_symbol = "[FAIL]"

        print(
            f"{idx:02d}. {status_symbol} Câu hỏi: \"{q[:45]}...\" | "
            f"Kỳ vọng: {expected.value:<16} | Dự đoán: {res.intent.value:<16} (Score: {res.confidence:.2f})"
        )
        # Giữ nhịp độ trong giới hạn 15 RPM của Gemini Free Tier
        await asyncio.sleep(4.2)

    accuracy = (correct_count / total_count) * 100
    print(f"\n{'-'*70}")
    print(f"KẾT QUẢ ĐÁNH GIÁ: {correct_count}/{total_count} câu chính xác ({accuracy:.1f}%)")
    print(f"{'-'*70}\n")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
