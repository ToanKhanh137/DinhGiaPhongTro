"""Kiểm tra mô hình trên TIN ĐĂNG MỚI (out-of-time validation).

Cross-validation trộn tin của cùng một thời điểm. Câu hỏi thực tế hơn: huấn luyện trên dữ liệu đã có,
mô hình dự đoán tốt đến đâu cho các tin xuất hiện SAU ĐÓ?

  - Ngày xuất hiện của tin = lần crawl đầu tiên thấy tin đó (cột crawled_at trong data/raw/*.jsonl)
  - Train: tin thấy lần đầu trước CUTOFF.  Test: tin thấy lần đầu từ CUTOFF trở đi.
  - Test chia 2 phần: tin "đăng lại" (cùng group_id với một tin trong train) và tin thật sự mới.

Kết quả: reports/temporal_validation.md

    python src/temporal_validation.py
"""
import numpy as np
import pandas as pd

from common import RAW_DIR, REPORTS_DIR, read_jsonl
from features import FEATURE_COLS, add_features, load_rooms
from intervals import METHODS, interval_bounds, interval_bundle, oof_parts
from train import metrics, models

CUTOFF = "2026-10-12"  # lượt crawl thứ hai; trước đó là dữ liệu đợt 8/10
MODEL_NAMES = ["Dummy (trung bình)", "HistGradientBoosting", "Ridge + TF-IDF", "Ridge + TF-IDF × 0.7 + HGB × 0.3"]


def first_seen():
    rows = []
    for name, prefix, key in [("chotot", "ct_", "list_id"), ("phongtro123", "pt_", "ad_id"), ("mogi", "mg_", "ad_id")]:
        for r in read_jsonl(RAW_DIR / f"{name}.jsonl"):
            rows.append((prefix + str(r[key]), r["crawled_at"][:10]))
    return pd.DataFrame(rows, columns=["id", "first_seen"]).groupby("id")["first_seen"].min()


def main():
    df = add_features(load_rooms())
    df["first_seen"] = df["id"].map(first_seen())
    train = df[df["first_seen"] < CUTOFF]
    test = df[df["first_seen"] >= CUTOFF]
    repost = test["group_id"].isin(train["group_id"])
    print(f"train {len(train)} tin | test {len(test)} tin mới (đăng lại: {int(repost.sum())}, thật sự mới: {int((~repost).sum())})")
    print("ngày xuất hiện của tin test:", test["first_seen"].value_counts().sort_index().to_dict())
    print("nguồn của tin test:", test["source"].value_counts().to_dict())

    rows = []
    for name in MODEL_NAMES:
        m = models()[name].fit(train[FEATURE_COLS], np.log(train["price"]))
        pred = pd.Series(np.exp(m.predict(test[FEATURE_COLS])), index=test.index)
        for part, mask in [("tất cả tin mới", slice(None)), ("chỉ tin thật sự mới", ~repost), ("chỉ tin đăng lại", repost)]:
            t = test[mask]
            if len(t) >= 20:
                rows.append({"mô hình": name, "tập test": part, "số tin": len(t), **metrics(t["price"], pred[t.index])})
    res = pd.DataFrame(rows).round(3)
    print("\n", res.to_string(index=False))

    # Khoảng giá 80% trên tin mới: phần dư, mô hình độ khó và phân vị đều chỉ khớp trên train (src/intervals.py)
    name = MODEL_NAMES[-1]
    X_tr, y_tr = train[FEATURE_COLS], np.log(train["price"])
    _, pred_tr, resid, scale, best_diff, _ = oof_parts(X_tr, y_tr, train["group_id"], name)
    iv = interval_bundle(X_tr, pred_tr, resid, scale, best_diff)
    pred_log = models()[name].fit(X_tr, y_tr).predict(test[FEATURE_COLS])
    y_te = np.log(test["price"]).to_numpy()
    cov_rows = []
    for method in METHODS:
        lo, hi = interval_bounds(iv, test[FEATURE_COLS], pred_log, method)
        for part, mask in [("tất cả tin mới", np.ones(len(test), bool)), ("chỉ tin thật sự mới", (~repost).to_numpy()),
                           ("chỉ tin đăng lại", repost.to_numpy())]:
            if mask.sum() >= 20:
                cov_rows.append({"cách tính": method, "tập test": part, "số tin": int(mask.sum()),
                                 "độ phủ (%)": ((y_te[mask] >= lo[mask]) & (y_te[mask] <= hi[mask])).mean() * 100,
                                 "giá thật dưới khoảng (%)": (y_te[mask] < lo[mask]).mean() * 100,
                                 "giá thật trên khoảng (%)": (y_te[mask] > hi[mask]).mean() * 100,
                                 "độ rộng TB (triệu)": ((np.exp(hi[mask]) - np.exp(lo[mask])) / 1e6).mean()})
    cov = pd.DataFrame(cov_rows).round(2)
    print("\n", cov.to_string(index=False))

    out = [f"# Kiểm tra trên tin đăng mới (train: thấy trước {CUTOFF}, test: thấy từ {CUTOFF})\n",
           f"Train {len(train)} tin phòng riêng. Test {len(test)} tin: {int(repost.sum())} tin đăng lại "
           f"(cùng phòng với một tin trong train) và {int((~repost).sum())} tin thật sự mới.\n",
           f"Ngày xuất hiện của tin test: {test['first_seen'].value_counts().sort_index().to_dict()}. "
           f"Nguồn: {test['source'].value_counts().to_dict()}.\n",
           res.to_markdown(index=False),
           "\nSo sánh với GroupKFold trong `model_comparison.csv`: nếu sai số trên tin mới tương đương thì mô hình "
           "không bị quá khớp vào thời điểm crawl. Lưu ý tập test nhỏ và gần như chỉ từ Chợ Tốt (các trang khác ít tin mới).\n",
           f"## Khoảng giá 80% trên tin mới ({name})\n",
           "Phần dư, mô hình độ khó và phân vị đều chỉ khớp trên train. Mục tiêu: độ phủ 80%, mỗi phía ngoài khoảng 10%.\n",
           cov.to_markdown(index=False), ""]
    cov.to_csv(REPORTS_DIR / "temporal_intervals.csv", index=False, encoding="utf-8-sig")
    res.to_csv(REPORTS_DIR / "temporal_validation.csv", index=False, encoding="utf-8-sig")
    (REPORTS_DIR / "temporal_validation.md").write_text("\n".join(out), encoding="utf-8")
    print("->", REPORTS_DIR / "temporal_validation.md")


if __name__ == "__main__":
    main()
