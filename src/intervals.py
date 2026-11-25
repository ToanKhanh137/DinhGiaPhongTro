"""KHOẢNG GIÁ THÍCH NGHI cho từng tin (normalized conformal prediction + phân vị theo mức giá dự đoán).

Cách đơn giản nhất: khoảng 80% = dự đoán + phân vị 10% / 90% của phần dư, một độ rộng chung (trên thang log) cho mọi tin.
Nhưng độ khó khác nhau giữa các nguồn tin và giữa các mức giá. Cách làm:

  1. Phần dư out-of-fold r = log(giá thật) − log(giá dự đoán) của mô hình chính (GroupKFold).
  2. "Mô hình độ khó" g(x): HistGradientBoosting dự đoán |r| từ đặc trưng (cũng out-of-fold). Độ phức tạp của g được chọn
     trong DIFFICULTY theo RMSE out-of-fold khi dự đoán |r| (|r| khó đoán, mô hình sâu dễ học vẹt → khoảng rộng thừa).
  3. Điểm chuẩn hóa s = r / g(x). Khoảng giá = dự đoán + [phân vị 10% của s, phân vị 90% của s] × g(x).
  4. Phân vị ở bước 3 lấy RIÊNG cho từng mức giá dự đoán (PRED_EDGES; "Mondrian conformal"): người dùng chỉ nhìn thấy giá
     dự đoán, nên độ phủ cần đúng 80% ở từng mức giá dự đoán chứ không chỉ đúng khi gộp tất cả.

Đánh giá (vòng ngoài GroupKFold 5-fold, phân vị lấy từ các fold KHÁC): độ phủ (tỉ lệ giá thật nằm trong khoảng, mục tiêu
80%) và độ rộng trung bình. Cùng độ phủ, khoảng hẹp hơn là tốt hơn; độ phủ nên đều giữa các nhóm tin.

Lưu ý khi đọc bảng: nhóm theo GIÁ THẬT (rất rẻ / rất đắt) luôn phủ thiếu với mọi cách tính. Đó là hệ quả của việc chọn
nhóm theo chính đại lượng cần đoán (tin rẻ bất thường so với mô tả thì nằm ngoài khoảng), không sửa được bằng cách đổi
khoảng. Điều bảo đảm được là độ phủ theo những gì biết trước khi xem giá: nguồn, diện tích, mức giá dự đoán.

Kết quả: reports/intervals.md, models/interval_model.joblib (web demo dùng nếu có)

    python src/intervals.py
"""
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

from common import REPORTS_DIR
from features import CAT_COLS, FEATURE_COLS, NUM_COLS, add_features, load_rooms
from train import MODELS_DIR, SEED, models

LEVEL = (0.1, 0.9)  # khoảng 80%
MIN_SCALE = 0.02
PRED_EDGES = [2.5, 3.0, 3.5, 4.0, 5.0]  # ranh giới các mức giá dự đoán (triệu), mỗi mức ≥ 700 tin
PRED_NAMES = ["< 2,5", "2,5–3", "3–3,5", "3,5–4", "4–5", "> 5"]
# các mức phức tạp của mô hình độ khó; chọn theo RMSE out-of-fold khi dự đoán |phần dư|
DIFFICULTY = {
    "sâu (300 cây, không giới hạn độ sâu)": dict(max_iter=300),
    "nông (150 cây, sâu 3)": dict(max_iter=150, max_depth=3),
    "rất nông (100 cây, sâu 2)": dict(max_iter=100, max_depth=2),
}
METHODS = ["một độ rộng chung", "thích nghi theo tin", "thích nghi + theo mức giá dự đoán"]
FINAL = METHODS[-1]  # cách web demo dùng


def difficulty_model(**params):
    pre = ColumnTransformer([
        ("num", "passthrough", NUM_COLS),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=10, sparse_output=False), CAT_COLS),
    ])
    kw = dict(learning_rate=0.05, min_samples_leaf=40, random_state=SEED)
    kw.update(params)
    return make_pipeline(pre, HistGradientBoostingRegressor(**kw))


def pred_bin(pred_log):
    """Chỉ số mức giá dự đoán (0 … len(PRED_EDGES)) từ log giá dự đoán (đồng)."""
    return np.digitize(np.exp(pred_log) / 1e6, PRED_EDGES)


