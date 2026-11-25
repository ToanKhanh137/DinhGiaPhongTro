"""Kiểm thử các hàm xử lý văn bản quan trọng (sai ở đây -> rò rỉ nhãn hoặc dữ liệu bẩn).

    python -m pytest tests -q
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from build_dataset import size_from_text  # noqa: E402
from common import mask_phone  # noqa: E402
from crawl_phongtro123 import parse_price  # noqa: E402
from features import mask_money, strip_accents  # noqa: E402
from listing_type import rule_predict  # noqa: E402


def clean(text):
    return mask_money(strip_accents(text))


@pytest.mark.parametrize("text, expected", [
    ("2.5 triệu/tháng", 2_500_000),
    ("800 nghìn/tháng", 800_000),
    ("2 triệu 500 nghìn", 2_500_000),
    ("5 triệu 300 nghìn", 5_300_000),
    ("Thỏa thuận", None),
])
def test_parse_price(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("Phòng rộng 25m2 có gác", 25.0),
    ("diện tích 30 m² thoáng", 30.0),
    ("Rộng khoảng 35m, full đồ", 35.0),
    ("Phòng 22,5m2", 22.5),
    ("Phòng đẹp full đồ", None),
])
def test_size_from_text(text, expected):
    assert size_from_text(text) == expected


def test_strip_accents():
    assert strip_accents("Điều Hòa, nóng lạnh") == "dieu hoa, nong lanh"
    assert strip_accents("điều hoà") == strip_accents("điều hòa")


@pytest.mark.parametrize("text", [
    "Giá 3,5 tr / tháng", "Phòng 5tr6 full đồ", "#3TR450", "8 Triệu", "giá 3.500.000đ",
    "giá 3500000", "5 triệu 300 nghìn", "Điện 4k/số",
])
def test_mask_money_removes_all_digits_of_prices(text):
    assert not any(ch.isdigit() for ch in clean(text)), clean(text)


@pytest.mark.parametrize("text, kept", [
    ("căn 2n1k rộng", "2n1k"),
    ("1k1n full đồ", "1k1n"),
    ("phòng 25m2", "25m2"),
    ("ngõ 147B Tân Mai", "147b"),
    ("năm 2025 mới xây", "2025"),
])
def test_mask_money_keeps_non_price_numbers(text, kept):
    assert kept in clean(text)


def test_mask_phone():
    out = mask_phone("LH 0983.655.550 hoặc 0912 345 678, +84 912345678, giá 3500000đ, 35m2")
    assert out.count("<SĐT>") == 3
    assert "3500000" in out and "35m2" in out


@pytest.mark.parametrize("text, label", [
    ("Homestay ở ghép giường tầng 1tr2/người", "G"),
    ("Tìm bạn nữ ở ghép phòng 20m2", "G"),
    ("Còn 3 phòng giá 3tr2 - 3tr5", "N"),
    ("Phòng giá từ 2,8 triệu đến 3,5 triệu", "N"),
    ("Phòng khép kín 20m2 full đồ, giá 3tr5", "R"),
])
def test_rule_predict(text, label):
    assert rule_predict(pd.Series([strip_accents(text)]))[0] == label


@pytest.mark.parametrize("text, label", [
    ("Giá 3tr6 với 3tr8, phòng gác xép", "N"),
    ("Tầng 1: 3,5 triệu. Tầng 2: 3 triệu.", "N"),
    ("Giá thuê 3,8 - 4 - 4,1 triệu tùy phòng", "N"),
    ("Phòng 2N1K giá 5tr, 35m2, điện 4k/số, nước 100k/người", "R"),
    ("Homestay ở ghép giá 1tr5 bao điện nước", "G"),
])
def test_rule_v2_predict(text, label):
    from listing_type import rule_v2_predict
    assert rule_v2_predict(pd.Series([strip_accents(text)]))[0] == label


def test_room_groups():
    from build_dataset import room_groups
    base = "Cho thuê phòng khép kín full đồ, ban công, thang máy, ngõ 12 Trần Duy Hưng, gần chợ, giờ giấc tự do"
    df = pd.DataFrame([
        # 0 và 1: cùng phòng đăng lại, giá lệch 100 nghìn, diện tích ghi khác -> cùng nhóm nhờ mô tả
        dict(district="Cầu Giấy", ward="Phường Yên Hòa", price=4_000_000, size=25.0, text=base),
        dict(district="Cầu Giấy", ward="Phường Yên Hòa", price=4_100_000, size=28.0, text=base + "."),
        # 2: mô tả khác hẳn, cùng phường / giá / diện tích với 0 -> cùng nhóm nhờ khóa trùng
        dict(district="Cầu Giấy", ward="Phường Yên Hòa", price=4_000_000, size=25.0, text="Studio mới xây, máy giặt riêng"),
        # 3 và 4: thiếu diện tích, cùng phường / giá nhưng mô tả khác -> KHÔNG ghép
        dict(district="Đống Đa", ward="Phường Láng", price=3_000_000, size=None, text="Phòng trọ gác xép giá rẻ gần chợ"),
        dict(district="Đống Đa", ward="Phường Láng", price=3_000_000, size=None, text="Căn 1N1K có bếp riêng và ban công"),
        # 5: mô tả giống 0 nhưng giá chênh 50% -> KHÔNG ghép
        dict(district="Cầu Giấy", ward="Phường Dịch Vọng", price=6_000_000, size=40.0, text=base),
    ])
    g = room_groups(df)
    assert g[0] == g[1] == g[2]
    assert g[3] != g[4]
    assert g[5] != g[0]
