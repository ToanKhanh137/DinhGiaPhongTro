# Dàn ý báo cáo đồ án (theo yêu cầu trong Course-Intro.pdf)

Mỗi mục ghi: nội dung cần viết · lấy số liệu / hình ở đâu. Số liệu cụ thể lấy từ lần chạy
`python src/run_pipeline.py` cuối cùng (đừng chép số trong file này vì dữ liệu còn thay đổi).

Thầy chấm theo: độ khó bài toán · độ phù hợp phương pháp · **đánh giá và lựa chọn mô hình kỹ lưỡng** ·
chất lượng thuyết trình · chất lượng báo cáo · hệ thống thử nghiệm (chức năng, dễ dùng).

---

## 1. Giới thiệu bài toán thực tế
- Vấn đề: sinh viên thuê trọ không biết giá đăng có hợp lý không; thông tin phân tán trên nhiều trang.
- Mục tiêu: ước lượng giá thuê hợp lý + khoảng dao động; nhận diện tin "hớ" / "hời".
- Input / output của hệ thống (bảng): diện tích, quận/phường, nội thất, mô tả → giá (triệu/tháng), khoảng 80%.
- Kịch bản sử dụng: sinh viên dán tin đăng vào web → biết giá thị trường.

## 2. Dữ liệu
- 3 nguồn, cách thu thập, đạo đức (robots.txt, crawl chậm, không lưu dữ liệu cá nhân) · `README.md` mục *Nguồn dữ liệu*
- Quy trình làm sạch + số dòng sau mỗi bước · `reports/cleaning_log.txt`
- Vấn đề dữ liệu thực tế (ăn điểm "độ khó"):
  - ~51% tin Chợ Tốt không ghi diện tích → cờ `size_missing`
  - tin trùng giữa các nguồn / đăng lại → `group_id`, GroupKFold
  - địa giới hành chính đổi năm 2025 → bảng đối chiếu phường cũ ↔ mới
  - ~60% mô tả có ghi giá → che giá (`mask_money`) chống rò rỉ nhãn
  - tin ở ghép / nhiều mức giá → bài toán phân loại phụ (mục 3.2)
- EDA: `reports/figures/01`–`05`

## 3. Phương pháp
### 3.1 Hồi quy giá (Chương 3)
- Đặc trưng: số (diện tích, khoảng cách tới 7 trường ĐH / trung tâm), phân loại (quận, nội thất, nguồn), từ khóa tiện ích, TF-IDF mô tả.
- Mô hình: Dummy → Linear / Ridge / Lasso → Random Forest / HistGradientBoosting → Ridge + TF-IDF
  → kết hợp Ridge + TF-IDF × 0,7 + HGB × 0,3 (mô hình cuối). Mục tiêu log(giá).
- Lý do chọn Ridge + TF-IDF (dữ liệu văn bản thưa, nhiều chiều → mô hình tuyến tính có chính quy hóa hợp hơn cây).
### 3.2 Phân loại loại tin (Chương 5)
- 3 lớp R / G / N, 240 nhãn tay, luật regex vs TF-IDF + LogReg / NB / SVM vs kết hợp · `reports/listing_type.md`
### 3.3 Phân cụm khu vực trọ (Chương 4)
- Đơn vị phường, chọn đặc trưng, chọn k, K-Means vs Agglomerative vs DBSCAN · `reports/clustering.md`
### 3.4 Luật kết hợp (Chương 6)
- Apriori trên tiện ích + mức giá + cụm · `reports/association_rules.md`

