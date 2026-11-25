# Phân tích lỗi — Ridge + TF-IDF (dự đoán out-of-fold, GroupKFold 5-fold)

Tổng: 7409 tin. MAE = 0.598 triệu, MAPE = 17.2%, 70% tin có sai số ≤ 20%.

## Theo khoảng giá

| khoảng giá   |   số tin |   giá TB (triệu) |   MAE (triệu) |   MAPE (%) |   đoán lệch TB (%) |
|:-------------|---------:|-----------------:|--------------:|-----------:|-------------------:|
| ≤2tr         |      779 |             1.66 |          0.53 |      36.06 |              32.99 |
| 2-3tr        |     1877 |             2.67 |          0.46 |      17.37 |               7.51 |
| 3-4tr        |     2223 |             3.63 |          0.46 |      12.82 |               0.32 |
| 4-5tr        |     1495 |             4.58 |          0.62 |      13.45 |              -4.86 |
| 5-7tr        |      888 |             5.82 |          0.92 |      15.59 |             -11.96 |
| 7-10tr       |      127 |             8.23 |          2.09 |      25.05 |             -24.36 |
| >10tr        |       20 |            12.74 |          5.52 |      41.01 |             -40.8  |

## Mô hình có lệch có hệ thống không? (nhóm theo giá dự đoán)

Bảng "Theo khoảng giá" ở trên nhóm theo giá THẬT nên luôn cho thấy "co về trung bình" (phòng rẻ bị đoán cao, phòng đắt bị đoán thấp) với mọi mô hình chưa hoàn hảo. Câu hỏi đúng cho người dùng là: khi mô hình báo một mức giá, giá thật trung bình có đúng mức đó không?

| mức giá dự đoán   |   số tin |   giá dự đoán TB (triệu) |   giá thật TB (triệu) |   đoán lệch (thang log, %) |
|:------------------|---------:|-------------------------:|----------------------:|---------------------------:|
| <2,5tr            |     1240 |                     2.07 |                  2.14 |                        0   |
| 2,5-3tr           |     1054 |                     2.75 |                  2.89 |                       -2.3 |
| 3-3,5tr           |     1205 |                     3.26 |                  3.35 |                       -0.3 |
| 3,5-4tr           |     1263 |                     3.74 |                  3.86 |                       -1   |
| 4-5tr             |     1736 |                     4.43 |                  4.49 |                        0.6 |
| >5tr              |      911 |                     5.81 |                  5.81 |                        2.5 |

Hồi quy log giá thật theo log giá dự đoán: hệ số góc = 0.980 (1,000 là lý tưởng). Thử kéo giãn dự đoán theo đường hồi quy này (hệ số lấy từ các fold khác): MAE 0.598 → 0.596 triệu, MAPE 17.16% → 17.16%. Lệch lớn nhất giữa các mức giá dự đoán là 2.5% (so với hàng chục % khi nhóm theo giá thật). Nếu con số này nhỏ và kéo giãn không giảm sai số thì hiện tượng co về trung bình theo giá thật đến từ phần biến động giá mà đặc trưng không giải thích được, không sửa được bằng hiệu chỉnh sau.

## Theo nguồn

| source      |   số tin |   giá TB (triệu) |   MAE (triệu) |   MAPE (%) |   đoán lệch TB (%) |
|:------------|---------:|-----------------:|--------------:|-----------:|-------------------:|
| chotot      |     2760 |             4.12 |          0.7  |      18.18 |               2.95 |
| mogi        |     1221 |             3.92 |          0.5  |      13.8  |               1.59 |
| phongtro123 |     3428 |             3.36 |          0.55 |      17.53 |               2.52 |

## Theo độ chính xác tọa độ

| geo_precision   |   số tin |   giá TB (triệu) |   MAE (triệu) |   MAPE (%) |   đoán lệch TB (%) |
|:----------------|---------:|-----------------:|--------------:|-----------:|-------------------:|
| district        |      395 |             3.65 |          0.59 |      18.3  |               3.49 |
| exact           |     2760 |             4.12 |          0.7  |      18.18 |               2.95 |
| ward            |     4254 |             3.5  |          0.53 |      16.39 |               2.16 |

## Có ghi diện tích không

| ghi diện tích   |   số tin |   giá TB (triệu) |   MAE (triệu) |   MAPE (%) |   đoán lệch TB (%) |
|:----------------|---------:|-----------------:|--------------:|-----------:|-------------------:|
| có              |     5997 |             3.56 |          0.57 |      17.14 |               2.38 |
| không           |     1412 |             4.48 |          0.72 |      17.26 |               3.13 |

