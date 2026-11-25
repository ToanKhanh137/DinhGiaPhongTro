"""PHÂN CỤM các khu vực trọ (đơn vị: phường, địa giới mới) theo mặt bằng giá và đặc điểm phòng.

Mỗi phường có >= MIN_LISTINGS tin loại R được mô tả bằng: giá/m² trung vị, giá trung vị, diện tích trung vị,
tỉ lệ tin có các tiện ích chính, khoảng cách tới trung tâm / trường ĐH gần nhất.

  1. Chọn số cụm k cho K-Means bằng Elbow (inertia), Silhouette, Davies-Bouldin, Calinski-Harabasz;
     độ ổn định của k và của các cụm bằng lấy mẫu con
  2. So sánh K-Means, Agglomerative (Ward), DBSCAN (eps theo đồ thị k-khoảng cách)
  3. Hồ sơ từng cụm + bản đồ + chiếu PCA 2 chiều

Kết quả: reports/clustering.md, reports/figures/08_*.png ... 10_*.png, data/processed/ward_clusters.csv

    python src/clustering.py
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from common import PROCESSED_DIR, REPORTS_DIR
from features import add_features, load_rooms

FIG_DIR = REPORTS_DIR / "figures"
FIG_DIR.mkdir(exist_ok=True)
SEED = 42
MIN_LISTINGS = 10
AMENITIES = ["kw_khep_kin", "kw_full_do", "kw_thang_may", "kw_may_giat", "kw_ban_cong",
             "kw_gac_xep", "kw_studio", "kw_1_ngu", "kw_chung_chu", "kw_ccmn"]
FEATURE_SETS = {
    "giá + vị trí (4)": ["ppm_median", "price_median", "dist_center", "dist_min_uni"],
    "gọn: giá/m² + vị trí + 4 tiện ích (7)": ["ppm_median", "dist_center", "dist_min_uni",
                                              "p_kw_full_do", "p_kw_thang_may", "p_kw_khep_kin", "p_kw_ccmn"],
    "đầy đủ (15)": ["ppm_median", "price_median", "size_median", "dist_center", "dist_min_uni"]
                   + [f"p_{a}" for a in AMENITIES],
}
MAIN_SET = "gọn: giá/m² + vị trí + 4 tiện ích (7)"
FEATURES = FEATURE_SETS[MAIN_SET]
K_RANGE = range(2, 9)
N_BOOT = 200


def choose_k(ksel):
    """Trong các k có silhouette >= 90% mức tốt nhất, chọn k có Davies-Bouldin nhỏ nhất."""
    ok = ksel[ksel["silhouette"] >= 0.9 * ksel["silhouette"].max()]
    return int(ok["davies_bouldin"].idxmin())


def ward_table(df):
    df = df.assign(ppm=df["price"] / df["size"])
    g = df.groupby("ward")
    wards = pd.DataFrame({
        "district": g["district"].agg(lambda s: s.mode().iat[0]),
        "n": g.size(),
        "lat": g["lat"].median(),
        "lon": g["lon"].median(),
        "ppm_median": g["ppm"].median() / 1e3,          # nghìn VND/m²
        "price_median": g["price"].median() / 1e6,      # triệu VND
        "size_median": g["size"].median(),
        # log khoảng cách: phân phối lệch phải, vài xã ngoại thành (Hòa Lạc ~36 km) sẽ chiếm riêng một cụm nếu để nguyên
        "dist_center": np.log1p(g["dist_center"].median()),
        "dist_min_uni": np.log1p(g["dist_min_uni"].median()),
        **{f"p_{a}": g[a].mean() for a in AMENITIES},
    })
    return wards[wards["n"] >= MIN_LISTINGS].dropna(subset=FEATURE_SETS["đầy đủ (15)"])


def scores(X, labels):
    mask = labels >= 0  # DBSCAN: bỏ điểm nhiễu khi tính chỉ số
    if len(set(labels[mask])) < 2:
        return dict(silhouette=np.nan, davies_bouldin=np.nan, calinski_harabasz=np.nan)
    return dict(silhouette=silhouette_score(X[mask], labels[mask]),
                davies_bouldin=davies_bouldin_score(X[mask], labels[mask]),
                calinski_harabasz=calinski_harabasz_score(X[mask], labels[mask]))


def main():
    wards = ward_table(add_features(load_rooms()))
    out = ["# Phân cụm khu vực trọ (đơn vị: phường)\n",
           f"{len(wards)} phường có ≥ {MIN_LISTINGS} tin phòng riêng. Đặc trưng chuẩn hóa z-score.\n"]

    # 0. So sánh bộ đặc trưng (K-Means, k = 2..8)
    rows = []
    for name, feats in FEATURE_SETS.items():
        Xf = StandardScaler().fit_transform(wards[feats])
        for k in K_RANGE:
            lab = KMeans(n_clusters=k, n_init=20, random_state=SEED).fit_predict(Xf)
            rows.append({"bộ đặc trưng": name, "k": k, **scores(Xf, lab)})
    fs = pd.DataFrame(rows)
    fs_best = fs.loc[fs.groupby("bộ đặc trưng")["silhouette"].idxmax()].set_index("bộ đặc trưng").round(3)
    print(fs_best.to_string(), "\n")
    out.append("## So sánh bộ đặc trưng (k có silhouette tốt nhất của mỗi bộ)\n\n" + fs_best.to_markdown() +
               "\n\nThêm nhiều đặc trưng tỉ lệ tiện ích làm cấu trúc cụm mờ đi (ít điểm, nhiều chiều nhiễu). "
               f"Dùng bộ **{MAIN_SET}**: cân bằng giữa chất lượng cụm và khả năng diễn giải.\n")
    X = StandardScaler().fit_transform(wards[FEATURES])

    # 1. Chọn k
    rows = []
    for k in K_RANGE:
        km = KMeans(n_clusters=k, n_init=20, random_state=SEED).fit(X)
        rows.append({"k": k, "inertia": km.inertia_, **scores(X, km.labels_)})
    ksel = pd.DataFrame(rows).set_index("k")
    best_k = choose_k(ksel)
    out.append("## Chọn số cụm cho K-Means\n\n" + ksel.round(3).to_markdown() +
               "\n\nQuy tắc: trong các k có silhouette ≥ 90% mức tốt nhất, chọn k có Davies-Bouldin nhỏ nhất "
               f"→ **k = {best_k}** (silhouette càng lớn càng tốt, Davies-Bouldin càng nhỏ càng tốt).\n")
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    for ax, col, title in zip(axes, ["inertia", "silhouette", "davies_bouldin"],
                              ["Elbow (inertia)", "Silhouette (↑)", "Davies-Bouldin (↓)"]):
        ax.plot(ksel.index, ksel[col], "o-")
        ax.axvline(best_k, color="grey", ls="--", lw=0.8)
        ax.set_title(title)
        ax.set_xlabel("k")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "08_choose_k.png", dpi=150)
    plt.close()

    # 2. So sánh thuật toán (cùng k)
    nn = NearestNeighbors(n_neighbors=5).fit(X)
    kdist = np.sort(nn.kneighbors(X)[0][:, -1])
    eps = float(np.quantile(kdist, 0.9))  # "khuỷu" của đồ thị k-khoảng cách, lấy xấp xỉ phân vị 90%
    algos = {
        f"K-Means (k={best_k})": KMeans(n_clusters=best_k, n_init=20, random_state=SEED).fit_predict(X),
        f"Agglomerative Ward (k={best_k})": AgglomerativeClustering(n_clusters=best_k, linkage="ward").fit_predict(X),
        f"DBSCAN (eps={eps:.2f}, min_samples=5)": DBSCAN(eps=eps, min_samples=5).fit_predict(X),
    }
    km_labels = list(algos.values())[0]
    comp = pd.DataFrame([{"thuật toán": name, "số cụm": len(set(lab[lab >= 0])), "điểm nhiễu": int((lab < 0).sum()),
                          **scores(X, lab), "ARI so với K-Means": adjusted_rand_score(km_labels, lab)}
                         for name, lab in algos.items()]).set_index("thuật toán").round(3)
    print(comp.to_string())
    out.append("## So sánh thuật toán\n\n" + comp.to_markdown() +
               "\n\nARI (Adjusted Rand Index) đo mức độ hai cách phân cụm giống nhau (1 = trùng hoàn toàn).\n")

    # 2b. Độ ổn định: lấy mẫu con 80% số phường KHÔNG hoàn lại (lấy mẫu có hoàn lại tạo điểm trùng -> "cụm" giả rất
    #     chặt, làm chỉ số chọn k thiên về nhiều cụm), chọn k theo cùng quy tắc, so cụm với kết quả trên toàn bộ
    rng = np.random.default_rng(SEED)
    chosen, aris = [], []
    for _ in range(N_BOOT):
        idx = rng.choice(len(X), size=int(0.8 * len(X)), replace=False)
        Xb = X[idx]
        kb = choose_k(pd.DataFrame([{"k": k, **scores(Xb, KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(Xb))}
                                    for k in K_RANGE]).set_index("k"))
        chosen.append(kb)
        lab_b = KMeans(n_clusters=best_k, n_init=10, random_state=SEED).fit(Xb).predict(X)
        aris.append(adjusted_rand_score(km_labels, lab_b))
    k_freq = pd.Series(chosen).value_counts(normalize=True).sort_index().mul(100).round(1)
    print(f"\nlấy mẫu con: k được chọn {k_freq.to_dict()} (%), ARI với k={best_k}: trung vị {np.median(aris):.2f}")
    out.append(f"## Độ ổn định ({N_BOOT} mẫu con, mỗi mẫu 80% số phường)\n\n"
               f"Tỉ lệ mỗi k được quy tắc chọn: " + ", ".join(f"k = {k}: {v}%" for k, v in k_freq.items()) + ".\n\n"
               f"ARI giữa cụm K-Means (k = {best_k}) học trên mẫu con và trên toàn bộ: trung vị {np.median(aris):.2f}, "
               f"khoảng 10–90%: {np.quantile(aris, 0.1):.2f} – {np.quantile(aris, 0.9):.2f}. "
               "Số cụm dao động giữa các mẫu là dấu hiệu dữ liệu không có cấu trúc cụm rõ.\n")

    # 3. Hồ sơ cụm (K-Means), sắp theo giá/m² tăng dần
    wards["cluster"] = km_labels
    order = wards.groupby("cluster")["ppm_median"].median().sort_values().index
    wards["cluster"] = wards["cluster"].map({c: i + 1 for i, c in enumerate(order)})
    for c in ["dist_center", "dist_min_uni"]:
        wards[c + "_km"] = np.expm1(wards[c])
    prof = wards.groupby("cluster").agg(so_phuong=("n", "size"), so_tin=("n", "sum"),
                                        **{(c + "_km" if c.startswith("dist") else c): (c + "_km" if c.startswith("dist") else c, "median")
                                           for c in FEATURES}).round(2)
    top = wards.sort_values("n", ascending=False).reset_index()
    prof["phường tiêu biểu (nhiều tin nhất)"] = top.groupby("cluster")["ward"].agg(lambda s: ", ".join(s.head(4)))
    print("\n", prof.T.to_string())
    out.append("## Hồ sơ các cụm (K-Means, trung vị theo phường; cụm 1 = giá/m² thấp nhất)\n\n" + prof.T.to_markdown() + "\n")

    cmap = plt.get_cmap("viridis", best_k)
    plt.figure(figsize=(7, 7))
    sc = plt.scatter(wards["lon"], wards["lat"], c=wards["cluster"], cmap=cmap, s=wards["n"].clip(upper=200) * 1.5,
                     alpha=0.8, edgecolor="white", linewidth=0.5)
    plt.colorbar(sc, ticks=range(1, best_k + 1), label="cụm (1 = rẻ nhất / m²)")
    plt.title("Các cụm khu vực trọ (mỗi điểm là một phường, kích thước = số tin)")
    plt.xlabel("kinh độ")
    plt.ylabel("vĩ độ")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "09_cluster_map.png", dpi=150)
    plt.close()

    pca = PCA(n_components=2, random_state=SEED).fit(X)
    P = pca.transform(X)
    plt.figure(figsize=(6.5, 5))
    sc = plt.scatter(P[:, 0], P[:, 1], c=wards["cluster"], cmap=cmap, s=30, alpha=0.85)
    plt.colorbar(sc, ticks=range(1, best_k + 1), label="cụm")
    plt.xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.0%} phương sai)")
    plt.ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.0%} phương sai)")
    plt.title("Các phường chiếu lên 2 thành phần chính")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "10_cluster_pca.png", dpi=150)
    plt.close()

    wards.reset_index().to_csv(PROCESSED_DIR / "ward_clusters.csv", index=False, encoding="utf-8")
    (REPORTS_DIR / "clustering.md").write_text("\n".join(out), encoding="utf-8")
    print("->", REPORTS_DIR / "clustering.md")


if __name__ == "__main__":
    main()
