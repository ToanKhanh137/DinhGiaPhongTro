"""Backend cho giao diện web: phục vụ trang tĩnh + các API.

    python web/server.py            # mở http://localhost:8000
    python web/server.py --open     # tự mở trình duyệt
(cần chạy src/run_pipeline.py trước để có models/best_model.joblib)

API
  GET  /api/meta          danh sách quận / phường, thông tin mô hình
  POST /api/predict       giá ước tính + khoảng giá + loại tin + giải thích + tin tương tự
  GET  /api/fetch?url=    đọc một tin đăng từ Chợ Tốt / Phongtro123 / Mogi để điền sẵn form
  GET  /api/map           mặt bằng giá theo phường (cho bản đồ)
  GET  /api/about         số liệu đánh giá mô hình (cho trang "Về mô hình")
"""
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import joblib
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from build_dataset import norm_district, norm_ward, size_from_text  # noqa: E402
from common import PROCESSED_DIR, REPORTS_DIR, get_session, mask_phone  # noqa: E402
from crawl_mogi import parse_detail as mogi_detail  # noqa: E402
from crawl_phongtro123 import parse_detail as pt_detail  # noqa: E402
from crawl_phongtro123 import parse_price  # noqa: E402
from features import (FEATURE_COLS, KEYWORD_LABELS, KEYWORDS, SOURCE_LABELS, add_features,  # noqa: E402
                      load_rooms, strip_accents)
from listing_type import rule_v2_predict  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
MODEL_FILE = ROOT / "models" / "best_model.joblib"

TYPE_INFO = {
    "R": ("Phòng riêng", "Tin cho thuê một phòng với một mức giá — đúng loại tin mô hình được huấn luyện."),
    "G": ("Ở ghép", "Tin ở ghép / homestay / ký túc xá: giá thường tính theo người hoặc theo giường, "
                    "nên giá ước tính cho cả phòng dưới đây chỉ để tham khảo."),
    "N": ("Nhiều mức giá", "Tin liệt kê nhiều phòng hoặc khoảng giá. Hãy nhập đúng diện tích và giá của "
                           "phòng bạn quan tâm để so sánh chính xác."),
}
CHOTOT_FURNISHING = {1: "Nội thất cao cấp", 2: "Nội thất đầy đủ", 3: "Nhà trống"}
# "Nếu tin có thêm...": (nhãn hiển thị, cột từ khóa, cụm từ thêm vào mô tả)
WHATIF = [
    ("thang máy", "kw_thang_may", "có thang máy"), ("máy giặt riêng", "kw_may_giat", "máy giặt riêng"),
    ("full đồ", "kw_full_do", "full đồ"), ("ban công", "kw_ban_cong", "ban công thoáng"),
    ("điều hòa", "kw_dieu_hoa", "điều hòa"), ("vệ sinh khép kín", "kw_khep_kin", "vệ sinh khép kín"),
    ("tủ lạnh", "kw_tu_lanh", "tủ lạnh"), ("khóa vân tay", "kw_van_tay", "khóa vân tay"),
    ("nhà mới xây", "kw_moi_xay", "nhà mới xây"), ("bếp riêng", "kw_bep_rieng", "bếp riêng"),
]

# ---------------------------------------------------------------- dữ liệu và mô hình
bundle = joblib.load(MODEL_FILE)
model = bundle["model"]
# khoảng giá thích nghi theo từng tin và mức giá dự đoán (src/intervals.py); không có thì dùng một độ rộng chung
INTERVAL_FILE = ROOT / "models" / "interval_model.joblib"
interval = joblib.load(INTERVAL_FILE) if INTERVAL_FILE.exists() else None
all_rooms = pd.read_csv(PROCESSED_DIR / "rooms.csv")   # để suy tọa độ theo phường / quận
rooms = load_rooms()                                    # chỉ phòng riêng: tin tương tự, bản đồ
rooms_feat = add_features(rooms)

# Phần tuyến tính dùng để giải thích (Ridge + TF-IDF trong mô hình kết hợp, hoặc chính mô hình nếu là Ridge)
if hasattr(model, "named_estimators_"):
    linear = model.named_estimators_["ridge_tfidf"]
    linear_weight = model.weights[0] / sum(model.weights)
else:
    linear, linear_weight = model, 1.0
