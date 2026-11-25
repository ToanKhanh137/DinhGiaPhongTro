# Ước lượng giá thuê phòng trọ tại Hà Nội

Đồ án môn Nhập môn Học máy và Khai phá dữ liệu (IT3190), nhóm 9, học kỳ 2026.1.

Nhóm tự thu thập tin cho thuê phòng trọ ở Hà Nội từ Chợ Tốt, Phongtro123 và Mogi, rồi xây mô hình ước lượng giá thuê.
Người dùng nhập diện tích, vị trí, nội thất và mô tả phòng (hoặc dán link tin đăng); hệ thống trả về giá ước tính,
khoảng giá 80% của các phòng tương tự và nhận xét giá chủ trọ đưa ra là đắt, hợp lý hay rẻ.

Đồ án đang thực hiện. Việc tiếp theo của từng thành viên ở mục [Tiến độ và phân công](#tiến-độ-và-phân-công).

## Kết quả hiện tại

Dữ liệu đến 15/11/2026 (sẽ chạy lại khi chốt dữ liệu): 10.079 tin sau làm sạch, trong đó 7.409 tin phòng riêng dùng
cho mô hình giá.
Đánh giá bằng GroupKFold 5-fold (các tin của cùng một phòng luôn nằm cùng một phía train hoặc test).

| Mô hình | MAE (triệu) | MAPE | R² |
|---|---|---|---|
| Đoán bằng giá trung bình | 1,08 | 33,4% | −0,03 |
| Linear Regression / Ridge | 0,68 | 19,5% | 0,55 |
| Random Forest | 0,65 | 18,6% | 0,58 |
| HistGradientBoosting | 0,64 | 18,2% | 0,60 |
| Ridge + TF-IDF | 0,60 | 17,2% | 0,64 |
| 0,7 × (Ridge + TF-IDF) + 0,3 × HistGradientBoosting | 0,58 | 16,5% | 0,66 |

- Trên 1.618 tin đăng xuất hiện sau thời điểm huấn luyện: MAPE 17,3%.
- Phân loại loại tin (phòng riêng / ở ghép / nhiều mức giá) để lọc nhiễu: macro-F1 0,88.
- Phân cụm 60 phường: tách được khu giá thấp và khu giá cao. Luật kết hợp (Apriori) giữa tiện ích và mức giá.

Báo cáo chi tiết: `docs/BAO_CAO_NHAP.md`.

## Cách chạy

Cần Python 3.10 trở lên. Repo không chứa dữ liệu và mô hình đã huấn luyện (xem `data/README.md`).

```bash
pip install -r requirements.txt
python src/crawl_all.py        # thu thập dữ liệu (bỏ qua nếu đã có thư mục data/)
python src/run_pipeline.py     # làm sạch, huấn luyện, đánh giá, phân cụm, luật kết hợp (~25 phút)
python -m pytest tests -q      # kiểm thử
python web/server.py --open    # web demo tại http://localhost:8000
```

## Cấu trúc

| Thư mục / file | Nội dung |
|---|---|
| `src/crawl_*.py` | thu thập tin đăng từ 3 trang |
| `src/build_dataset.py` | gộp nguồn, làm sạch, gom tin trùng |
| `src/features.py` | đặc trưng: diện tích, vị trí, từ khóa tiện ích, TF-IDF mô tả |
| `src/listing_type.py`, `src/label_*.py` | phân loại loại tin, gán nhãn, đo độ đồng thuận nhãn |
| `src/train.py`, `src/experiments.py`, `src/extra_experiments.py` | mô hình giá và các thí nghiệm |
| `src/intervals.py`, `src/temporal_validation.py`, `src/error_analysis.py` | khoảng giá, kiểm tra trên tin mới, phân tích lỗi |
| `src/clustering.py`, `src/association_rules.py` | phân cụm khu vực, luật kết hợp |
| `src/run_pipeline.py` | chạy tất cả các bước theo thứ tự |
| `web/` | web demo |
| `reports/` | bảng kết quả và hình |
| `docs/` | báo cáo nháp, hướng dẫn gán nhãn, ảnh chụp demo |
| `tests/` | kiểm thử |

## Dữ liệu

Thu thập theo robots.txt của từng trang, giãn cách 1,5 giây giữa các request. Không lưu tên, tài khoản người đăng;
số điện thoại trong mô tả được che. Dữ liệu chỉ dùng cho học tập và không công bố lại.

## Tiến độ và phân công

Đã xong: thu thập 7 lượt dữ liệu (08/10 – 15/11), làm sạch, mô hình giá, khoảng giá, kiểm tra trên tin mới, phân loại
loại tin, phân cụm, luật kết hợp, web demo, báo cáo nháp.

Mốc: **M1** nộp báo cáo tiến độ · **M2** chốt dữ liệu và thí nghiệm bổ sung · **M3** nộp báo cáo cuối kỳ ·
**M4** thuyết trình, vấn đáp. Xong việc nào thì đánh dấu việc đó.

**Phạm Thành Trung**
- [ ] Đưa thư mục `data/` lên Drive của nhóm; xong khi cả nhóm tải về chạy được (M1)
- [ ] Crawl thêm ít nhất 2 lượt, mỗi lượt ghi số tin mới (M2)
- [ ] Viết chương Dữ liệu của báo cáo cuối kỳ (M3)
- [ ] Rà soát số liệu báo cáo cuối kỳ với `reports/` và với đề xuất đã nộp (M3)

**Lê Tuấn Trung**
- [ ] Bảng nguyên nhân 30 tin bị đoán sai nặng nhất (M2)
- [ ] Thí nghiệm khoảng giá bằng hồi quy phân vị, so với cách hiện tại (M2)
- [ ] Viết các mục đặc trưng, ablation, tinh chỉnh siêu tham số, phân tích lỗi (M3)

**Trần Việt Gia Khánh**
- [ ] Gán độc lập 100 tin bằng `src/label_tool.py`, đo độ đồng thuận nhãn (M2)
- [ ] Viết các mục phân loại loại tin (M3)
- [ ] Slide thuyết trình 12 phút (M4)

**Hà Trọng Thắng**
- [ ] Rà README cho người mới; gắn tag `bao-cao-tien-do` khi nộp báo cáo tiến độ (M1)
- [ ] Clone về máy khác, chạy lại toàn bộ theo README; xong khi test pass và web chạy (M2)
- [ ] Viết các mục phân cụm, luật kết hợp, web demo, cấu trúc mã nguồn (M3)
- [ ] Kịch bản demo 3 tình huống và video dự phòng (M4)

**Nguyễn Khánh Toàn**
- [x] Tạo repo GitHub
- [ ] Thêm thành viên vào repo; nộp báo cáo tiến độ (M1)
- [ ] Chạy lại pipeline với dữ liệu đã chốt, cập nhật số liệu (M2)
- [ ] Viết các mục mô hình giá, đánh giá, khoảng giá, kết luận; ghép báo cáo cuối kỳ (M3)
- [ ] Tổ chức buổi hỏi chéo trước vấn đáp (M4)
