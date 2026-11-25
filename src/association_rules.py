"""KHAI PHÁ LUẬT KẾT HỢP giữa các tiện ích trong tin đăng và mức giá (Apriori).

Mỗi tin phòng riêng (loại R) là một "giao dịch" gồm các item:
  - tiện ích nhắc trong mô tả (khép kín, điều hòa, thang máy, máy giặt, gác xép, ...)
  - mức giá theo tam phân vị: gia_thap / gia_tb / gia_cao
  - khu vực theo cụm của src/clustering.py (nếu đã chạy): cum_1 ... cum_k

Câu hỏi: tiện ích nào thường đi cùng nhau, và tổ hợp nào gắn với phòng giá cao / giá thấp?

Kết quả: reports/association_rules.md, reports/figures/11_rules_scatter.png

    python src/association_rules.py
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

from common import PROCESSED_DIR, REPORTS_DIR
from features import KEYWORD_COLS, add_features, load_rooms

FIG_DIR = REPORTS_DIR / "figures"
MIN_SUPPORT = 0.03
MIN_CONFIDENCE = 0.5
MIN_LIFT = 1.2
# Bỏ các từ khóa không phải tiện ích của phòng
SKIP = {"kw_gan_truong", "kw_khong_chung_chu"}


def transactions(df):
    items = pd.DataFrame(index=df.index)
    for c in KEYWORD_COLS:
        if c not in SKIP:
            items[c.removeprefix("kw_")] = df[c].astype(bool)
    q = df["price"].quantile([1 / 3, 2 / 3]).values
    items["gia_thap"] = df["price"] <= q[0]
    items["gia_tb"] = (df["price"] > q[0]) & (df["price"] <= q[1])
    items["gia_cao"] = df["price"] > q[1]
    clusters_file = PROCESSED_DIR / "ward_clusters.csv"
    if clusters_file.exists():
        cl = pd.read_csv(clusters_file).set_index("ward")["cluster"]
        cluster = df["ward"].map(cl)
        for c in sorted(cluster.dropna().unique()):
            items[f"cum_{int(c)}"] = cluster == c
    return items, q


def fmt(itemset):
    return ", ".join(sorted(itemset))


def main():
    df = add_features(load_rooms())
    items, q = transactions(df)
    out = ["# Luật kết hợp: tiện ích ↔ mức giá (Apriori)\n",
           f"{len(items)} tin phòng riêng, {items.shape[1]} item. Mức giá theo tam phân vị: "
           f"gia_thap ≤ {q[0] / 1e6:.2f} tr < gia_tb ≤ {q[1] / 1e6:.2f} tr < gia_cao. "
           f"Ngưỡng: support ≥ {MIN_SUPPORT}, confidence ≥ {MIN_CONFIDENCE}, lift ≥ {MIN_LIFT}.\n",
           "## Tần suất từng item\n\n" + (items.mean().sort_values(ascending=False) * 100).round(1)
           .to_frame("% số tin").to_markdown() + "\n"]

    freq = apriori(items, min_support=MIN_SUPPORT, use_colnames=True, max_len=4)
    rules = association_rules(freq, metric="confidence", min_threshold=MIN_CONFIDENCE)
    rules = rules[rules["lift"] >= MIN_LIFT].copy()
    rules["luật"] = rules["antecedents"].map(fmt) + "  →  " + rules["consequents"].map(fmt)
    cols = ["luật", "support", "confidence", "lift"]
    print(f"{len(freq)} tập phổ biến, {len(rules)} luật")
    out.append(f"Tìm được {len(freq)} tập phổ biến và {len(rules)} luật thỏa ngưỡng.\n")

    price_items = {"gia_thap", "gia_tb", "gia_cao"}
    for title, cons in [("Luật dẫn tới phòng GIÁ CAO", {"gia_cao"}), ("Luật dẫn tới phòng GIÁ THẤP", {"gia_thap"})]:
        sub = rules[rules["consequents"] == frozenset(cons)].sort_values(["lift", "confidence"], ascending=False)
        sub = sub.drop_duplicates("luật").head(12)
        print(f"\n{title}\n", sub[cols].round(3).to_string(index=False))
        out.append(f"## {title}\n\n" + (sub[cols].round(3).to_markdown(index=False) if len(sub) else "_(không có luật nào)_") + "\n")

    # luật giữa các tiện ích với nhau (không chứa item giá / cụm)
    is_amenity = lambda s: not (s & price_items) and not any(i.startswith("cum_") for i in s)
    amen = rules[rules["antecedents"].map(is_amenity) & rules["consequents"].map(is_amenity)]
    amen = amen[amen["consequents"].map(len) == 1].sort_values("lift", ascending=False).head(15)
    print("\nLuật giữa các tiện ích\n", amen[cols].round(3).to_string(index=False))
    out.append("## Tiện ích thường đi cùng nhau\n\n" + amen[cols].round(3).to_markdown(index=False) + "\n")

    plt.figure(figsize=(6.5, 5))
    sc = plt.scatter(rules["support"], rules["confidence"], c=rules["lift"], cmap="viridis", s=12, alpha=0.7)
    plt.colorbar(sc, label="lift")
    plt.xlabel("support (độ hỗ trợ)")
    plt.ylabel("confidence (độ tin cậy)")
    plt.title(f"{len(rules)} luật kết hợp (lift ≥ {MIN_LIFT})")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "11_rules_scatter.png", dpi=150)
    plt.close()

    (REPORTS_DIR / "association_rules.md").write_text("\n".join(out), encoding="utf-8")
    print("->", REPORTS_DIR / "association_rules.md")


if __name__ == "__main__":
    main()