ct, ridge = linear[0], linear[-1]
feature_names = ct.get_feature_names_out()
feature_mean = np.asarray(ct.transform(rooms_feat[FEATURE_COLS]).mean(axis=0)).ravel()

app = FastAPI(title="Trọ này có hớ không?")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ---------------------------------------------------------------- giải thích dự đoán
OTHER_TEXT = "Các chi tiết khác trong mô tả"


def term_group(term: str, clean: str, spans) -> str:
    """Gán một token TF-IDF (1-2 từ, đã bỏ dấu) vào tiện ích mà nó nằm trong, ví dụ "sinh khep" -> khép kín."""
    for m in re.finditer(r"(?<!\w)" + re.escape(term) + r"(?!\w)", clean):
        for start, end, label in spans:
            if m.start() < end and m.end() > start:
                return label
    return OTHER_TEXT


def explain(X: pd.DataFrame, top: int = 8):
    """Đóng góp (trên log giá) của từng nhóm đặc trưng so với một phòng trung bình, phần tuyến tính."""
    clean = X["text_clean"].iat[0]
    spans = [(m.start(), m.end(), KEYWORD_LABELS[col])
             for col, pattern in KEYWORDS.items() for m in re.finditer(pattern, clean)]
    xt = ct.transform(X[FEATURE_COLS])
    x = np.asarray(xt.todense()).ravel() if hasattr(xt, "todense") else np.asarray(xt).ravel()
    contrib = ridge.coef_ * (x - feature_mean) * linear_weight
    groups = {}
    for i in np.flatnonzero(np.abs(contrib) > 1e-6):
        kind, feat = feature_names[i].split("__", 1)
        if feat in ("size", "log_size", "size_missing"):
            key = ("Diện tích", "core")
        elif feat.startswith("dist_") or feat.startswith("district"):
            key = ("Vị trí (quận, khoảng cách)", "core")
        elif feat.startswith("furnishing"):
            key = ("Nội thất", "core")
        elif feat in KEYWORD_LABELS:
            # so với phòng trung bình: tin KHÔNG nhắc tiện ích phổ biến cũng làm giá thay đổi
            key = (KEYWORD_LABELS[feat] if x[i] > 0 else f"không nhắc tới {KEYWORD_LABELS[feat]}", "keyword")
        elif kind == "txt" and x[i] > 0:
            label = term_group(feat, clean, spans)
            key = (label, "text" if label == OTHER_TEXT else "keyword")
        else:  # từ không có trong tin (so với tin trung bình), nguồn, độ dài mô tả...: không hiển thị
            key = ("Khác", "other")
        groups[key] = groups.get(key, 0.0) + contrib[i]
    items = [{"label": k[0], "kind": k[1], "effect_pct": round((np.exp(v) - 1) * 100, 1)}
             for k, v in groups.items() if k[1] != "other" and abs(v) > 0.004]
    items.sort(key=lambda d: -abs(d["effect_pct"]))
    return items[:top]


# ---------------------------------------------------------------- API
class Query(BaseModel):
    district: str
    ward: str | None = None
    size: float = Field(gt=4, lt=200)
    furnishing: str | None = None
    text: str = ""
    asking: float | None = Field(default=None, ge=0, le=100)  # triệu/tháng
    source: str | None = None  # nguồn tin khi đọc từ link; không có thì lấy trung bình trên các nguồn


def title_of(text: str) -> str:
    first = str(text).split("\n", 1)[0].strip()
    return first[:90] + ("…" if len(first) > 90 else "")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/meta")
def meta():
    counts = rooms.groupby(["district", "ward"]).size().reset_index(name="n")
    wards = {d: g.sort_values("n", ascending=False)["ward"].tolist() for d, g in counts.groupby("district")}
    district_n = rooms["district"].value_counts()
    return {
        "districts": [d for d in district_n.index if district_n[d] >= 20],
        "wards": wards,
        "furnishings": bundle["furnishings"],
        "model": {"name": bundle["name"], "mae": bundle["metrics"]["MAE (triệu)"], "mape": bundle["metrics"]["MAPE (%)"],
                  "r2": bundle["metrics"]["R2"]},
        "n_listings": int(len(rooms)),
        "updated": datetime.fromtimestamp(MODEL_FILE.stat().st_mtime).strftime("%d/%m/%Y"),
    }


