import streamlit as st
import requests
import pandas as pd
import json

# 페이지 기본 설정
st.set_page_config(page_title="통합 경로 & 날씨 가이드", page_icon="🚗", layout="wide")

# -------------------------------------------------------------------
# 1. 한국 주소/지하철역/건물명 검색 엔진 (API 키 없이 다중 검색)
# -------------------------------------------------------------------

def get_coordinates(query_str):
    """
    주소, 도로명주소, 지하철역, 건물명 검색 성공률 100%를 목표로 하는 검색 함수
    """
    q = query_str.strip()
    if not q:
        return None, None, None

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StreamlitApp/1.0"}

    # 1차: VWorld(국토교통부) 오픈 API 이용 (한국 주소/도로명/건물 최적화)
    try:
        vworld_url = "https://api.vworld.kr/req/search"
        params = {
            "service": "search",
            "request": "search",
            "version": "2.0",
            "crs": "EPSG:4326",
            "size": "1",
            "page": "1",
            "query": q,
            "type": "PLACE", # 장소 검색
            "format": "json",
            "key": "CEB52025-0E6F-3235-9C08-118E3F868E21" # VWorld 공공 오픈키
        }
        res = requests.get(vworld_url, params=params, headers=headers, timeout=3)
        if res.status_code == 200:
            data = res.json()
            items = data.get("response", {}).get("result", {}).get("items", [])
            if items:
                item = items[0]
                lon = float(item["point"]["x"])
                lat = float(item["point"]["y"])
                name = item.get("title", q)
                return lat, lon, name
    except Exception:
        pass

    # 2차: 검색어 변환 알고리즘 (OpenStreetMap 보완)
    search_queries = []
    
    # '금천구', '은평구' 등 구/동 단위 처리
    if q.endswith("구") or q.endswith("동") or q.endswith("시"):
        search_queries.append(f"서울특별시 {q}")
        search_queries.append(f"대한민국 {q}")
    
    # '강남역', '홍대입구' 등 역 처리
    if not q.endswith("역") and ("역" in q or len(q) <= 4):
        search_queries.append(f"{q}역")
        search_queries.append(f"{q}역 대한민국")
    else:
        search_queries.append(f"{q} 대한민국")
        search_queries.append(f"대한민국 {q}")

    search_queries.append(q)

    # OpenStreetMap 순차 시도
    for query in search_queries:
        try:
            osm_url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": query,
                "format": "json",
                "limit": 1,
                "accept-language": "ko"
            }
            res = requests.get(osm_url, params=params, headers=headers, timeout=3)
            if res.status_code == 200 and len(res.json()) > 0:
                data = res.json()[0]
                lat = float(data["lat"])
                lon = float(data["lon"])
                name = data.get("display_name", query)
                return lat, lon, name
        except Exception:
            continue

    return None, None, None


def get_route_info(start_lat, start_lon, end_lat, end_lon):
    """두 좌표 간 차량 이동거리(km) 및 소요시간(분) 계산"""
    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=false"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if "routes" in data and len(data["routes"]) > 0:
                route = data["routes"][0]
                distance_km = route["distance"] / 1000.0
                duration_min = route["duration"] / 60.0
                return round(distance_km, 1), round(duration_min), None
    except Exception as e:
        return None, None, str(e)
    return None, None, "경로를 찾을 수 없습니다."


def get_weather_and_air(lat, lon):
    """위도/경도 기반 현재 기온, 날씨 및 미세먼지(PM10) 데이터 조회"""
    weather_url = "https://api.open-meteo.com/v1/forecast"
    w_params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "timezone": "Asia/Tokyo"
    }
    
    air_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    a_params = {
        "latitude": lat,
        "longitude": lon,
        "current": "pm10",
        "timezone": "Asia/Tokyo"
    }
    
    temp, weather_code, pm10 = 20.0, 0, 15.0
    
    try:
        w_res = requests.get(weather_url, params=w_params, timeout=5)
        if w_res.status_code == 200:
            w_data = w_res.json().get("current_weather", {})
            temp = w_data.get("temperature", 20.0)
            weather_code = w_data.get("weathercode", 0)
    except Exception:
        pass

    try:
        a_res = requests.get(air_url, params=a_params, timeout=5)
        if a_res.status_code == 200:
            a_data = a_res.json().get("current", {})
            pm10 = a_data.get("pm10", 15.0)
    except Exception:
        pass

    is_rain = weather_code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99]
    is_snow = weather_code in [71, 73, 75, 77, 85, 86]
    is_dust = pm10 > 50.0

    return {
        "temp": temp,
        "pm10": pm10,
        "is_rain": is_rain,
        "is_snow": is_snow,
        "is_dust": is_dust,
        "weather_code": weather_code
    }


# -------------------------------------------------------------------
# 2. 배경 테마 및 맞춤 알림 메시지
# -------------------------------------------------------------------

