import asyncio
import logging
from pathlib import Path
import sys
import uuid

# Thêm đường dẫn backend vào sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.ai.chunking import chunk_text
from app.api.deps import get_llm_client
from app.db.session import AsyncSessionLocal
from app.models.category import Category
from app.models.department import Department
from app.models.enums import ProcessingStatus
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_data")

DEPARTMENTS_DATA = [
    {
        "name": "Phòng Công nghệ Thông tin",
        "description": "Quản lý hạ tầng mạng, máy tính, tài khoản email trường, cổng thông tin sinh viên và bản quyền phần mềm.",
        "email": "cntt@school.edu.vn",
    },
    {
        "name": "Phòng Đào tạo",
        "description": "Quản lý chương trình đào tạo, đăng ký học phần, thời khoá biểu, điểm số, phúc khảo và cấp phát bằng tốt nghiệp.",
        "email": "daotao@school.edu.vn",
    },
    {
        "name": "Phòng Công tác Sinh viên",
        "description": "Chăm lo đời sống sinh viên, xét cấp học bổng, quản lý ký túc xá, cấp giấy xác nhận và hỗ trợ việc làm.",
        "email": "ctsv@school.edu.vn",
    },
    {
        "name": "Phòng Cơ sở Vật chất",
        "description": "Quản lý, bảo trì hệ thống giảng đường, phòng thí nghiệm, điều hoà, điện nước và trang thiết bị âm thanh máy chiếu.",
        "email": "csvc@school.edu.vn",
    },
    {
        "name": "Phòng Kế hoạch & Tài chính",
        "description": "Thu học phí, cấp hoá đơn điện tử, xử lý hoàn phí rút học phần và thanh toán các chế độ chính sách sinh viên.",
        "email": "kttc@school.edu.vn",
    },
]

CATEGORIES_DATA = [
    # CNTT
    {
        "dept_name": "Phòng Công nghệ Thông tin",
        "name": "Mạng & Wifi trường",
        "description": "Sự cố kết nối wifi sinh viên, wifi ký túc xá, mạng dây phòng thực hành.",
        "sla_response_minutes": 30,
        "sla_resolve_minutes": 180,
    },
    {
        "dept_name": "Phòng Công nghệ Thông tin",
        "name": "Tài khoản & Email trường",
        "description": "Quên mật khẩu, khoá tài khoản Office 365, cổng đào tạo portal hoặc tài khoản thư viện.",
        "sla_response_minutes": 30,
        "sla_resolve_minutes": 120,
    },
    {
        "dept_name": "Phòng Công nghệ Thông tin",
        "name": "Phần mềm & Bản quyền học tập",
        "description": "Cài đặt phần mềm chuyên ngành (Matlab, AutoCAD, SPSS) và kích hoạt bản quyền Windows/Office.",
        "sla_response_minutes": 60,
        "sla_resolve_minutes": 360,
    },
    # Đào tạo
    {
        "dept_name": "Phòng Đào tạo",
        "name": "Đăng ký học phần",
        "description": "Trùng lịch học, lớp hết chỗ, mở lớp tăng cường, hủy học phần quá hạn.",
        "sla_response_minutes": 60,
        "sla_resolve_minutes": 480,
    },
    {
        "dept_name": "Phòng Đào tạo",
        "name": "Phúc khảo & Bảng điểm",
        "description": "Đơn xin phúc khảo bài thi kết thúc học phần, in bảng điểm chính thức, chỉnh sửa thông tin điểm.",
        "sla_response_minutes": 120,
        "sla_resolve_minutes": 1440,
    },
    {
        "dept_name": "Phòng Đào tạo",
        "name": "Tốt nghiệp & Chứng chỉ",
        "description": "Xét chuẩn đầu ra ngoại ngữ, tin học, xét tốt nghiệp đợt sớm, nhận bằng gốc.",
        "sla_response_minutes": 120,
        "sla_resolve_minutes": 1440,
    },
    # CTSV
    {
        "dept_name": "Phòng Công tác Sinh viên",
        "name": "Ký túc xá",
        "description": "Đăng ký lưu trú KTX, gia hạn phòng, sửa chữa điện nước phòng ở KTX.",
        "sla_response_minutes": 60,
        "sla_resolve_minutes": 360,
    },
    {
        "dept_name": "Phòng Công tác Sinh viên",
        "name": "Học bổng & Miễn giảm học phí",
        "description": "Nộp hồ sơ học bổng khuyến khích học tập, học bổng doanh nghiệp, chế độ trợ cấp khó khăn.",
        "sla_response_minutes": 120,
        "sla_resolve_minutes": 1440,
    },
    {
        "dept_name": "Phòng Công tác Sinh viên",
        "name": "Giấy tờ & Xác nhận sinh viên",
        "description": "Cấp giấy xác nhận sinh viên vay vốn ngân hàng, tạm hoãn nghĩa vụ quân sự, cấp lại thẻ sinh viên bị mất.",
        "sla_response_minutes": 60,
        "sla_resolve_minutes": 240,
    },
    # CSVC
    {
        "dept_name": "Phòng Cơ sở Vật chất",
        "name": "Thiết bị giảng đường & Âm thanh",
        "description": "Máy chiếu phòng học không lên, hỏng micro, bảng từ hư hỏng, bàn ghế gãy hỏng.",
        "sla_response_minutes": 30,
        "sla_resolve_minutes": 120,
    },
    {
        "dept_name": "Phòng Cơ sở Vật chất",
        "name": "Điện nước & Điều hoà",
        "description": "Điều hoà chảy nước, mất điện cục bộ giảng đường, rò rỉ nước nhà vệ sinh.",
        "sla_response_minutes": 30,
        "sla_resolve_minutes": 180,
    },
    # KTTC
    {
        "dept_name": "Phòng Kế hoạch & Tài chính",
        "name": "Học phí & Hoá đơn",
        "description": "Thắc mắc số tiền học phí, thanh toán qua ngân hàng chưa gạch nợ, xuất hoá đơn điện tử.",
        "sla_response_minutes": 60,
        "sla_resolve_minutes": 480,
    },
]