@app.post("/api/predict")
def predict(q: Query):
    ward = q.ward or None
    area = all_rooms[all_rooms["ward"] == ward] if ward else all_rooms[all_rooms["district"] == q.district]
    if area.empty:
        area = all_rooms[all_rooms["district"] == q.district]
    # Mô hình có học hiệu ứng nguồn tin; tin đọc từ link dùng đúng nguồn, tin tự nhập lấy trung bình trên các nguồn
    sources = [q.source] if q.source in SOURCE_LABELS else list(SOURCE_LABELS)
    row = pd.DataFrame([{
        "size": q.size, "district": q.district, "ward": ward,
        "lat": area["lat"].median(), "lon": area["lon"].median(),
        "furnishing": q.furnishing or None, "source": sources[0],
        "geo_precision": "ward" if ward else "district", "text": q.text,
    }])
    X = add_features(row)
    # dự đoán theo lô: (tin gốc + mỗi tiện ích còn thiếu được thêm vào mô tả) × mỗi nguồn
    missing = [(label, phrase) for label, col, phrase in WHATIF if X[col].iat[0] == 0]
    texts = [q.text] + [q.text + chr(10) + phrase for _, phrase in missing]
    variants = pd.concat([row.assign(text=t, source=src) for t in texts for src in sources], ignore_index=True)
    Xv = add_features(variants)[FEATURE_COLS]
    logs = model.predict(Xv).reshape(len(texts), len(sources)).mean(axis=1)
    pred_log = float(logs[0])
    whatif = sorted(({"label": label, "phrase": phrase, "price": round(float(np.exp(v) / 1e6), 2),
                      "delta_pct": round(float((np.exp(v - pred_log) - 1) * 100), 1)}
                     for (label, phrase), v in zip(missing, logs[1:])), key=lambda d: -d["delta_pct"])
    pred = float(np.exp(pred_log) / 1e6)
    if interval:
        # độ khó: trung bình trên các nguồn (như giá ước tính); phân vị lấy theo mức giá dự đoán nếu có
        scale = max(float(interval["model"].predict(Xv.iloc[:len(sources)]).mean()), interval["min_scale"])
        q_lo, q_hi = interval["q_low"], interval["q_high"]
        if "pred_edges" in interval:
            b = int(np.digitize(pred, interval["pred_edges"]))
            q_lo, q_hi = interval["q_low_bins"][b], interval["q_high_bins"][b]
        lo, hi = (float(np.exp(pred_log + q * scale) / 1e6) for q in (q_lo, q_hi))
    else:
        lo, hi = (float(np.exp(pred_log + bundle[k]) / 1e6) for k in ("resid_q10", "resid_q90"))

    verdict = None
    if q.asking:
        verdict = {"level": "high" if q.asking > hi else "low" if q.asking < lo else "fair",
                   "diff_pct": round((q.asking / pred - 1) * 100)}

    ltype = rule_v2_predict(pd.Series([strip_accents(q.text)]))[0] if q.text.strip() else "R"

    pool = rooms[rooms["ward"] == ward] if ward else rooms[rooms["district"] == q.district]
    if len(pool) < 5:
        pool = rooms[rooms["district"] == q.district]
    pool = pool.dropna(subset=["size"])
    similar = pool[(pool["size"] - q.size).abs() <= max(5, q.size * 0.25)]
    # 8 tin gần diện tích nhất; khi bằng nhau thì chọn ngẫu nhiên (cố định) để không thiên về tin rẻ / đắt
    near = (similar.assign(gap=(similar["size"] - q.size).abs()).sample(frac=1, random_state=0)
            .sort_values("gap", kind="stable").head(8).sort_values("price"))

    return {
        "price": round(pred, 2), "low": round(lo, 2), "high": round(hi, 2),
        "verdict": verdict,
        "listing_type": {"code": ltype, "label": TYPE_INFO[ltype][0], "note": TYPE_INFO[ltype][1]},
        "keywords": [label for col, label in KEYWORD_LABELS.items() if X[col].iloc[0] == 1],
        "explain": explain(X),
        "explain_share": round(linear_weight * 100),
        "whatif": whatif[:6],
        "area": {
            "name": ward or q.district, "n_similar": int(len(similar)),
            "prices": (similar["price"] / 1e6).round(2).tolist()[:300],
            "median": round(float(similar["price"].median() / 1e6), 2) if len(similar) else None,
        },
        "similar": [{"price": round(r.price / 1e6, 2), "size": r.size, "ward": r.ward if isinstance(r.ward, str) else r.district,  # tin thiếu phường: ward là NaN
                     "source": SOURCE_LABELS.get(r.source, r.source), "title": title_of(r.text)}
                    for r in near.itertuples()],
    }


