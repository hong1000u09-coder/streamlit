import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 1. 페이지 설정
st.set_page_config(page_title="서울시 공영주차장 안내", layout="wide")
st.title("🚗 서울시 공영주차장 안내 대시보드")
st.caption("지도를 확대/축소하면 주차장 마커 크기도 화면에 맞게 조절됩니다.")
st.markdown("---")

# 2. 데이터 불러오기 함수
@st.cache_data
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = "서울시 공영주차장 안내 정보.csv"
    file_path = os.path.join(current_dir, file_name)
    
    if not os.path.exists(file_path):
        alternative_name = "서울시 공영주차장 안내 정보"
        alternative_path = os.path.join(current_dir, alternative_name)
        if os.path.exists(alternative_path):
            file_path = alternative_path
            
    df = pd.read_csv(file_path, encoding="utf-8")
    
    # 위도/경도 결측치 제거 및 숫자형 변환
    df = df.dropna(subset=['위도', '경도'])
    df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
    df['경도'] = pd.to_numeric(df['경도'], errors='coerce')
    
    # 자치구 정보 추출
    df['자치구'] = df['주소'].apply(lambda x: x.split()[0] if isinstance(x, str) else "미분류")
    
    return df

try:
    df = load_data()
    
    # 3. 사이드바 필터 설정
    st.sidebar.header("🔍 주차장 필터링")
    
    gu_list = ["전체"] + sorted(list(df['자치구'].unique()))
    selected_gu = st.sidebar.selectbox("자치구를 선택하세요", gu_list)
    
    pay_list = ["전체"] + list(df['유무료구분명'].unique())
    selected_pay = st.sidebar.selectbox("유/무료 구분", pay_list)
    
    # 데이터 필터링 적용
    filtered_df = df.copy()
    if selected_gu != "전체":
        filtered_df = filtered_df[filtered_df['자치구'] == selected_gu]
    if selected_pay != "전체":
        filtered_df = filtered_df[filtered_df['유무료구분명'] == selected_pay]
        
    # 4. 상단 요약 지표 (Metrics)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("검색된 주차장 수", f"{len(filtered_df)} 개")
    with col2:
        total_slots = filtered_df['총 주차면'].sum()
        st.metric("총 주차 가능 면수", f"{int(total_slots):,} 면")
    with col3:
        free_count = len(filtered_df[filtered_df['유무료구분명'] == '무료'])
        st.metric("무료 주차장 수", f"{free_count} 개")
        
    st.markdown("---")
    
    # 5. 지도 시각화 및 상세 정보 분할 배치
    map_col, info_col = st.columns([2, 1])
    
    with map_col:
        st.subheader("📍 주차장 위치 지도 (인터랙티브)")
        if not filtered_df.empty:
            # 💡 Plotly를 활용해 화면 확대/축소에 따라 유연하게 반응하는 마크 구현
            fig = px.scatter_mapbox(
                filtered_df,
                lat="위도",
                lon="경도",
                hover_name="주차장명",
                hover_data={"주소": True, "유무료구분명": True, "위도": False, "경도": False},
                zoom=11,
                height=500
            )
            
            # 스타일 설정 및 마커 크기 고정 방식 해제 (화면에 맞게 크기 동적 조절 가능)
            fig.update_traces(marker=dict(size=12, opacity=0.8, color="#FF4B4B"))
            fig.update_layout(
                mapbox_style="open-street-map", # 별도의 토큰이 필요 없는 무료 오픈 스트리트 맵 사용
                margin={"r":0,"t":0,"l":0,"b":0}
            )
            
            # Streamlit에 차트 표시
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("조건에 맞는 주차장이 없습니다.")
            
    with info_col:
        st.subheader("📋 주차장 선택 상세 정보")
        if not filtered_df.empty:
            selected_parking = st.selectbox(
                "상세 정보를 볼 주차장을 선택하세요", 
                options=filtered_df['주차장명'].unique()
            )
            
            p_info = filtered_df[filtered_df['주차장명'] == selected_parking].iloc[0]
            
            st.write(f"🏠 **주소:** {p_info['주소']}")
            st.write(f"📞 **전화번호:** {p_info['전화번호']}")
            st.write(f"🎫 **유무료:** {p_info['유무료구분명']}")
            st.write(f"💰 **기본 요금:** {p_info['기본 주차 요금']}원 ({p_info['기본 주차 시간(분 단위)']}분 기준)")
        else:
            st.write("데이터가 없습니다.")

    # 6. 하단 데이터 테이블 표기
    st.markdown("---")
    st.subheader("📊 주차장 원본 데이터 (필터링됨)")
    show_cols = ['주차장명', '주소', '주차장 종류명', '총 주차면', '유무료구분명', '기본 주차 요금', '일 최대 요금']
    st.dataframe(filtered_df[show_cols], use_container_width=True, hide_index=True)

except FileNotFoundError:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    st.error(f"❌ 파일을 찾을 수 없습니다! 현재 위치: [{current_dir}]")
except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
