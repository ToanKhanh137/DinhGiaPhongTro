# Kiểm tra trên tin đăng mới (train: thấy trước 2026-10-12, test: thấy từ 2026-10-12)

Train 5791 tin phòng riêng. Test 1618 tin: 325 tin đăng lại (cùng phòng với một tin trong train) và 1293 tin thật sự mới.

Ngày xuất hiện của tin test: {'2026-10-12': 153, '2026-10-16': 154, '2026-10-22': 288, '2026-11-01': 448, '2026-11-04': 76, '2026-11-15': 499}. Nguồn: {'chotot': 1533, 'phongtro123': 57, 'mogi': 28}.

| mô hình                          | tập test            |   số tin |   MAE (triệu) |   RMSE (triệu) |   MAPE (%) |     R2 |
|:---------------------------------|:--------------------|---------:|--------------:|---------------:|-----------:|-------:|
| Dummy (trung bình)               | tất cả tin mới      |     1618 |         1.191 |          1.614 |     32.382 | -0.156 |
| Dummy (trung bình)               | chỉ tin thật sự mới |     1293 |         1.259 |          1.713 |     33.177 | -0.194 |
| Dummy (trung bình)               | chỉ tin đăng lại    |      325 |         0.919 |          1.138 |     29.217 | -0.035 |
| HistGradientBoosting             | tất cả tin mới      |     1618 |         0.713 |          1.013 |     19.148 |  0.544 |
| HistGradientBoosting             | chỉ tin thật sự mới |     1293 |         0.751 |          1.069 |     20.092 |  0.536 |
| HistGradientBoosting             | chỉ tin đăng lại    |      325 |         0.561 |          0.755 |     15.395 |  0.545 |
| Ridge + TF-IDF                   | tất cả tin mới      |     1618 |         0.663 |          0.932 |     17.945 |  0.615 |
| Ridge + TF-IDF                   | chỉ tin thật sự mới |     1293 |         0.705 |          0.988 |     18.959 |  0.603 |
| Ridge + TF-IDF                   | chỉ tin đăng lại    |      325 |         0.497 |          0.662 |     13.908 |  0.649 |
| Ridge + TF-IDF × 0.7 + HGB × 0.3 | tất cả tin mới      |     1618 |         0.642 |          0.91  |     17.337 |  0.633 |
| Ridge + TF-IDF × 0.7 + HGB × 0.3 | chỉ tin thật sự mới |     1293 |         0.683 |          0.965 |     18.378 |  0.621 |
| Ridge + TF-IDF × 0.7 + HGB × 0.3 | chỉ tin đăng lại    |      325 |         0.478 |          0.646 |     13.197 |  0.666 |

So sánh với GroupKFold trong `model_comparison.csv`: nếu sai số trên tin mới tương đương thì mô hình không bị quá khớp vào thời điểm crawl. Lưu ý tập test nhỏ và gần như chỉ từ Chợ Tốt (các trang khác ít tin mới).

## Khoảng giá 80% trên tin mới (Ridge + TF-IDF × 0.7 + HGB × 0.3)

Phần dư, mô hình độ khó và phân vị đều chỉ khớp trên train. Mục tiêu: độ phủ 80%, mỗi phía ngoài khoảng 10%.

| cách tính                         | tập test            |   số tin |   độ phủ (%) |   giá thật dưới khoảng (%) |   giá thật trên khoảng (%) |   độ rộng TB (triệu) |
|:----------------------------------|:--------------------|---------:|-------------:|---------------------------:|---------------------------:|---------------------:|
| một độ rộng chung                 | tất cả tin mới      |     1618 |        77.13 |                      11.43 |                      11.43 |                 1.95 |
| một độ rộng chung                 | chỉ tin thật sự mới |     1293 |        74.94 |                      12.99 |                      12.06 |                 2    |
| một độ rộng chung                 | chỉ tin đăng lại    |      325 |        85.85 |                       5.23 |                       8.92 |                 1.75 |
| thích nghi theo tin               | tất cả tin mới      |     1618 |        79.6  |                      10.69 |                       9.7  |                 2.11 |
| thích nghi theo tin               | chỉ tin thật sự mới |     1293 |        77.8  |                      12.14 |                      10.05 |                 2.18 |
| thích nghi theo tin               | chỉ tin đăng lại    |      325 |        86.77 |                       4.92 |                       8.31 |                 1.8  |
| thích nghi + theo mức giá dự đoán | tất cả tin mới      |     1618 |        78.92 |                      10.75 |                      10.32 |                 2.05 |
| thích nghi + theo mức giá dự đoán | chỉ tin thật sự mới |     1293 |        77.18 |                      12.14 |                      10.67 |                 2.11 |
| thích nghi + theo mức giá dự đoán | chỉ tin đăng lại    |      325 |        85.85 |                       5.23 |                       8.92 |                 1.79 |
