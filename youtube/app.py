import re
import pandas as pd
import streamlit as st
from googleapiclient.discovery import build

# -----------------------------
# 페이지 설정
# -----------------------------
st.set_page_config(
    page_title="YouTube 댓글 분석기",
    page_icon="🎥",
    layout="wide"
)

st.title("🎥 YouTube 댓글 분석기")
st.caption("YouTube Data API를 이용하여 댓글을 분석합니다.")

# -----------------------------
# API KEY
# -----------------------------
try:
    API_KEY = st.secrets["YOUTUBE_API_KEY"]
except Exception:
    st.error("Streamlit Secrets에 YOUTUBE_API_KEY를 등록하세요.")
    st.stop()

youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY
)

# -----------------------------
# URL 입력
# -----------------------------
url = st.text_input(
    "유튜브 영상 URL",
    placeholder="https://www.youtube.com/watch?v=xxxxxxxx"
)

# -----------------------------
# video_id 추출
# -----------------------------
def extract_video_id(url):

    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})"

    match = re.search(pattern, url)

    if match:
        return match.group(1)

    return None


# -----------------------------
# 영상 정보
# -----------------------------
def get_video_info(video_id):

    request = youtube.videos().list(
        part="snippet,statistics",
        id=video_id
    )

    response = request.execute()

    if len(response["items"]) == 0:
        return None

    item = response["items"][0]

    info = {
        "title": item["snippet"]["title"],
        "channel": item["snippet"]["channelTitle"],
        "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
        "published": item["snippet"]["publishedAt"],
        "viewCount": item["statistics"].get("viewCount", 0),
        "likeCount": item["statistics"].get("likeCount", 0),
        "commentCount": item["statistics"].get("commentCount", 0)
    }

    return info


# -----------------------------
# 댓글 가져오기
# -----------------------------
def get_comments(video_id, max_comments=1000):

    comments = []

    nextPageToken = None

    progress = st.progress(0)

    while True:

        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
            pageToken=nextPageToken,
            textFormat="plainText"
        )

        response = request.execute()

        for item in response["items"]:

            snippet = item["snippet"]["topLevelComment"]["snippet"]

            comments.append({

                "작성자": snippet["authorDisplayName"],
                "댓글": snippet["textDisplay"],
                "좋아요": snippet["likeCount"],
                "작성시간": snippet["publishedAt"]

            })

            progress.progress(min(len(comments)/max_comments,1.0))

            if len(comments) >= max_comments:
                progress.empty()
                return pd.DataFrame(comments)

        nextPageToken = response.get("nextPageToken")

        if not nextPageToken:
            break

    progress.empty()

    return pd.DataFrame(comments)


# -----------------------------
# 분석 시작
# -----------------------------
if st.button("댓글 분석 시작"):

    if url == "":
        st.warning("URL을 입력하세요.")
        st.stop()

    video_id = extract_video_id(url)

    if video_id is None:
        st.error("올바른 URL이 아닙니다.")
        st.stop()

    with st.spinner("영상 정보를 가져오는 중..."):

        info = get_video_info(video_id)

    if info is None:
        st.error("영상을 찾을 수 없습니다.")
        st.stop()

    st.image(info["thumbnail"], width=500)

    col1, col2, col3 = st.columns(3)

    col1.metric("조회수", f'{int(info["viewCount"]):,}')
    col2.metric("좋아요", f'{int(info["likeCount"]):,}')
    col3.metric("댓글수", f'{int(info["commentCount"]):,}')

    st.subheader(info["title"])
    st.write(info["channel"])

    with st.spinner("댓글 수집 중..."):

        df = get_comments(video_id)

    st.success(f"{len(df)}개의 댓글 수집 완료!")

    st.dataframe(df.head())
    # =====================================================
# 2부 - 키워드 분석 + 워드클라우드
# =====================================================

from collections import Counter
from kiwipiepy import Kiwi
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import plotly.express as px
import os

# -----------------------------
# 형태소 분석기
# -----------------------------
kiwi = Kiwi()

# -----------------------------
# 불용어
# -----------------------------
STOPWORDS = {
    "영상","진짜","정말","그냥","너무","이번","오늘","사람","생각",
    "이거","저거","그것","합니다","입니다","있는","하는","있다",
    "그리고","에서","으로","대한","때문","우리","여기","저기",
    "ㅋㅋ","ㅎㅎ","ㅠㅠ","ㅜㅜ","이다","입니다","있는데",
    "같아요","하세요","입니다","있어요","댓글","유튜브"
}

# -----------------------------
# 명사 추출
# -----------------------------
def extract_keywords(texts):

    nouns = []

    for sentence in texts:

        try:

            tokens = kiwi.tokenize(str(sentence))

            for token in tokens:

                if token.tag.startswith("N"):

                    word = token.form.strip()

                    if len(word) < 2:
                        continue

                    if word in STOPWORDS:
                        continue

                    nouns.append(word)

        except:
            pass

    return nouns


# -----------------------------
# TOP20 생성
# -----------------------------
def keyword_dataframe(words):

    counter = Counter(words)

    return pd.DataFrame(
        counter.most_common(20),
        columns=["단어","빈도"]
    )


# -----------------------------
# 워드클라우드
# -----------------------------
def draw_wordcloud(words):

    if len(words) == 0:
        st.warning("단어가 없습니다.")
        return

    font_path = "fonts/NanumGothic.ttf"

    if not os.path.exists(font_path):

        st.error("fonts/NanumGothic.ttf 를 추가하세요.")

        return

    text = " ".join(words)

    wc = WordCloud(
        font_path=font_path,
        width=1400,
        height=800,
        background_color="white",
        colormap="viridis"
    ).generate(text)

    fig, ax = plt.subplots(figsize=(14,8))

    ax.imshow(wc)

    ax.axis("off")

    st.pyplot(fig)


# =====================================================
# 키워드 분석 시작
# =====================================================

st.divider()

st.header("📊 댓글 키워드 분석")

words = extract_keywords(df["댓글"])

keyword_df = keyword_dataframe(words)

if len(keyword_df) > 0:

    col1, col2 = st.columns([1,1])

    with col1:

        st.subheader("TOP20 키워드")

        fig = px.bar(
            keyword_df,
            x="단어",
            y="빈도",
            color="빈도",
            text="빈도"
        )

        fig.update_traces(textposition="outside")

        fig.update_layout(
            height=500,
            xaxis_title="단어",
            yaxis_title="빈도",
            showlegend=False
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col2:

        st.subheader("☁️ 한글 워드클라우드")

        draw_wordcloud(words)

else:

    st.warning("분석할 단어가 없습니다.")


# =====================================================
# 댓글 검색
# =====================================================

st.divider()

st.subheader("🔍 댓글 검색")

keyword = st.text_input("검색어를 입력하세요.")

if keyword:

    result = df[
        df["댓글"].str.contains(
            keyword,
            case=False,
            na=False
        )
    ]

    st.write(f"검색 결과 : {len(result)}개")

    st.dataframe(
        result,
        use_container_width=True
    )
