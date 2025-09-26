import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
import pdb
import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go

# ================= Binance =================
BINANCE_ENDPOINTS = [
    "https://data-api.binance.vision/api/v3/klines",   # mirror (ít bị chặn)
    "https://api.binance.com/api/v3/klines"            # official
]

def get_klines_binance(symbol="BTCUSDT", interval="1h", limit=200):
    for base in BINANCE_ENDPOINTS:
        try:
            url = f"{base}?symbol={symbol}&interval={interval}&limit={limit}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data, columns=[
                    "time", "open", "high", "low", "close", "volume",
                    "close_time", "qav", "trades", "taker_base", "taker_quote", "ignore"
                ])
                df["time"] = pd.to_datetime(df["time"], unit="ms")
                df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
                print(f"✅ Thành công Binance endpoint: {base}")
                return df
        except Exception as e:
            print(f"⚠️ Binance lỗi ({base}): {e}")
            continue
    return pd.DataFrame()

# ================= Bybit =================
def get_klines_bybit(symbol="BTCUSDT", interval="60", limit=200, category="spot"):
    url = "https://api.bybit.com/v5/market/kline"
    params = {"category": category, "symbol": symbol, "interval": interval, "limit": limit}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "result" not in data or "list" not in data["result"]:
            raise ValueError(f"Phản hồi API Bybit không hợp lệ: {data}")

        kline_data = data["result"]["list"][::-1]  # đảo ngược: cũ → mới
        df = pd.DataFrame(kline_data, columns=[
            "time","open","high","low","close","volume","turnover"
        ])
        df["time"] = pd.to_datetime(df["time"].astype(int), unit="s")
        df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
        print("✅ Thành công Bybit endpoint")
        return df
    except Exception as e:
        print(f"⚠️ Bybit lỗi: {e}")
        return pd.DataFrame()

# ================= Auto Fallback =================
def get_klines_auto(symbol="BTCUSDT", interval="1h", limit=200):
    # Map interval cho Bybit
    interval_map = {"1m":"1", "5m":"5", "15m":"15", "1h":"60", "4h":"240", "1d":"D"}
    try:
        df = get_klines_binance(symbol, interval, limit)
        if not df.empty:
            return df, "binance"
        df = get_klines_bybit(symbol, interval_map.get(interval, "60"), limit)
        if not df.empty:
            return df, "bybit"
    except Exception as e:
        print(f"⚠️ Lỗi trong get_klines_auto: {e}")
    return pd.DataFrame(), "none"

# ================= RSI =================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = pd.Series(gain).rolling(period).mean()
    avg_loss = pd.Series(loss).rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ================= Streamlit App =================
st.title("📊 RSI Realtime (Binance + Bybit fallback)")

symbol = st.text_input("Nhập cặp coin (ví dụ: BTCUSDT, ETHUSDT...)", "BTCUSDT")

if st.button("Tính RSI"):
    intervals = ["5m", "15m", "1h", "4h", "1d"]
    results = {}

    for interval in intervals:
        df, source = get_klines_auto(symbol, interval, 200)
        if df.empty or "close" not in df.columns:
            results[interval] = "N/A"
            continue
        
        df["RSI"] = calculate_rsi(df["close"])
        df = df.dropna(subset=["RSI"])
        if not df.empty:
            rsi_latest = round(df["RSI"].iloc[-1], 2)
            results[interval] = f"{rsi_latest} ({source})"
        else:
            results[interval] = "N/A"

    st.subheader(f"✅ RSI(14) hiện tại của {symbol}")
    for interval, rsi_val in results.items():
        st.write(f"Khung {interval}: **{rsi_val}**")

    # Vẽ chart cho 1 khung
    st.subheader("📈 Biểu đồ chi tiết")
    chosen_interval = st.selectbox("Chọn khung thời gian:", intervals, index=2)

    df, source = get_klines_auto(symbol, chosen_interval, 200)
    if not df.empty:
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
        fig_candle.update_layout(title=f"Biểu đồ {symbol} ({chosen_interval}) - {source}", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_candle, use_container_width=True)

        # Biểu đồ RSI
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df["time"], y=df["RSI"], mode="lines", name="RSI"))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
        fig_rsi.update_layout(title=f"RSI(14) - {symbol} ({chosen_interval})", yaxis=dict(range=[0, 100]))
        st.plotly_chart(fig_rsi, use_container_width=True)
    else:
        st.error("❌ Không lấy được dữ liệu để vẽ biểu đồ")