def render_weather_alerts(weather):
    temp = weather["temp"]
    pm10 = weather["pm10"]
    is_rain = weather["is_rain"]
    is_snow = weather["is_snow"]
    is_dust = weather["is_dust"]

    st.subheader("📢 실시간 맞춤 안내 메시지")
    
    # 1. 미세먼지(황사) 알림
    if is_dust:
        st.error(f"😷 **미세먼지(황사)가 높습니다! (PM10: {pm10:.1f} µg/m³)**\n\n미세먼지(황사)가 있으니 **마스크를 착용해주시는것을 추천드립니다**")
    else:
        st.success(f"🌿 **미세먼지 수치 양호 (PM10: {pm10:.1f} µg/m³)**\n\n대기질이 쾌적합니다.")

    # 2. 비/우산 알림
    if is_rain:
        st.info("🌧️ **현재 비가 오고 있습니다!**\n\n외출 시 **우산을 챙겨주세요.**")
    elif is_snow:
        st.info("❄️ **현재 눈이 내리고 있습니다!**\n\n빙판길 조심하세요.")

    # 3. 30도 이상 더위/물 알림
    if temp >= 30:
        st.warning(f"🔥 **무더위 주의! (현재 기온: {temp}°C)**\n\n기온이 30도가 넘으니 **물을 자주 마셔주세요!**")

    # 배경 화면 연출
    if is_rain:
        bg_color = "linear-gradient(135deg, #3a6073, #16222a)"
        icon = "🌧️ 비 내리는 날씨"
    elif is_snow:
        bg_color = "linear-gradient(135deg, #e6dada, #274046)"
        icon = "❄️ 눈 내리는 날씨"
    elif temp >= 30:
        bg_color = "linear-gradient(135deg, #ff7e5f, #feb47b)"
        icon = "☀️ 이글거리는 더운 날씨"
    else:
        bg_color = "linear-gradient(135deg, #757f9a, #d7dde8)"
        icon = "⛅ 쾌적한 날씨"

    css = f"""
    <style>
    .stApp {{
        background: {bg_color};
        color: #ffffff;
    }}
    .weather-card {{
        background: rgba(0, 0, 0, 0.4);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 20px;
        backdrop-filter: blur(8px);
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    st.markdown(
        f'<div class="weather-card"><h2>{icon}</h2><h1>목적지 기온: {temp}°C</h1></div>', 
        unsafe_allow_html=True
    )


# -------------------------------------------------------------------
# 3. 메인 화면 구성
# -------------------------------------------------------------------

st.title("🚗 출발지 & 목적지 통합 교통·날씨 가이드")
st.caption("주소, 도로명주소, 지하철역, 건물명을 입력하세요.")

col1, col2 = st.columns(2)

with col1:
    start_address = st.text_input("🚩 출발지 입력", value="서울시 금천구 가산동")
with col2:
    end_address = st.text_input("🏁 목적지 입력", value="서울특별시 은평구 불광동")

if st.button("🚀 바로 조회하기", use_container_width=True):
    if not start_address or not end_address:
        st.warning("출발지와 목적지를 모두 입력해 주세요.")
    else:
        with st.spinner("위치 확인 및 경로 계산 중..."):
            s_lat, s_lon, s_full = get_coordinates(start_address)
            e_lat, e_lon, e_full = get_coordinates(end_address)

            if not s_lat:
                st.error(f"❌ 출발지 '{start_address}'의 위치를 찾지 못했습니다. '금천구', '가산동', '가산디지털단지역'처럼 단어를 단순화해서 입력해 보세요.")
            elif not e_lat:
                st.error(f"❌ 목적지 '{end_address}'의 위치를 찾지 못했습니다. '은평구', '불광동', '연신내역'처럼 단어를 단순화해서 입력해 보세요.")
            else:
                # 1. 경로 계산
                dist_km, dur_min, err = get_route_info(s_lat, s_lon, e_lat, e_lon)
                
                # 2. 날씨 및 미세먼지
                weather = get_weather_and_air(e_lat, e_lon)

                # 3. 알림 및 배경 연출
                render_weather_alerts(weather)

                # 4. 소요시간 및 요약
                st.subheader("📊 한눈에 보는 핵심 정보")
                m1, m2, m3, m4 = st.columns(4)

                hours = int(dur_min // 60)
                mins = int(dur_min % 60)
                dur_str = f"{hours}시간 {mins}분" if hours > 0 else f"{mins}분"

                m1.metric("⏱️ 예상 소요시간", dur_str)
                m2.metric("📏 이동 거리", f"{dist_km} km")
                m3.metric("🌡️ 기온", f"{weather['temp']} °C")
                m4.metric("😷 미세먼지", f"{weather['pm10']:.1f} µg/m³")

                st.write(f"**출발지**: {start_address} (`{s_full}`)")
                st.write(f"**목적지**: {end_address} (`{e_full}`)")

                st.divider()

                # 5. 지도 표시
                st.subheader("📍 위치 및 경로 지도")
                map_df = pd.DataFrame({
                    "lat": [s_lat, e_lat],
                    "lon": [s_lon, e_lon]
                })
                st.map(map_df, zoom=10)

