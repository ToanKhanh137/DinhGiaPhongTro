"""So sánh các mô hình hồi quy dự đoán giá thuê, đánh giá bằng GroupKFold 5-fold.

- Mục tiêu: log(giá) khi huấn luyện, đổi về VND khi tính metric.
- GroupKFold theo group_id: tin đăng lại / đăng 2 nơi của cùng 1 phòng không bị chia
  vào cả train lẫn test (tránh rò rỉ dữ liệu làm kết quả đẹp giả).
- Kết quả: reports/model_comparison.csv

    python src/train.py
"""
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor, VotingRegressor
from sklearn.linear_model import LassoCV, LinearRegression, Ridge, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score, root_mean_squared_error
from sklearn.model_selection import GroupKFold, KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from common import PROCESSED_DIR, REPORTS_DIR, ROOT
from features import CAT_COLS, FEATURE_COLS, NUM_COLS, TEXT_COL, add_features, load_rooms

warnings.filterwarnings("ignore", category=UserWarning)
SEED = 42
MODELS_DIR = ROOT / "models"
# alpha của Ridge + TF-IDF: cố định thay vì RidgeCV (nhanh hơn ~50 lần với ma trận TF-IDF lớn).
# Giá trị được chọn bằng GroupKFold trong experiments.py (mục E) -- chạy lại mục đó nếu dữ liệu thay đổi nhiều.
RIDGE_TFIDF_ALPHA = 1.0


def preprocessor(tfidf=False):
    parts = [
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), NUM_COLS),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=10), CAT_COLS),
    ]
    if tfidf:
        parts.append(("txt", TfidfVectorizer(ngram_range=(1, 2), min_df=5, max_features=20000, sublinear_tf=True),
                      TEXT_COL))
    return ColumnTransformer(parts)


def models():
    return {
        "Dummy (trung bình)": make_pipeline(preprocessor(), DummyRegressor()),
        "Linear Regression": make_pipeline(preprocessor(), LinearRegression()),
        "Ridge": make_pipeline(preprocessor(), RidgeCV(alphas=np.logspace(-2, 3, 20))),
        "Lasso": make_pipeline(preprocessor(), LassoCV(alphas=np.logspace(-4, 0, 30), max_iter=5000)),
        "Random Forest": make_pipeline(preprocessor(), RandomForestRegressor(
            n_estimators=300, min_samples_leaf=2, n_jobs=-1, random_state=SEED)),
        "HistGradientBoosting": make_pipeline(preprocessor(), HistGradientBoostingRegressor(
            max_iter=500, learning_rate=0.05, random_state=SEED)),
        "Ridge + TF-IDF": make_pipeline(preprocessor(tfidf=True), Ridge(alpha=RIDGE_TFIDF_ALPHA)),
        # Kết hợp: trung bình có trọng số (trên log giá); trọng số chọn ở experiments.py mục F
        "Ridge + TF-IDF × 0.7 + HGB × 0.3": VotingRegressor([
            ("ridge_tfidf", make_pipeline(preprocessor(tfidf=True), Ridge(alpha=RIDGE_TFIDF_ALPHA))),
            ("hgb", make_pipeline(preprocessor(), HistGradientBoostingRegressor(
                max_iter=500, learning_rate=0.05, random_state=SEED))),
        ], weights=[0.7, 0.3]),
    }


def metrics(true, pred):
    """Metric trên thang VND (true, pred là giá VND)."""
    return {
        "MAE (triệu)": mean_absolute_error(true, pred) / 1e6,
        "RMSE (triệu)": root_mean_squared_error(true, pred) / 1e6,
        "MAPE (%)": mean_absolute_percentage_error(true, pred) * 100,
        "R2": r2_score(true, pred),
    }


def evaluate(model, X, y_log, groups, splitter):
    """Trả về (metric trung bình các fold, phần dư out-of-fold trên thang log)."""
    rows = []
    oof_resid = pd.Series(np.nan, index=y_log.index)
    for tr, te in splitter.split(X, y_log, groups):
        model.fit(X.iloc[tr], y_log.iloc[tr])
        pred_log = model.predict(X.iloc[te])
        oof_resid.iloc[te] = y_log.iloc[te] - pred_log
        rows.append(metrics(np.exp(y_log.iloc[te]), np.exp(pred_log)))
    return pd.DataFrame(rows).mean(), oof_resid


def main():
    df = add_features(load_rooms())
    X, y_log, groups = df[FEATURE_COLS], np.log(df["price"]), df["group_id"]
    print(f"{len(df)} mẫu, {groups.nunique()} nhóm, {len(NUM_COLS)} đặc trưng số + {len(CAT_COLS)} đặc trưng phân loại\n")

    results, resids = {}, {}
    for name, model in models().items():
        results[name], resids[name] = evaluate(model, X, y_log, groups, GroupKFold(n_splits=5))
        print(f"{name:22s} {results[name].round(3).to_dict()}")
    table = pd.DataFrame(results).T.round(3)

    # Để thấy tác động của rò rỉ dữ liệu: KFold ngẫu nhiên (không theo nhóm) với mô hình tốt nhất
    best = table["MAE (triệu)"].idxmin()
    leaky = evaluate(models()[best], X, y_log, groups,
                     KFold(n_splits=5, shuffle=True, random_state=SEED))[0].round(3)
    table.loc[f"{best} - KFold ngẫu nhiên (có rò rỉ)"] = leaky

    print("\n", table.to_string())
    table.to_csv(REPORTS_DIR / "model_comparison.csv", encoding="utf-8-sig")
    print(f"\n-> {REPORTS_DIR / 'model_comparison.csv'}")

    # Huấn luyện lại mô hình tốt nhất trên toàn bộ dữ liệu để dùng cho demo
    # Khoảng giá 80%: lấy phân vị 10% / 90% của phần dư out-of-fold
    final = models()[best].fit(X, y_log)
    q_lo, q_hi = resids[best].quantile([0.1, 0.9])
    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump({"model": final, "name": best, "metrics": table.loc[best].to_dict(),
                 "resid_q10": q_lo, "resid_q90": q_hi,
                 "districts": sorted(df["district"].dropna().unique()),
                 "furnishings": sorted(df["furnishing"].dropna().unique())},
                MODELS_DIR / "best_model.joblib")
    print(f"-> {MODELS_DIR / 'best_model.joblib'} ({best})")


if __name__ == "__main__":
    main()
