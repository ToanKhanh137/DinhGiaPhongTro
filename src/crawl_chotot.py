"""Crawl tin cho thuê phòng trọ Hà Nội từ Chợ Tốt (API JSON công khai).

Mỗi lần chạy lưu một "snapshot" vào data/raw/chotot.jsonl (append).
Nên chạy định kỳ (vd. mỗi 2-3 ngày) trong vài tuần để tích lũy dữ liệu;
tin trùng sẽ được lọc ở bước build_dataset.py.

Chỉ giữ các trường cần cho bài toán -- KHÔNG lưu tên, SĐT, avatar, account của người đăng.

    python src/crawl_chotot.py
"""
import argparse
from datetime import datetime

from common import RAW_DIR, append_jsonl, get_session, mask_phone, polite_get

API = "https://gateway.chotot.com/v1/public/ad-listing"
CATEGORY_PHONG_TRO = 1050
REGION_HA_NOI = 12000
PAGE_SIZE = 50

KEEP_FIELDS = [
    "ad_id", "list_id", "list_time", "orig_list_time", "subject", "body",
    "price", "price_string", "size", "deposit",
    "area_name", "ward_name", "ward_name_v3", "street_name",
    "latitude", "longitude", "furnishing_rent", "is_main_street",
    "number_of_images", "contain_videos", "type",
]


def slim(ad: dict) -> dict:
    rec = {k: ad.get(k) for k in KEEP_FIELDS}
    rec["body"] = mask_phone(rec["body"])
    rec["subject"] = mask_phone(rec["subject"])
    # nhãn nội thất dạng chữ (vd. "Nội thất đầy đủ") nằm trong feature_params
    for item in (ad.get("feature_params") or {}).get("compare", {}).get("items", []):
        if item.get("id") == "furnishing_rent":
            rec["furnishing_label"] = item.get("value")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=1000)
    args = ap.parse_args()

    session = get_session()
    crawled_at = datetime.now().isoformat(timespec="seconds")
    out = RAW_DIR / "chotot.jsonl"
    total, n = None, 0
    for page in range(args.max_pages):
        params = dict(cg=CATEGORY_PHONG_TRO, region_v2=REGION_HA_NOI, limit=PAGE_SIZE, o=page * PAGE_SIZE)
        data = polite_get(session, API, params=params).json()
        total = data.get("total", total)
        ads = data.get("ads") or []
        if not ads:
            break
        records = [{**slim(a), "source": "chotot", "crawled_at": crawled_at} for a in ads]
        append_jsonl(out, records)
        n += len(records)
        print(f"trang {page + 1}: +{len(records)} (tổng {n}/{total})")
        if n >= (total or 0):
            break
    print(f"Xong: {n} tin -> {out}")


if __name__ == "__main__":
    main()
