"""Phân tích khám phá dữ liệu -> reports/figures/*.png

    python src/eda.py
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from common import PROCESSED_DIR, REPORTS_DIR
from features import KEYWORD_COLS, KEYWORD_LABELS, SOURCE_LABELS, add_features

FIG_DIR = REPORTS_DIR / "figures"
FIG_DIR.mkdir(exist_ok=True)
sns.set_theme(style="whitegrid")


def save(name):
    plt.tight_layout()
    plt.savefig(FIG_DIR / name, dpi=150)
    plt.close()
    print("->", FIG_DIR / name)


def main():
    df = add_features(pd.read_csv(PROCESSED_DIR / "rooms.csv"))
    df["price_m"] = df["price"] / 1e6
    df["ppm_k"] = df["price"] / df["size"] / 1e3
    df["Nguồn"] = df["source"].map(SOURCE_LABELS).fillna(df["source"])

    print(df[["price_m", "size", "ppm_k"]].describe().round(2).to_string(), "\n")
    print(df["source"].value_counts().to_string(), "\n")

    # 1. Phân bố giá theo nguồn
    sns.histplot(data=df, x="price_m", hue="Nguồn", bins=60, element="step")
    plt.xlabel("Giá thuê (triệu/tháng)")
    plt.ylabel("Số tin")
    plt.title("Phân bố giá thuê")
    save("01_price_hist.png")

    # 2. Giá theo quận (các quận có >= 30 tin)
    top = df["district"].value_counts()
    top = top[top >= 30].index
    order = df[df["district"].isin(top)].groupby("district")["price_m"].median().sort_values().index
    plt.figure(figsize=(8, 6))
    sns.boxplot(data=df[df["district"].isin(top)], y="district", x="price_m", order=order, showfliers=False)
    plt.xlabel("Giá thuê (triệu/tháng)")
    plt.ylabel("")
    plt.title("Giá thuê theo quận/huyện")
    save("02_price_by_district.png")

    # 3. Giá theo diện tích
    sns.scatterplot(data=df, x="size", y="price_m", hue="Nguồn", alpha=0.4, s=12)
    plt.xlabel("Diện tích (m²)")
    plt.ylabel("Giá (triệu/tháng)")
    plt.title("Giá thuê theo diện tích")
    save("03_price_vs_size.png")

    # 4. Bản đồ giá/m²
    # chỉ tin có tọa độ thật (Chợ Tốt); Phongtro123 / Mogi chỉ có tọa độ suy ra theo phường
    d = df[df["geo_precision"] == "exact"].dropna(subset=["ppm_k"])
    plt.figure(figsize=(7, 7))
    sc = plt.scatter(d["lon"], d["lat"], c=d["ppm_k"].clip(upper=d["ppm_k"].quantile(0.95)), cmap="viridis", s=8, alpha=0.7)
    plt.colorbar(sc, label="nghìn đồng / m² / tháng")
    plt.xlim(105.70, 105.95)
    plt.ylim(20.90, 21.12)
    plt.xlabel("kinh độ")
    plt.ylabel("vĩ độ")
    plt.title("Giá thuê / m² theo vị trí (tin Chợ Tốt có tọa độ)")
    save("04_ppm_map.png")

    # 5. Chênh lệch giá trung vị khi tin có / không có từ khóa tiện ích
    rows = []
    for c in KEYWORD_COLS:
        has = df.loc[df[c] == 1, "price_m"]
        if len(has) >= 20:
            rows.append({"tiện ích": KEYWORD_LABELS.get(c, c), "số tin": len(has),
                         "chênh lệch (%)": (has.median() / df.loc[df[c] == 0, "price_m"].median() - 1) * 100})
    kw = pd.DataFrame(rows).sort_values("chênh lệch (%)")
    print(kw.round(1).to_string(index=False))
    plt.figure(figsize=(7, 6))
    sns.barplot(data=kw, y="tiện ích", x="chênh lệch (%)", color="steelblue")
    plt.ylabel("")
    plt.xlabel("chênh lệch giá trung vị so với tin không nhắc (%)")
    plt.title("Chênh lệch giá trung vị khi tin có nhắc tới tiện ích")
    save("05_keyword_effect.png")


if __name__ == "__main__":
    main()
