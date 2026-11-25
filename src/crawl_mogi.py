"""Crawl tin cho thuê phòng trọ Hà Nội từ mogi.vn.

Bước 1 (mặc định): trang danh sách ?cp=N -> tiêu đề, quận, diện tích, số PN/WC, giá.
Bước 2 (--details): trang chi tiết -> địa chỉ (tới phường, theo địa giới CŨ), mô tả đầy đủ.
Chạy lại được giữa chừng, tin đã lấy sẽ bỏ qua.

robots.txt của site cho phép các trang này (chỉ chặn /api/, /Property/, /template/...).
KHÔNG lưu tên / SĐT người đăng.

    python src/crawl_mogi.py
    python src/crawl_mogi.py --details
"""
import argparse
import re
from datetime import datetime

from bs4 import BeautifulSoup

from common import RAW_DIR, append_jsonl, get_session, mask_phone, polite_get, read_jsonl
from crawl_phongtro123 import parse_price

LIST_URL = "https://mogi.vn/ha-noi/thue-phong-tro-nha-tro"
LIST_OUT = RAW_DIR / "mogi.jsonl"
DETAIL_OUT = RAW_DIR / "mogi_details.jsonl"


def parse_list_page(html: str, crawled_at: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    records = []
    for li in soup.select("ul.props > li"):
        link = li.select_one("a.link-overlay")
        m = re.search(r"-id(\d+)", link["href"]) if link else None
        if not m:
            continue
        attrs = [a.get_text(" ", strip=True) for a in li.select("ul.prop-attr li")]
        size = next((float(x.group(1).replace(",", ".")) for a in attrs if (x := re.match(r"([\d.,]+)\s*m", a))), None)
        bedrooms = next((int(x.group(1)) for a in attrs if (x := re.match(r"(\d+)\s*PN", a))), None)
        wcs = next((int(x.group(1)) for a in attrs if (x := re.match(r"(\d+)\s*WC", a))), None)
        price_el = li.select_one(".price")
        addr_el = li.select_one(".prop-addr")
        created_el = li.select_one(".prop-created")
        records.append({
            "ad_id": int(m.group(1)),
            "url": link["href"],
            "subject": mask_phone(link.get_text(" ", strip=True)),
            "price": parse_price(price_el.get_text(" ", strip=True)) if price_el else None,
            "price_string": price_el.get_text(" ", strip=True) if price_el else None,
            "size": size,
            "bedrooms": bedrooms,
            "wcs": wcs,
            "district_text": addr_el.get_text(" ", strip=True) if addr_el else None,
            "created_text": created_el.get_text(" ", strip=True) if created_el else None,
            "source": "mogi",
            "crawled_at": crawled_at,
        })
    return records


def crawl_list(max_pages: int):
    session = get_session()
    crawled_at = datetime.now().isoformat(timespec="seconds")
    n = 0
    for page in range(1, max_pages + 1):
        recs = parse_list_page(polite_get(session, LIST_URL, params={"cp": page}).text, crawled_at)
        if not recs:
            break
        append_jsonl(LIST_OUT, recs)
        n += len(recs)
        if page % 10 == 0:
            print(f"trang {page}: tổng {n}")
    print(f"Xong: {n} tin -> {LIST_OUT}")


def parse_detail(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    addr = soup.select_one(".address")
    body = soup.select_one(".info-content-body")
    attrs = {}
    for row in soup.select(".info-attrs .info-attr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all("span")]
        if len(cells) >= 2:
            attrs[cells[0]] = cells[-1]
    return {
        "address": addr.get_text(" ", strip=True) if addr else None,
        "body": mask_phone(body.get_text("\n", strip=True)) if body else None,
        "attrs": attrs,
    }


def crawl_details(limit: int | None):
    done = {r["ad_id"] for r in read_jsonl(DETAIL_OUT)}
    todo = {r["ad_id"]: r["url"] for r in read_jsonl(LIST_OUT) if r["ad_id"] not in done}
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
        if i % 100 == 0:
            print(f"  {i}/{len(todo)}")
    print("Xong ->", DETAIL_OUT)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=1000)
    ap.add_argument("--details", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    crawl_details(args.limit) if args.details else crawl_list(args.max_pages)
