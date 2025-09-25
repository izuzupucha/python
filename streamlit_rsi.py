import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go

# ===== Hàm lấy dữ liệu từ Binance =====
from binance.client import Client
# ===== Kết nối client (không cần API key cho dữ liệu public) =====
client = Client()

# ===== Hàm lấy dữ liệu Kline =====
def get_klines(symbol="BTCUSDT", interval="1h", limit=200):
    try:
        # Gọi API qua python-binance
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=[
            "time", "open", "high", "low", "close", "volume",
            "close_time", "qav", "trades", "taker_base", "taker_quote", "ignore"
        ])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        return df
    except Exception as e:
        print("❌ Lỗi khi gọi Binance:", e)
        return pd.DataFrame()


# ===== Hàm tính RSI =====
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = pd.Series(gain).rolling(period).mean()
    avg_loss = pd.Series(loss).rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ===== Streamlit App =====
st.title("📊 RSI Realtime từ Binance + Biểu đồ Nến")

symbol = st.text_input("Nhập cặp coin (ví dụ: BTCUSDT, ETHUSDT...)", "BTCUSDT")

if st.button("Tính RSI"):
    intervals = ["5m", "15m", "1h", "4h", "1d"]
    results = {}

    for interval in intervals:
        df = get_klines(symbol, interval)
        df["RSI"] = calculate_rsi(df["close"])
        df = df.dropna(subset=["RSI"])  # tránh lỗi NaN
    
        if not df.empty:
            rsi_latest = round(df["RSI"].iloc[-1], 2)
            results[interval] = rsi_latest
        else:
            results[interval] = "N/A"

    st.subheader(f"✅ RSI(14) hiện tại của {symbol}")
    for interval, rsi_val in results.items():
        st.write(f"Khung {interval}: **{rsi_val}**")

    # ========== Vẽ Chart cho 1 khung chọn ==========
    st.subheader("📈 Xem chi tiết biểu đồ")
    chosen_interval = st.selectbox("Chọn khung thời gian:", intervals, index=2)

    df = get_klines(symbol, chosen_interval)
    df["RSI"] = calculate_rsi(df["close"])

    # Biểu đồ nến
    fig_candle = go.Figure(data=[go.Candlestick(
        x=df["time"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="Giá"
    )])
    fig_candle.update_layout(title=f"Biểu đồ {symbol} ({chosen_interval})", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig_candle, use_container_width=True)

    # Biểu đồ RSI
    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=df["time"], y=df["RSI"], mode="lines", name="RSI"))
    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
    fig_rsi.update_layout(title=f"RSI(14) - {symbol} ({chosen_interval})", yaxis=dict(range=[0, 100]))
    st.plotly_chart(fig_rsi, use_container_width=True)