## Theo quận (≥ 50 tin)

| district     |   số tin |   giá TB (triệu) |   MAE (triệu) |   MAPE (%) |   đoán lệch TB (%) |
|:-------------|---------:|-----------------:|--------------:|-----------:|-------------------:|
| Nam Từ Liêm  |      843 |             3.83 |          0.55 |      15.12 |               1.92 |
| Thanh Trì    |      341 |             3.31 |          0.46 |      15.25 |               2.16 |
| Hà Đông      |      631 |             3.43 |          0.49 |      15.26 |               2.44 |
| Tây Hồ       |      350 |             3.69 |          0.55 |      15.6  |               1.43 |
| Cầu Giấy     |      890 |             4.12 |          0.62 |      15.97 |               2.27 |
| Thanh Xuân   |      787 |             3.89 |          0.6  |      16.4  |               2.21 |
| Bắc Từ Liêm  |      536 |             3.37 |          0.53 |      16.84 |               2.44 |
| Hoàng Mai    |     1051 |             3.73 |          0.63 |      18.34 |               2.59 |
| Hoài Đức     |      109 |             2.95 |          0.52 |      18.44 |               2.09 |
| Ba Đình      |      305 |             4.01 |          0.72 |      18.74 |               2.6  |
| Đống Đa      |      807 |             4.22 |          0.73 |      18.84 |               3.66 |
| Long Biên    |      171 |             2.88 |          0.56 |      19.4  |               2.44 |
| Hai Bà Trưng |      413 |             3.65 |          0.66 |      19.79 |               2.98 |
| Hoàn Kiếm    |       66 |             3.45 |          0.63 |      20.5  |               4.09 |

## Từ / cụm từ ảnh hưởng mạnh nhất (hệ số Ridge trên log giá)

Hệ số dương: tin có cụm từ này thường đắt hơn; âm: rẻ hơn (văn bản đã bỏ dấu, đã che giá).

|            |   hệ số |
|:-----------|--------:|
| 2n1k       |   0.872 |
| 1n1k       |   0.636 |
| nguyen du  |   0.429 |
| giat rieng |   0.394 |
| tro 2n1k   |   0.383 |
| khach      |   0.376 |
| 2n1k full  |   0.364 |
| sinh khep  |   0.357 |
| ib         |   0.34  |
| phong 2n1k |   0.338 |
| lon        |   0.32  |
| loc        |   0.308 |
| n1k        |   0.304 |
| moi        |   0.303 |
| van phong  |   0.302 |
| duong noi  |   0.299 |
| pccc       |   0.295 |
| ib lh      |   0.293 |
| tay        |   0.287 |
| da thang   |   0.281 |
| vsc        |  -0.51  |
| sinh chung |  -0.451 |
| tro        |  -0.415 |
| re         |  -0.407 |
| khong khep |  -0.404 |
| nha cap    |  -0.356 |
| nuoc       |  -0.352 |
| phong tro  |  -0.348 |
| kin rong   |  -0.342 |
| co         |  -0.327 |
| vien thue  |  -0.318 |
| gom dien   |  -0.301 |
| free dich  |  -0.301 |
| wifi cho   |  -0.292 |
| tro khu    |  -0.284 |
| co phong   |  -0.281 |
| dan cu     |  -0.277 |
| da day     |  -0.274 |
| lai ngay   |  -0.272 |
| rieng chu  |  -0.272 |

## 15 tin bị đoán sai nhiều nhất (đọc tay để tìm nguyên nhân)

