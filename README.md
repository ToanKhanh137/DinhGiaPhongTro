# Trọ này có hớ không? — Định giá phòng trọ Hà Nội

Đồ án môn **Nhập môn Học máy và Khai phá dữ liệu (IT3190)**, kỳ 2026.1.

Hệ thống ước lượng **giá thuê hợp lý + khoảng giá phổ biến** cho phòng trọ / căn hộ mini tại Hà Nội
từ dữ liệu tin đăng thực tế do nhóm tự thu thập, giúp sinh viên đánh giá một tin đăng đắt hay rẻ so với thị trường.

- **Input:** diện tích, quận/phường, tình trạng nội thất, mô tả tin đăng (tùy chọn).
- **Output:** giá ước tính (VND/tháng), khoảng giá 80%, đánh giá "hớ / hợp lý / hời" nếu nhập giá chủ trọ đưa ra.

Project dùng kiến thức của cả 4 chương: **tiền xử lý** (Ch. 2), **hồi quy** (Ch. 3), **phân cụm** (Ch. 4),
**phân loại** (Ch. 5), **luật kết hợp** (Ch. 6). Dàn ý báo cáo: `docs/DAN_Y_BAO_CAO.md`.

## Cấu trúc thư mục

```
DoAn_DinhGiaPhongTro/
├── src/
│   ├── common.py              # cấu hình, tọa độ các trường ĐH, hàm dùng chung
│   ├── crawl_chotot.py        # crawl Chợ Tốt (API JSON công khai, có tọa độ)
│   ├── crawl_phongtro123.py   # crawl phongtro123.com (HTML; --details lấy mô tả đầy đủ)
│   ├── crawl_mogi.py          # crawl mogi.vn (HTML; --details lấy địa chỉ + mô tả)
│   ├── crawl_all.py           # chạy mọi crawler một lượt, --loop-hours N để lặp
│   ├── build_dataset.py       # gộp 3 nguồn, làm sạch, bỏ trùng, gán tọa độ, group_id
│   ├── features.py            # đặc trưng (khoảng cách, từ khóa, văn bản đã che giá), load_rooms()
│   ├── listing_type.py        # PHÂN LOẠI loại tin: phòng riêng / ở ghép / nhiều mức giá
│   ├── train.py               # HỒI QUY: so sánh mô hình bằng GroupKFold, lưu mô hình tốt nhất
│   ├── intervals.py           # khoảng giá 80% thích nghi theo từng tin (conformal), kiểm tra độ phủ
│   ├── temporal_validation.py # kiểm tra trên tin đăng mới (train tin cũ, test tin xuất hiện sau)
│   ├── experiments.py         # thí nghiệm A–G: văn bản, tinh chỉnh (nested CV), ablation, tọa độ, alpha, kết hợp, phường
│   ├── extra_experiments.py   # thí nghiệm H–I: tham số TF-IDF, stacking Ridge -> HGB
│   ├── eda.py                 # hình vẽ EDA -> reports/figures/
│   ├── error_analysis.py      # phân tích lỗi -> reports/error_analysis.md
│   ├── label_agreement.py     # độ đồng thuận giữa hai người gán nhãn (Cohen's kappa)
│   ├── label_tool.py          # trang web cục bộ để người gán thứ hai gán 100 tin
│   ├── clustering.py          # PHÂN CỤM khu vực trọ (phường) -> reports/clustering.md
│   ├── association_rules.py   # LUẬT KẾT HỢP tiện ích ↔ mức giá (Apriori) -> reports/association_rules.md
│   └── run_pipeline.py        # chạy toàn bộ các bước trên theo thứ tự (ưu tiên CPU thấp)
├── crawl_dinh_ky.bat          # nhấp đúp: crawl lặp mỗi 12 giờ (treo máy)
├── chay_demo.bat              # nhấp đúp: mở demo web
├── web/                       # demo web: server.py (FastAPI + API dự đoán), static/ (HTML/CSS/JS)
├── app/app.py                 # bản demo cũ bằng Streamlit (giữ để tham khảo)
├── data/raw/                  # dữ liệu crawl (jsonl, append theo từng lần chạy)
├── data/labels/               # 540 nhãn tay (240 theo luật + 300 ngẫu nhiên); label_review_log.csv: nhật ký rà soát
├── data/processed/            # rooms.csv (dữ liệu sạch), listing_type.csv, ward_clusters.csv
├── models/                    # mô hình đã huấn luyện (data/ và models/ không có trên GitHub, xem data/README.md)
├── docs/                      # báo cáo nháp, dàn ý, hướng dẫn gán nhãn (HUONG_DAN_GAN_NHAN.md), ảnh chụp demo
├── tests/                     # unit test cho các hàm xử lý văn bản (python -m pytest tests -q)
└── reports/                   # nhật ký, bảng kết quả (.csv/.md), hình vẽ (figures/)
```

