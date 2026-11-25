"""Gộp dữ liệu thô 2 nguồn -> làm sạch -> data/processed/rooms.csv

Các bước (số dòng sau mỗi bước được ghi vào reports/cleaning_log.txt để đưa vào báo cáo):
  1. Chợ Tốt: bỏ trùng theo list_id (giữ bản crawl mới nhất).
  2. Phongtro123: bỏ trùng theo ad_id, ghép mô tả đầy đủ nếu đã crawl --details.
  3. Chuẩn hóa: quận (theo địa giới cũ, cả 2 nguồn đều có), phường (theo địa giới mới 2025),
     diện tích (nếu thiếu thì tách từ mô tả).
  4. Tọa độ: Chợ Tốt có sẵn lat/lon; Phongtro123 không có -> dùng trung vị tọa độ các tin
     Chợ Tốt cùng phường (mới), nếu không có thì cùng quận. Cột geo_precision ghi lại độ chính xác.
  5. Lọc giá trị bất thường: giá, diện tích, giá/m² ngoài khoảng hợp lý.
  6. group_id: các tin của cùng một phòng (đăng lại / đăng nhiều nơi): trùng (phường, giá, diện tích) hoặc
     mô tả gần giống nhau trong cùng quận (xem room_groups)
     -> dùng cho GroupKFold để tránh rò rỉ dữ liệu giữa train/test.
"""
import re
from datetime import datetime

import numpy as np
import pandas as pd

from common import PROCESSED_DIR, RAW_DIR, REPORTS_DIR, mask_phone, read_jsonl

PRICE_MIN, PRICE_MAX = 500_000, 30_000_000  # VND/tháng
SIZE_MIN, SIZE_MAX = 5, 150                  # m²

log_lines = []


def log(msg):
    print(msg)
    log_lines.append(msg)


def norm_district(s):
    if not isinstance(s, str):
        return None
    s = s.split(",")[0].strip()
    s = re.sub(r"^(Quận|Huyện|Thị xã)\s+", "", s)
    return s or None


def norm_ward(s):
    if not isinstance(s, str):
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def size_from_text(text):
    """'rộng khoảng 35m', '25m2', '30 m²' -> 35.0"""
    if not isinstance(text, str):
        return None
    m = re.search(r"(\d{1,3}(?:[.,]\d)?)\s*(?:m2|m²|m\b|mét vuông)", text, re.I)
    return float(m.group(1).replace(",", ".")) if m else None


def load_chotot():
    df = pd.DataFrame(read_jsonl(RAW_DIR / "chotot.jsonl"))
    if df.empty:
        return df
    log(f"[chotot] thô: {len(df)}")
    df = df.sort_values("crawled_at").drop_duplicates("list_id", keep="last")
    log(f"[chotot] sau bỏ trùng list_id: {len(df)}")
    text = df["subject"].fillna("") + "\n" + df["body"].fillna("")
    size = df["size"].astype(float)
    n_missing = int(size.isna().sum())
    size = size.fillna(text.map(size_from_text))
    log(f"[chotot] thiếu diện tích: {n_missing}, tách được từ mô tả: {n_missing - int(size.isna().sum())}")
    return pd.DataFrame({
        "id": "ct_" + df["list_id"].astype(str),
        "source": "chotot",
        "price": df["price"].astype(float),
        "size": size,
        "district": df["area_name"].map(norm_district),
        "ward": df["ward_name_v3"].map(norm_ward),
        "ward_old": df["ward_name"].map(norm_ward),
        "lat": df["latitude"].astype(float),
        "lon": df["longitude"].astype(float),
        "geo_precision": "exact",
        "furnishing": df.get("furnishing_label"),
        "posted_at": pd.to_datetime(df["list_time"], unit="ms"),
        "text": text,
    })


def load_phongtro123():
    df = pd.DataFrame(read_jsonl(RAW_DIR / "phongtro123.jsonl"))
    if df.empty:
        return df
    log(f"[phongtro123] thô: {len(df)}")
    df = df.sort_values("crawled_at").drop_duplicates("ad_id", keep="last")
    log(f"[phongtro123] sau bỏ trùng ad_id: {len(df)}")
    details = pd.DataFrame(read_jsonl(RAW_DIR / "phongtro123_details.jsonl"))
    if not details.empty:
        details = details.drop_duplicates("ad_id", keep="last")[["ad_id", "body"]]
        df = df.merge(details, on="ad_id", how="left")
        log(f"[phongtro123] có mô tả đầy đủ: {int(df['body'].notna().sum())}")
    else:
        df["body"] = None
    body = df["body"].fillna(df["short_desc"]).fillna("")
    ward = df["address"].str.extract(r"((?:Phường|Xã|Thị trấn)\s[^,]+)")[0].map(norm_ward)
    posted = pd.to_datetime(df["posted_at"].str.extract(r"(\d{2}:\d{2} \d{2}/\d{2}/\d{4})")[0],
                            format="%H:%M %d/%m/%Y", errors="coerce")
    return pd.DataFrame({
        "id": "pt_" + df["ad_id"].astype(str),
        "source": "phongtro123",
        "price": df["price"].astype(float),
        "size": df["size"].astype(float).fillna(body.map(size_from_text)),
        "district": df["district_text"].map(norm_district),
        "ward": ward,
        "lat": np.nan,
        "lon": np.nan,
        "geo_precision": None,
        "furnishing": None,
        "posted_at": posted,
        "text": df["subject"].fillna("") + "\n" + body,
    })


