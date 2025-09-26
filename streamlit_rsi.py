import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
import pdb

# ===== Hàm lấy dữ liệu từ Binance =====
#from binance.client import Client
#client = Client("", "", {"verify": True, "timeout": 20})
#client.API_URL = "https://api.binance.us/api"   # mirror domain (ít khi bị chặn hơn)

# ===== Hàm lấy dữ liệu Kline =====
#def get_klines(symbol="BTCUSDT", interval="1h", limit=200):
#    try:
        # Gọi API qua python-binance
#        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
#        df = pd.DataFrame(klines, columns=[
#            "time", "open", "high", "low", "close", "volume",
#            "close_time", "qav", "trades", "taker_base", "taker_quote", "ignore"
#        ])
#        df["time"] = pd.to_datetime(df["time"], unit="ms")
#        df["open"] = df["open"].astype(float)
#        df["high"] = df["high"].astype(float)
#        df["low"] = df["low"].astype(float)
#        df["close"] = df["close"].astype(float)
#        df["volume"] = df["volume"].astype(float)
#        return df
#    except Exception as e:
#        print("❌ Lỗi khi gọi Binance:", e)
#        return pd.DataFrame()

BINANCE_ENDPOINTS = [
    "https://data-api.binance.vision/api/v3/klines",
    "https://api1.binance.com/api/v3/klines",
    "https://api2.binance.com/api/v3/klines",
    "https://api3.binance.com/api/v3/klines",
    "https://api.binance.com/api/v3/klines",
]

import requests
import pandas as pd
import time
import streamlit as st

BINANCE_ENDPOINTS = [
    "https://data-api.binance.vision/api/v3/klines",
    "https://api1.binance.com/api/v3/klines",
    "https://api2.binance.com/api/v3/klines",
    "https://api3.binance.com/api/v3/klines",
    "https://api.binance.com/api/v3/klines",
]

def get_klines_binance(symbol="BTCUSDT", interval="5m", limit=200, max_retries=2):
    """
    Lấy dữ liệu nến từ Binance, có fallback qua nhiều endpoint.
    Trả về DataFrame với cột: time, open, high, low, close, volume
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; my-rsi-app/1.0)"}
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    last_err = None

    for base in BINANCE_ENDPOINTS:
        url = base
        st.write(f"🔄 Thử gọi Binance API: {url}")
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=10)
                resp.raise_for_status()
                data = resp.json()

                if isinstance(data, list) and len(data) > 0:
                    st.success(f"✅ Thành công từ endpoint: {url}")

                    # Convert sang DataFrame
                    df = pd.DataFrame(data, columns=[
                        "time", "open", "high", "low", "close", "volume",
                        "close_time", "qav", "trades", "taker_base", "taker_quote", "ignore"
                    ])
                    df["time"] = pd.to_datetime(df["time"], unit="ms")
                    df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
                    return df

                else:
                    last_err = f"Bad payload {data}"
                    break

            except requests.exceptions.Timeout:
                last_err = "⏰ Timeout"
                st.warning(f"⏰ Lỗi timeout {url} (attempt {attempt+1})")
                time.sleep(1)

            except requests.exceptions.RequestException as e:
                last_err = str(e)
                st.warning(f"⚠️ Request error {url} (attempt {attempt+1}): {e}")
                time.sleep(1)

            except Exception as e:
                last_err = str(e)
                st.error(f"⚠️ Lỗi không xác định tại {url}: {e}")
                break

    st.error(f"❌ Tất cả endpoint Binance đều thất bại. Lỗi cuối: {last_err}")
    return pd.DataFrame()



def get_klines_bybit(symbol="BTCUSDT", interval="60", limit=200, category="spot"):
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": category,   # "spot" hoặc "linear"
        "symbol": symbol,
        "interval": interval,   # "1"=1m, "5"=5m, "15"=15m, "60"=1h, "240"=4h, "D"=1d
        "limit": limit
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "result" not in data or "list" not in data["result"]:
            raise ValueError(f"Phản hồi API Bybit không hợp lệ: {data}")

        # Bybit trả list theo thứ tự mới nhất → cũ nhất, ta đảo ngược lại
        kline_data = data["result"]["list"][::-1]

        df = pd.DataFrame(kline_data, columns=[
            "time", "open", "high", "low", "close", "volume", "turnover"
        ])

        # Convert kiểu dữ liệu
        df["time"] = pd.to_datetime(df["time"].astype(int), unit="s")
        df[["open", "high", "low", "close", "volume"]] = df[
            ["open", "high", "low", "close", "volume"]
        ].astype(float)

        return df, data   # ✅ luôn trả 2 giá trị

    except requests.exceptions.Timeout:
        return pd.DataFrame(), {"error": "⏰ Kết nối API Bybit quá thời gian chờ"}

    except requests.exceptions.RequestException as e:
        return pd.DataFrame(), {"error": f"❌ Lỗi khi gọi API Bybit: {e}"}

    except Exception as e:
        return pd.DataFrame(), {"error": f"⚠️ Lỗi không xác định: {e}"}




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
        df = get_klines_binance("BTCUSDT", "1h", 200)

        if not df.empty:
            st.write("📊 Data preview:", df.head())
        else:
            st.error("Không lấy được dữ liệu Binance.")
        
        
        df, raw = get_klines_bybit(symbol, interval)
        # ✅ Debug JSON trên màn hình
        st.subheader(f"Raw JSON {interval}")
        st.json(raw)
        if df.empty or "close" not in df.columns:
            results[interval] = "N/A"
            continue
        
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




