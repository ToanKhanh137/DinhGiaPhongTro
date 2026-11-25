"""Crawl tin cho thuê phòng trọ Hà Nội từ phongtro123.com.

Bước 1 (mặc định): duyệt các trang danh sách ?page=N -> giá, diện tích, quận, địa chỉ, mô tả ngắn.
Bước 2 (--details): vào từng trang chi tiết lấy mô tả đầy đủ. Chậm (~1.5s/tin), có thể dừng
giữa chừng và chạy lại -- các tin đã lấy sẽ được bỏ qua.

robots.txt của site cho phép các trang này (chỉ chặn /api và một số tham số).
KHÔNG lưu tên / SĐT người đăng.

    python src/crawl_phongtro123.py              # danh sách
    python src/crawl_phongtro123.py --details    # mô tả đầy đủ
"""
import argparse
import json
import re
from datetime import datetime

from bs4 import BeautifulSoup

from common import RAW_DIR, append_jsonl, get_session, mask_phone, polite_get, read_jsonl

BASE = "https://phongtro123.com"
LIST_URL = BASE + "/tinh-thanh/ha-noi"
LIST_OUT = RAW_DIR / "phongtro123.jsonl"
DETAIL_OUT = RAW_DIR / "phongtro123_details.jsonl"


def parse_price(text: str):
    """'2.5 triệu/tháng' -> 2_500_000 ; '800 nghìn/tháng' -> 800_000 ;
    '2 triệu 500 nghìn' -> 2_500_000 (mogi.vn)."""
    parts = re.findall(r"([\d.,]+)\s*(triệu|nghìn|ngàn|đồng)", text or "", re.I)
    if not parts:
        return None
    scale = {"triệu": 1e6, "nghìn": 1e3, "ngàn": 1e3, "đồng": 1}
    return int(sum(float(v.replace(",", ".")) * scale[u.lower()] for v, u in parts))


def parse_list_page(html: str, crawled_at: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    records = []
    for li in soup.select("li"):
        ld = li.find("script", type="application/ld+json", recursive=False)
        if not ld:
            continue
        try:
            info = json.loads(ld.string)
        except (TypeError, json.JSONDecodeError):
            continue
        url = info.get("url", "")
        m = re.search(r"pr(\d+)\.html", url)
        if not m:
            continue
        price_el = li.select_one(".text-green")
        area_el = price_el.find_next("span", class_=False) if price_el else None
        area_m = re.search(r"([\d.,]+)\s*m", area_el.get_text(" ", strip=True)) if area_el else None
        district_el = li.select_one("a[href*='/tinh-thanh/ha-noi/']")
        time_el = li.find("time")
        desc_el = li.select_one("p")
        records.append({
            "ad_id": int(m.group(1)),
            "url": url,
            "subject": mask_phone(info.get("name")),
            "price": parse_price(price_el.get_text(" ", strip=True)) if price_el else None,
            "price_string": price_el.get_text(" ", strip=True) if price_el else None,
            "size": float(area_m.group(1).replace(",", ".")) if area_m else None,
            "district_text": district_el.get_text(" ", strip=True) if district_el else None,
            "district_slug": district_el["href"].rstrip("/").split("/")[-1] if district_el else None,
            "address": (info.get("address") or {}).get("streetAddress"),
            "posted_at": time_el.get("title") if time_el else None,
            "short_desc": mask_phone(desc_el.get_text(" ", strip=True)) if desc_el else None,
            "vip_class": " ".join(li.find("figure")["class"]) if li.find("figure") else None,
            "source": "phongtro123",
            "crawled_at": crawled_at,
        })
    return records


def crawl_list(max_pages: int):
    session = get_session()
    crawled_at = datetime.now().isoformat(timespec="seconds")
    n = 0
    for page in range(1, max_pages + 1):
        html = polite_get(session, LIST_URL, params={"page": page}).text
        recs = parse_list_page(html, crawled_at)
        if not recs:
            break
        append_jsonl(LIST_OUT, recs)
        n += len(recs)
        print(f"trang {page}: +{len(recs)} (tổng {n})")
    print(f"Xong: {n} tin -> {LIST_OUT}")


def parse_detail(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    desc = None
    for h in soup.find_all("h2"):
        if "Thông tin mô tả" in h.get_text():
            desc = "\n".join(p.get_text(" ", strip=True) for p in h.find_next_siblings("p"))
            break
    table = {}
    for tr in soup.select("table tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) >= 2:
            table[cells[0].rstrip(":")] = cells[1]
    return {"body": mask_phone(desc), "table": table}


def crawl_details(limit: int | None):
    done = {r["ad_id"] for r in read_jsonl(DETAIL_OUT)}
    todo = {}
    for r in read_jsonl(LIST_OUT):
        if r["ad_id"] not in done:
            todo[r["ad_id"]] = r["url"]
    todo = list(todo.items())[:limit] if limit else list(todo.items())
    print(f"Cần lấy {len(todo)} trang chi tiết (đã có {len(done)})")
    session = get_session()
    for i, (ad_id, url) in enumerate(todo, 1):
        try:
            html = polite_get(session, url).text
        except RuntimeError as e:
            print(e)
            continue
        append_jsonl(DETAIL_OUT, [{"ad_id": ad_id, **parse_detail(html)}])
        if i % 50 == 0:
            print(f"  {i}/{len(todo)}")
    print("Xong ->", DETAIL_OUT)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=1000)
    ap.add_argument("--details", action="store_true", help="lấy mô tả đầy đủ từ trang chi tiết")
    ap.add_argument("--limit", type=int, default=None, help="giới hạn số trang chi tiết (để thử)")
    args = ap.parse_args()
    crawl_details(args.limit) if args.details else crawl_list(args.max_pages)