## Cài đặt và chạy

Yêu cầu Python ≥ 3.10.

Repo không chứa dữ liệu (`data/`) và mô hình đã huấn luyện (`models/`): dữ liệu crawl chỉ dùng nội bộ nhóm, xem
`data/README.md`. Thành viên nhóm chép thư mục `data/` từ Drive của nhóm rồi chạy từ bước 2.

```bash
pip install -r requirements.txt

# 1. Thu thập dữ liệu
python src/crawl_all.py                       # 1 lượt cả 3 nguồn (lượt đầu vài giờ, các lượt sau ~15 phút)
python src/crawl_all.py --loop-hours 12       # hoặc nhấp đúp crawl_dinh_ky.bat để treo máy

# 2. Làm sạch -> phân loại loại tin -> huấn luyện -> thí nghiệm -> EDA -> phân tích lỗi -> phân cụm -> luật kết hợp
python src/run_pipeline.py                    # ~25 phút (thí nghiệm có nested CV), RAM ~1 GB
python -m pytest tests -q                     # 53 test (xử lý văn bản, gom tin trùng, khoảng giá, API web)
python src/extra_experiments.py               # (tùy chọn) thí nghiệm H–I: tham số TF-IDF, stacking (~5 phút)

# 3. Demo web (hoặc nhấp đúp chay_demo.bat)
python web/server.py --open                   # mở http://localhost:8000
```

## Nguồn dữ liệu và đạo đức thu thập

| Nguồn | Cách lấy | Có tọa độ | Ghi chú |
|---|---|---|---|
| Chợ Tốt — mục Phòng trọ, Hà Nội | API JSON công khai mà website dùng | ✅ | có cả tên phường cũ và phường mới (sau sáp nhập 2025) |
| phongtro123.com — Hà Nội | parse HTML trang danh sách / chi tiết | ❌ | robots.txt cho phép; tọa độ suy ra từ phường mới. Phân trang chỉ hiển thị ~4.900 tin |
| mogi.vn — Hà Nội | parse HTML trang danh sách / chi tiết | ❌ | robots.txt cho phép; chỉ có phường cũ → đổi sang phường mới / tọa độ qua bảng đối chiếu từ Chợ Tốt |

- Crawl chậm (1.5 giây/request), chỉ phục vụ học tập, **không công khai lại dữ liệu thô**.
- **Không lưu tên, số điện thoại, tài khoản người đăng**; số điện thoại trong mô tả được thay bằng `<SĐT>`.
- Đã crawl 5 lượt: 8/10, 12/10, 16/10, 22/10, 1/11. Tin mới xuất hiện chậm, chủ yếu ở Chợ Tốt (~50 tin/ngày);
  từ 16/10 Mogi chỉ còn hiển thị ~18 trang (~260 tin).

## Phương pháp

1. **Tiền xử lý** (`build_dataset.py`, nhật ký từng bước trong `reports/cleaning_log.txt`):
   bỏ trùng, chuẩn hóa quận/phường, tách diện tích từ mô tả khi thiếu, lọc giá/diện tích/giá-m² bất thường.
