"""Demo: nhập thông tin phòng -> giá thuê hợp lý + khoảng giá 80%.

    streamlit run app/app.py
(cần chạy src/build_dataset.py và src/train.py trước để có models/best_model.joblib)
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from features import FEATURE_COLS, add_features  # noqa: E402

st.set_page_config(page_title="Trọ này có hớ không?", page_icon="🏠")


@st.cache_resource
def load_bundle():
    return joblib.load(ROOT / "models" / "best_model.joblib")


@st.cache_data
def load_rooms():
    return pd.read_csv(ROOT / "data" / "processed" / "rooms.csv")


bundle = load_bundle()
rooms = load_rooms()

st.title("🏠 Trọ này có hớ không?")
st.caption(f"Mô hình: {bundle['name']} · MAE ≈ {bundle['metrics']['MAE (triệu)']:.2f} triệu · "
           f"MAPE ≈ {bundle['metrics']['MAPE (%)']:.0f}% (GroupKFold)")

col1, col2 = st.columns(2)
with col1:
    district = st.selectbox("Quận/huyện", bundle["districts"],
                            index=bundle["districts"].index("Hai Bà Trưng") if "Hai Bà Trưng" in bundle["districts"] else 0)
    wards = sorted(rooms.loc[rooms["district"] == district, "ward"].dropna().unique())
    ward = st.selectbox("Phường/xã (địa giới mới)", ["(không rõ)"] + wards)
    size = st.number_input("Diện tích (m²)", 5.0, 150.0, 20.0, step=1.0)
    asking = st.number_input("Giá chủ trọ đưa ra (triệu/tháng, để 0 nếu chỉ muốn tham khảo)", 0.0, 30.0, 0.0, step=0.1)
with col2:
    furnishing = st.selectbox("Nội thất", ["không rõ"] + bundle["furnishings"])
    text = st.text_area("Dán mô tả tin đăng (không bắt buộc)", height=170,
                        placeholder="VD: Phòng khép kín, điều hòa, nóng lạnh, giờ giấc tự do, không chung chủ...")

# Tọa độ ước lượng = trung vị các tin cùng phường (hoặc cùng quận)
same = rooms[rooms["ward"] == ward] if ward != "(không rõ)" else rooms[rooms["district"] == district]
lat, lon = same["lat"].median(), same["lon"].median()

row = pd.DataFrame([{
    "size": size, "district": district, "ward": None if ward == "(không rõ)" else ward,
    "lat": lat, "lon": lon, "furnishing": None if furnishing == "không rõ" else furnishing,
    "source": "chotot", "geo_precision": "ward" if ward != "(không rõ)" else "district",
    "text": text,
}])
X = add_features(row)[FEATURE_COLS]
pred_log = bundle["model"].predict(X)[0]
pred = np.exp(pred_log) / 1e6
lo, hi = np.exp(pred_log + bundle["resid_q10"]) / 1e6, np.exp(pred_log + bundle["resid_q90"]) / 1e6

st.divider()
st.metric("Giá hợp lý ước tính", f"{pred:.2f} triệu/tháng")
st.write(f"Khoảng giá phổ biến (80%): **{lo:.2f} – {hi:.2f} triệu/tháng**")
if asking > 0:
    if asking > hi:
        st.error(f"Giá {asking:.1f} triệu cao hơn mức phổ biến ~{(asking / pred - 1) * 100:.0f}% → có thể đang bị hớ.")
    elif asking < lo:
        st.success(f"Giá {asking:.1f} triệu rẻ hơn mặt bằng ~{(1 - asking / pred) * 100:.0f}% → hời (nhưng nên kiểm tra kỹ).")
    else:
        st.info("Giá nằm trong khoảng phổ biến của thị trường.")

found = [c.removeprefix("kw_").replace("_", " ") for c in X.columns if c.startswith("kw_") and X[c].iloc[0]]
if found:
    st.caption("Tiện ích nhận diện từ mô tả: " + ", ".join(found))

with st.expander(f"Các tin tương tự trong dữ liệu ({len(same)} tin cùng khu vực)"):
    near = same.assign(diff=(same["size"] - size).abs()).nsmallest(10, "diff")
    st.dataframe(near[["price", "size", "ward", "source"]].assign(price=near["price"] / 1e6)
                 .rename(columns={"price": "giá (triệu)", "size": "m²", "ward": "phường", "source": "nguồn"}),
                 hide_index=True)
    st.map(same[["lat", "lon"]].dropna())
