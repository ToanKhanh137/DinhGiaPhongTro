"""Thí nghiệm bổ sung (GroupKFold 5-fold), chạy riêng vì không bắt buộc cho pipeline:

  H. Tham số TF-IDF: n-gram, ngưỡng tần suất (min_df), số đặc trưng tối đa
  I. Stacking: dự đoán out-of-fold của Ridge + TF-IDF làm thêm một đặc trưng cho HGB,
     so với trung bình có trọng số 0,7 / 0,3 đang dùng

Kết quả: reports/extra_experiments.csv, reports/extra_experiments.md

    python src/extra_experiments.py
"""
import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from common import REPORTS_DIR
from features import CAT_COLS, FEATURE_COLS, NUM_COLS, TEXT_COL, add_features, load_rooms
from train import RIDGE_TFIDF_ALPHA, SEED, evaluate, metrics, models

warnings.filterwarnings("ignore")
CV = GroupKFold(n_splits=5)


def ridge_tfidf(ngram=(1, 2), min_df=5, max_features=20000, alpha=RIDGE_TFIDF_ALPHA):
    return make_pipeline(ColumnTransformer([
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), NUM_COLS),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=10), CAT_COLS),
        ("txt", TfidfVectorizer(ngram_range=ngram, min_df=min_df, max_features=max_features, sublinear_tf=True),
         TEXT_COL),
    ]), Ridge(alpha=alpha))


def stacking_cv(X, y, groups, lr, iters):
    """Mỗi fold ngoài: OOF của Ridge trên tập train (GroupKFold trong) -> đặc trưng cho HGB; tập test dùng Ridge
    huấn luyện trên toàn bộ tập train của fold."""
    pre = ColumnTransformer([
        ("num", "passthrough", NUM_COLS + ["ridge_pred"]),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=10, sparse_output=False), CAT_COLS),
    ])
    rows = []
    for tr, te in CV.split(X, y, groups):
        Xtr, ytr, gtr = X.iloc[tr].copy(), y.iloc[tr], groups.iloc[tr]
        oof = np.zeros(len(tr))
        for itr, ite in GroupKFold(n_splits=5).split(Xtr, ytr, gtr):
            oof[ite] = ridge_tfidf().fit(Xtr.iloc[itr], ytr.iloc[itr]).predict(Xtr.iloc[ite])
        Xtr["ridge_pred"] = oof
        Xte = X.iloc[te].copy()
        Xte["ridge_pred"] = ridge_tfidf().fit(Xtr[FEATURE_COLS], ytr).predict(Xte[FEATURE_COLS])
        hgb = make_pipeline(pre, HistGradientBoostingRegressor(learning_rate=lr, max_iter=iters, min_samples_leaf=30,
                                                                random_state=SEED)).fit(Xtr, ytr)
        rows.append(metrics(np.exp(y.iloc[te]), np.exp(hgb.predict(Xte))))
    return pd.DataFrame(rows).mean()


def main():
    df = add_features(load_rooms())
    X, y, groups = df[FEATURE_COLS], np.log(df["price"]), df["group_id"]
    rows = []

    def record(exp, name, m):
        rows.append({"thí nghiệm": exp, "cấu hình": name, **m.round(4).to_dict()})
        print(f"[{exp}] {name:60s} MAE={m['MAE (triệu)']:.4f}  R2={m['R2']:.4f}", flush=True)

    # H. Tham số TF-IDF (mặc định: n-gram 1-2, min_df 5, tối đa 20.000 đặc trưng)
    for name, kw in [("mặc định (1-2 gram, min_df 5, 20k)", {}), ("1-3 gram", dict(ngram=(1, 3))),
                     ("min_df 2", dict(min_df=2)), ("min_df 10", dict(min_df=10)),
                     ("tối đa 50k đặc trưng", dict(max_features=50000)),
                     ("không giới hạn, min_df 3", dict(max_features=None, min_df=3)),
                     ("1-3 gram, min_df 3, 50k, alpha 1,5", dict(ngram=(1, 3), max_features=50000, min_df=3, alpha=1.5))]:
        record("H. tham số TF-IDF", name, evaluate(ridge_tfidf(**kw), X, y, groups, CV)[0])

    # I. Stacking
    record("I. stacking", "trung bình có trọng số 0,7 / 0,3 (đang dùng)",
           evaluate(models()["Ridge + TF-IDF × 0.7 + HGB × 0.3"], X, y, groups, CV)[0])
    for lr, iters in [(0.05, 300), (0.03, 500)]:
        record("I. stacking", f"Ridge (OOF) -> HGB, learning rate {lr}, {iters} vòng", stacking_cv(X, y, groups, lr, iters))

    out = pd.DataFrame(rows)
    out.to_csv(REPORTS_DIR / "extra_experiments.csv", index=False, encoding="utf-8-sig")
    (REPORTS_DIR / "extra_experiments.md").write_text(
        "# Thí nghiệm bổ sung (GroupKFold 5-fold)\n\n" + f"{len(df)} tin phòng riêng.\n\n" + out.to_markdown(index=False),
        encoding="utf-8")
    print("->", REPORTS_DIR / "extra_experiments.md")


if __name__ == "__main__":
    main()
