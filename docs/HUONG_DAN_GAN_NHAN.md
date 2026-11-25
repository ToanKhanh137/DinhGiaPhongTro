# Hướng dẫn gán nhãn loại tin đăng (R / G / N)

Dùng cho file `data/labels/listing_type_labels.csv` (bài toán phân loại phụ, `src/listing_type.py`).
Mục đích của nhãn: biết **giá đăng có phải là giá của một phòng cụ thể hay không**, để mô hình định giá chỉ học
trên những tin mà giá đăng thực sự là giá của một phòng.

## Câu hỏi khi gán nhãn

Đọc tiêu đề + mô tả, tự hỏi: **"Con số giá của tin này là giá của cái gì?"**

| Nhãn | Giá đăng là… | Dấu hiệu thường gặp |
|---|---|---|
| **G** — ở ghép | giá **một người / một giường / một slot** | "1tr5/người", "/ng/tháng", "ở ghép", "homestay giường tầng", "dorm", "sleepbox", "KTX", "còn 3 slot", "tìm bạn ở ghép" |
| **N** — nhiều mức giá | **không gắn với một phòng cụ thể**: tin chào nhiều phòng / loại phòng có giá khác nhau, hoặc chỉ ghi khoảng giá / giá "từ" | "giá từ 3tr5", "3tr5 – 4tr", "3tr2, 3tr4 và 3tr5", "tầng 1: 3,5tr, tầng 2: 3tr", "phòng to 3,5tr, phòng nhỏ 2,7tr", "đa dạng các loại phòng từ studio đến 2PN" |
| **R** — phòng riêng | giá của **một phòng / căn hộ / tầng cụ thể** (hoặc của nhiều phòng giống hệt nhau cùng một giá) | "phòng 20m², giá 3tr5", "còn 2 phòng, giá 2tr6/phòng", "cho thuê cả tầng 3 gồm 2 phòng, giá 3tr5" |

## Thứ tự ưu tiên

1. Nếu giá chính của tin là giá **theo người / giường** → **G** (kể cả khi tin có nhắc thêm loại phòng khác).
2. Nếu không, và tin có **từ 2 mức giá phòng khác nhau**, hoặc **khoảng giá / giá "từ"** → **N**.
3. Còn lại → **R**.

## Các trường hợp ranh giới (đã thống nhất)

| Trường hợp | Nhãn | Lý do |
|---|---|---|
| Một phòng, giá đổi theo **số người ở** ("2tr nếu ở 1 người, 2,2tr nếu ở 2 người") | R | vẫn là giá của một phòng cụ thể |
| Một phòng, giá đổi theo **thời hạn hợp đồng** / ưu đãi ("4,5tr, đóng 6 tháng còn 3,9tr", "giảm 500k tháng đầu") | R | khuyến mãi, không phải phòng khác |
| Nhiều phòng **cùng một giá** ("còn 20 phòng 25m², giá 3tr5") | R | giá đăng đúng là giá mỗi phòng |
| Phòng riêng có nhắc "có thể ở ghép" nhưng giá tính **cả phòng** | R | giá không phải theo người |
| Phòng 3,6tr, chủ "hỗ trợ tìm người ở ghép, 1tr/người" | R | giá phòng cố định; 1tr/người chỉ là chia tiền |
| Hai phòng hai giá, giá đăng khớp một trong hai ("3,6tr ~20m² và 4,3tr ~30m²") | N | tin có 2 mức giá phòng; quy ước giữ đơn giản, không suy đoán giá đăng ứng với phòng nào |
| Một phòng nhưng chỉ ghi khoảng ("phòng 16m², 2tr – 2tr2") | N | giá không xác định |
| Tòa nhà nhiều loại phòng, không ghi giá trong mô tả, giá đăng là một con số | N | giá đăng không gắn với loại phòng nào |
| Nhiều phòng, **không ghi giá nào** trong mô tả, giá đăng là một con số | R | không có dấu hiệu nhiều mức giá |
| Giá trong mô tả **lệch** giá đăng (đăng 4,7tr, mô tả 3,7tr) nhưng chỉ có một phòng | R | lỗi nhập giá, không phải nhiều mức giá |
| Giá điện, nước, dịch vụ, tiền cọc, phí môi giới | bỏ qua | không phải giá phòng |

## Quy trình đã làm

1. **Lần 1** (08/10 và 16/10): gán 540 tin gồm 240 tin chọn theo luật và 300 tin chọn ngẫu nhiên (xem `src/listing_type.py`).
2. **Rà soát lần 2** (04/11): đọc lại **toàn bộ 540 tin** theo hướng dẫn này. Mỗi tin hiển thị tiêu đề và mọi đoạn văn
   quanh các con số tiền và từ khóa ở ghép. Tin nào bản rút gọn chưa đủ thông tin thì đọc toàn văn (16 tin).
   Đọc lại toàn bộ chứ không chỉ những tin mô hình đoán khác nhãn, để tránh thiên lệch về phía mô hình.
   - Kết quả: **26 / 540 nhãn (4,8%) được sửa, tất cả từ R sang N** (12 tin mẫu theo luật, 14 tin mẫu ngẫu nhiên).
     Lỗi chủ yếu là bỏ sót khoảng giá nằm giữa mô tả ("giá cả hợp lý: chỉ từ 3 – 3,8 triệu", "còn 2 phòng 2,3tr và 2,6tr").
     Không có nhãn G nào phải sửa.
   - Chi tiết từng thay đổi kèm lý do: `data/labels/label_review_log.csv`. Bản trước rà soát: `listing_type_labels_v1.csv`.
3. **Đo độ đồng thuận** (15/11): 100 tin lấy ngẫu nhiên từ mẫu ngẫu nhiên (`data/labels/kappa_sample_100.csv`, không kèm
   nhãn cũ) được gán lại độc lập bằng `python src/label_tool.py`. Kết quả (`python src/label_agreement.py` →
   `reports/label_agreement.md`): trùng nhãn 94 / 100, Cohen's kappa 0,85 (khoảng tin cậy bootstrap 95%: 0,72–0,95).
   6 tin lệch: 5 tin lần đầu N, lần hai R — mô tả đều có khoảng giá / giá "từ" ("3,7tr – 4tr tuỳ phòng", "giá từ 4,7
   triệu", "3,8 – 4 – 4,1 triệu"), theo bảng trên là N; 1 tin hệ thống ở ghép nhiều cơ sở, nhiều mức giá theo người
   (G theo thứ tự ưu tiên, lần hai gán N). Nhãn dùng cho mô hình vẫn là nhãn sau rà soát lần 2.
4. Hạn chế: mới có một lượt gán lại trên 100 tin. Chỗ dễ lệch nhất là khoảng giá / giá "từ" nằm giữa mô tả dài: người
   gán dễ đọc lướt qua và gán R.