KNOWLEDGE_DOCS_DATA = [
    {
        "category_name": "Mạng & Wifi trường",
        "title": "Hướng dẫn kết nối Wifi Sinh viên và Ký túc xá",
        "source_url": "https://cntt.school.edu.vn/huong-dan/wifi-sinh-vien",
        "content": """HỆ THỐNG WIFI DÀNH CHO SINH VIÊN VÀ KÝ TÚC XÁ

1. Tên mạng Wifi (SSID):
- Tại khu vực giảng đường và thư viện: Chọn SSID "SV_School_Wifi".
- Tại khu vực các toà Ký túc xá (KTX A, KTX B): Chọn SSID "KTX_SinhVien".

2. Phương thức xác thực:
- Mật khẩu WPA2 ban đầu: "SinhVien@2026".
- Sau khi kết nối, trang đăng nhập xác thực mạng (Captive Portal) sẽ tự động mở ra. Nếu không tự mở, sinh viên truy cập trình duyệt vào địa chỉ: http://wifi.school.edu.vn.
- Tên đăng nhập: Mã số sinh viên (ví dụ: 20210001).
- Mật khẩu: Mật khẩu cổng đào tạo của sinh viên.

3. Khắc phục lỗi thường gặp:
- Nếu thiết bị báo "IP Configuration Failure" hoặc "Không nhận được địa chỉ IP": Hãy vào Cài đặt Wifi -> Bấm Quên mạng (Forget Network) -> Tắt/bật lại Wifi và kết nối lại.
- Nếu không thấy trang Captive Portal: Hãy mở tab ẩn danh trên trình duyệt và gõ 1.1.1.1 hoặc 8.8.8.8 để hệ thống chuyển hướng.
- Mỗi tài khoản sinh viên được đăng nhập tối đa 02 thiết bị đồng thời. Nếu vượt quá giới hạn, thiết bị đăng nhập trước sẽ tự động bị đăng xuất.""",
    },
    {
        "category_name": "Tài khoản & Email trường",
        "title": "Quy trình cấp lại mật khẩu Email trường và Portal sinh viên",
        "source_url": "https://cntt.school.edu.vn/ho-tro/quen-mat-khau",
        "content": """HƯỚNG DẪN ĐỔI VÀ KHÔI PHỤC MẬT KHẨU TÀI KHOẢN TRƯỜNG

1. Khôi phục mật khẩu tự động qua Email cá nhân:
- Truy cập cổng: https://portal.school.edu.vn/forgot-password.
- Nhập Mã số sinh viên và Mã bảo mật.
- Hệ thống sẽ gửi một mã OTP gồm 6 chữ số tới Email cá nhân của sinh viên đã đăng ký trong hồ sơ nhập học.
- Nhập mã OTP và đặt lại mật khẩu mới (Mật khẩu tối thiểu 8 ký tự, bao gồm chữ hoa, chữ thường và chữ số).

2. Khôi phục tài khoản Office 365 / Microsoft Teams:
- Tài khoản Office 365 có định dạng: [MSSV]@student.school.edu.vn.
- Nếu quên mật khẩu Office 365, sinh viên đăng nhập vào Portal đào tạo -> Chọn mục "Tiện ích sinh viên" -> Bấm nút "Đồng bộ / Reset mật khẩu Office 365". Mật khẩu sẽ được cập nhật trùng với mật khẩu Portal trong vòng 5 phút.

3. Trường hợp tài khoản bị khoá:
- Tài khoản sẽ bị tạm khoá 30 phút nếu nhập sai mật khẩu quá 5 lần liên tiếp.
- Nếu cần mở khoá khẩn cấp hoặc mất email cá nhân nhận OTP, sinh viên cần mang theo Căn cước công dân hoặc Thẻ sinh viên đến trực tiếp Phòng CNTT (Phòng 204, Nhà A1) trong giờ hành chính để được cấp lại trực tiếp.""",
    },
    {
        "category_name": "Đăng ký học phần",
        "title": "Quy định và hướng dẫn Đăng ký học phần tín chỉ",
        "source_url": "https://daotao.school.edu.vn/quy-che/dang-ky-hoc-phan",
        "content": """QUY ĐỊNH ĐĂNG KÝ HỌC PHẦN ĐÀO TẠO THEO HỆ TÍN CHỈ

1. Các giai đoạn đăng ký trong học kỳ:
- Giai đoạn 1 (Đăng ký sớm theo khóa): Dành cho sinh viên đăng ký theo đúng tiến độ khung chương trình của khóa mình.
- Giai đoạn 2 (Đăng ký học ghép / học vượt): Dành cho toàn bộ sinh viên có nhu cầu học vượt, học cải thiện điểm hoặc học lại.
- Giai đoạn 3 (Hiệu chỉnh đăng ký): Diễn ra trong 02 tuần đầu tiên của học kỳ chính thức. Sinh viên được phép rút bớt hoặc đăng ký thêm các lớp học phần còn trống chỗ.

2. Giới hạn số tín chỉ đăng ký:
- Học kỳ chính (Kỳ 1, Kỳ 2): Tối thiểu 14 tín chỉ, tối đa 24 tín chỉ đối với sinh viên có học lực Khá trở lên. Sinh viên diện cảnh báo học tập chỉ được đăng ký tối đa 14 tín chỉ.
- Học kỳ hè (Kỳ phụ): Tối đa 8 tín chỉ.

3. Hướng dẫn hủy / rút học phần:
- Rút học phần trong thời gian hiệu chỉnh (2 tuần đầu): Không lưu điểm F, được hoàn 100% học phí về tài khoản sinh viên.
- Rút học phần sau tuần thứ 2 đến tuần thứ 6: Nhận điểm W (Rút môn), không được hoàn lại học phí. Sau tuần thứ 6, sinh viên không được phép rút học phần.""",
    },
    {
        "category_name": "Phúc khảo & Bảng điểm",
        "title": "Thủ tục nộp đơn Phúc khảo điểm thi và In bảng điểm",
        "source_url": "https://daotao.school.edu.vn/thu-tuc/phuc-khao-bang-diem",
        "content": """QUY TRÌNH PHÚC KHẢO ĐIỂM THI VÀ XIN CẤP BẢNG ĐIỂM

1. Thủ tục nộp đơn phúc khảo bài thi kết thúc học phần:
- Thời hạn nộp đơn: Trong vòng 07 ngày làm việc kể từ thời điểm điểm học phần được công bố chính thức trên Portal đào tạo. Sau thời hạn này, hệ thống sẽ tự động đóng chức năng khiếu nại.
- Hình thức nộp đơn: Trực tuyến tại cổng: https://portal.school.edu.vn/phuc-khao.
- Lệ phí phúc khảo: 50.000 VNĐ / bài thi. Lệ phí sẽ được tự động hoàn trả vào tài khoản sinh viên nếu sau khi chấm lại điểm thi tăng từ 0.5 điểm trở lên.
- Thời gian công bố kết quả: Phòng Đào tạo sẽ tổ chức ban chấm phúc khảo và công bố kết quả điểm sau 15 ngày làm việc.

2. Cấp phát Bảng điểm quá trình học tập:
- Bảng điểm điện tử có chữ ký số: Sinh viên có thể tự xuất file PDF có mã QR xác thực tại Portal -> Bảng điểm -> "Xuất bảng điểm có mã xác thực" (Miễn phí).
- Bảng điểm bản cứng có mộc đỏ: Đăng ký tại Cổng dịch vụ một cửa -> Chọn số lượng bản in (20.000 VNĐ / bản). Nhận kết quả sau 02 ngày làm việc tại Phòng Đào tạo (Cửa số 3).""",
    },
    {
        "category_name": "Ký túc xá",
        "title": "Nội quy lưu trú và Quy trình sửa chữa kỹ thuật tại Ký túc xá",
        "source_url": "https://ctsv.school.edu.vn/ktx/noi-quy-sua-chua",
        "content": """QUY ĐỊNH LƯU TRÚ VÀ XỬ LÝ SỰ CỐ KỸ THUẬT PHÒNG Ở KTX

1. Giờ giấc và nề nếp sinh hoạt:
- Giờ đóng mở cổng Ký túc xá: Mở cửa lúc 05h00 và đóng cửa lúc 23h00 hàng ngày. Sinh viên về muộn cần xuất trình thẻ nội trú và có lý do chính đáng được Ban quản lý chấp thuận.
- Nghiêm cấm nấu ăn bằng bếp gas, bếp từ công suất lớn (>1500W) trong phòng ngủ.
- Không tự ý đấu nối hệ thống điện, không đưa người ngoài vào phòng ngủ qua đêm.

2. Quy trình báo hỏng và sửa chữa thiết bị phòng:
- Khi phát sinh sự cố điện nước (vỡ ống nước, chập điện, hỏng quạt trần, tắc cống, hỏng khoá cửa phòng): Trưởng phòng ở đăng nhập hệ thống Helpdesk và tạo Ticket báo hỏng thuộc danh mục "Ký túc xá".
- Ghi rõ: Tên toà nhà, Số phòng, Vị trí hỏng hóc và số điện thoại liên hệ của người trực phòng.
- Đội kỹ thuật trực KTX sẽ đến kiểm tra và khắc phục trong vòng 03 đến 06 giờ làm việc. Các sự cố khẩn cấp (rò rỉ nước ngập phòng, chập cháy điện) liên hệ ngay Hotline trực ban KTX: 024.3869.xxxx để được ngắt điện nước tức thời.""",
    },
    {
        "category_name": "Giấy tờ & Xác nhận sinh viên",
        "title": "Hướng dẫn xin cấp Giấy xác nhận sinh viên và Làm lại thẻ bị mất",
        "source_url": "https://ctsv.school.edu.vn/giay-to-sinh-vien",
        "content": """QUY TRÌNH CẤP GIẤY XÁC NHẬN VÀ CẤP LẠI THẺ SINH VIÊN

1. Các loại Giấy xác nhận sinh viên thường dùng:
- Giấy xác nhận tạm hoãn nghĩa vụ quân sự (dành cho sinh viên nam).
- Giấy xác nhận sinh viên để vay vốn ngân hàng chính sách xã hội.
- Giấy giới thiệu thực tập tại cơ quan, doanh nghiệp.
- Giấy xác nhận làm vé tháng xe buýt (vé liên tuyến sinh viên).

2. Cách thức đăng ký:
- Đăng ký online: Sinh viên truy cập Portal -> Mục "Dịch vụ một cửa" -> Chọn mẫu giấy cần in và điền mục đích.
- Thời gian xử lý: Sau 24 giờ làm việc, sinh viên đến Văn phòng Công tác sinh viên (Tầng 1 Nhà H1) để nhận bản giấy có đóng dấu mộc đỏ của Nhà trường.

3. Thủ tục làm lại Thẻ sinh viên khi bị mất hoặc hỏng:
- Bước 1: Khai báo mất thẻ trên Portal để khoá chức năng gửi xe và mượn sách thư viện của thẻ cũ.
- Bước 2: Nộp đơn xin cấp lại thẻ sinh viên kèm biên lai nộp phí cấp lại (50.000 VNĐ).
- Bước 3: Trong thời gian chờ in thẻ cứng mới (khoảng 07 ngày), sinh viên sử dụng thẻ sinh viên điện tử trên App di động của trường để điểm danh và ra vào cổng.""",
    },
    {
        "category_name": "Học phí & Hoá đơn",
        "title": "Thời hạn và phương thức nộp học phí qua cổng ngân hàng",
        "source_url": "https://kttc.school.edu.vn/huong-dan-dong-hoc-phi",
        "content": """HƯỚNG DẪN THANH TOÁN HỌC PHÍ VÀ XUẤT HOÁ ĐƠN ĐIỆN TỬ

1. Thời hạn nộp học phí:
- Học phí được thông báo vào tuần thứ 4 của học kỳ và hạn chót nộp là kết thúc tuần thứ 8 của học kỳ chính.
- Sinh viên chưa hoàn thành học phí đúng hạn sẽ bị tạm khoá quyền đăng ký học phần cho học kỳ tiếp theo và không có tên trong danh sách thi kết thúc học phần.

2. Phương thức thanh toán học phí:
- Cách 1: Thanh toán trực tuyến qua cổng thanh toán VNPAY / Momo trên Portal sinh viên (Gạch nợ tức thì trong vòng 1 phút).
- Cách 2: Chuyển khoản qua ngân hàng định danh (Virtual Account):
  + Tên ngân hàng: BIDV / Vietcombank.
  + Số tài khoản thụ hưởng: Cú pháp riêng của mỗi sinh viên hiển thị trên Portal.
  + Tên người thụ hưởng: [Họ và tên sinh viên] - [MSSV].
  + Số tiền: Chính xác số tiền học phí còn nợ.

3. Hoá đơn điện tử học phí:
- Sau khi thanh toán thành công 24 giờ, hoá đơn giá trị gia tăng điện tử sẽ được phát hành.
- Phụ huynh hoặc sinh viên có thể tự tra cứu và tải hoá đơn điện tử có mã của cơ quan thuế tại địa chỉ: https://hoadon.school.edu.vn bằng cách nhập Mã số sinh viên.""",
    },
    {
        "category_name": "Thiết bị giảng đường & Âm thanh",
        "title": "Quy trình báo hỏng máy chiếu, micro và thiết bị phòng học",
        "source_url": "https://csvc.school.edu.vn/giang-duong/sua-chua-thiet-bi",
        "content": """QUY TRÌNH HỖ TRỢ KỸ THUẬT VÀ BÁO HỎNG TRANG THIẾT BỊ GIẢNG ĐƯỜNG

1. Các thiết bị tiêu chuẩn trong mỗi phòng học:
- 01 máy chiếu và màn chiếu tự động (hoặc Smart TV 75 inch).
- 01 bộ khuếch đại âm thanh (Ampli) và 02 micro không dây.
- Cáp kết nối HDMI, Type-C và dây âm thanh 3.5mm tại bục giảng.
- Hệ thống quạt trần và điều hoà nhiệt độ.

2. Hướng dẫn nhanh khi máy chiếu không nhận hình ảnh:
- Kiểm tra nguồn điện máy chiếu đã cắm và đèn Status sáng màu xanh.
- Nhấn tổ hợp phím Windows + P trên laptop và chọn chế độ "Duplicate" (Nhân bản màn hình).
- Đảm bảo đầu chuyển HDMI/Type-C tiếp xúc chặt chẽ.

3. Cách báo hỏng khẩn cấp trong giờ học:
- Nếu thiết bị hỏng trước hoặc trong buổi học: Giảng viên hoặc Lớp trưởng gọi trực tiếp số điện thoại trực kỹ thuật dán tại góc bục giảng (ví dụ Giảng đường B1: 024.3869.1111) để có kỹ thuật viên mang micro/cáp thay thế trong vòng 5-10 phút.
- Đối với hỏng hóc cần sửa chữa lớn (cháy bóng đèn máy chiếu, hỏng màn chiếu): Vui lòng tạo Ticket trên Helpdesk thuộc danh mục "Thiết bị giảng đường & Âm thanh" để bố trí kỹ thuật viên thay thế sau giờ học.""",
    },
]


