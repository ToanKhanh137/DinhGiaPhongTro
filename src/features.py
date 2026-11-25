"""Tạo đặc trưng từ bảng rooms.csv: vị trí (khoảng cách tới các trường ĐH, trung tâm)
và tiện ích tách từ mô tả tin đăng bằng từ khóa."""
import re
import unicodedata

import pandas as pd

from common import CITY_CENTER, PROCESSED_DIR, UNIVERSITIES, haversine_km

# Từ khóa viết KHÔNG DẤU (văn bản cũng được bỏ dấu trước khi so khớp,
# nên "điều hòa" / "điều hoà" / "dieu hoa" đều khớp).
KEYWORDS = {
    "kw_khep_kin": r"khep kin|vskk|wc rieng|ve sinh rieng|vs rieng|wc khep kin",
    "kw_chung_chu": r"(?<!khong )chung chu",
    "kw_khong_chung_chu": r"khong chung chu",
    "kw_gio_tu_do": r"gio giac tu do|gio tu do|tu do gio giac",
    "kw_dieu_hoa": r"dieu hoa|may lanh",
    "kw_nong_lanh": r"nong lanh|binh nong",
    "kw_tu_lanh": r"tu lanh",
    "kw_may_giat": r"may giat",
    "kw_thang_may": r"thang may",
    "kw_ban_cong": r"ban cong|cua so",
    "kw_gac_xep": r"gac xep|gac lung",
    "kw_full_do": r"full do|full noi that|day du noi that|noi that day du",
    "kw_studio": r"studio",
    "kw_1_ngu": r"1 ?(?:pn|ngu|phong ngu)\b|1k1n|1n1k",
    "kw_2_ngu": r"2 ?(?:pn|ngu|phong ngu)\b|2k1n|2n1k|2n2k",
    "kw_ccmn": r"ccmn|chung cu mini",
    "kw_bep_rieng": r"bep rieng|khu bep rieng",
    "kw_van_tay": r"van tay",
    "kw_camera": r"camera|bao ve",
    "kw_moi_xay": r"moi xay|moi tinh|nha moi",
    "kw_o_to": r"o to|oto",
    "kw_pet": r"thu cung|\bpet\b|nuoi cho|nuoi meo",
    "kw_gan_truong": r"gan truong|sinh vien|gan dh|gan dai hoc",
}
KEYWORD_COLS = list(KEYWORDS)

# Tên hiển thị (dùng cho hình vẽ và giao diện web)
KEYWORD_LABELS = {
    "kw_khep_kin": "khép kín", "kw_chung_chu": "chung chủ", "kw_khong_chung_chu": "không chung chủ",
    "kw_gio_tu_do": "giờ tự do", "kw_dieu_hoa": "điều hòa", "kw_nong_lanh": "nóng lạnh", "kw_tu_lanh": "tủ lạnh",
    "kw_may_giat": "máy giặt", "kw_thang_may": "thang máy", "kw_ban_cong": "ban công / cửa sổ",
    "kw_gac_xep": "gác xép", "kw_full_do": "full đồ", "kw_studio": "studio", "kw_1_ngu": "1 phòng ngủ",
    "kw_2_ngu": "2 phòng ngủ", "kw_ccmn": "chung cư mini", "kw_bep_rieng": "bếp riêng", "kw_van_tay": "khóa vân tay",
    "kw_camera": "camera / bảo vệ", "kw_moi_xay": "nhà mới", "kw_o_to": "ô tô đỗ cửa", "kw_pet": "nuôi thú cưng",
    "kw_gan_truong": "gần trường",
}
SOURCE_LABELS = {"chotot": "Chợ Tốt", "phongtro123": "Phongtro123", "mogi": "Mogi"}
DIST_COLS = [f"dist_{u}" for u in UNIVERSITIES] + ["dist_min_uni", "dist_center"]
NUM_COLS = ["size", "log_size", "size_missing", "text_len"] + DIST_COLS + KEYWORD_COLS
CAT_COLS = ["district", "furnishing", "source", "geo_precision"]
TEXT_COL = "text_clean"  # mô tả đã bỏ dấu + che giá, dùng cho TF-IDF
FEATURE_COLS = NUM_COLS + CAT_COLS + [TEXT_COL]


def load_rooms(only_private: bool = True) -> pd.DataFrame:
    """Đọc data/processed/rooms.csv. Mặc định chỉ giữ tin loại R (phòng riêng, một mức giá) theo nhãn
    của src/listing_type.py -- tin ở ghép (giá theo người) và tin nhiều mức giá là nhiễu với bài toán định giá."""
    df = pd.read_csv(PROCESSED_DIR / "rooms.csv")
    types_file = PROCESSED_DIR / "listing_type.csv"
    if not only_private:
        return df
    if not types_file.exists():
        print("!! Chưa có listing_type.csv -> dùng tất cả tin. Chạy src/listing_type.py trước.")
        return df
    df = df.merge(pd.read_csv(types_file), on="id", how="left")
    n_missing = int(df["listing_type"].isna().sum())
    if n_missing:
        print(f"!! {n_missing} tin chưa có nhãn loại tin (dữ liệu mới?) -> chạy lại src/listing_type.py")
    kept = df[df["listing_type"].fillna("R") == "R"].reset_index(drop=True)
    print(f"[load_rooms] giữ {len(kept)}/{len(df)} tin loại R (phòng riêng)")
    return kept


def strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.replace("đ", "d")


# Cụm chỉ tiền trong mô tả ("giá 3,5 tr", "5tr6", "#3TR450", "4k/số", "3.500.000đ").
# Phải xóa trước khi dùng văn bản làm đặc trưng, nếu không mô hình "đọc" luôn giá trong mô tả
# (rò rỉ nhãn) và demo trở nên vô nghĩa khi người dùng dán tin đăng có ghi giá.
_MONEY_RE = re.compile(
    r"(?<![a-z\d])\d+(?:[.,]\d+)?\s*(?:trieu|tr|t\b|k\b|nghin|ngan|cu\b|d\b|vnd|dong)\s*\d*"
    r"|(?<![\d.,])\d{1,3}(?:[.,]\d{3}){1,3}(?![\d.,])|(?<!\d)\d{6,9}(?!\d)")


def mask_money(text: str) -> str:
    """Áp dụng trên văn bản đã strip_accents."""
    return _MONEY_RE.sub(" ", text)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    import numpy as np
    df = df.copy()
    df["size_missing"] = df["size"].isna().astype(int)
    df["log_size"] = np.log(df["size"])
    text = df["text"].fillna("").map(strip_accents).map(mask_money)
    df["text_clean"] = text
    df["text_len"] = text.str.len()
    for col, pattern in KEYWORDS.items():
        df[col] = text.str.contains(pattern, regex=True).astype(int)
    for name, (lat, lon) in UNIVERSITIES.items():
        df[f"dist_{name}"] = haversine_km(df["lat"], df["lon"], lat, lon)
    df["dist_min_uni"] = df[[f"dist_{u}" for u in UNIVERSITIES]].min(axis=1)
    df["dist_center"] = haversine_km(df["lat"], df["lon"], *CITY_CENTER)
    df["furnishing"] = df["furnishing"].fillna("không rõ")
    return df
