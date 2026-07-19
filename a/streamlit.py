import streamlit as st
from googleapiclient.discovery import build
import re
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# ---------------------------------------------------------------- Do Not Edit
# 한글 폰트 설정 (WordCloud 및 Matplotlib 깨짐 방지)
# OS별 기본 폰트 설정 (Windows: Malgun Gothic, Mac: AppleGothic)
import platform
if platform.system() == 'Windows':
    font_path = "malgun.ttf"
elif platform.system() == 'Darwin':
    font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
else:
    font_path = None
# ---------------------------------------------------------------- Do Not Edit

# 유튜브 영상 ID 추출 함수
def extract_video_id(url):
    regex = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(regex, url)
    return match.group(1) if match else None

# 유튜브 API 데이터 가져오기 함수
def get_video_data(api_key, video_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    # 1. 영상 정보 가져오기
    video_response = youtube.videos().list(
        part='snippet,statistics',
        id=video_id
    ).execute()
    
    if not video_response['items']:
        return None, None
        
    video_info = video_response['items'][0]
    title = video_info['snippet']['title']
    channel_title = video_info['snippet']['channelTitle']
    view_count = video_info['statistics'].get('viewCount', 0)
    like_count = video_info['statistics'].get('likeCount', 0)
    comment_count = video_info['statistics'].get('commentCount', 0)
    thumbnail_url = video_info['snippet']['thumbnails']['high']['url']
    
    video_details = {
        'title': title,
        'channel': channel_title,
        'views': int(view_count),
        'likes': int(like_count),
        'comments_num': int(comment_count),
        'thumbnail': thumbnail_url
    }
    
    # 2. 댓글 가져오기 (최대 100개)
    comments = []
    try:
        comment_response = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=100,
            order='relevance' # 관련성 높은 순 (최신순은 'time')
        ).execute()
        
        for item in comment_response.get('items', []):
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            author = item['snippet']['topLevelComment']['snippet']['authorDisplayName']
            like_cnt = item['snippet']['topLevelComment']['snippet']['likeCount']
            comments.append({'작성자': author, '댓글': comment, '좋아요': like_cnt})
            
    except Exception as e:
        st.warning("댓글을 가져올 수 없거나 댓글 기능이 비활성화된 영상입니다.")
        
    return video_details, pd.DataFrame(comments)

# --- Streamlit UI 시작 ---
st.set_page_config(page_title="유튜브 댓글 분석기", layout="wide")

st.title("📊 유튜브 영상 및 댓글 분석기")
st.markdown("유튜브 링크를 넣으면 영상 정보와 댓글을 분석해 줍니다.")

# 사이드바에서 API 키 입력 받기
with st.sidebar:
    st.header("🔑 설정")
    api_key = st.text_input("YouTube API Key를 입력하세요", type="password")
    st.markdown("[Google Cloud Console](https://console.cloud.google.com/)에서 발급받을 수 있습니다.")

# 메인 화면 링크 입력
video_url = st.text_input("유튜브 영상 링크(URL)를 입력하세요", placeholder="https://www.youtube.com/watch?v=...")

if st.button("분석 시작하기"):
    if not api_key:
        st.error("오른쪽 사이드바에 YouTube API Key를 먼저 입력해주세요!")
    elif not video_url:
        st.error("유튜브 링크를 입력해주세요!")
    else:
        video_id = extract_video_id(video_url)
        
        if not video_id:
            st.error("올바른 유튜브 URL 형식이 아닙니다.")
        else:
            with st.spinner("유튜브 데이터를 분석 중입니다... 🚀"):
                video_details, df_comments = get_video_data(api_key, video_id)
                
            if video_details is None:
                st.error("영상 정보를 가져오지 못했습니다. 링크나 API 키를 확인해주세요.")
            else:
                # --- 1. 영상 정보 출력 ---
                st.subheader("📺 영상 기본 정보")
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.image(video_details['thumbnail'], use_container_width=True)
                
                with col2:
                    st.markdown(f"### **{video_details['title']}**")
                    st.markdown(f"**채널명:** {video_details['channel']}")
                    
                    # 지표 가독성 있게 표현
                    metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
                    metrics_col1.metric("조회수", f"{video_details['views']:,}회")
                    metrics_col2.metric("좋아요", f"{video_details['likes']:,}개")
                    metrics_col3.metric("전체 댓글 수", f"{video_details['comments_num']:,}개")
                
                st.divider()
                
                # --- 2. 댓글 분석 출력 ---
                if df_comments is not None and not df_comments.empty:
                    st.subheader("💬 댓글 분석 결과 (상위 100개 기준)")
                    
                    tab1, tab2 = st.tabs(["📊 자주 등장하는 단어 (WordCloud)", "📋 수집된 댓글 목록"])
                    
                    with tab1:
                        st.markdown("#### 댓글에서 가장 많이 언급된 단어들")
                        # 단순 텍스트 합치기 및 불용어 처리 (HTML 태그 제거)
                        all_text = " ".join(df_comments['댓글'].astype(str).tolist())
                        clean_text = re.sub(r'<[^>]*>', '', all_text) # HTML 태그 제거
                        
                        if len(clean_text.strip()) > 0:
                            try:
                                # 워드클라우드 생성
                                wordcloud = WordCloud(
                                    font_path=font_path,
                                    background_color='white',
                                    width=800,
                                    height=400
                                ).generate(clean_text)
                                
                                # 시각화
                                fig, ax = plt.subplots(figsize=(10, 5))
                                ax.imshow(wordcloud, interpolation='bilinear')
                                ax.axis('off')
                                st.pyplot(fig)
                            except Exception as e:
                                st.info("워드클라우드를 생성하는데 실패했습니다. (텍스트 부족 등)")
                        else:
                            st.info("분석할 문장 데이터가 부족합니다.")
                            
                    with tab2:
                        st.markdown("#### 수집된 댓글 리스트 (좋아요 많은 순 정렬 가능)")
                        # HTML 태그 제거 후 깔끔하게 보여주기
                        df_comments['댓글'] = df_comments['댓글'].str.replace(r'<[^>]*>', '', regex=True)
                        st.dataframe(df_comments.sort_values(by="좋아요", ascending=False), use_container_width=True)
                else:
                    st.info("가져온 댓글이 없습니다.")
