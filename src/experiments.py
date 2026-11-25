"""Các thí nghiệm bổ sung cho báo cáo (tất cả đánh giá bằng GroupKFold 5-fold):

  A. Biểu diễn văn bản: từ khóa thủ công  vs  TF-IDF (từ + n-gram)  vs  cả hai
  B. Tinh chỉnh HistGradientBoosting: cách đơn giản (lạc quan) vs nested CV (khách quan)
  C. Ablation: bỏ từng nhóm đặc trưng -> sai số tăng bao nhiêu
  D. Độ chính xác tọa độ: trên tin Chợ Tốt, tọa độ thật  vs  tọa độ trung vị phường
  E. Chọn alpha cho Ridge + TF-IDF
  F. Kết hợp mô hình: trung bình có trọng số Ridge + TF-IDF và HGB (VotingRegressor)
  G. Thêm đặc trưng phường

Kết quả: reports/experiments.csv + in ra màn hình.

    python src/experiments.py
"""
import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, VotingRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.model_selection import GroupKFold, RandomizedSearchCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from common import PROCESSED_DIR, REPORTS_DIR
from features import CAT_COLS, DIST_COLS, KEYWORD_COLS, NUM_COLS, add_features, load_rooms
from train import RIDGE_TFIDF_ALPHA, SEED, evaluate, metrics

warnings.filterwarnings("ignore")
CV = GroupKFold(n_splits=5)
ALPHAS = np.logspace(-2, 3, 20)


def linear_pipe(num_cols, cat_cols, tfidf=False, alpha=RIDGE_TFIDF_ALPHA, char=False):
    parts = [("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), num_cols),
             ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=10), cat_cols)]
    if tfidf:
        parts.append(("txt", TfidfVectorizer(ngram_range=(1, 2), min_df=5, max_features=20000, sublinear_tf=True),
                      "text_clean"))
    if char:  # n-gram ký tự: bắt viết tắt / sai chính tả ("vskk", "1n1k", "ccmn", "dieu hoa" vs "đieu hoa")
        parts.append(("chr", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=5, max_features=30000,
                                             sublinear_tf=True), "text_clean"))
        tfidf = True
    # có TF-IDF thì dùng alpha cố định (RidgeCV trên ma trận TF-IDF rất chậm), xem mục E
    return make_pipeline(ColumnTransformer(parts), Ridge(alpha=alpha) if tfidf else RidgeCV(alphas=ALPHAS))


def hgb_pipe(num_cols, cat_cols, **params):
    pre = ColumnTransformer([
        ("num", "passthrough", num_cols),  # HGB tự xử lý giá trị thiếu, không cần chuẩn hóa
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=10, sparse_output=False), cat_cols),
    ])
    return make_pipeline(pre, HistGradientBoostingRegressor(random_state=SEED, **params))


