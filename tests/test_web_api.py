"""Kiểm thử backend web (gọi trực tiếp các hàm API, cần models/best_model.joblib).

    python -m pytest tests -q
"""
import json
import math
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
server = pytest.importorskip("server")

BASE = dict(district="Hai Bà Trưng", size=20,
            text="Phòng khép kín 20m2, điều hòa, nóng lạnh, giờ giấc tự do, không chung chủ.")


def predict(**kw):
    return server.predict(server.Query(**{**BASE, **kw}))


def test_predict_range_is_consistent():
    r = predict()
    assert 0.5 < r["low"] < r["price"] < r["high"] < 30
    json.dumps(r, allow_nan=False)  # trả về được dưới dạng JSON


def test_predict_json_safe_when_similar_listing_has_no_ward():
    # tin tương tự thiếu tên phường (ward = NaN) từng làm API trả lỗi 500 vì NaN không hợp lệ trong JSON
    for district in sorted(server.all_rooms["district"].dropna().unique()):
        r = server.predict(server.Query(district=district, size=12, text="phòng trọ giá rẻ cho sinh viên"))
        json.dumps(r, allow_nan=False)
        assert r["low"] < r["price"] < r["high"]


def test_interval_uses_quantiles_of_predicted_price_level():
    iv = server.interval
    if iv is None or "pred_edges" not in iv:
        pytest.skip("chưa chạy src/intervals.py bản mới")
    assert len(iv["q_low_bins"]) == len(iv["q_high_bins"]) == len(iv["pred_edges"]) + 1
    assert all(lo < 0 < hi for lo, hi in zip(iv["q_low_bins"], iv["q_high_bins"]))


@pytest.mark.parametrize("asking, level", [(9.0, "high"), (1.0, "low")])
def test_verdict(asking, level):
    assert predict(asking=asking)["verdict"]["level"] == level


def test_price_written_in_text_does_not_leak():
    cheap = predict(text=BASE["text"] + " Giá 3tr/tháng.")
    pricey = predict(text=BASE["text"] + " Giá 9 triệu/tháng.")
    assert abs(cheap["price"] - pricey["price"]) < 0.01


def test_bigger_room_costs_more():
    assert predict(size=40)["price"] > predict(size=15)["price"]


def test_shared_room_is_flagged():
    r = predict(text="Homestay ở ghép giường tầng, 1tr5/người bao điện nước")
    assert r["listing_type"]["code"] == "G"


def test_explain_and_whatif():
    r = predict()
    assert r["explain"] and all(math.isfinite(e["effect_pct"]) for e in r["explain"])
    labels = {w["label"] for w in r["whatif"]}
    assert "khép kín" not in " ".join(labels)  # tiện ích đã có thì không gợi ý thêm
    assert all(w["price"] > 0 for w in r["whatif"])


def test_fetch_rejects_unsupported_site():
    with pytest.raises(HTTPException) as e:
        server.fetch("https://example.com/phong-tro-123")
    assert e.value.status_code == 400


def test_map_and_about_are_json_safe():
    m = server.map_data()
    assert m["wards"] and all(isinstance(w["lat"], float) for w in m["wards"])
    json.dumps(m, allow_nan=False)
    a = server.about()
    assert a["models"] and a["data"]["private"] > 0
    json.dumps(a, allow_nan=False)


def test_source_is_optional_and_consistent():
    avg = predict()["price"]
    for src in ("chotot", "phongtro123", "mogi"):
        p = predict(source=src)["price"]
        assert abs(p - avg) / avg < 0.3  # nguồn chỉ hiệu chỉnh nhẹ, không làm giá nhảy vọt
    assert predict(source="khong-ton-tai")["price"] == avg  # nguồn lạ -> lấy trung bình như tin tự nhập
