
"""
파리(평지) vs 한국(산악 지형) 7월 지역별 기온차 비교 앱
가설: 평지인 파리 인근은 지역 간 기온차가 작고, 산악 지형인 한국은 지역 간 기온차가 크다.

데이터 출처: Open-Meteo Historical Weather API (archive-api.open-meteo.com)
- ERA5/ERA5-Land 재분석 자료 + 각국 기상청 모델(프랑스: Météo-France, 한국: 기상청)을 결합한 데이터
- API 키·회원가입 불필요, 1940년 이후 자료 제공, CC BY 4.0 라이선스
- 공식 문서: https://open-meteo.com/en/docs/historical-weather-api
"""

import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="파리 vs 한국: 지형과 지역별 기온차", layout="wide")

# ------------------------------------------------------------------
# 1. 비교 도시 목록
#    프랑스: 파리 분지(Bassin Parisien) 내 평지 도시 5곳 (고도 15~154m, 반경 약 150km)
#    한국: 지형이 뚜렷하게 다른 도시 5곳 - 분지/고산/해안 혼합 (고도 26~773m)
# ------------------------------------------------------------------
FRANCE_CITIES = [
    {"name": "파리",     "lat": 48.8566, "lon": 2.3522, "elevation_m": 35,  "terrain": "평지"},
    {"name": "오를레앙", "lat": 47.9029, "lon": 1.9093, "elevation_m": 100, "terrain": "평지"},
    {"name": "랭스",     "lat": 49.2583, "lon": 4.0317, "elevation_m": 85,  "terrain": "평지"},
    {"name": "아미앵",   "lat": 49.8942, "lon": 2.2957, "elevation_m": 30,  "terrain": "평지"},
    {"name": "샤르트르", "lat": 48.4439, "lon": 1.4894, "elevation_m": 154, "terrain": "평지"},
]

KOREA_CITIES = [
    {"name": "서울",         "lat": 37.5665, "lon": 126.9780, "elevation_m": 38,  "terrain": "분지"},
    {"name": "대구",         "lat": 35.8714, "lon": 128.6014, "elevation_m": 50,  "terrain": "분지"},
    {"name": "강릉",         "lat": 37.7519, "lon": 128.8761, "elevation_m": 26,  "terrain": "해안(산맥 인접)"},
    {"name": "평창(대관령)", "lat": 37.6772, "lon": 128.7181, "elevation_m": 773, "terrain": "고산"},
    {"name": "목포",         "lat": 34.8118, "lon": 126.3922, "elevation_m": 38,  "terrain": "해안"},
]