def oof_parts(X, y, groups, model_name):
    """Bước 1–2 trên một tập huấn luyện: phần dư out-of-fold của mô hình chính và độ khó out-of-fold.

    Trả về (folds, pred, resid, scale, best_diff, diff_table); best_diff là mức phức tạp của mô hình độ khó có RMSE
    out-of-fold thấp nhất khi dự đoán |phần dư|.
    """
    folds = list(GroupKFold(n_splits=5).split(X, y, groups))
    pred = np.zeros(len(X))
    for tr, te in folds:
        pred[te] = models()[model_name].fit(X.iloc[tr], y.iloc[tr]).predict(X.iloc[te])
    resid = np.asarray(y) - pred
    abs_r = np.abs(resid)

    col = "RMSE dự đoán độ lớn phần dư"
    scales, diff_rows = {}, [{"mô hình độ khó": "hằng số (không dùng mô hình)", col: round(abs_r.std(), 4)}]
    for name, params in DIFFICULTY.items():
        s = np.zeros(len(X))
        for tr, te in folds:
            s[te] = difficulty_model(**params).fit(X.iloc[tr], abs_r[tr]).predict(X.iloc[te])
        scales[name] = np.clip(s, MIN_SCALE, None)
        diff_rows.append({"mô hình độ khó": name, col: round(np.sqrt(np.mean((abs_r - s) ** 2)), 4)})
    best_diff = min(DIFFICULTY, key=lambda n: np.mean((abs_r - scales[n]) ** 2))
    return folds, pred, resid, scales[best_diff], best_diff, pd.DataFrame(diff_rows)


def interval_bundle(X, pred, resid, scale, best_diff):
    """Mô hình độ khó khớp trên toàn bộ tập huấn luyện + các phân vị cần để tính khoảng cho tin mới."""
    score, bins = resid / scale, pred_bin(pred)
    q_bins = [np.quantile(score[bins == b], LEVEL) for b in range(len(PRED_NAMES))]
    q_resid = np.quantile(resid, LEVEL)
    return {"model": difficulty_model(**DIFFICULTY[best_diff]).fit(X, np.abs(resid)), "min_scale": MIN_SCALE,
            "resid_q_low": float(q_resid[0]), "resid_q_high": float(q_resid[1]),
            "q_low": float(np.quantile(score, LEVEL[0])), "q_high": float(np.quantile(score, LEVEL[1])),
            "pred_edges": PRED_EDGES, "q_low_bins": [float(q[0]) for q in q_bins],
            "q_high_bins": [float(q[1]) for q in q_bins]}


def interval_bounds(iv, X, pred_log, method=FINAL):
    """(log cận dưới, log cận trên) của khoảng 80% cho các tin X có log giá dự đoán pred_log."""
    pred_log = np.asarray(pred_log)
    if method == METHODS[0]:
        return pred_log + iv["resid_q_low"], pred_log + iv["resid_q_high"]
    scale = np.clip(iv["model"].predict(X), iv["min_scale"], None)
    if method == METHODS[1]:
        return pred_log + iv["q_low"] * scale, pred_log + iv["q_high"] * scale
    bins = pred_bin(pred_log)
    return (pred_log + np.asarray(iv["q_low_bins"])[bins] * scale,
            pred_log + np.asarray(iv["q_high_bins"])[bins] * scale)


