# Luật kết hợp: tiện ích ↔ mức giá (Apriori)

7409 tin phòng riêng, 26 item. Mức giá theo tam phân vị: gia_thap ≤ 3.00 tr < gia_tb ≤ 4.20 tr < gia_cao. Ngưỡng: support ≥ 0.03, confidence ≥ 0.5, lift ≥ 1.2.

## Tần suất từng item

|           |   % số tin |
|:----------|-----------:|
| cum_2     |       81.6 |
| dieu_hoa  |       54.5 |
| nong_lanh |       51   |
| full_do   |       42.2 |
| may_giat  |       41.3 |
| khep_kin  |       37.2 |
| gia_thap  |       35.8 |
| gia_tb    |       33.1 |
| ban_cong  |       31.5 |
| gia_cao   |       31   |
| tu_lanh   |       29.1 |
| thang_may |       23.7 |
| van_tay   |       20.6 |
| o_to      |       18.5 |
| camera    |       17.2 |
| gio_tu_do |       17   |
| ccmn      |       14.6 |
| cum_1     |       14.1 |
| moi_xay   |       10.5 |
| gac_xep   |       10.2 |
| studio    |        8.4 |
| 1_ngu     |        8.2 |
| chung_chu |        5.7 |
| pet       |        5   |
| bep_rieng |        3   |
| 2_ngu     |        2.9 |

Tìm được 1555 tập phổ biến và 3230 luật thỏa ngưỡng.

## Luật dẫn tới phòng GIÁ CAO

| luật                                     |   support |   confidence |   lift |
|:-----------------------------------------|----------:|-------------:|-------:|
| 1_ngu, may_giat  →  gia_cao              |     0.031 |        0.785 |  2.531 |
| 1_ngu, cum_2, full_do  →  gia_cao        |     0.031 |        0.708 |  2.282 |
| 1_ngu, full_do  →  gia_cao               |     0.036 |        0.694 |  2.235 |
| 1_ngu, cum_2  →  gia_cao                 |     0.049 |        0.692 |  2.229 |
| 1_ngu  →  gia_cao                        |     0.055 |        0.671 |  2.161 |
| ban_cong, thang_may, tu_lanh  →  gia_cao |     0.035 |        0.656 |  2.113 |
| may_giat, thang_may, tu_lanh  →  gia_cao |     0.056 |        0.625 |  2.015 |
| ban_cong, full_do, thang_may  →  gia_cao |     0.041 |        0.622 |  2.003 |
| cum_2, thang_may, tu_lanh  →  gia_cao    |     0.061 |        0.621 |  2.003 |
| cum_2, full_do, studio  →  gia_cao       |     0.031 |        0.621 |  2.002 |
| thang_may, tu_lanh  →  gia_cao           |     0.068 |        0.615 |  1.983 |
| full_do, studio  →  gia_cao              |     0.033 |        0.611 |  1.969 |

## Luật dẫn tới phòng GIÁ THẤP

| luật                           |   support |   confidence |   lift |
|:-------------------------------|----------:|-------------:|-------:|
| cum_1, khep_kin  →  gia_thap   |     0.039 |        0.626 |  1.746 |
| gac_xep, khep_kin  →  gia_thap |     0.033 |        0.608 |  1.695 |
| cum_1, nong_lanh  →  gia_thap  |     0.035 |        0.552 |  1.539 |
| cum_1  →  gia_thap             |     0.075 |        0.528 |  1.472 |
| cum_1, dieu_hoa  →  gia_thap   |     0.035 |        0.526 |  1.466 |

## Tiện ích thường đi cùng nhau

| luật                                     |   support |   confidence |   lift |
|:-----------------------------------------|----------:|-------------:|-------:|
| ban_cong, camera, thang_may  →  van_tay  |     0.04  |        0.878 |  4.27  |
| ban_cong, khep_kin, van_tay  →  camera   |     0.031 |        0.725 |  4.206 |
| camera, thang_may, tu_lanh  →  van_tay   |     0.034 |        0.854 |  4.151 |
| ban_cong, tu_lanh, van_tay  →  camera    |     0.035 |        0.698 |  4.047 |
| camera, full_do, thang_may  →  van_tay   |     0.041 |        0.832 |  4.045 |
| camera, nong_lanh, thang_may  →  van_tay |     0.049 |        0.826 |  4.015 |
| camera, may_giat, thang_may  →  van_tay  |     0.046 |        0.825 |  4.01  |
| ban_cong, camera, tu_lanh  →  van_tay    |     0.035 |        0.823 |  4.002 |
| camera, dieu_hoa, thang_may  →  van_tay  |     0.051 |        0.815 |  3.963 |
| ban_cong, full_do, van_tay  →  camera    |     0.043 |        0.683 |  3.963 |
| ban_cong, may_giat, van_tay  →  camera   |     0.046 |        0.683 |  3.961 |
| ban_cong, nong_lanh, van_tay  →  camera  |     0.049 |        0.68  |  3.947 |
| ban_cong, camera, may_giat  →  van_tay   |     0.046 |        0.811 |  3.945 |
| ccmn, nong_lanh, van_tay  →  camera      |     0.036 |        0.677 |  3.927 |
| ban_cong, thang_may, van_tay  →  camera  |     0.04  |        0.676 |  3.921 |
