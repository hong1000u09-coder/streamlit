import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 (와이드 모드)
st.set_page_config(page_title="Global Top 10 Dashboard", layout="wide")

st.title("🌐 글로벌 시가총액 Top 10 주식 대시보드")
st.caption("실시간 주가 정보와 최근 트렌드를 한눈에 확인하세요.")
st.markdown("---")

# 2. 글로벌 시총 Top 10 기업 정보 (티커 및 한글명)
top_10_companies = {
    "NVDA": "엔비디아 (NVIDIA)",
    "AAPL": "애플 (Apple)",
    "GOOGL": "알파벳 (Alphabet)",
    "MSFT": "마이크로소프트 (Microsoft)",
    "AMZN": "아마존 (Amazon)",
    "TSM": "TSMC",
    "AVGO": "브로드컴 (Broadcom)",
    "META": "메타 (Meta Platforms)",
    "TSLA": "테슬라 (Tesla)",
    "BRK-B": "버크셔 해서웨이 (Berkshire Hathaway)"
}

# 3. 사이드바 구성 (주식 선택 및 기간 설정)
st.sidebar.header("⚙️ 대시보드 설정")
selected_ticker = st.sidebar.selectbox(
    "조회할 기업을 선택하세요", 
    options=list(top_10_companies.keys()),
    format_func=lambda x: f"{top_10_companies[x]} ({x})"
)

period_options = {"1개월": "1mo", "3개월": "3mo", "6개월": "6mo", "1년": "1y", "올해 누적(YTD)": "ytd"}
selected_period = st.sidebar.radio("차트 기간 선택", list(period_options.keys()))

# 4. 데이터 로드 함수 (캐싱 적용으로 속도 향상)
@st.cache_data(ttl=600)
def get_stock_data(ticker, period):
    stock = yf.Ticker(ticker)
    # 주가 히스토리 데이터
    df = stock.history(period=period_options[period])
    # 기업 기본 정보
    info = stock.info
    return df, info

# 데이터 가져오기
with st.spinner('데이터를 불러오는 중입니다...'):
    try:
        df, info = get_stock_data(selected_ticker, selected_period)
        
        # 5. 메인 대시보드 화면 상단 지표 (Metrics)
        current_price = info.get('currentPrice', df['Close'].iloc[-1])
        prev_close = info.get('previousClose', df['Close'].iloc[-2])
        price_change = current_price - prev_close
        price_change_pct = (price_change / prev_close) * 100
        
        market_cap_trillion = info.get('marketCap', 0) / 1e12 # 조 달러 단위
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                label="현재가 (USD)", 
                value=f"${current_price:,.2f}", 
                delta=f"${price_change:,.2f} ({price_change_pct:+.2f}%)"
            )
        with col2:
            st.metric(label="시가총액", value=f"${market_cap_trillion:,.2f} T (조 달러)")
        with col3:
            st.metric(label="52주 최고가", value=f"${info.get('52WeekHigh', 0):,.2f}")
        with col4:
            st.metric(label="52주 최저가", value=f"${info.get('52WeekLow', 0):,.2f}")
            
        st.markdown("---")
        
        # 6. 좌측 차트 / 우측 기업 요약 배치 (Layout 분할)
        chart_col, info_col = st.columns([2, 1])
        
        with chart_col:
            st.subheader(f"📈 {top_10_companies[selected_ticker]} 주가 추이 ({selected_period})")
            
            # Plotly를 이용한 깔끔한 캔들스틱/라인 차트 선택 가능
            chart_type = st.segmented_control("차트 종류", ["라인", "캔들스틱"], default="라인")
            
            fig = go.Figure()
            if chart_type == "라인":
                fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='종가', line=dict(color='#1f77b4', width=2)))
            else:
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='주가'))
                
            fig.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                height=450,
                xaxis_rangeslider_visible=False,
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with info_col:
            st.subheader("🏢 기업 주요 요약")
            st.write(f"**섹터:** {info.get('sector', 'N/A')}")
            st.write(f"**산업군:** {info.get('industry', 'N/A')}")
            st.write(f"**PER (선행):** {info.get('forwardPE', 'N/A')}")
            st.write(f"**배당수익률:** {info.get('dividendYield', 0) * 100:.2f}%" if info.get('dividendYield') else "**배당수익률:** N/A")
            
            with st.expander("📝 기업 설명 보기"):
                st.caption(info.get('longBusinessSummary', '설명이 존재하지 않습니다.'))
                
        # 7. 하단 전체 순위표 제공
        st.markdown("---")
        st.subheader("🏆 글로벌 시총 상위 10개 기업 요약 테이블")
        
        # 미리 정의된 정적 데이터 또는 간략한 목록 표기
        summary_data = []
        for ticker, name in top_10_companies.items():
            summary_data.append({"티커": ticker, "기업명": name})
        
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
        
    except Exception as e:
        st.error(
            f"데이터를 가져오는 중 오류가 발생했습니다. Yahoo Finance API 제한이거나 티커 문제일 수 있습니다. (에러: {e})"
        )