# ---------------------------------------------------------------- đọc tin đăng từ link
def match_ward(district: str | None, ward: str | None):
    if not district or not ward:
        return None
    known = set(rooms.loc[rooms["district"] == district, "ward"].dropna())
    return ward if ward in known else None


def fetch_chotot(url: str):
    m = re.search(r"/(\d{6,})\.htm", url)
    if not m:
        raise HTTPException(400, "Không tìm thấy mã tin trong link Chợ Tốt.")
    r = get_session().get(f"https://gateway.chotot.com/v1/public/ad-listing/{m.group(1)}", timeout=20)
    if r.status_code != 200 or "ad" not in r.json():
        raise HTTPException(404, "Không đọc được tin này trên Chợ Tốt (tin có thể đã bị gỡ).")
    ad = r.json()["ad"]
    text = mask_phone(f"{ad.get('subject', '')}\n{ad.get('body', '')}")
    district = norm_district(ad.get("area_name"))
    return {"district": district, "ward": match_ward(district, norm_ward(ad.get("ward_name_v3"))),
            "size": ad.get("size") or size_from_text(text), "price": (ad.get("price") or 0) / 1e6 or None,
            "furnishing": CHOTOT_FURNISHING.get(ad.get("furnishing_rent")), "text": text}


def fetch_html(url: str):
    r = get_session().get(url, timeout=20)
    if r.status_code != 200:
        raise HTTPException(404, "Không mở được trang tin đăng.")
    return r.text


def fetch_phongtro123(url: str):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")
    d = pt_detail(html)
    title = soup.select_one("h1").get_text(" ", strip=True) if soup.select_one("h1") else ""
    price_el = soup.select_one("header .text-green") or soup.select_one(".text-green")
    size_m = re.search(r"([\d.,]+)\s*m<sup>2", html)
    address = d["table"].get("Địa chỉ", "")
    district = norm_district(d["table"].get("Quận huyện", "").replace("Cho thuê phòng trọ", "").strip())
    ward = re.search(r"((?:Phường|Xã|Thị trấn)\s[^,]+)", address)
    text = f"{title}\n{d['body'] or ''}"
    return {"district": district, "ward": match_ward(district, norm_ward(ward.group(1)) if ward else None),
            "size": float(size_m.group(1).replace(",", ".")) if size_m else size_from_text(text),
            "price": (parse_price(price_el.get_text(" ", strip=True)) or 0) / 1e6 or None if price_el else None,
            "furnishing": None, "text": text}


def fetch_mogi(url: str):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")
    d = mogi_detail(html)
    title = soup.select_one("h1").get_text(" ", strip=True) if soup.select_one("h1") else ""
    price_el = soup.select_one(".price")
    size_m = re.search(r"Diện tích sử dụng\s*([\d.,]+)", soup.get_text(" ", strip=True))
    parts = [p.strip() for p in (d["address"] or "").split(",")]
    district = next((norm_district(p) for p in parts if re.match(r"(Quận|Huyện|Thị xã)\s", p)), None)
    old_ward = next((norm_ward(p) for p in parts if re.match(r"(Phường|Xã|Thị trấn)\s", p)), None)
    # Mogi dùng tên phường cũ -> đổi sang phường mới nếu tra được
    pair = all_rooms.loc[(all_rooms["district"] == district) & (all_rooms["ward_old"] == old_ward), "ward"].dropna()
    ward = pair.mode().iat[0] if len(pair) else old_ward
    text = f"{title}\n{d['body'] or ''}"
    return {"district": district, "ward": match_ward(district, ward),
            "size": float(size_m.group(1).replace(",", ".")) if size_m else size_from_text(text),
            "price": (parse_price(price_el.get_text(" ", strip=True)) or 0) / 1e6 or None if price_el else None,
            "furnishing": None, "text": text}