2. **Phân loại loại tin** (`listing_type.py`): R = phòng riêng, G = ở ghép / KTX / homestay (giá theo người),
   N = nhiều phòng / khoảng giá. Mô hình giá chỉ học và đánh giá trên tin loại R (`features.load_rooms`).
3. **Đặc trưng** (`features.py`): diện tích, quận, nội thất, khoảng cách tới 7 trường ĐH lớn và trung tâm,
   23 từ khóa tiện ích, TF-IDF (n-gram từ 1–2) trên mô tả đã bỏ dấu.
   **Giá ghi trong mô tả ("5tr6", "giá 3,5 tr"...) được xóa trước khi tạo đặc trưng văn bản** (`mask_money`)
   để tránh rò rỉ nhãn.
4. **Hồi quy** (`train.py`): Dummy (baseline) → Linear / Ridge / Lasso → Random Forest / HistGradientBoosting
   → Ridge + TF-IDF → kết hợp Ridge + TF-IDF với HGB (trung bình có trọng số 0,7 / 0,3).
   Mục tiêu log(giá); metric MAE, RMSE, MAPE, R² trên thang VND.
   Alpha của Ridge + TF-IDF cố định = 1,0, chọn bằng GroupKFold (thí nghiệm E) — nhanh hơn RidgeCV ~50 lần.
5. **Đánh giá chống rò rỉ dữ liệu:** các tin của cùng một phòng (đăng lại / đăng nhiều nơi) luôn nằm cùng phía train
   hoặc test (**GroupKFold**). "Cùng một phòng" = cùng (phường, giá, diện tích có ghi) HOẶC cùng quận + mô tả giống nhau
   (cosine TF-IDF ≥ 0,85) + giá chênh ≤ 10% — thành phần liên thông của đồ thị các cặp (`build_dataset.room_groups`).
   Kiểm tra thêm trên **tin đăng mới** xuất hiện sau thời điểm huấn luyện (`temporal_validation.py`).
   **Khoảng giá 80% thích nghi theo từng tin** (normalized conformal prediction, `intervals.py`): loại tin khó đoán
   có khoảng rộng hơn; phân vị lấy riêng cho từng mức giá dự đoán; độ phủ được kiểm tra bằng GroupKFold.
6. **Phân cụm** (`clustering.py`): mỗi phường (≥ 10 tin) mô tả bằng giá/m², khoảng cách (log), tỉ lệ tiện ích;
   so sánh bộ đặc trưng, chọn k bằng Silhouette + Davies-Bouldin, so sánh K-Means / Agglomerative / DBSCAN.
7. **Luật kết hợp** (`association_rules.py`): Apriori trên tiện ích + mức giá (tam phân vị) + cụm khu vực.

## Kết quả hiện tại (15/11/2026)

10.079 tin sau làm sạch (7 lượt crawl 08/10 – 15/11), trong đó **7.409 tin phòng riêng** dùng cho mô hình giá.
GroupKFold 5-fold. **Báo cáo nháp đầy đủ: `docs/BAO_CAO_NHAP.md`.**

| Mô hình | MAE (triệu) | MAPE | R² |
|---|---|---|---|
| Dummy (trung bình) | 1,08 | 33,4% | −0,03 |
| Linear / Ridge | 0,68 | 19,5% | 0,55 |
| Random Forest | 0,65 | 18,6% | 0,58 |
| HistGradientBoosting | 0,64 | 18,2% | 0,60 |
| Ridge + TF-IDF | 0,60 | 17,2% | 0,64 |
| **Ridge + TF-IDF × 0,7 + HGB × 0,3** (dùng cho demo) | **0,58** | **16,5%** | **0,66** |
| Mô hình kết hợp, KFold ngẫu nhiên (bỏ qua tin trùng) | 0,56 | 16,1% | 0,67 |

Trên **tin đăng mới** (train tin đợt 8/10, test 1.618 tin xuất hiện 12/10 – 15/11): MAE 0,64 triệu, MAPE 17,3%;
riêng 1.293 phòng thật sự mới: MAPE 18,4%.

### Phát hiện chính

