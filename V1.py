import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="高盛 GEMS 實時監控", layout="wide")
st.title("🏦 高盛 GEMS 策略實時監控儀表板")
st.markdown(f"**董事總經理專用 – 跨截面動量策略即時訊號與風險控制** | {datetime.now().strftime('%Y-%m-%d %H:%M ET')}")

# Sidebar
st.sidebar.header("參數設定")
tickers_input = st.sidebar.text_area(
    "監控股票（逗號分隔）", 
    "AAPL,MSFT,GOOGL,AMZN,NVDA,TSLA,SPY,QQQ", 
    height=120
)
universe_tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]

if st.sidebar.button("🔄 強制清除快取並刷新"):
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=180)  # 3 分鐘快取
def compute_gems_signals(tickers):
    signals = []
    for ticker in tickers:
        try:
            # 單一 ticker 下載 + 2年歷史（確保足夠資料）
            df = yf.download(ticker, period="2y", progress=False, auto_adjust=True)
            
            if df.empty or len(df) < 130:
                signals.append({
                    "Ticker": ticker,
                    "Z-Score": np.nan,
                    "訊號": "⚪ 數據不足",
                    "最新價": np.nan,
                    "成交量(萬)": 0
                })
                continue

            price = df['Close'].dropna()
            
            ret_12m1 = (price.iloc[-22] / price.iloc[-253] - 1) if len(price) >= 253 else np.nan
            ret_6m   = (price.iloc[-1]  / price.iloc[-127] - 1) if len(price) >= 127 else np.nan
            
            # 簡化 Z-score（實際部署請用全宇宙標準化）
            z = (0.7 * np.nan_to_num(ret_12m1) + 0.3 * np.nan_to_num(ret_6m)) * 100
            z = round(float(z), 2)
            
            signal = "🟢 強力買入" if z > 1.5 else "🔴 強力放空" if z < -1.5 else "⚪ 中性"
            
            signals.append({
                "Ticker": ticker,
                "Z-Score": z,
                "訊號": signal,
                "最新價": round(float(price.iloc[-1]), 2),
                "成交量(萬)": round(float(df['Volume'].iloc[-1]) / 10000, 1)
            })
        except Exception as e:
            signals.append({
                "Ticker": ticker,
                "Z-Score": np.nan,
                "訊號": f"❌ 錯誤 ({str(e)[:30]})",
                "最新價": np.nan,
                "成交量(萬)": 0
            })
    
    df = pd.DataFrame(signals)
    if df.empty:
        df = pd.DataFrame(columns=["Ticker", "Z-Score", "訊號", "最新價", "成交量(萬)"])
    return df

signals_df = compute_gems_signals(universe_tickers)

# 主畫面
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("📊 即時 GEMS 訊號表")
    if signals_df.empty:
        st.error("無法取得任何股票數據，請檢查網路連線")
    else:
        sorted_df = signals_df.sort_values(by="Z-Score", ascending=False, na_position="last")
        st.dataframe(
            sorted_df.style.background_gradient(subset=["Z-Score"], cmap="RdYlGn"),
            use_container_width=True,
            hide_index=True
        )

with col2:
    st.subheader("📈 風險總覽")
    valid = signals_df[signals_df["Z-Score"].notna()]
    st.metric("成功計算股票數", f"{len(valid)} / {len(universe_tickers)}")
    if len(valid) > 0:
        st.metric("強力買入", len(valid[valid["Z-Score"] > 1.5]))
        st.metric("強力放空", len(valid[valid["Z-Score"] < -1.5]))
        st.metric("平均 Z-Score", f"{valid['Z-Score'].mean():.2f}")

# K線圖
st.subheader("📉 個股 K 線圖")
selected = st.selectbox("選擇股票檢視", options=universe_tickers)
if selected:
    try:
        hist = yf.download(selected, period="6mo")
        fig = go.Figure(data=[go.Candlestick(
            x=hist.index,
            open=hist['Open'], high=hist['High'],
            low=hist['Low'], close=hist['Close']
        )])
        fig.update_layout(title=f"{selected} 價格走勢 (過去6個月)", xaxis_title="日期", yaxis_title="股價")
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.warning(f"無法載入 {selected} 圖表")

st.caption("⚠️ 示範應用程式。生產環境請改接 Polygon / Bloomberg API + 完整 S&P 500 宇宙。所有交易決策需經過 GS Quant 完整驗證。")