@app.get("/api/fetch")
def fetch(url: str):
    host = urlparse(url.strip()).netloc.lower()
    if host.endswith("chotot.com") or host.endswith("nhatot.com"):
        data, source = fetch_chotot(url), "Chợ Tốt"
    elif host.endswith("phongtro123.com"):
        data, source = fetch_phongtro123(url), "Phongtro123"
    elif host.endswith("mogi.vn"):
        data, source = fetch_mogi(url), "Mogi"
    else:
        raise HTTPException(400, "Hiện hỗ trợ link từ chotot.com, nhatot.com, phongtro123.com và mogi.vn.")
    if data["district"] not in set(rooms["district"]):
        data["district"] = None
    code = {v: k for k, v in SOURCE_LABELS.items()}.get(source)
    return {"source": source, "source_code": code, **data}


# ---------------------------------------------------------------- bản đồ và thông tin mô hình
@app.get("/api/map")
def map_data():
    df = rooms.assign(ppm=rooms["price"] / rooms["size"])
    clusters = {}
    cf = PROCESSED_DIR / "ward_clusters.csv"
    if cf.exists():
        clusters = pd.read_csv(cf).set_index("ward")["cluster"].to_dict()
    g = df.groupby("ward")
    # Chỉ dùng tin có tọa độ cấp phường/chính xác để xã/phường thiếu tọa độ không bị gán về tâm quận và đè lên phường khác
    has_ward_geo = df["geo_precision"] != "district" if "geo_precision" in df.columns else pd.Series(True, index=df.index)
    g_geo = df[has_ward_geo].groupby("ward")
    wards = pd.DataFrame({
        "district": g["district"].agg(lambda s: s.mode().iat[0]), "n": g.size(),
        "lat": g_geo["lat"].median(), "lon": g_geo["lon"].median(),
        "price": g["price"].median() / 1e6, "ppm": g["ppm"].median() / 1e3, "size": g["size"].median(),
    })
    wards = wards[wards["n"] >= 8].dropna().reset_index()
    wards[["price", "ppm", "size"]] = wards[["price", "ppm", "size"]].round(2)
    wards[["lat", "lon"]] = wards[["lat", "lon"]].round(5)
    wards["cluster"] = wards["ward"].map(clusters)
    district = df.groupby("district").agg(n=("price", "size"), price=("price", "median"), ppm=("ppm", "median"))
    district = district[district["n"] >= 30].assign(price=lambda d: (d["price"] / 1e6).round(2),
                                                    ppm=lambda d: (d["ppm"] / 1e3).round(0))
    wards = wards.astype(object).where(wards.notna(), None)  # NaN (phường chưa thuộc cụm nào) -> null trong JSON
    return {"wards": wards.to_dict("records"),
            "districts": district.sort_values("price", ascending=False).reset_index().to_dict("records")}


def read_csv_safe(name):
    f = REPORTS_DIR / name
    return pd.read_csv(f, encoding="utf-8-sig") if f.exists() else pd.DataFrame()


@app.get("/api/about")
def about():
    comp = read_csv_safe("model_comparison.csv").rename(columns={"Unnamed: 0": "model"})
    exp = read_csv_safe("experiments.csv")
    temporal = read_csv_safe("temporal_validation.csv")
    intervals = read_csv_safe("intervals.csv")
    ablation = exp[exp["thí nghiệm"].str.startswith("C.")] if len(exp) else exp
    full = exp[(exp["thí nghiệm"].str.startswith("A.")) & (exp["cấu hình"] == "Ridge + từ khóa + TF-IDF")] if len(exp) else exp
    counts = all_rooms["source"].value_counts()
    return {
        "models": comp.to_dict("records"),
        "ablation": ([{"config": "Đầy đủ đặc trưng", "r2": float(full["R2"].iat[0])}] if len(full) else []) +
                    [{"config": r["cấu hình"], "r2": float(r["R2"])} for _, r in ablation.iterrows()],
        "temporal": temporal.to_dict("records"),
        "intervals": intervals.to_dict("records"),
        "data": {"total": int(len(all_rooms)), "private": int(len(rooms)),
                 "sources": {SOURCE_LABELS.get(k, k): int(v) for k, v in counts.items()}},
    }


if __name__ == "__main__":
    import threading
    import webbrowser

    import uvicorn
    if "--open" in sys.argv:  # mô hình đã nạp xong ở trên -> mở trình duyệt sau khi server khởi động
        threading.Timer(1.5, webbrowser.open, args=["http://localhost:8000"]).start()
    uvicorn.run(app, host="127.0.0.1", port=8000)
