# Phân cụm khu vực trọ (đơn vị: phường)

60 phường có ≥ 10 tin phòng riêng. Đặc trưng chuẩn hóa z-score.

## So sánh bộ đặc trưng (k có silhouette tốt nhất của mỗi bộ)

| bộ đặc trưng                          |   k |   silhouette |   davies_bouldin |   calinski_harabasz |
|:--------------------------------------|----:|-------------:|-----------------:|--------------------:|
| giá + vị trí (4)                      |   2 |        0.394 |            0.955 |              46.735 |
| gọn: giá/m² + vị trí + 4 tiện ích (7) |   2 |        0.287 |            1.294 |              28.663 |
| đầy đủ (15)                           |   2 |        0.236 |            1.551 |              21.078 |

Thêm nhiều đặc trưng tỉ lệ tiện ích làm cấu trúc cụm mờ đi (ít điểm, nhiều chiều nhiễu). Dùng bộ **gọn: giá/m² + vị trí + 4 tiện ích (7)**: cân bằng giữa chất lượng cụm và khả năng diễn giải.

## Chọn số cụm cho K-Means

|   k |   inertia |   silhouette |   davies_bouldin |   calinski_harabasz |
|----:|----------:|-------------:|-----------------:|--------------------:|
|   2 |   281.089 |        0.287 |            1.294 |              28.663 |
|   3 |   218.45  |        0.239 |            1.234 |              26.295 |
|   4 |   191.203 |        0.23  |            1.244 |              22.337 |
|   5 |   165.353 |        0.221 |            1.335 |              21.175 |
|   6 |   147.402 |        0.213 |            1.211 |              19.973 |
|   7 |   137.839 |        0.209 |            1.167 |              18.082 |
|   8 |   127.638 |        0.201 |            1.149 |              17.015 |

Quy tắc: trong các k có silhouette ≥ 90% mức tốt nhất, chọn k có Davies-Bouldin nhỏ nhất → **k = 2** (silhouette càng lớn càng tốt, Davies-Bouldin càng nhỏ càng tốt).

## So sánh thuật toán

| thuật toán                       |   số cụm |   điểm nhiễu |   silhouette |   davies_bouldin |   calinski_harabasz |   ARI so với K-Means |
|:---------------------------------|---------:|-------------:|-------------:|-----------------:|--------------------:|---------------------:|
| K-Means (k=2)                    |        2 |            0 |        0.287 |            1.294 |              28.663 |                1     |
| Agglomerative Ward (k=2)         |        2 |            0 |        0.288 |            1.253 |              22.285 |                0.428 |
| DBSCAN (eps=2.68, min_samples=5) |        1 |            3 |      nan     |          nan     |             nan     |                0.025 |

ARI (Adjusted Rand Index) đo mức độ hai cách phân cụm giống nhau (1 = trùng hoàn toàn).

## Độ ổn định (200 mẫu con, mỗi mẫu 80% số phường)

Tỉ lệ mỗi k được quy tắc chọn: k = 2: 75.5%, k = 3: 17.5%, k = 4: 3.5%, k = 5: 2.0%, k = 6: 1.5%.

ARI giữa cụm K-Means (k = 2) học trên mẫu con và trên toàn bộ: trung vị 0.93, khoảng 10–90%: 0.81 – 1.00. Số cụm dao động giữa các mẫu là dấu hiệu dữ liệu không có cấu trúc cụm rõ.

## Hồ sơ các cụm (K-Means, trung vị theo phường; cụm 1 = giá/m² thấp nhất)

|                                   | 1                                                                      | 2                                                                    |
|:----------------------------------|:-----------------------------------------------------------------------|:---------------------------------------------------------------------|
| so_phuong                         | 23                                                                     | 37                                                                   |
| so_tin                            | 1046                                                                   | 6046                                                                 |
| ppm_median                        | 104.08                                                                 | 140.0                                                                |
| dist_center_km                    | 7.67                                                                   | 6.34                                                                 |
| dist_min_uni_km                   | 5.21                                                                   | 1.98                                                                 |
| p_kw_full_do                      | 0.26                                                                   | 0.41                                                                 |
| p_kw_thang_may                    | 0.14                                                                   | 0.24                                                                 |
| p_kw_khep_kin                     | 0.45                                                                   | 0.38                                                                 |
| p_kw_ccmn                         | 0.05                                                                   | 0.12                                                                 |
| phường tiêu biểu (nhiều tin nhất) | Phường Vĩnh Tuy, Phường Đông Ngạc, Phường Hoàng Mai, Phường Hoàng Liệt | Phường Từ Liêm, Phường Định Công, Phường Hà Đông, Phường Khương Đình |