def main():
    df = add_features(load_rooms())
    y, groups = np.log(df["price"]), df["group_id"]
    rows = []

    def record(exp, name, model, data=df, y_=y, g_=groups):
        m, _ = evaluate(model, data, y_, g_, CV)
        rows.append({"thí nghiệm": exp, "cấu hình": name, **m.round(3).to_dict()})
        print(f"[{exp}] {name:45s} MAE={m['MAE (triệu)']:.3f}  MAPE={m['MAPE (%)']:.1f}%  R2={m['R2']:.3f}")

    # A. Biểu diễn văn bản
    no_kw = [c for c in NUM_COLS if c not in KEYWORD_COLS]
    record("A. văn bản", "Ridge, không dùng văn bản", linear_pipe(no_kw, CAT_COLS))
    record("A. văn bản", "Ridge + từ khóa thủ công", linear_pipe(NUM_COLS, CAT_COLS))
    record("A. văn bản", "Ridge + TF-IDF", linear_pipe(no_kw, CAT_COLS, tfidf=True))
    record("A. văn bản", "Ridge + từ khóa + TF-IDF", linear_pipe(NUM_COLS, CAT_COLS, tfidf=True))
    record("A. văn bản", "Ridge + từ khóa + TF-IDF ký tự", linear_pipe(NUM_COLS, CAT_COLS, char=True))
    record("A. văn bản", "Ridge + từ khóa + TF-IDF từ + ký tự", linear_pipe(NUM_COLS, CAT_COLS, tfidf=True, char=True))

    # B. Tinh chỉnh HGB
    record("B. tinh chỉnh", "HGB mặc định", hgb_pipe(NUM_COLS, CAT_COLS))

    def make_search(n_iter):
        return RandomizedSearchCV(
            hgb_pipe(NUM_COLS, CAT_COLS),
            {
                "histgradientboostingregressor__learning_rate": [0.02, 0.05, 0.1],
                "histgradientboostingregressor__max_iter": [200, 400, 800],
                "histgradientboostingregressor__max_leaf_nodes": [15, 31, 63],
                "histgradientboostingregressor__min_samples_leaf": [10, 20, 50],
                "histgradientboostingregressor__l2_regularization": [0.0, 0.1, 1.0],
            },
            n_iter=n_iter, cv=GroupKFold(n_splits=3), scoring="neg_mean_absolute_error", random_state=SEED,
            n_jobs=2,  # ít worker để không cạn RAM (máy 8GB)
        )

    # B1. Cách đơn giản (lạc quan): tìm tham số trên TOÀN BỘ dữ liệu, rồi chấm cấu hình đó bằng CV 5-fold
    #     -> dữ liệu test của CV 5-fold đã "được nhìn thấy" lúc chọn tham số
    search = make_search(20)
    search.fit(df, y, groups=groups)
    best = {k.split("__")[1]: v for k, v in search.best_params_.items()}
    print("   tham số tốt nhất:", best)
    record("B. tinh chỉnh", f"HGB tinh chỉnh (chọn trên toàn bộ dữ liệu) {best}", hgb_pipe(NUM_COLS, CAT_COLS, **best))

    # B2. Nested CV (khách quan): vòng ngoài GroupKFold 5-fold chấm điểm; trong MỖI fold ngoài, tham số được chọn
    #     bằng RandomizedSearchCV (GroupKFold 3-fold) chỉ trên phần train của fold đó
    nested, chosen = [], []
    for tr, te in CV.split(df, y, groups):
        inner = make_search(10).fit(df.iloc[tr], y.iloc[tr], groups=groups.iloc[tr])
        chosen.append({k.split("__")[1]: v for k, v in inner.best_params_.items()})
        nested.append(metrics(np.exp(y.iloc[te]), np.exp(inner.predict(df.iloc[te]))))
    m = pd.DataFrame(nested).mean()
    rows.append({"thí nghiệm": "B. tinh chỉnh", "cấu hình": "HGB tinh chỉnh — nested CV (khách quan)", **m.round(3).to_dict()})
    print(f"[B. tinh chỉnh] nested CV  MAE={m['MAE (triệu)']:.3f}  MAPE={m['MAPE (%)']:.1f}%  R2={m['R2']:.3f}")
    print("   tham số chọn ở từng fold ngoài:", chosen)

    # C. Ablation trên mô hình Ridge + từ khóa + TF-IDF
    groups_feat = {
        "vị trí (khoảng cách + quận)": (DIST_COLS, ["district"]),
        "diện tích": (["size", "log_size", "size_missing"], []),
        "từ khóa + TF-IDF": (KEYWORD_COLS + ["text_len"], []),
        "nội thất": ([], ["furnishing"]),
    }
    for name, (drop_num, drop_cat) in groups_feat.items():
        num = [c for c in NUM_COLS if c not in drop_num]
        cat = [c for c in CAT_COLS if c not in drop_cat]
        record("C. ablation", f"bỏ {name}", linear_pipe(num, cat, tfidf="TF-IDF" not in name))

    # D. Độ chính xác tọa độ (chỉ tin Chợ Tốt có tọa độ thật)
    ct = df[df["source"] == "chotot"].copy()
    ct_y, ct_g = np.log(ct["price"]), ct["group_id"]
    record("D. tọa độ", f"Chợ Tốt ({len(ct)} tin), tọa độ thật", linear_pipe(NUM_COLS, CAT_COLS, tfidf=True), ct, ct_y, ct_g)
    centroid = ct.groupby("ward")[["lat", "lon"]].transform("median")
    ct_ward = add_features(ct.assign(lat=centroid["lat"].fillna(ct["lat"]), lon=centroid["lon"].fillna(ct["lon"])))
    record("D. tọa độ", "Chợ Tốt, tọa độ = trung vị phường", linear_pipe(NUM_COLS, CAT_COLS, tfidf=True), ct_ward, ct_y, ct_g)

    # E. Chọn alpha cho Ridge + TF-IDF (giá trị tốt nhất -> RIDGE_TFIDF_ALPHA trong train.py)
    for a in [0.1, 0.3, 1.0, 3.0, 10.0]:
        record("E. alpha Ridge+TF-IDF", f"alpha = {a}", linear_pipe(NUM_COLS, CAT_COLS, tfidf=True, alpha=a))

    # F. Kết hợp Ridge + TF-IDF (mạnh về văn bản) với HGB (phi tuyến trên đặc trưng có cấu trúc)
    for w in [(1, 0), (0.7, 0.3), (0.5, 0.5)]:
        ens = VotingRegressor([("ridge_tfidf", linear_pipe(NUM_COLS, CAT_COLS, tfidf=True)),
                               ("hgb", hgb_pipe(NUM_COLS, CAT_COLS, **best))], weights=list(w))
        record("F. kết hợp mô hình", f"Ridge+TF-IDF × {w[0]} + HGB × {w[1]}", ens)

    # G. Thêm phường (one-hot, phường ít tin gộp chung) -- định vị chi tiết hơn quận + khoảng cách
    record("G. phường", "Ridge + TF-IDF, quận", linear_pipe(NUM_COLS, CAT_COLS, tfidf=True))
    record("G. phường", "Ridge + TF-IDF, quận + phường", linear_pipe(NUM_COLS, CAT_COLS + ["ward"], tfidf=True))

    out = pd.DataFrame(rows)
    out.to_csv(REPORTS_DIR / "experiments.csv", index=False, encoding="utf-8-sig")
    print(f"\n-> {REPORTS_DIR / 'experiments.csv'}")


if __name__ == "__main__":
    main()