def main():
    bundle = joblib.load(MODELS_DIR / "best_model.joblib")
    df = add_features(load_rooms())
    X, y, groups = df[FEATURE_COLS], np.log(df["price"]), df["group_id"]

    # 1–2. phần dư out-of-fold của mô hình chính; mô hình độ khó out-of-fold (đã chọn mức phức tạp)
    folds, pred, resid, scale, best_diff, diff_table = oof_parts(X, y, groups, bundle["name"])
    score = resid / scale
    print(diff_table.to_string(index=False))
    print("-> mô hình độ khó:", best_diff)

    # 3. đánh giá: với mỗi fold, phân vị lấy từ các fold còn lại
    bins = pred_bin(pred)
    lo = {m: np.zeros(len(df)) for m in METHODS}
    hi = {m: np.zeros(len(df)) for m in METHODS}
    for tr, te in folds:
        in_tr, in_te = np.zeros(len(df), bool), np.zeros(len(df), bool)
        in_tr[tr], in_te[te] = True, True
        q = np.quantile(resid[tr], LEVEL)
        lo[METHODS[0]][te], hi[METHODS[0]][te] = pred[te] + q[0], pred[te] + q[1]
        q = np.quantile(score[tr], LEVEL)
        lo[METHODS[1]][te], hi[METHODS[1]][te] = pred[te] + q[0] * scale[te], pred[te] + q[1] * scale[te]
        for b in range(len(PRED_NAMES)):
            trb, teb = in_tr & (bins == b), in_te & (bins == b)
            q = np.quantile(score[trb], LEVEL)
            lo[FINAL][teb], hi[FINAL][teb] = pred[teb] + q[0] * scale[teb], pred[teb] + q[1] * scale[teb]
    price = df["price"].to_numpy() / 1e6
    to_m = lambda v: np.exp(v) / 1e6

    def summary(lo, hi, mask):
        inside = (price[mask] >= to_m(lo[mask])) & (price[mask] <= to_m(hi[mask]))
        width = to_m(hi[mask]) - to_m(lo[mask])
        return {"độ phủ (%)": inside.mean() * 100, "độ rộng TB (triệu)": width.mean(),
                "độ rộng TB / giá (%)": (width / to_m(pred[mask])).mean() * 100}

    groups_eval = {"tất cả": np.ones(len(df), bool),
                   "có ghi diện tích": (df["size_missing"] == 0).to_numpy(),
                   "không ghi diện tích": (df["size_missing"] == 1).to_numpy(),
                   **{f"nguồn {s}": (df["source"] == s).to_numpy() for s in sorted(df["source"].unique())},
                   **{f"giá dự đoán {n} triệu": bins == b for b, n in enumerate(PRED_NAMES)},
                   "giá thật < 2 triệu": price < 2, "giá thật 2–5 triệu": (price >= 2) & (price <= 5),
                   "giá thật > 5 triệu": price > 5}
    rows = []
    for name, mask in groups_eval.items():
        for method in METHODS:
            rows.append({"nhóm tin": name, "cách tính": method, "số tin": int(mask.sum()),
                         **{k: round(v, 2) for k, v in summary(lo[method], hi[method], mask).items()}})
    table = pd.DataFrame(rows)
    print(table.to_string(index=False))

    # lưu mô hình độ khó (huấn luyện trên toàn bộ) + phân vị điểm chuẩn hóa theo mức giá dự đoán cho web demo
    joblib.dump(interval_bundle(X, pred, resid, scale, best_diff), MODELS_DIR / "interval_model.joblib")

    out = ["# Khoảng giá 80%: một độ rộng chung, thích nghi theo tin, thích nghi + theo mức giá dự đoán\n",
           f"{len(df)} tin phòng riêng, GroupKFold 5-fold; phân vị lấy từ các fold khác fold đang chấm. "
           "Mục tiêu độ phủ 80%; cùng độ phủ thì khoảng hẹp hơn là tốt hơn.\n",
           "## Chọn mô hình độ khó\n",
           "RMSE out-of-fold khi dự đoán độ lớn phần dư (thang log). Độ lớn phần dư khó đoán: mô hình tốt nhất chỉ hơn hằng số một chút, "
           f"mô hình sâu thì học vẹt. Chọn: **{best_diff}**.\n",
           diff_table.to_markdown(index=False),
           "\n## Độ phủ và độ rộng theo nhóm tin\n",
           f"Web demo dùng cách **{FINAL}**. Nhóm theo giá thật phủ thiếu với mọi cách tính (chọn nhóm theo chính đại "
           "lượng cần đoán), xem ghi chú đầu file `src/intervals.py`.\n",
           table.to_markdown(index=False)]
    (REPORTS_DIR / "intervals.md").write_text("\n".join(out), encoding="utf-8")
    table.to_csv(REPORTS_DIR / "intervals.csv", index=False, encoding="utf-8-sig")
    print("->", REPORTS_DIR / "intervals.md", "+", MODELS_DIR / "interval_model.joblib")


if __name__ == "__main__":
    main()
