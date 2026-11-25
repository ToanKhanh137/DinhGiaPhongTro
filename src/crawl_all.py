"""Chạy tất cả crawler một lượt (danh sách 3 nguồn + trang chi tiết các tin mới).

    python src/crawl_all.py                  # chạy 1 lượt
    python src/crawl_all.py --loop-hours 12  # lặp mỗi 12 giờ (để treo máy)

Mỗi lượt chỉ lấy trang chi tiết của tin MỚI, nên các lượt sau nhanh hơn nhiều lượt đầu.
Nhật ký: reports/crawl_all.log
"""
import argparse
import subprocess
import sys
import time
from datetime import datetime

from common import REPORTS_DIR, ROOT

STEPS = [
    ["src/crawl_chotot.py"],
    ["src/crawl_phongtro123.py"],
    ["src/crawl_mogi.py"],
    ["src/crawl_phongtro123.py", "--details"],
    ["src/crawl_mogi.py", "--details"],
]
LOG = REPORTS_DIR / "crawl_all.log"


def run_once():
    with open(LOG, "a", encoding="utf-8") as log:
        log.write(f"\n===== Lượt crawl {datetime.now():%Y-%m-%d %H:%M} =====\n")
        for step in STEPS:
            log.write(f"--- {' '.join(step)}\n")
            log.flush()
            r = subprocess.run([sys.executable, *step], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            if r.returncode != 0:
                log.write(f"!!! lỗi (mã {r.returncode}), chuyển sang bước tiếp theo\n")
        log.write(f"===== Xong {datetime.now():%Y-%m-%d %H:%M} =====\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop-hours", type=float, default=0)
    args = ap.parse_args()
    while True:
        start = time.time()
        run_once()
        print(f"{datetime.now():%Y-%m-%d %H:%M} xong một lượt, xem {LOG}")
        if not args.loop_hours:
            break
        time.sleep(max(0, args.loop_hours * 3600 - (time.time() - start)))
