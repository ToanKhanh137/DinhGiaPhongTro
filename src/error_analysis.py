"""Phân tích lỗi của mô hình tốt nhất (Ridge + TF-IDF) bằng dự đoán out-of-fold (GroupKFold 5-fold):

  1. Sai số theo khoảng giá, nguồn, quận, độ chính xác tọa độ, có/không ghi diện tích
  2. Các từ / cụm từ TF-IDF có hệ số lớn nhất (kéo giá lên / xuống)
  3. Các tin bị đoán sai nhiều nhất (để đọc tay xem vì sao)
  4. Kiểm tra lệch có hệ thống theo mức giá dự đoán + thử "kéo giãn" dự đoán (calibration_section)

Kết quả: reports/error_analysis.md + reports/figures/06_*.png, 07_*.png

    python src/error_analysis.py
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.model_selection import GroupKFold

from common import PROCESSED_DIR, REPORTS_DIR
from features import FEATURE_COLS, SOURCE_LABELS, add_features, load_rooms
from train import models

FIG_DIR = REPORTS_DIR / "figures"
FIG_DIR.mkdir(exist_ok=True)
MODEL_NAME = "Ridge + TF-IDF"


def oof_predictions(df):
    X, y = df[FEATURE_COLS], np.log(df["price"])
    pred = pd.Series(np.nan, index=df.index)
    fold = pd.Series(-1, index=df.index)
    for k, (tr, te) in enumerate(GroupKFold(n_splits=5).split(X, y, df["group_id"])):
        model = models()[MODEL_NAME].fit(X.iloc[tr], y.iloc[tr])
        pred.iloc[te] = model.predict(X.iloc[te])
        fold.iloc[te] = k
    return np.exp(pred), fold


def calibration_section(df):
    """Mô hình có lệch có hệ thống không? Nhóm theo giá DỰ ĐOÁN (thứ người dùng nhìn thấy), không theo giá thật."""
    ly, lp = np.log(df["price"]), np.log(df["pred"])
    g = df.assign(log_gap=lp - ly).groupby("mức giá dự đoán", observed=True)
    table = pd.DataFrame({
        "số tin": g.size(),
        "giá dự đoán TB (triệu)": (g["pred"].mean() / 1e6).round(2),
        "giá thật TB (triệu)": (g["price"].mean() / 1e6).round(2),
        "đoán lệch (thang log, %)": ((np.exp(g["log_gap"].mean()) - 1) * 100).round(1),
    })
    slope, intercept = np.polyfit(lp, ly, 1)
    # thử "kéo giãn" dự đoán: log giá mới = a + b × log giá dự đoán, (a, b) ước lượng trên các fold khác
    stretched = pd.Series(np.nan, index=df.index)
    for k in sorted(df["fold"].unique()):
        tr, te = df["fold"] != k, df["fold"] == k
        b, a = np.polyfit(lp[tr], ly[tr], 1)
        stretched[te] = np.exp(a + b * lp[te])
    mae = lambda p: (p - df["price"]).abs().mean() / 1e6
    mape = lambda p: ((p - df["price"]).abs() / df["price"]).mean() * 100
    return ("## Mô hình có lệch có hệ thống không? (nhóm theo giá dự đoán)\n\n"
            "Bảng \"Theo khoảng giá\" ở trên nhóm theo giá THẬT nên luôn cho thấy \"co về trung bình\" (phòng rẻ bị đoán "
            "cao, phòng đắt bị đoán thấp) với mọi mô hình chưa hoàn hảo. Câu hỏi đúng cho người dùng là: khi mô hình báo "
            "một mức giá, giá thật trung bình có đúng mức đó không?\n\n" + md(table) + "\n\n"
            f"Hồi quy log giá thật theo log giá dự đoán: hệ số góc = {slope:.3f} (1,000 là lý tưởng). "
            f"Thử kéo giãn dự đoán theo đường hồi quy này (hệ số lấy từ các fold khác): MAE {mae(df['pred']):.3f} → "
            f"{mae(stretched):.3f} triệu, MAPE {mape(df['pred']):.2f}% → {mape(stretched):.2f}%. "
            f"Lệch lớn nhất giữa các mức giá dự đoán là {table['đoán lệch (thang log, %)'].abs().max():.1f}% (so với "
            "hàng chục % khi nhóm theo giá thật). Nếu con số này nhỏ và kéo giãn không giảm sai số thì hiện tượng co về "
            "trung bình theo giá thật đến từ phần biến động giá mà đặc trưng không giải thích được, không sửa được bằng "
            "hiệu chỉnh sau.\n")


def error_table(df, by):
    g = df.groupby(by, observed=True)
    return pd.DataFrame({
        "số tin": g.size(),
        "giá TB (triệu)": g["price"].mean() / 1e6,
        "MAE (triệu)": g["abs_err"].mean() / 1e6,
        "MAPE (%)": g["ape"].mean() * 100,
        "đoán lệch TB (%)": g["signed_pe"].mean() * 100,  # >0: đoán cao hơn thực tế
    }).round(2)


def md(table):
    return table.to_markdown()  # cần gói tabulate


def main():
    df = add_features(load_rooms())
    df["pred"], df["fold"] = oof_predictions(df)
    df["abs_err"] = (df["pred"] - df["price"]).abs()
    df["ape"] = df["abs_err"] / df["price"]
    df["signed_pe"] = (df["pred"] - df["price"]) / df["price"]
    df["khoảng giá"] = pd.cut(df["price"] / 1e6, [0, 2, 3, 4, 5, 7, 10, 30],
                              labels=["≤2tr", "2-3tr", "3-4tr", "4-5tr", "5-7tr", "7-10tr", ">10tr"])
    df["ghi diện tích"] = np.where(df["size_missing"] == 1, "không", "có")
    df["mức giá dự đoán"] = pd.cut(df["pred"] / 1e6, [0, 2.5, 3, 3.5, 4, 5, 30],
                                  labels=["<2,5tr", "2,5-3tr", "3-3,5tr", "3,5-4tr", "4-5tr", ">5tr"])

    sections = [f"# Phân tích lỗi — {MODEL_NAME} (dự đoán out-of-fold, GroupKFold 5-fold)\n",
                f"Tổng: {len(df)} tin. MAE = {df['abs_err'].mean() / 1e6:.3f} triệu, "
                f"MAPE = {df['ape'].mean() * 100:.1f}%, "
                f"{(df['ape'] <= 0.2).mean() * 100:.0f}% tin có sai số ≤ 20%.\n"]
    for title, by in [("Theo khoảng giá", "khoảng giá"), ("Theo nguồn", "source"),
                      ("Theo độ chính xác tọa độ", "geo_precision"), ("Có ghi diện tích không", "ghi diện tích")]:
        sections.append(f"## {title}\n\n{md(error_table(df, by))}\n")
    sections.insert(3, calibration_section(df))  # ngay sau bảng "Theo khoảng giá"
    top_d = df["district"].value_counts()
    sections.append("## Theo quận (≥ 50 tin)\n\n"
                    + md(error_table(df[df["district"].isin(top_d[top_d >= 50].index)], "district")
                         .sort_values("MAPE (%)")) + "\n")

    # Hệ số TF-IDF của mô hình huấn luyện trên toàn bộ dữ liệu
    final = models()[MODEL_NAME].fit(df[FEATURE_COLS], np.log(df["price"]))
    ct, ridge = final[0], final[-1]
    names = ct.get_feature_names_out()
    coef = pd.Series(ridge.coef_, index=names)
    txt = coef[coef.index.str.startswith("txt__")].rename(lambda s: s.removeprefix("txt__"))
    top = pd.concat([txt.nlargest(20), txt.nsmallest(20)])
    sections.append("## Từ / cụm từ ảnh hưởng mạnh nhất (hệ số Ridge trên log giá)\n\n"
                    "Hệ số dương: tin có cụm từ này thường đắt hơn; âm: rẻ hơn (văn bản đã bỏ dấu, đã che giá).\n\n"
                    + md(top.round(3).to_frame("hệ số")) + "\n")
    plt.figure(figsize=(7, 9))
    colors = ["#2a9d8f" if v > 0 else "#e76f51" for v in top.values]
    plt.barh(top.index[::-1], top.values[::-1], color=colors[::-1])
    plt.axvline(0, color="grey", lw=0.8)
    plt.title("Cụm từ trong mô tả kéo giá lên / xuống")
    plt.xlabel("hệ số Ridge (log giá)")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "06_tfidf_coefficients.png", dpi=150)
    plt.close()

    # Dự đoán vs thực tế
    plt.figure(figsize=(6, 6))
    sns.scatterplot(x=df["price"] / 1e6, y=df["pred"] / 1e6, s=8, alpha=0.4,
                    hue=df["source"].map(SOURCE_LABELS).fillna(df["source"]).rename("Nguồn"))
    lim = [0, 15]
    plt.plot(lim, lim, "k--", lw=1)
    plt.xlim(lim)
    plt.ylim(lim)
    plt.xlabel("Giá thực tế (triệu)")
    plt.ylabel("Giá dự đoán (triệu)")
    plt.title("Giá dự đoán (out-of-fold) so với giá thực tế")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "07_pred_vs_actual.png", dpi=150)
    plt.close()

    worst = df.nlargest(15, "ape")[["id", "source", "district", "size", "price", "pred", "text"]].copy()
    worst["price"] = (worst["price"] / 1e6).round(2)
    worst["pred"] = (worst["pred"] / 1e6).round(2)
    worst["text"] = worst["text"].str.replace(r"\s+", " ", regex=True).str[:140]
    sections.append("## 15 tin bị đoán sai nhiều nhất (đọc tay để tìm nguyên nhân)\n\n" + md(worst.set_index("id")) + "\n")

    out = REPORTS_DIR / "error_analysis.md"
    out.write_text("\n".join(sections), encoding="utf-8")
    print("\n".join(sections[:3]))
    print("->", out)


if __name__ == "__main__":
    main()
