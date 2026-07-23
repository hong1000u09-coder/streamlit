import os
import urllib.request
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import streamlit as st
from newspaper import Article
from openai import OpenAI
from wordcloud import WordCloud

# ==========================================
# 0. 한글 폰트 설정 (Streamlit Cloud 대비)
# ==========================================
FONT_PATH = "NanumGothic.ttf"


@st.cache_resource
def load_korean_font():
    """Streamlit Cloud 리눅스 환경을 위해 나눔고딕 폰트를 자동으로 다운로드합니다."""
    if not os.path.exists(FONT_PATH):
        font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        urllib.request.urlretrieve(font_url, FONT_PATH)
    fm.fontManager.addfont(FONT_PATH)
    return FONT_PATH


font_path = load_korean_font()

# ==========================================
# 1. Streamlit페이지 및 OpenAI 클라이언트 설정
# ==========================================
st.set_page_config(
    page_title="AI 뉴스 기사 분석기", page_icon="📰", layout="wide"
)

st.title("📰 AI 뉴스 기사 분석기")
st.caption("뉴스 URL을 입력하면 본문 추출, AI 요약, 감정 분석, 키워드 시각화를 진행합니다.")

# st.secrets로부터 OpenAI API Key 로드
if "OPENAI_API_KEY" not in st.secrets:
    st.error(
        "Secrets에 `OPENAI_API_KEY`가 설정되어 있지 않습니다. Streamlit App Settings에서 설정해주세요."
    )
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


# ==========================================
# 2. 뉴스 기사 크롤링 함수
# ==========================================
def extract_article(url):
    try:
        article = Article(url, language="ko")
        article.download()
        article.parse()
        return article.title, article.text
    except Exception as e:
        st.error(f"기사를 불러오는 중 오류가 발생했습니다: {e}")
        return None, None


# ==========================================
# 3. OpenAI API 분석 함수
# ==========================================
def analyze_article(text):
    prompt = f"""
    다음 뉴스 기사를 읽고 아래 요청사항에 맞추어 한국어로 답변해주세요.

    [요청사항]
    1. 기사의 핵심 내용을 3줄 이내로 요약할 것.
    2. 기사의 전반적인 감정을 분석할 것 (긍정, 중립, 부정 중 하나를 반드시 선택).
    3. 기사에서 가장 중요한 핵심 키워드 10개를 쉼표(,)로 구분하여 추출할 것.

    [응답 형식]
    요약:
    - 요약 내용 1
    - 요약 내용 2
    - 요약 내용 3

    감정: [긍정 / 중립 / 부정 중 하나]

    키워드: 키워드1, 키워드2, 키워드3, ...

    [기사 본문]
    {text[:3000]}  # API 토큰 절약을 위해 상위 3000자 사용
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content


# ==========================================
# 4. 사용자 입력 및 메인 로직
# ==========================================
url_input = st.text_input("분석할 뉴스 기사 URL을 입력하세요:")

if st.button("분석 시작", type="primary"):
    if not url_input.strip():
        st.warning("URL을 입력해주세요.")
    else:
        with st.spinner("뉴스 기사를 가져오는 중..."):
            title, text = extract_article(url_input)

        if title and text:
            st.subheader(f"📌 기사 제목: {title}")

            with st.expander("📄 기사 본문 접기/열기"):
                st.write(text)

            with st.spinner("AI가 기사를 분석하고 시각화하는 중..."):
                analysis_result = analyze_article(text)

                # 분석 결과 파싱 (간단한 문자열 분할)
                summary_text = ""
                sentiment_val = "중립"
                keywords = []

                lines = analysis_result.split("\n")
                current_section = None

                for line in lines:
                    line_str = line.strip()
                    if line_str.startswith("요약:"):
                        current_section = "summary"
                        continue
                    elif line_str.startswith("감정:"):
                        sentiment_val = (
                            line_str.replace("감정:", "").strip().replace("[", "").replace("]", "")
                        )
                        current_section = None
                        continue
                    elif line_str.startswith("키워드:"):
                        kw_str = line_str.replace("키워드:", "").strip()
                        keywords = [k.strip() for k in kw_str.split(",") if k.strip()]
                        current_section = None
                        continue

                    if current_section == "summary" and line_str:
                        summary_text += line_str + "\n"

                # ------------------------------------------
                # 결과 출력 UI
                # ------------------------------------------
                st.markdown("---")
                col1, col2 = st.columns([1, 1])

                with col1:
                    st.markdown("### 📝 AI 요약")
                    st.info(
                        summary_text if summary_text else analysis_result
                    )

                    st.markdown("### 🎭 감정 분석 결과")
                    st.success(f"분석된 감정 상태: **{sentiment_val}**")

                    # Plotly Pie Chart
                    sentiment_scores = {"긍정": 0, "중립": 0, "부정": 0}
                    if "긍정" in sentiment_val:
                        sentiment_scores["긍정"] = 100
                    elif "부정" in sentiment_val:
                        sentiment_scores["부정"] = 100
                    else:
                        sentiment_scores["중립"] = 100

                    colors = {
                        "긍정": "#2ecc71",
                        "중립": "#95a5a6",
                        "부정": "#e74c3c",
                    }

                    fig = go.Figure(
                        data=[
                            go.Pie(
                                labels=list(sentiment_scores.keys()),
                                values=list(sentiment_scores.values()),
                                hole=0.4,
                                marker_colors=[
                                    colors[k] for k in sentiment_scores.keys()
                                ],
                            )
                        ]
                    )
                    fig.update_layout(
                        title_text="기사 감정 비율",
                        margin=dict(t=40, b=0, l=0, r=0),
                        height=300,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    st.markdown("### ☁️ 핵심 키워드 WordCloud")
                    if keywords:
                        # 키워드 가상 빈도수 생성
                        word_freq = {
                            word: (len(keywords) - i) * 10
                            for i, word in enumerate(keywords)
                        }

                        wc = WordCloud(
                            font_path=font_path,
                            background_color="white",
                            width=800,
                            height=600,
                            colormap="Blues",
                        ).generate_from_frequencies(word_freq)

                        fig_wc, ax = plt.subplots(figsize=(8, 6))
                        ax.imshow(wc, interpolation="bilinear")
                        ax.axis("off")
                        st.pyplot(fig_wc)

                        st.markdown("**추출된 핵심 키워드:**")
                        st.write(", ".join([f"`{k}`" for k in keywords]))
                    else:
                        st.warning("키워드를 추출하지 못했습니다.")