def load_mogi():
    df = pd.DataFrame(read_jsonl(RAW_DIR / "mogi.jsonl"))
    if df.empty:
        return df
    log(f"[mogi] thô: {len(df)}")
    df = df.sort_values("crawled_at").drop_duplicates("ad_id", keep="last")
    log(f"[mogi] sau bỏ trùng ad_id: {len(df)}")
    details = pd.DataFrame(read_jsonl(RAW_DIR / "mogi_details.jsonl"))
    if not details.empty:
        df = df.merge(details.drop_duplicates("ad_id", keep="last")[["ad_id", "address", "body"]], on="ad_id", how="left")
        log(f"[mogi] có trang chi tiết: {int(df['body'].notna().sum())}")
    else:
        df["address"], df["body"] = None, None
    body = df["body"].fillna("")
    return pd.DataFrame({
        "id": "mg_" + df["ad_id"].astype(str),
        "source": "mogi",
        "price": df["price"].astype(float),
        "size": df["size"].astype(float).fillna(body.map(size_from_text)),
        "district": df["district_text"].map(norm_district),
        "ward": None,
        "ward_old": df["address"].str.extract(r"((?:Phường|Xã|Thị trấn)\s[^,]+)")[0].map(norm_ward),
        "lat": np.nan,
        "lon": np.nan,
        "geo_precision": None,
        "furnishing": None,
        "posted_at": pd.NaT,
        "text": df["subject"].fillna("") + "\n" + body,
    })


def fill_coords(df):
    """Phongtro123 / Mogi không có tọa độ -> trung vị tọa độ các tin Chợ Tốt cùng khu vực:
    cùng phường mới (Phongtro123) -> cùng quận + phường cũ (Mogi) -> cùng quận."""
    exact = df[df["geo_precision"] == "exact"]

    # Mogi chỉ có phường cũ: suy ra phường mới từ các cặp (quận, phường cũ) -> phường mới của Chợ Tốt
    old_to_new = (exact.dropna(subset=["ward_old", "ward"]).groupby(["district", "ward_old"])["ward"]
                  .agg(lambda x: x.mode().iat[0]))
    need = df["ward"].isna() & df["ward_old"].notna()
    keys = list(zip(df.loc[need, "district"], df.loc[need, "ward_old"]))
    df.loc[need, "ward"] = [old_to_new.get(k) for k in keys]

    def apply(mask, centers, key_cols, label):
        keys = list(zip(*[df.loc[mask, c] for c in key_cols])) if len(key_cols) > 1 else df.loc[mask, key_cols[0]]
        coords = [centers.loc[k].values if k in centers.index else (np.nan, np.nan) for k in keys]
        if coords:
            df.loc[mask, ["lat", "lon"]] = np.array(coords, dtype=float)
            df.loc[mask & df["lat"].notna(), "geo_precision"] = label

    apply(df["lat"].isna() & df["ward_old"].notna(),
          exact.groupby(["district", "ward_old"])[["lat", "lon"]].median(), ["district", "ward_old"], "ward")
    apply(df["lat"].isna() & df["ward"].notna(), exact.groupby("ward")[["lat", "lon"]].median(), ["ward"], "ward")
    dist_c = exact.groupby("district")[["lat", "lon"]].median()
    miss = df["lat"].isna()
    by_dist = miss & df["district"].isin(dist_c.index)
    df.loc[by_dist, ["lat", "lon"]] = dist_c.loc[df.loc[by_dist, "district"]].values
    df.loc[by_dist, "geo_precision"] = "district"
    log(f"[tọa độ] {df['geo_precision'].value_counts(dropna=False).to_dict()}")
    return df


