"""ĐỘ ĐỒNG THUẬN GIỮA HAI NGƯỜI GÁN NHÃN loại tin (Cohen's kappa).

540 nhãn R / G / N hiện do một người gán và rà soát. Để biết nhãn có phụ thuộc người gán không, một thành viên KHÁC gán
độc lập 100 tin theo docs/HUONG_DAN_GAN_NHAN.md (không xem nhãn cũ), rồi so với nhãn hiện có.

  Bước 1 — tạo file 100 tin (lấy ngẫu nhiên, hạt giống cố định, từ 300 tin của mẫu ngẫu nhiên; không kèm nhãn cũ):
      python src/label_agreement.py --make
  Bước 2 — người gán thứ hai mở data/labels/kappa_sample_100.csv bằng Excel, điền cột `label` (R, G hoặc N) và cột
           `labeled_by` (họ tên), lưu lại dưới dạng CSV UTF-8.
  Bước 3 — tính kết quả:
      python src/label_agreement.py

Kết quả: reports/label_agreement.md (tỉ lệ trùng nhãn, kappa kèm khoảng tin cậy bootstrap 95%, bảng chéo, các tin lệch).
Cách đọc kappa (Landis & Koch): 0,61–0,80 là đồng thuận tốt, > 0,80 là gần như hoàn toàn.
"""
import argparse

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from common import REPORTS_DIR, ROOT

LABEL_FILE = ROOT / "data" / "labels" / "listing_type_labels.csv"
SAMPLE_FILE = ROOT / "data" / "labels" / "kappa_sample_100.csv"
N_SAMPLE, SEED = 100, 2026
CLASSES = ["R", "G", "N"]


def make_sample():
    if SAMPLE_FILE.exists() and pd.read_csv(SAMPLE_FILE)["label"].notna().any():
        raise SystemExit(f"{SAMPLE_FILE} đã có nhãn được điền, không ghi đè. Đổi tên file cũ nếu muốn tạo lại.")
    lab = pd.read_csv(LABEL_FILE)
    sample = lab[lab["sample"] == "ngau_nhien"].sample(N_SAMPLE, random_state=SEED)[["id", "price", "size", "text"]]
    sample = sample.assign(label="", labeled_by="")
    sample.to_csv(SAMPLE_FILE, index=False, encoding="utf-8-sig")
    print(f"-> {SAMPLE_FILE}: {len(sample)} tin, điền cột label (R / G / N) và labeled_by")


def agreement(first, second):
    """(tỉ lệ trùng nhãn, kappa, cận dưới, cận trên của khoảng tin cậy bootstrap 95%)."""
    first, second = np.asarray(first), np.asarray(second)
    kappa = cohen_kappa_score(first, second, labels=CLASSES)
    rng = np.random.default_rng(SEED)
    boot = []
    for _ in range(2000):
        i = rng.integers(0, len(first), len(first))
        k = cohen_kappa_score(first[i], second[i], labels=CLASSES)
        if not np.isnan(k):
            boot.append(k)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return float((first == second).mean()), float(kappa), float(lo), float(hi)


def main():
    if not SAMPLE_FILE.exists():
        raise SystemExit(f"Chưa có {SAMPLE_FILE}. Chạy: python src/label_agreement.py --make")
    second = pd.read_csv(SAMPLE_FILE)
    second["label"] = second["label"].astype("string").str.strip().str.upper()
    todo = second["label"].isna() | (second["label"] == "")
    if todo.any():
        raise SystemExit(f"Còn {int(todo.sum())}/{len(second)} tin chưa điền cột label trong {SAMPLE_FILE}.")
    bad = second[~second["label"].isin(CLASSES)]
    if len(bad):
        raise SystemExit(f"Nhãn không hợp lệ (chỉ nhận R, G, N): {bad['label'].unique().tolist()}")

    first = pd.read_csv(LABEL_FILE)[["id", "label", "labeled_by"]]
    m = second.merge(first, on="id", suffixes=("_2", "_1"), validate="one_to_one")
    acc, kappa, lo, hi = agreement(m["label_1"], m["label_2"])
    cross = pd.crosstab(m["label_1"], m["label_2"]).reindex(index=CLASSES, columns=CLASSES, fill_value=0)
    cross.index.name, cross.columns.name = "người gán 1 ↓ / người gán 2 →", None
    diff = m[m["label_1"] != m["label_2"]].copy()
    diff["text"] = diff["text"].str.replace(r"\s+", " ", regex=True).str[:200]

    who1 = ", ".join(sorted(m["labeled_by_1"].dropna().unique()))
    who2 = ", ".join(sorted(m["labeled_by_2"].dropna().astype(str).unique())) or "(chưa ghi tên)"
    out = ["# Độ đồng thuận giữa hai người gán nhãn loại tin\n",
           f"{len(m)} tin lấy ngẫu nhiên từ mẫu ngẫu nhiên 300 tin. Người gán 1: {who1}. Người gán 2: {who2} "
           "(gán độc lập theo `docs/HUONG_DAN_GAN_NHAN.md`, không xem nhãn của người gán 1).\n",
           f"- Tỉ lệ trùng nhãn: **{acc * 100:.1f}%** ({int(round(acc * len(m)))}/{len(m)} tin)",
           f"- Cohen's kappa: **{kappa:.2f}** (khoảng tin cậy bootstrap 95%: {lo:.2f} – {hi:.2f})\n",
           "## Bảng chéo\n", cross.to_markdown(), "",
           f"## {len(diff)} tin hai người gán khác nhau\n",
           diff[["id", "label_1", "label_2", "text"]].to_markdown(index=False) if len(diff) else "Không có.", ""]
    path = REPORTS_DIR / "label_agreement.md"
    path.write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out[:6]))
    print("->", path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--make", action="store_true", help="tạo file 100 tin cho người gán thứ hai")
    make_sample() if parser.parse_args().make else main()