@st.cache_data(show_spinner=False)
def fetch_daily_temps(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    """Open-Meteo 아카이브 API에서 일별 평균/최고/최저 기온을 가져온다."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min",
        "timezone": "auto",
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    daily = r.json()["daily"]
    df = pd.DataFrame(daily)
    df["date"] = pd.to_datetime(df["time"])
    df = df.rename(columns={
        "temperature_2m_mean": "tmean",
        "temperature_2m_max": "tmax",
        "temperature_2m_min": "tmin",
    })
    # 일부 지역은 mean이 비어있을 수 있어 max/min 평균으로 보정
    df["tmean"] = df["tmean"].fillna((df["tmax"] + df["tmin"]) / 2)
    return df[["date", "tmean", "tmax", "tmin"]]


def load_all(year: int) -> pd.DataFrame:
    start_date, end_date = f"{year}-07-01", f"{year}-07-31"
    rows = []
    for country, cities in [("프랑스", FRANCE_CITIES), ("한국", KOREA_CITIES)]:
        for city in cities:
            df = fetch_daily_temps(city["lat"], city["lon"], start_date, end_date)
            df["country"] = country
            df["city"] = city["name"]
            df["elevation_m"] = city["elevation_m"]
            df["terrain"] = city["terrain"]
            rows.append(df)
    return pd.concat(rows, ignore_index=True)


# ------------------------------------------------------------------
# 사이드바
# ------------------------------------------------------------------
st.sidebar.header("설정")
year = st.sidebar.selectbox("분석 연도 (7월)", [2025, 2024, 2023, 2026], index=0)
heatwave_threshold = st.sidebar.slider("폭염 기준 최고기온(°C)", 30, 36, 33)

st.title("지형이 지역별 기온 편차에 미치는 영향: 파리 vs 한국")
st.markdown(
    f"""
**가설**: 평지인 파리 인근(프랑스 파리 분지)은 지역 간 7월 기온차가 작고,
산악 지형인 한국은 지역 간 기온차가 클 것이다.

**대상 지역**
- 프랑스(평지): {", ".join(c["name"] for c in FRANCE_CITIES)} — 고도 15~154m, 반경 약 150km
- 한국(산악·분지·해안 혼합): {", ".join(c["name"] for c in KOREA_CITIES)} — 고도 26~773m

**{year}년 7월 1일 ~ 31일** 기준
"""
)

with st.spinner("Open-Meteo에서 기후 데이터를 불러오는 중..."):
    data = load_all(year)

# ------------------------------------------------------------------
# 1. 도시별 일별 평균기온 추이
# ------------------------------------------------------------------
st.subheader("1. 도시별 일별 평균기온 추이")
fig1 = px.line(
    data, x="date", y="tmean", color="city", facet_col="country",
    labels={"tmean": "평균기온(°C)", "date": "날짜", "city": "도시"},
)
fig1.update_yaxes(matches=None)
st.plotly_chart(fig1, use_container_width=True)
st.caption("같은 날짜라도 도시 간 선이 얼마나 겹쳐 있는지(=편차가 작은지) 비교해 보면 좋음.")

# ------------------------------------------------------------------
# 2. 같은 날 지역 간 기온 편차 (핵심 가설 검증 그래프)
# ------------------------------------------------------------------
st.subheader("2. 같은 날짜의 지역 간 기온 편차 (도시 간 최대-최소 기온차)")
spread = (
    data.groupby(["country", "date"])["tmean"]
    .agg(["max", "min", "std"])
    .reset_index()
)
spread["range"] = spread["max"] - spread["min"]

fig2 = px.line(
    spread, x="date", y="range", color="country",
    labels={"range": "지역 간 기온차(°C)", "date": "날짜", "country": "국가"},
)
st.plotly_chart(fig2, use_container_width=True)

avg_spread = spread.groupby("country")[["range", "std"]].mean().reset_index()
avg_spread.columns = ["국가", "평균 지역 간 기온차(°C)", "평균 표준편차(°C)"]

st.subheader("3. 7월 한 달 평균 지역 간 기온 편차 요약")
col1, col2 = st.columns([1, 1])
with col1:
    fig3 = px.bar(
        avg_spread, x="국가", y="평균 지역 간 기온차(°C)", color="국가",
        text_auto=".2f",
    )
    st.plotly_chart(fig3, use_container_width=True)
with col2:
    st.dataframe(avg_spread.round(2), hide_index=True, use_container_width=True)

# ------------------------------------------------------------------
# 4. 고도와 평균기온의 관계
# ------------------------------------------------------------------
st.subheader("4. 고도와 7월 평균기온의 관계")
city_summary = (
    data.groupby(["country", "city", "elevation_m", "terrain"])["tmean"]
    .mean().reset_index()
)
fig4 = px.scatter(
    city_summary, x="elevation_m", y="tmean", color="country",
    hover_data=["city", "terrain"], text="city",
    labels={"elevation_m": "고도(m)", "tmean": "7월 평균기온(°C)", "country": "국가"},
)
fig4.update_traces(textposition="top center")
st.plotly_chart(fig4, use_container_width=True)
st.caption("한국 도시들이 고도에 따라 기온이 뚜렷하게 갈리는지, 프랑스 도시들은 고도와 큰 상관없이 비슷한 기온대에 모여 있는지 비교.")

# ------------------------------------------------------------------
# 5. 열돔 현상과의 연결: 분지 지형의 폭염일수·일교차
# ------------------------------------------------------------------
st.subheader("5. 열돔 현상과의 연결: 분지 지형의 폭염일수·일교차")
st.markdown(
    """
열돔 현상은 고기압이 특정 지역 상공에 정체되며 열이 축적되는 현상으로, 도시 열섬과는
원리가 다르지만 '지형이 열을 가두는 효과'라는 점에서 분지 지형의 열 축적과 비교해 볼 만함.
아래 그래프는 분지 도시(대구·서울)와 고산·해안 도시의 폭염일수·일교차를 비교함.
"""
)

data["heatwave_day"] = data["tmax"] >= heatwave_threshold
heatwave_counts = (
    data.groupby(["country", "city", "terrain"])["heatwave_day"]
    .sum().reset_index()
    .rename(columns={"heatwave_day": "폭염일수"})
)

data["diurnal_range"] = data["tmax"] - data["tmin"]
diurnal = (
    data.groupby(["country", "city", "terrain"])["diurnal_range"]
    .mean().reset_index()
    .rename(columns={"diurnal_range": "평균 일교차(°C)"})
)

col3, col4 = st.columns(2)
with col3:
    fig5 = px.bar(
        heatwave_counts, x="city", y="폭염일수", color="terrain",
        labels={"city": "도시"}, title=f"최고기온 {heatwave_threshold}°C 이상 일수",
    )
    st.plotly_chart(fig5, use_container_width=True)
with col4:
    fig6 = px.bar(
        diurnal, x="city", y="평균 일교차(°C)", color="terrain",
        labels={"city": "도시"}, title="7월 평균 일교차",
    )
    st.plotly_chart(fig6, use_container_width=True)

# ------------------------------------------------------------------
# 데이터 출처 및 유의사항
# ------------------------------------------------------------------
with st.expander("데이터 출처 및 분석 방법 설명 (펼쳐서 보기)"):
    st.markdown(
        """
**데이터 출처**
- Open-Meteo Historical Weather API (`archive-api.open-meteo.com`)
- ERA5/ERA5-Land 재분석 자료를 기반으로, 프랑스는 Météo-France, 한국은 기상청(KMA) 등
  각국 기상 모델과 결합해 제공되는 데이터
- API 키·회원가입 없이 무료 사용 가능 (비상업적 이용 기준), 1940년 이후 자료 제공
- 공식 문서: https://open-meteo.com/en/docs/historical-weather-api
- 참고: 재분석 자료는 실제 관측소 값과 소폭 차이가 있을 수 있음. 국내 관측소 원자료가
  필요하면 기상청 기상자료개방포털(data.kma.go.kr), 프랑스는 Météo-France의 공공데이터
  포털에서 지점별 원자료를 받을 수 있음.

**분석 방법**
1. 프랑스는 파리 분지 내 평지 도시 5곳(고도 15~154m), 한국은 지형이 서로 다른 도시 5곳
   (고도 26~773m, 분지·고산·해안 포함)을 선정함.
2. 같은 날짜에 대해 도시 간 평균기온의 최대-최소 차이(지역 간 기온차)를 계산해,
   두 국가의 7월 한 달 평균값을 비교함 — 이 값이 가설을 직접 검증하는 핵심 지표임.
3. 고도와 평균기온의 상관관계, 폭염일수·일교차를 추가로 살펴봐 지형(분지 vs 고산)이
   기온 분포에 미치는 영향을 보조적으로 확인함.

**유의사항**
- 도시 5곳씩은 각 국가를 대표하는 표본이 아니라 지형 대비를 위해 의도적으로 선정한
  사례이므로, 결과를 "프랑스 전체 vs 한국 전체"로 일반화하지 않도록 주의가 필요함.
- 열돔 현상(고기압 정체로 인한 광역적 열 축적)과 분지 지형의 국지적 열 축적은
  원리가 다른 현상이며, 이 앱은 두 현상의 유사성(지형·기압 배치가 열을 가두는 효과)을
  비교하는 것이지 동일시하는 것이 아님.
"""
    )
