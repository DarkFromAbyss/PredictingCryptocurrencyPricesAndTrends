import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import os

# Cấu hình trang
st.set_page_config(page_title="Crypto AI Sniper", layout="wide")

# Địa chỉ Gateway (Khi chạy Docker, dùng tên service 'gateway')
# Khi chạy local, dùng 'localhost'
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://gateway:8000")

st.title("🚀 Crypto AI Sniper Dashboard")

# --- SIDEBAR: CẤU HÌNH ---
st.sidebar.header("🔧 Cấu hình")
symbol = st.sidebar.text_input("Cặp tiền", value="BTC-USDT")
model_type = st.sidebar.selectbox("Loại Model", ["lstm", "hybrid", "attention"])
timeframe = st.sidebar.selectbox("Khung thời gian", ["1h", "15m", "4h", "1d"])

# --- TAB GIAO DIỆN ---
tab1, tab2, tab3 = st.tabs(["📈 Thị trường & Dự đoán", "🧠 Huấn luyện AI", "💾 Dữ liệu"])

# === TAB 1: THỊ TRƯỜNG & DỰ ĐOÁN ===
with tab1:
    st.header(f"Phân tích {symbol}")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        initial_capital = st.number_input("Vốn Backtest ($)", value=1000)
        if st.button("🔮 Chạy Dự đoán & Backtest", type="primary"):
            with st.spinner("AI đang suy nghĩ..."):
                try:
                    # Gọi API
                    response = requests.post(
                        f"{GATEWAY_URL}/api/v1/ml/evaluate/{symbol}",
                        params={"model_type": model_type, "initial_capital": initial_capital}
                    )
                    
                    # --- SỬA TỪ ĐÂY ---
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Kiểm tra xem Backend có trả về lỗi logic không (dù HTTP 200)
                        if data.get("status") == "error":
                            st.error(f"Backend báo lỗi: {data.get('message')}")
                        
                        # Kiểm tra xem có đúng là format mới không
                        elif "model_info" in data:
                            st.success("Hoàn tất!")
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Sai số (RMSE)", data['model_info']['rmse'])
                            m2.metric("Lợi nhuận (ROI)", data['backtest_result']['roi'])
                            m3.metric("Tổng tài sản", data['backtest_result']['final_equity'])
                            
                            if 'plot_url' in data:
                                # Xử lý đường dẫn ảnh để hiển thị đúng trong Docker
                                # (Code này chỉ là ví dụ, cần mapping volume đúng)
                                st.image(data['plot_url'], caption="Biểu đồ Dự đoán vs Thực tế")
                        else:
                            # Trường hợp Backend trả về format cũ (không có model_info)
                            st.warning("⚠️ Backend đang trả về phiên bản cũ (Chưa có Backtest).")
                            st.json(data) # In luôn dữ liệu thô ra để xem lỗi gì
                    else:
                        st.error(f"Lỗi HTTP {response.status_code}: {response.text}")
                        
                except Exception as e:
                    st.error(f"Lỗi kết nối hoặc xử lý dữ liệu: {e}")

# === TAB 2: HUẤN LUYỆN AI ===
with tab2:
    st.header("Phòng tập Gym cho AI")
    
    c1, c2 = st.columns(2)
    epochs = c1.number_input("Số Epochs", value=10, min_value=1)
    batch_size = c2.number_input("Batch Size", value=32)
    
    if st.button("🏋️‍♂️ Bắt đầu Train"):
        with st.spinner(f"Đang train model {model_type}... (Có thể mất vài phút)"):
            try:
                res = requests.post(
                    f"{GATEWAY_URL}/api/v1/ml/train/{symbol}",
                    params={"model_type": model_type, "epochs": epochs, "batch_size": batch_size}
                )
                if res.status_code == 200:
                    train_data = res.json()
                    st.json(train_data)
                    st.balloons()
                else:
                    st.error(res.text)
            except Exception as e:
                st.error(f"Lỗi: {e}")

# === TAB 3: QUẢN LÝ DỮ LIỆU ===
with tab3:
    st.header("Đồng bộ dữ liệu từ Binance")
    start_date = st.date_input("Từ ngày", value=pd.to_datetime("2023-01-01"))
    
    if st.button("📥 Tải dữ liệu mới"):
        with st.spinner("Đang tải hàng nghìn cây nến..."):
            try:
                res = requests.post(
                    f"{GATEWAY_URL}/api/v1/data/sync/{symbol}",
                    params={
                        "timeframe": timeframe,
                        "start_date": str(start_date)
                    }
                )
                if res.status_code == 200:
                    st.success("Đồng bộ thành công!")
                    st.json(res.json())
                else:
                    st.error(res.text)
            except Exception as e:
                st.error(f"Lỗi: {e}")