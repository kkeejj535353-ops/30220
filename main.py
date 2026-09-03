import streamlit as st
import requests
import pandas as pd

# 페이지 기본 설정
st.set_page_config(page_title="스마트 교통 & 날씨·미세먼지 가이드", page_icon="🚗", layout="wide")

# -------------------------------------------------------------------
# 1. API 데이터 수집 함수들
# -------------------------------------------------------------------

def get_coordinates(address):
    """
     입력값이 '금천구', '은평구' 같은 구/동/지명이더라도
    자동으로 검색어를 보완하여 위치 좌표를 찾아냅니다.
    """
    address = address.strip()
    
    # 검색 실패를 줄이기 위한 검색어 보완 목록
    search_queries = [
        f"{address} 대한민국",       # 1순위: '금천구 대한민국'
        f"서울 {address}",          # 2순위: '서울 금천구'
        address                    # 3순위: 입력값 그대로
    ]
    
    headers = {"User-Agent": "StreamlitSmartApp/4.0 (contact@example.com)"}
    
    for query in search_queries:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "limit": 1,
            "accept-language": "ko"
        }
        try:
            res = requests.get(url, params=params, headers=headers, timeout=5)
            if res.status_code == 200 and len(res.json()) > 0:
                data = res.json()[0]
                # 장소 이름이 너무 길 경우 입력한 단어 위주로 깔끔하게 처리
                display_name = data.get("display_name", query)
                return float(data["lat"]), float(data["lon"]), display_name
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
        "current": "pm10,pm2_5",
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
# 2. 배경 테마 및 알림 메시지
# -------------------------------------------------------------------

def render_weather_alerts(weather):
    temp = weather["temp"]
    pm10 = weather["pm10"]
    is_rain = weather["is_rain"]
    is_snow = weather["is_snow"]
    is_dust = weather["is_dust"]

    st.subheader("📢 실시간 맞춤 안내 메시지")
    
    # 1. 미세먼지(황사) 추천
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

    # 배경 화면 설정
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

st.title("🚗 간단 지역 입력 경로·날씨·미세먼지 안내")
st.caption("지역 이름만 입력해도 바로 소요시간, 날씨, 미세먼지 정보를 확인합니다.")

col1, col2 = st.columns(2)

with col1:
    start_address = st.text_input("🚩 출발지 입력", value="금천구")
with col2:
    end_address = st.text_input("🏁 목적지 입력", value="은평구")

if st.button("🚀 바로 조회하기", use_container_width=True):
    if not start_address or not end_address:
        st.warning("출발지와 목적지를 모두 입력해 주세요.")
    else:
        with st.spinner("위치 확인 및 교통/날씨 정보 불러오는 중..."):
            s_lat, s_lon, s_full = get_coordinates(start_address)
            e_lat, e_lon, e_full = get_coordinates(end_address)

            if not s_lat:
                st.error(f"출발지 '{start_address}'의 위치를 찾을 수 없습니다.")
            elif not e_lat:
                st.error(f"목적지 '{end_address}'의 위치를 찾을 수 없습니다.")
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

                st.write(f"**출발지**: {start_address} ({s_full})")
                st.write(f"**목적지**: {end_address} ({e_full})")

                st.divider()

                # 5. 지도 표시
                st.subheader("📍 위치 및 경로 지도")
                map_df = pd.DataFrame({
                    "lat": [s_lat, e_lat],
                    "lon": [s_lon, e_lon]
                })
                st.map(map_df, zoom=10)

                
    
