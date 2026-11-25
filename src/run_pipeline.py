"""Chạy toàn bộ pipeline: làm sạch -> phân loại loại tin -> huấn luyện -> thí nghiệm -> EDA -> phân tích lỗi
-> phân cụm -> luật kết hợp.

Tiến trình tự hạ mức ưu tiên xuống "Below Normal" (Windows) để vẫn dùng máy / chơi game
bình thường trong lúc chạy; các tiến trình con thừa hưởng mức ưu tiên này.

    python src/run_pipeline.py
    python src/run_pipeline.py --skip-experiments   # bỏ bước thí nghiệm (~15 phút)
"""
import argparse
import os
import subprocess
import sys
import time

from common import ROOT


def lower_priority():
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = wintypes.HANDLE  # handle 64-bit, không khai báo sẽ bị cắt thành int 32-bit
        k32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k32.SetPriorityClass(k32.GetCurrentProcess(), 0x4000)  # BELOW_NORMAL_PRIORITY_CLASS
    else:
        os.nice(10)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-experiments", action="store_true")
    args = ap.parse_args()
    lower_priority()
    steps = ["src/build_dataset.py", "src/listing_type.py", "src/train.py", "src/intervals.py",
             "src/temporal_validation.py", "src/experiments.py", "src/eda.py", "src/error_analysis.py",
             "src/clustering.py", "src/association_rules.py"]
    if args.skip_experiments:
        steps.remove("src/experiments.py")
    for step in steps:
        t = time.time()
        print(f"\n######## {step}", flush=True)
        r = subprocess.run([sys.executable, step], cwd=ROOT)
        print(f"######## {step}: {'OK' if r.returncode == 0 else 'LỖI'} ({time.time() - t:.0f}s)", flush=True)
        if r.returncode != 0:
            sys.exit(r.returncode)