1. **Văn bản mô tả quan trọng hơn vị trí:** bỏ văn bản R² 0,64 → 0,41; bỏ diện tích → 0,56; bỏ vị trí chỉ → 0,63.
   TF-IDF hơn hẳn 23 từ khóa thủ công (0,64 so với 0,55).
2. **Những thứ đã thử mà không giúp:** TF-IDF ký tự, đặc trưng phường, tinh chỉnh tham số TF-IDF (± 0,003 R²),
   tinh chỉnh HGB (nested CV R² 0,613, bằng mặc định), stacking Ridge → HGB (0,657 so với 0,659 của trung bình
   có trọng số) → giới hạn nằm ở thông tin trong dữ liệu, không ở thuật toán.
3. **Rò rỉ dữ liệu — và một lỗi đã sửa:** giá ghi trong mô tả (~60% tin) được che bằng `mask_money` (có test).
   Với tin trùng, phiên bản đầu chỉ gom theo (phường, giá, diện tích) và gom nhầm mọi tin *thiếu* diện tích cùng phường,
   cùng giá thành một "phòng" (nhóm > 1.200 tin) → các fold lệch phân bố, điểm GroupKFold thấp giả và chênh lệch với
   KFold ngẫu nhiên (~0,08) bị hiểu nhầm là rò rỉ. Sau khi gom theo cặp tin (khóa trùng hoặc mô tả giống ≥ 85%), chênh
   lệch thật chỉ ~0,01.
4. **Tọa độ chính xác không giúp thêm** so với tọa độ trung vị phường (R² 0,587 vs 0,588 trên tin Chợ Tốt).
5. **Khoảng giá thích nghi** (conformal, phân vị theo mức giá dự đoán): một độ rộng chung phủ thiếu ở tin được đoán
   giá thấp (69%) và thừa ở Mogi (88%); cách mới phủ 79,0–80,0% ở mọi mức giá dự đoán, 78,3–81,7% ở mọi nguồn, độ rộng
   trung bình giảm nhẹ (1,83 → 1,78 triệu). Mô hình độ khó phải nông: bản sâu trước đây làm khoảng rộng thừa ~6%.
   Trên tin đăng mới độ phủ còn ~79% (một độ rộng chung: 77%) — `reports/temporal_validation.md`.
6. **Phân tích lỗi:** phân khúc 2–5 triệu MAPE 13–17%; 70% tin sai số ≤ 20%. Theo giá thật thì "co về trung bình"
   (phòng ≤ 2 triệu bị đoán cao 33%), nhưng theo giá dự đoán mô hình lệch không quá 3% và kéo giãn dự đoán không giảm
   sai số — đây là giới hạn thông tin của mô tả, không phải lỗi hiệu chỉnh.
7. **Phân loại loại tin** (540 nhãn tay, 300 ngẫu nhiên để đánh giá khách quan; đã rà soát lần 2 theo
   `docs/HUONG_DAN_GAN_NHAN.md`, sửa 26 nhãn R → N): luật regex 0,75 macro-F1 trên mẫu ngẫu nhiên (0,81 trên mẫu chọn
   theo luật — lạc quan); **luật v2 đếm số mức giá: 0,88** (ngang mô hình luật v2 + TF-IDF + LR 0,88 → chọn luật vì
   đơn giản hơn). Chỉ học trên phòng riêng: R² 0,629 → 0,635.
8. **Phân cụm** (60 phường): cách chia ổn định duy nhất là **khu giá thấp** (~104k/m², xa trường ĐH) và **khu giá cao**
   (~140k/m², gần trường, nhiều chung cư mini) — k = 2 được chọn ở 76% trong 200 mẫu con, ARI 0,93; các cách chia mịn
   hơn không ổn định. Silhouette 0,20–0,29 → cấu trúc cụm yếu.
9. **Luật kết hợp:** {1 ngủ, máy giặt} → giá cao (lift 2,5); {gác xép, khép kín} → giá thấp (lift 1,6);
   "gói an ninh CCMN" camera – vân tay – thang máy – ban công (lift 4,1–4,2).