async def seed_data() -> None:
    logger.info("Bắt đầu khởi tạo dữ liệu mẫu cho hệ thống Helpdesk AI...")
    llm = get_llm_client()

    async with AsyncSessionLocal() as session:
        # 1. Thêm phòng ban (Departments)
        dept_map: dict[str, Department] = {}
        for d_info in DEPARTMENTS_DATA:
            res = await session.execute(
                select(Department).where(Department.name == d_info["name"])
            )
            dept = res.scalar_one_or_none()
            if dept is None:
                dept = Department(
                    name=d_info["name"],
                    description=d_info["description"],
                    email=d_info["email"],
                    is_active=True,
                )
                session.add(dept)
                await session.flush()
                logger.info("Đã tạo phòng ban: %s", dept.name)
            dept_map[dept.name] = dept

        await session.commit()

        # 2. Thêm danh mục (Categories)
        cat_map: dict[str, Category] = {}
        for c_info in CATEGORIES_DATA:
            dept = dept_map.get(c_info["dept_name"])
            if not dept:
                continue
            res = await session.execute(
                select(Category).where(Category.name == c_info["name"])
            )
            cat = res.scalar_one_or_none()
            if cat is None:
                cat = Category(
                    department_id=dept.id,
                    name=c_info["name"],
                    description=c_info["description"],
                    sla_response_minutes=c_info["sla_response_minutes"],
                    sla_resolve_minutes=c_info["sla_resolve_minutes"],
                    is_active=True,
                )
                session.add(cat)
                await session.flush()
                logger.info("Đã tạo danh mục: %s (thuộc %s)", cat.name, dept.name)
            cat_map[cat.name] = cat

        await session.commit()

        # 3. Thêm tài liệu tri thức (Knowledge Documents & Chunks)
        for doc_info in KNOWLEDGE_DOCS_DATA:
            cat = cat_map.get(doc_info["category_name"])
            res = await session.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.title == doc_info["title"])
            )
            doc = res.scalar_one_or_none()
            if doc is None:
                doc = KnowledgeDocument(
                    title=doc_info["title"],
                    category_id=cat.id if cat else None,
                    content=doc_info["content"],
                    source_url=doc_info["source_url"],
                    processing_status=ProcessingStatus.READY,
                    is_published=True,
                )
                session.add(doc)
                await session.flush()

                # Tách đoạn và tạo vector embedding
                chunks = chunk_text(doc.content, chunk_size=800, overlap=150)
                texts = [c.content for c in chunks]
                vectors = await llm.embed(texts, task_type="RETRIEVAL_DOCUMENT")

                db_chunks = [
                    KnowledgeChunk(
                        document_id=doc.id,
                        chunk_index=c.chunk_index,
                        content=c.content,
                        token_count=c.token_count,
                        embedding=vec,
                    )
                    for c, vec in zip(chunks, vectors)
                ]
                session.add_all(db_chunks)
                await session.flush()
                logger.info("Đã tạo tài liệu tri thức: %s (%d chunks)", doc.title, len(chunks))

        await session.commit()

    logger.info("Hoàn tất khởi tạo dữ liệu mẫu thành công!")


if __name__ == "__main__":
    asyncio.run(seed_data())

