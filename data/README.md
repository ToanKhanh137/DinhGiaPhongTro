# Thư mục dữ liệu

Dữ liệu **không có trên GitHub**: đây là tin đăng nhóm tự crawl, chỉ dùng cho học tập và không công bố lại. Thành viên
nhóm lấy bản đầy đủ từ thư mục Drive riêng của nhóm rồi chép vào đây, giữ nguyên cấu trúc:

```
data/
├── raw/         # dữ liệu thô từng lượt crawl (chotot.jsonl, phongtro123*.jsonl, mogi*.jsonl)
├── processed/   # rooms.csv, listing_type.csv, ward_clusters.csv do src/run_pipeline.py tạo
└── labels/      # nhãn tay loại tin (R / G / N), nhật ký rà soát, mẫu đo độ đồng thuận
```

Người ngoài nhóm có thể tự thu thập dữ liệu mới bằng `python src/crawl_all.py` (tạo `data/raw/`). Bước phân loại loại
tin trong `src/run_pipeline.py` cần thêm file nhãn `data/labels/listing_type_labels.csv`; nhóm cung cấp khi được yêu cầu.
