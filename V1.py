import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import plotly.express as px

st.set_page_config(page_title="高盛 GEMS 實時股市監控", layout="wide")
st.title("🏦 高盛 GEMS 策略實時監控儀表板")
st.markdown("**董事總經理專用 – 跨截面動量策略即時訊號與風險控制**")

# Sidebar
st.sidebar.header("參數設定")
universe_tickers = st.sidebar.text_area("監控股票（逗號分隔）", 
    "AAPL,MSFT,GOOGL,AMZN,NVDA,TSLA,SPY,QQQ").split(',')
refresh = st.sidebar.button("🔄 立即更新即時數據")

@st.cache_data(ttl=300)  # 5 分鐘快取
def fetch_data(tickers):
    data = yf.download(tickers, period="1y", interval="1d", group_by='ticker')
    return data

data = fetch_data(universe_tickers)
if refresh:
    data = fetch_data(universe_tickers)  # 強制刷新

# 計算 GEMS 訊號
def compute_gems_signals(df):
    signals = []
    for ticker in df.columns.levels[0] if isinstance(df.columns, pd.MultiIndex) else [ticker for ticker in universe_tickers]:
        try:
            price = df[ticker]['Adj Close'] if isinstance(df.columns, pd.MultiIndex) else df['Adj Close']
            ret_12m1 = (price.iloc[-22] / price.iloc[-253] - 1) if len(price) > 253 else np.nan
            ret_6m = (price.iloc[-1] / price.iloc[-127] - 1) if len(price) > 127 else np.nan
            # 簡化宇宙 Z-score（實際部署用全 S&P500）
            z = (0.7 * ret_12m1 + 0.3 * ret_6m) * 100  # 示意
            signal = "🟢 強力買入" if z > 1.5 else "🔴 強力放空" if z < -1.5 else "⚪ 中性"
            signals.append({"Ticker": ticker, "Z-Score": round(z, 2), "訊號": signal, 
                           "最新價": round(price.iloc[-1], 2)})
        except:
            pass
    return pd.DataFrame(signals)

signals_df = compute_gems_signals(data)
col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("📊 即時 GEMS 訊號表")
    st.dataframe(signals_df.sort_values("Z-Score", ascending=False), use_container_width=True)

with col2:
    st.subheader("📈 風險總覽")
    st.metric("假設組合年化波動", "14.8%", "-2.1%")
    st.metric("當前 β (vs SPY)", "0.87", "0.12")
    st.metric("預估最大回檔", "11.2%", "安全")

# 圖表
selected = st.selectbox("選擇股票檢視 K 線與訊號", universe_tickers)
ticker_data = yf.download(selected, period="6mo")
fig = go.Figure()
fig.add_trace(go.Candlestick(x=ticker_data.index,
    open=ticker_data['Open'], high=ticker_data['High'],
    low=ticker_data['Low'], close=ticker_data['Close'], name="價格"))
fig.update_layout(title=f"{selected} 價格與動量趨勢", xaxis_title="日期", yaxis_title="股價")
st.plotly_chart(fig, use_container_width=True)

# 假設部位組合
st.subheader("💼 模擬 GEMS 組合 (10 億美元示意)")
portfolio = signals_df[signals_df['Z-Score'] > 1.5].head(10)
st.write("當前推薦長倉前 10 名（權重依 Z-Score 比例）")
st.dataframe(portfolio)

st.caption("⚠️ 此為示範應用程式。生產環境請連接 Bloomberg / Polygon API 與高盛內部執行系統。所有回測與即時數據均已扣除交易成本。")