| id           | source      | district    |   size |   price |   pred | text                                                                                                                                              |
|:-------------|:------------|:------------|-------:|--------:|-------:|:--------------------------------------------------------------------------------------------------------------------------------------------------|
| ct_134714619 | chotot      | Đống Đa     |    nan |    0.5  |   5.19 | Phòng trọ Đống Đa, 1 Ngủ, Full nội thất, Ô tô đỗ cửa 📢 📢 TRUNG TÂM ĐỐNG ĐA - BAN CÔNG & CỬA SỔ THOÁNG 💯 1 Ngủ 1 Bếp - 5xx (tiểu học) - Ô tô    |
| mg_22109565  | mogi        | Đống Đa     |     45 |    1.5  |   5.48 | Phòng trọ mới, đầy đủ tiện nghi, giá tốt, free dịch vụ - Phòng trọ cho thuê với vị trí vô cùng thuận tiện gần các trường Đại học Thủy lợi, Đ      |
| mg_21934955  | mogi        | Cầu Giấy    |     40 |    1.3  |   4.41 | PASS DOM 20 NGÕ 69 YÊN HÒA 1tr3/1 tháng (đã bao gồm điện nước, wifi) PASS DOM 20 NGÕ 69 YÊN HÒA 1tr3/1 tháng (đã bao gồm điện nước, wifi) Do      |
| pt_591152    | phongtro123 | Hoàn Kiếm   |     30 |    1    |   3.37 | Cho thuê phòng trọ giá siêu rẻ, siêu siêu rẻ tại 47/203 Hồng Hà, Phường Phúc Tân, Quận Hoàn Kiếm, Hà Nội Cho thuê phòng tại 47/203 Hồng Hà,       |
| pt_647103    | phongtro123 | Nam Từ Liêm |     30 |    1    |   3.3  | Cho thuê phòng trọ Đại Học Công Nghiệp ở 1 người giá rẻ tại Xuân Phương Tiết kiệm chi phí mà được chủ động sinh hoạt 1 mình không phụ thuộc       |
| ct_135504547 | chotot      | Thanh Xuân  |    nan |    1.3  |   4.05 | Phòng trọ 79B Quan Nhân - 1.3tr/tháng 🏡 79B QUAN NHÂN – CHỈ 1TR3/THÁNG 🔥 💰 Giá thuê: 1.300.000đ/tháng 🎁 Free dịch vụ chung, Wi-Fi ✨ Đầy đủ t |
| ct_135367652 | chotot      | Đống Đa     |    nan |    1    |   3.05 | Phòng trọ 1.000.000 Đống Đa có điều hòa 🏠12 Nguyễn Phúc Lai - Đống Đa 🏮Giá phòng: 1.000.000 ✔️Có ĐIỀU HOÀ ✔️Vệ sinh chung có người dọn hàng     |
| pt_315672    | phongtro123 | Thanh Xuân  |     32 |    1.1  |   3.33 | Phòng trọ tiện ích ngõ 265 Lương Thế Vinh, Thanh Xuân, Hà Nội Khai trương phòng trọ ngõ 265 Lương Thế Vinh, Thanh Xuân, Hà Nội *************      |
| ct_135699814 | chotot      | Hoàng Mai   |     50 |    1.5  |   4.42 | cho thuê nhà cấp 4. 1tr5/tháng Nhà cấp 4 diện tích 50m2. Cả sân Nội thất chỉ có bộ bàn ghế ngồi uống nước thôi nhé. Phù hợp gia đình ở Mình       |
| pt_649520    | phongtro123 | Cầu Giấy    |     30 |    1.4  |   3.97 | Home Nghĩa Tân phục vụ bạn sinh viên và công sở tại 82 phố Nghĩa Tân Home có vị trí rất thuận lợi, gầ các trường ĐHQG, Báo Chí, Sư Phạm, Mầm      |
| ct_134927711 | chotot      | Bắc Từ Liêm |     15 |    0.65 |   1.79 | Cho thuê phòng trọ giá 650k/tháng Còn 1 phòng trống, cho thuê phòng trọ giá 650k tại Phú Kiều, Bắc Từ Liêm, Hà Nội. Khu vực đông dân cư, vài      |
| pt_310120    | phongtro123 | Thanh Xuân  |     25 |    1.25 |   3.33 | Cho thuê 5/481 Vũ Tông Phan, full đồ, có điều hòa( 1,25tr/người) Địa chỉ: Nhà số 5 ngõ 481 Vũ Tông Phan, Thanh Xuân, Hà Nội. Đi ra Ngã Tư Sở      |
| pt_648427    | phongtro123 | Chương Mỹ   |     35 |    1.8  |   4.76 | Cho thuê phòng trọ Phụng Châu, Chương Mỹ, DT 35m2, FULL nội thất, giá 1,8 triệu/tháng Cho thuê phòng trọ Thôn Phụng Nghĩa, xã Phụng Châu, hu      |
| pt_309335    | phongtro123 | Hà Đông     |     35 |    1.5  |   3.89 | Cho thuê phòng tầng 1, được sử dụng đầy đủ tiện nghi của nhà. Nhà 05 tầng khu dân cư dân trí cao. Cho thuê phòng tầng 1. Được sử dụng các ti      |
| ct_134991511 | chotot      | Hoàng Mai   |    nan |    1.5  |   3.89 | Phòng trọ TRƯƠNG ĐỊNH BỜ SÔNG SÉT, có cho ngắn hạn 1.5tr / tháng TRƯƠNG ĐỊNH BỜ SÔNG SÉT ( có cho ngắn hạn ) ✅ Miễn phí điện, nước, dịch vụ,     |
