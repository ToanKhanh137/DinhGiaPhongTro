"""Kiểm thử các hàm tính khoảng giá (src/intervals.py) trên dữ liệu giả, không cần mô hình đã huấn luyện.

    python -m pytest tests -q
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from intervals import METHODS, PRED_EDGES, interval_bounds, pred_bin  # noqa: E402


class ConstantDifficulty:
    """Mô hình độ khó giả: mọi tin có cùng độ khó."""

    def __init__(self, value):
        self.value = value

    def predict(self, X):
        return np.full(len(X), self.value)


def bundle(scale=0.2):
    n = len(PRED_EDGES) + 1
    return {"model": ConstantDifficulty(scale), "min_scale": 0.02, "resid_q_low": -0.3, "resid_q_high": 0.25,
            "q_low": -1.5, "q_high": 1.4, "pred_edges": PRED_EDGES,
            "q_low_bins": [-1.0 - 0.1 * b for b in range(n)], "q_high_bins": [1.0 + 0.1 * b for b in range(n)]}


def log_price(million):
    return np.log(np.asarray(million, dtype=float) * 1e6)


def test_pred_bin_puts_boundary_price_in_upper_level():
    assert pred_bin(log_price([1.0, 2.49, 2.51, 3.2, 4.99, 5.01, 12.0])).tolist() == [0, 0, 1, 2, 4, 5, 5]


def test_common_width_ignores_difficulty():
    pred = log_price([2.0, 6.0])
    lo, hi = interval_bounds(bundle(scale=0.5), np.zeros((2, 1)), pred, METHODS[0])
    assert np.allclose(lo, pred - 0.3) and np.allclose(hi, pred + 0.25)


def test_adaptive_width_scales_with_difficulty():
    pred = log_price([3.0, 3.0])
    lo_easy, hi_easy = interval_bounds(bundle(scale=0.1), np.zeros((2, 1)), pred, METHODS[1])
    lo_hard, hi_hard = interval_bounds(bundle(scale=0.3), np.zeros((2, 1)), pred, METHODS[1])
    assert np.allclose(hi_easy - lo_easy, 2.9 * 0.1) and np.allclose(hi_hard - lo_hard, 2.9 * 0.3)


def test_final_method_uses_quantiles_of_the_predicted_price_level():
    pred = log_price([2.0, 6.0])  # mức 0 và mức cao nhất
    lo, hi = interval_bounds(bundle(scale=0.2), np.zeros((2, 1)), pred, METHODS[2])
    top = len(PRED_EDGES)
    assert np.allclose(lo, pred + np.array([-1.0, -1.0 - 0.1 * top]) * 0.2)
    assert np.allclose(hi, pred + np.array([1.0, 1.0 + 0.1 * top]) * 0.2)
    assert (lo < pred).all() and (pred < hi).all()


def test_difficulty_is_clipped_at_min_scale():
    pred = log_price([3.0])
    lo, hi = interval_bounds(bundle(scale=0.0), np.zeros((1, 1)), pred, METHODS[1])
    assert np.allclose(hi - lo, 2.9 * 0.02)