def room_groups(df, sim=0.85, price_tol=0.10):
    """group_id = "cùng một phòng" (đăng lại / đăng nhiều nơi), ghép theo từng CẶP tin rồi lấy thành phần liên thông:
      - cùng phường + cùng giá + cùng diện tích (diện tích phải có ghi; tin thiếu diện tích không ghép kiểu này);
      - cùng quận + mô tả giống nhau (cosine TF-IDF >= sim) + giá chênh <= price_tol.
    Dùng cho GroupKFold: tin của cùng một phòng không được nằm ở cả train và test."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from sklearn.feature_extraction.text import TfidfVectorizer
    from features import strip_accents

    n = len(df)
    rows, cols = [], []
    has_size = df["size"].notna()
    key = (df["ward"].fillna(df["district"]) + "|" + df["price"].astype(int).astype(str) + "|"
           + df["size"].round().astype("Int64").astype(str))
    for _, idx in df[has_size].groupby(key[has_size]).indices.items():
        ids = df.index[has_size][idx]
        rows += [ids[0]] * (len(ids) - 1)
        cols += list(ids[1:])
    n_exact = len(rows)

    text = df["text"].fillna("").map(strip_accents)
    price = df["price"].to_numpy()
    for _, idx in df.groupby("district").indices.items():
        if len(idx) < 2:
            continue
        m = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True).fit_transform(text.iloc[idx])
        cos = (m @ m.T).tocoo()
        keep = (cos.row < cos.col) & (cos.data >= sim)
        i, j = idx[cos.row[keep]], idx[cos.col[keep]]
        close = np.abs(price[i] - price[j]) <= price_tol * np.maximum(price[i], price[j])
        rows += list(i[close])
        cols += list(j[close])
    graph = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    n_groups, labels = connected_components(graph, directed=False)
    sizes = np.bincount(labels)
    log(f"[nhóm] ghép {n_exact} cặp trùng (phường, giá, diện tích) + {len(rows) - n_exact} cặp mô tả giống nhau "
        f"(cosine >= {sim}, giá chênh <= {price_tol:.0%}) -> {n_groups} phòng; nhóm lớn nhất {sizes.max()} tin")
    return labels


def main():
    df = pd.concat([load_chotot(), load_phongtro123(), load_mogi()], ignore_index=True)
    # che số điện thoại lần nữa: tiêu đề tin Phongtro123 crawl trước 25/11 chưa được che lúc crawl
    df["text"] = df["text"].map(mask_phone)
    log(f"[gộp] {len(df)} tin")
    df = fill_coords(df)

    steps = [
        ("thiếu giá", df["price"].notna()),
        (f"giá ngoài [{PRICE_MIN:,}, {PRICE_MAX:,}]", df["price"].between(PRICE_MIN, PRICE_MAX)),
        # tin không ghi diện tích (rất nhiều tin môi giới) vẫn giữ lại, mô hình dùng cờ size_missing
        (f"diện tích ngoài [{SIZE_MIN}, {SIZE_MAX}] m²", df["size"].isna() | df["size"].between(SIZE_MIN, SIZE_MAX)),
        ("không có tọa độ", df["lat"].notna()),
    ]
    for name, keep in steps:
        before = len(df)
        df = df[keep.reindex(df.index, fill_value=False)]
        log(f"[lọc] bỏ {before - len(df)} tin {name} -> còn {len(df)}")

    ppm = df["price"] / df["size"]
    lo, hi = ppm.quantile([0.01, 0.99])
    before = len(df)
    df = df[ppm.isna() | ppm.between(lo, hi)]
    log(f"[lọc] bỏ {before - len(df)} tin có giá/m² ngoài phân vị 1-99% "
        f"[{lo:,.0f}, {hi:,.0f}] -> còn {len(df)}")

    log(f"[diện tích] {int(df['size'].isna().sum())}/{len(df)} tin không ghi diện tích (giữ lại, gắn cờ size_missing)")
    df = df.reset_index(drop=True)
    df["group_id"] = room_groups(df)
    log(f"[nhóm] {df['group_id'].nunique()} nhóm phòng khác nhau / {len(df)} tin "
        f"(nhóm xuất hiện ở >1 nguồn: {int((df.groupby('group_id')['source'].nunique() > 1).sum())})")
    log(f"[nguồn] {df['source'].value_counts().to_dict()}")

    out = PROCESSED_DIR / "rooms.csv"
    df.to_csv(out, index=False, encoding="utf-8")
    log(f"-> {out}")
    (REPORTS_DIR / "cleaning_log.txt").write_text(
        f"# build_dataset.py chạy lúc {datetime.now():%Y-%m-%d %H:%M}\n" + "\n".join(log_lines) + "\n",
        encoding="utf-8")


if __name__ == "__main__":
    main()