## 4. Thực nghiệm và đánh giá  ← phần quan trọng nhất
- Thiết lập: GroupKFold 5-fold, metric MAE / RMSE / MAPE / R² trên thang VND.
- Bảng so sánh mô hình · `reports/model_comparison.csv`
- Rò rỉ dữ liệu: GroupKFold vs KFold ngẫu nhiên (dòng cuối bảng trên)
- Thí nghiệm A–E · `reports/experiments.csv`
  - A: biểu diễn văn bản (không văn bản / từ khóa / TF-IDF)
  - B: tinh chỉnh HGB
  - C: ablation từng nhóm đặc trưng
  - D: tọa độ chính xác vs tọa độ phường
  - E: chọn alpha cho Ridge
  - F: kết hợp mô hình (Ridge + TF-IDF với HGB) → mô hình cuối
- **Kiểm tra trên tin đăng mới** (train tin cũ, test tin xuất hiện sau) · `reports/temporal_validation.md`
- Lọc loại tin: huấn luyện trên tất cả vs chỉ phòng riêng · `reports/listing_type.md`
- Phân tích lỗi · `reports/error_analysis.md`, hình `06`, `07`
- Phân cụm: hình `08`–`10`; luật kết hợp: hình `11`

## 5. Hệ thống demo
- Kiến trúc: backend FastAPI (`web/server.py`, 2 API: `/api/meta`, `/api/predict`) + frontend HTML/CSS/JS (`web/static/`).
- Chức năng: nhập quận/phường, diện tích, nội thất, mô tả, giá chủ trọ → giá ước tính + khoảng giá 80% + nhận xét
  hớ / hợp lý / hời; thanh so sánh với các phòng tương tự trong khu vực; tiện ích nhận diện từ mô tả; bảng tin tương tự.
- Ảnh chụp màn hình (chế độ sáng / tối / điện thoại). Cách chạy: nhấp đúp `chay_demo.bat` (mở `/#mau` để điền sẵn tin mẫu).

## 6. Cấu trúc mã nguồn
- Bảng: file → vai trò (lấy từ `README.md` mục *Cấu trúc thư mục*). Mô tả hàm chính:
  `build_dataset.main`, `features.add_features / load_rooms / mask_money`, `train.models / evaluate`,
  `listing_type.rule_predict`, `clustering.ward_table / choose_k`.
- Kiểm thử: `tests/test_text_processing.py` (30 test cho che giá, đọc giá, tách diện tích, luật phân loại).

## 7. Khó khăn và giải pháp · Phân công công việc
- Khó khăn: Nominatim bị chặn → tọa độ theo phường; Phongtro123 giới hạn phân trang; máy 8 GB RAM hết bộ nhớ
  khi tinh chỉnh song song → giảm số worker; RidgeCV chậm → cố định alpha đã chọn bằng CV (nhanh ~50×).
- Bảng phân công (ai làm phần nào).

## 8. Khám phá mới / kết luận
- Lấy từ `README.md` mục *Phát hiện chính*. Gợi ý chọn 4–5 ý mạnh nhất:
  văn bản quan trọng hơn vị trí · rò rỉ qua giá ghi trong mô tả + bài học về lỗi gom tin trùng (chênh 0,08 giả → 0,01 thật) · tương quan ≠ nhân quả ("khép kín" rẻ hơn) ·
  nhiễu nhãn từ tin ở ghép / nhiều giá · khu giá thấp / khu giá cao (k = 2 ổn định) và "gói an ninh CCMN" ·
  nhiều cách cải tiến thuật toán không giúp → giới hạn nằm ở dữ liệu.
- Hạn chế + hướng phát triển.

---

## Gợi ý slide thuyết trình
1. Tiêu đề: "Trọ này có hớ không?" · 2. Vấn đề + demo 1 câu · 3. Dữ liệu (3 nguồn, số tin, khó khăn) ·
4. Làm sạch + rò rỉ dữ liệu · 5. Đặc trưng · 6. So sánh mô hình · 7. Ablation (văn bản > vị trí) ·
8. Từ nào kéo giá lên/xuống (hình 06) · 9. Phân tích lỗi + phân loại loại tin · 10. Bản đồ cụm (hình 09) ·
11. Luật kết hợp · 12. Demo trực tiếp · 13. Kết luận + hạn chế
