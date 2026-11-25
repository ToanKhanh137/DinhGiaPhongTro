# Phân loại loại tin đăng (R = phòng riêng, G = ở ghép, N = nhiều phòng / khoảng giá)

538 tin có nhãn: {'R': 299, 'N': 165, 'G': 74}; trong đó 300 tin chọn ngẫu nhiên (phân bố thật: {'R': 212, 'N': 67, 'G': 21}). Đánh giá: Stratified 5-fold lặp 5 lần trên cả 538 tin; cột "ngẫu nhiên" chỉ chấm trên các tin chọn ngẫu nhiên (khách quan).

## So sánh phương pháp

| phương pháp                                             |   macro-F1 (cả 540) |   macro-F1 (ngẫu nhiên) |   accuracy (ngẫu nhiên) |   ± macro-F1 (ngẫu nhiên) |
|:--------------------------------------------------------|--------------------:|------------------------:|------------------------:|--------------------------:|
| Luật regex                                              |               0.803 |                   0.745 |                   0.83  |                     0     |
| Luật regex v2 (+ đếm mức giá)                           |               0.87  |                   0.876 |                   0.91  |                     0     |
| TF-IDF từ + Logistic Regression                         |               0.803 |                   0.789 |                   0.805 |                     0.011 |
| TF-IDF từ + Naive Bayes                                 |               0.717 |                   0.704 |                   0.781 |                     0.008 |
| TF-IDF từ + Linear SVM                                  |               0.795 |                   0.785 |                   0.807 |                     0.014 |
| TF-IDF ký tự + Linear SVM                               |               0.793 |                   0.772 |                   0.807 |                     0.022 |
| Luật + TF-IDF từ + Logistic Regression                  |               0.813 |                   0.749 |                   0.831 |                     0.006 |
| Luật v2 + đếm mức giá + TF-IDF từ + Logistic Regression |               0.884 |                   0.876 |                   0.91  |                     0     |

Cao nhất: Luật regex v2 (+ đếm mức giá) (0.876). Chọn phương pháp đơn giản nhất (luật trước, rồi đến mô hình học máy) trong khoảng 0.01 so với điểm cao nhất: **Luật regex v2 (+ đếm mức giá)** (0.876). Lưu ý: luật v2 và đặc trưng đếm mức giá được thêm SAU KHI xem lỗi trên mẫu ngẫu nhiên, nên điểm của chúng trên mẫu này hơi lạc quan.

## Luật regex — chấm trên 300 tin ngẫu nhiên

```
              precision    recall  f1-score   support

           R      0.824     0.972     0.892       212
           G      0.741     0.952     0.833        21
           N      1.000     0.343     0.511        67

    accuracy                          0.830       300
   macro avg      0.855     0.756     0.745       300
weighted avg      0.857     0.830     0.803       300
```

Ma trận nhầm lẫn:

|        |   đoán R |   đoán G |   đoán N |
|:-------|---------:|---------:|---------:|
| thật R |      206 |        6 |        0 |
| thật G |        1 |       20 |        0 |
| thật N |       43 |        1 |       23 |

## Luật regex v2 (+ đếm mức giá) — chấm trên 300 tin ngẫu nhiên

```
              precision    recall  f1-score   support

           R      0.965     0.910     0.937       212
           G      0.741     0.952     0.833        21
           N      0.822     0.896     0.857        67

    accuracy                          0.910       300
   macro avg      0.843     0.919     0.876       300
weighted avg      0.917     0.910     0.912       300
```

Ma trận nhầm lẫn:

|        |   đoán R |   đoán G |   đoán N |
|:-------|---------:|---------:|---------:|
| thật R |      193 |        6 |       13 |
| thật G |        1 |       20 |        0 |
| thật N |        6 |        1 |       60 |

## Luật v1 và v2 trên từng mẫu

| phương pháp                   |   macro-F1 (theo luật) |   recall N (theo luật) |   macro-F1 (ngẫu nhiên) |   recall N (ngẫu nhiên) |
|:------------------------------|-----------------------:|-----------------------:|------------------------:|------------------------:|
| Luật regex                    |                  0.813 |                  0.776 |                   0.745 |                   0.343 |
| Luật regex v2 (+ đếm mức giá) |                  0.853 |                  0.898 |                   0.876 |                   0.896 |

## Ảnh hưởng của rà soát nhãn lần 2 (26/538 nhãn đổi)

Cùng dự đoán (lần lặp đầu của CV, mô hình học trên nhãn đã rà soát), chấm trên 300 tin ngẫu nhiên với nhãn cũ và nhãn đã rà soát. Phân bố thật trong mẫu ngẫu nhiên trước rà soát: {'R': 226, 'N': 53, 'G': 21}.

| phương pháp                                             |   macro-F1 ngẫu nhiên (nhãn cũ) |   macro-F1 ngẫu nhiên (đã rà soát) |
|:--------------------------------------------------------|--------------------------------:|-----------------------------------:|
| Luật regex                                              |                           0.737 |                              0.745 |
| Luật regex v2 (+ đếm mức giá)                           |                           0.837 |                              0.876 |
| TF-IDF từ + Logistic Regression                         |                           0.775 |                              0.789 |
| TF-IDF từ + Naive Bayes                                 |                           0.722 |                              0.698 |
| TF-IDF từ + Linear SVM                                  |                           0.763 |                              0.779 |
| TF-IDF ký tự + Linear SVM                               |                           0.741 |                              0.744 |
| Luật + TF-IDF từ + Logistic Regression                  |                           0.737 |                              0.745 |
| Luật v2 + đếm mức giá + TF-IDF từ + Logistic Regression |                           0.837 |                              0.876 |

## Gán nhãn toàn bộ 10079 tin bằng `Luật regex v2 (+ đếm mức giá)`

| listing_type   |   số tin |   giá trung vị (triệu) |   % dự đoán |   % thật (mẫu ngẫu nhiên) |
|:---------------|---------:|-----------------------:|------------:|--------------------------:|
| G              |      534 |                   1.65 |         5.3 |                       7   |
| N              |     2136 |                   3.5  |        21.2 |                      22.3 |
| R              |     7409 |                   3.6  |        73.5 |                      70.7 |

## Ảnh hưởng tới mô hình giá (Ridge + TF-IDF, GroupKFold 5-fold, chỉ chấm trên tin loại R)

| huấn luyện trên   |   số tin train |   MAE (triệu) |   MAPE (%) |    R2 |
|:------------------|---------------:|--------------:|-----------:|------:|
| tất cả các loại   |          10079 |         0.605 |     17.161 | 0.629 |
| chỉ loại R        |           7409 |         0.601 |     17.24  | 0.635 |
