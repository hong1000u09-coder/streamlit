import streamlit as st
import pandas as pd
import os

# 1. 페이지 설정
st.set_page_config(page_title="서울시 공영주차장 안내", layout="wide")
st.title("🚗 서울시 공영주차장 안내 대시보드")
st.markdown("---")

# 2. 데이터 불러오기 함수 (경로 탐색 보완 버전)
@st.cache_data
def load_data():
    # 현재 실행 중인 파이썬 파일(app.py)의 절대 경로 폴더 확인
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = "서울시 공영주차장 안내 정보.csv"
    file_path = os.path.join(current_dir, file_name)
    
    # 만약 사용자가 실수로 파일명을 '서울시 공영주차장 안내 정보.csv.csv'로 저장했을 경우 대비
    if not os.path.exists(file_path):
        alternative_name = "서울시 공영주차장 안내 정보"
        alternative_path = os.path.join(current_dir, alternative_name)
        if os.path.exists(alternative_path):
            file_path = alternative_path
            
    # 인코딩 오류 방지를 위해 utf-8 또는 cp949 적용
    df = pd.read_csv(file_path, encoding="utf-8")
    
    # 위도, 경도 컬럼명을 Streamlit 지도 인식용(latitude, longitude)으로 변경
    df = df.rename(columns={'위도': 'latitude', '경도': 'longitude'})
    
    # 위도/경도 결측치 제거 및 숫자형 변환
    df = df.dropna(subset=['latitude', 'longitude'])
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    
    # 주소에서 '구' 정보 추출
    df['자치구'] = df['주소'].apply(lambda x: x.split()[0] if isinstance(x, str) else "미분류")
    
    return df

try:
    df = load_data()
    
    # 3. 사이드바 필터 설정
    st.sidebar.header("🔍 주차장 필터링")
    
    # 자치구 선택 (전체 또는 특정 구)
    gu_list = ["전체"] + sorted(list(df['자치구'].unique()))
    selected_gu = st.sidebar.selectbox("자치구를 선택하세요", gu_list)
    
    # 유무료 구분 필터
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
        st.subheader("📍 주차장 위치 지도")
        if not filtered_df.empty:
            st.map(filtered_df[['latitude', 'longitude']])
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
    # 현재 탐색을 시도한 경로를 화면에 출력해서 디버깅을 돕습니다.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    st.error(f"❌ 파일을 찾을 수 없습니다! 현재 파이썬 파일 위치는 [{current_dir}] 입니다. 이 폴더 안에 CSV 파일이 들어있는지 꼭 확인해 주세요.")
except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
