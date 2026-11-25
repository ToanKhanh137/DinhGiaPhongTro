"""Cấu hình và hàm dùng chung cho toàn project."""
import json
import re
import sys
import time
from pathlib import Path

import requests

# Console Windows mặc định không in được tiếng Việt
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"
for _d in (RAW_DIR, PROCESSED_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (IT3190 student project - educational use)"
REQUEST_DELAY = 1.5  # giây giữa 2 request, crawl chậm để không làm phiền server

# Tọa độ GẦN ĐÚNG của các trường ĐH lớn (lat, lon) -- nhóm nên kiểm tra lại trên Google Maps.
UNIVERSITIES = {
    "hust": (21.0049, 105.8432),   # ĐH Bách khoa Hà Nội
    "neu": (20.9990, 105.8425),    # ĐH Kinh tế Quốc dân
    "vnu": (21.0380, 105.7826),    # ĐHQG Hà Nội (Xuân Thủy)
    "ftu": (21.0230, 105.8053),    # ĐH Ngoại thương
    "ptit": (20.9808, 105.7874),   # Học viện Bưu chính Viễn thông (Hà Đông)
    "haui": (21.0537, 105.7353),   # ĐH Công nghiệp Hà Nội
    "tlu": (21.0075, 105.8247),    # ĐH Thủy lợi
}
CITY_CENTER = (21.0285, 105.8542)  # Hồ Hoàn Kiếm


def get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def polite_get(session: requests.Session, url: str, retries: int = 3, **kwargs) -> requests.Response:
    """GET có delay + retry đơn giản."""
    for attempt in range(retries):
        try:
            time.sleep(REQUEST_DELAY)
            r = session.get(url, timeout=30, **kwargs)
            if r.status_code == 200:
                return r
            print(f"  HTTP {r.status_code} -> {url}")
        except requests.RequestException as e:
            print(f"  lỗi mạng ({e.__class__.__name__}) lần {attempt + 1}")
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Không tải được {url}")


def append_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


_PHONE_RE = re.compile(r"(?:\+?84|0)(?:[\s.\-]?\d){8,10}")


def mask_phone(text):
    """Che số điện thoại trong mô tả tin đăng (không lưu dữ liệu cá nhân)."""
    return _PHONE_RE.sub("<SĐT>", text) if text else text


def haversine_km(lat1, lon1, lat2, lon2):
    """Khoảng cách đường chim bay (km). Chạy được cả với numpy array."""
    import numpy as np
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(a))