10. **Tương quan ≠ nhân quả:** tin nhắc "khép kín" có giá trung vị thấp hơn ~13%.

## Hạn chế đã biết

- Giá là **giá niêm yết**, không phải giá chốt hợp đồng.
- Tọa độ tin Phongtro123 / Mogi chỉ chính xác tới mức phường (cột `geo_precision`).
- Tọa độ các trường ĐH trong `common.py` là gần đúng.
- Dữ liệu trong hơn 5 tuần (08/10 – 15/11), giá trọ có tính mùa vụ (cao điểm tháng 8–9).
- Nhãn loại tin chỉ có 540 tin; độ đồng thuận mới đo trên 100 tin gán lại độc lập (kappa 0,85); luật v2 được
  thiết kế sau khi xem lỗi trên mẫu ngẫu nhiên. Số cụm và thứ tự cụm có thể đổi giữa các lần chạy.

## Việc tiếp theo (gợi ý chia việc)

- [x] Rà lại 540 nhãn tay (04/11, theo `docs/HUONG_DAN_GAN_NHAN.md`; nhật ký `data/labels/label_review_log.csv`)
- [x] Đo độ đồng thuận nhãn: 100 tin gán lại độc lập bằng `python src/label_tool.py`, trùng 94/100, Cohen's kappa 0,85 (0,72–0,95) — `reports/label_agreement.md`
- [ ] Chạy crawl định kỳ thêm vài tuần (`crawl_dinh_ky.bat`), rồi `run_pipeline.py` lấy số liệu cuối
- [x] Nested CV cho phần tinh chỉnh HGB (thí nghiệm B)
- [x] Kết hợp Ridge-TF-IDF + HGB (thí nghiệm F, đang dùng cho demo); kiểm tra trên tin mới
- [x] Thử TF-IDF ký tự, đặc trưng phường (không cải thiện); tinh chỉnh TF-IDF và stacking Ridge → HGB (`docs/BAO_CAO_NHAP.md`)
- [x] Khoảng giá thích nghi theo từng tin và theo mức giá dự đoán (`src/intervals.py`, cập nhật 15/11)
- [x] Giao diện web (`web/`), 3 trang:
  - **Định giá**: dán link tin đăng (Chợ Tốt / Nhà Tốt / Phongtro123 / Mogi) để tự điền, hoặc nhập tay; giá ước tính +
    khoảng giá + nhận xét so với giá chủ trọ; nhận diện loại tin (phòng riêng / ở ghép / nhiều mức giá); "Vì sao ra giá
    này?" (đóng góp từng yếu tố, phần tuyến tính của mô hình); "Nếu tin có thêm…" (định giá lại khi thêm tiện ích);
    so sánh với các phòng tương tự; kéo thanh diện tích để định giá lại ngay
  - **Bản đồ giá**: mặt bằng giá / m² và giá trung vị theo phường (Leaflet; nền bản đồ Esri xám sáng / tối, dự phòng
    OpenStreetMap vì một số mạng chặn máy chủ ô bản đồ OSM; cần Internet cho nền bản đồ),
    xếp hạng quận
  - **Về mô hình**: số liệu đánh giá, so sánh mô hình, ablation, kiểm tra trên tin mới
  - Font và thư viện bản đồ lưu sẵn trong `web/static/vendor/` → chạy được không cần mạng (trừ nền bản đồ);
    giao diện sáng / tối theo hệ điều hành (ép bằng `?theme=light` hoặc `?theme=dark`), dùng được trên điện thoại;
    "Đã kiểm tra gần đây" lưu 6 tin vừa định giá trong trình duyệt (tiện chuyển qua lại khi demo)
- [x] Báo cáo nháp `docs/BAO_CAO_NHAP.md` (đã chèn 14 hình kèm chú thích) — nhóm điền phân công, chỉnh văn rồi xuất PDF
- [ ] Slide 12 phút (gợi ý cấu trúc trong `docs/DAN_Y_BAO_CAO.md`)
