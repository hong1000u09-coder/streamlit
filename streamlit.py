import streamlit as st
import pandas as pd
import numpy as np

# 앱 제목 설정
st.title("📊 나의 첫 Streamlit 대시보드")

# 사이드바에 입력창 만들기
st.sidebar.header("설정 변경")
data_points = st.sidebar.slider("데이터 개수 선택", min_value=10, max_value=1000, value=100)

# 메인 화면 설명
st.write(f"현재 **{data_points}개**의 무작위 데이터를 시각화하고 있습니다.")

# 무작위 데이터 생성
chart_data = pd.DataFrame(
    np.random.randn(data_points, 3),
    columns=['데이터 A', '데이터 B', '데이터 C']
)

# 꺾은선 그래프 그리기
st.subheader("📈 실시간 라인 차트")
st.line_chart(chart_data)

# 데이터 표 보여주기
st.subheader("📋 원본 데이터 보기")
if st.checkbox("데이터프레임 확장"):
    st.dataframe(chart_data)
else:
    st.write("위 체크박스를 누르면 표를 볼 수 있습니다.")
