import streamlit as st
import requests
import pandas as pd

# 페이지 기본 설정
st.set_page_config(page_title="스마트 교통 & 날씨·미세먼지 가이드", page_icon="🚗", layout="wide")

# -------------------------------------------------------------------
# 1. API 데이터 수집 함수들
# -------------------------------------------------------------------

def get_coordinates(address):
    """주소/지명을 입력받아 위도, 경도를 반환 (한국 검색 최적화)"""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "countrycodes": "kr",
        "accept-language": "ko"
    }
    headers = {"User-Agent": "StreamlitSmartApp/3.0"}
    
    try:
        res = requests.get(url, params=params, headers=headers, timeout=5)
        if res.status_code == 200 and len(res.json()) > 0:
            data = res.json()[0]
            return float(data["lat"]), float(data["lon"]), data["display_name"]
    except Exception:
        pass

    # 2차 시도 (국가 제한 해제)
    try:
        params.pop("countrycodes", None)
        res = requests.get(url, params=params, headers=headers, timeout=5)
        if res.status_code == 200 and len(res.json()) > 0:
            data = res.json()[0]
            return float(data["lat"]), float(data["lon"]), data["display_name"]
    except Exception:
        pass

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
    """위도/경도 기반 현재 기온, 날씨 및 미세먼지(PM10) 데이터 조회 (Open-Meteo)"""
    # 1. 날씨 정보
    weather_url = "https://api.open-meteo.com/v1/forecast"
    w_params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "timezone": "Asia/Tokyo"
    }
    
    # 2. 미세먼지(대기질) 정보
    air_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    a_params = {
        "latitude": lat,
        "longitude": lon,
        "current": "pm10,pm2_5",
        "timezone": "Asia/Tokyo"
    }
    
    temp, weather_code, pm10 = 20.0, 0, 15.0  # 기본값
    
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

    # WMO 날씨 코드 파싱
    is_rain = weather_code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99]
    is_snow = weather_code in [71, 73, 75, 77, 85, 86]
    
    # 미세먼지(황사) 나쁨 기준 (PM10 > 50 µg/m³)
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
# 2. 배경 테마 및 맞춤 알림 메시지 출력
# -------------------------------------------------------------------

def render_weather_alerts(weather):
    temp = weather["temp"]
    pm10 = weather["pm10"]
    is_rain = weather["is_rain"]
    is_snow = weather["is_snow"]
    is_dust = weather["is_dust"]

    # --- 맞춤 안내 알림 상자들 ---
    st.subheader("📢 실시간 맞춤 안내 메시지")
    
    # 1. 미세먼지/황사 알림
    if is_dust:
        st.error(f"😷 **미세먼지(황사)가 높습니다! (PM10: {pm10:.1f} µg/m³)**\n\n미세먼지(황사)가 있으니 **마스크를 착용해주시는 것을 추천드립니다.**")
    else:
        st.success(f"🌿 **미세먼지 수치 양호 (PM10: {pm10:.1f} µg/m³)**\n\n대기질이 쾌적합니다.")

    # 2. 비/우산 알림
    if is_rain:
        st.info("🌧️ **현재 목적지에 비가 오고 있습니다!**\n\n외출 시 **우산을 꼭 챙겨주세요.**")
    elif is_snow:
        st.info("❄️ **현재 목적지에 눈이 내리고 있습니다!**\n\n빙판길 운전에 주의하세요.")

    # 3. 30도 이상 더위/물 알림
    if temp >= 30:
        st.warning(f"🔥 **무더위 주의! (현재 기온: {temp}°C)**\n\n기온이 30도가 넘으니 **물을 자주 마셔주세요!**")

    # --- 배경 테마 결정 ---
    if is_rain:
        bg_color = "linear-gradient(135deg, #3a6073, #16222a)"
        icon = "🌧️ 비 내리는 중"
    elif is_snow:
        bg_color = "linear-gradient(135deg, #e6dada, #274046)"
        icon = "❄️ 눈 내리는 중"
    elif temp >= 30:
        bg_color = "linear-gradient(135deg, #ff7e5f, #feb47b)"
        icon = "☀️ 이글거리는 무더운 날씨"
    else:
        bg_color = "linear-gradient(135deg, #757f9a, #d7dde8)"
        icon = "⛅ 쾌적함/구름"

    # CSS 적용
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
st.caption("주소를 입력하면 소요시간, 도로 정보, 날씨, 미세먼지 및 안내 메시지가 즉시 출력됩니다.")

col1, col2 = st.columns(2)

with col1:
    start_address = st.text_input("🚩 출발지 주소/명칭 입력", value="서울시청")
with col2:
    end_address = st.text_input("🏁 목적지 주소/명칭 입력", value="부산시청")

if st.button("🚀 즉시 조회하기", use_container_width=True):
    if not start_address or not end_address:
        st.warning("출발지와 목적지 주소를 모두 입력해 주세요.")
    else:
        with st.spinner("위치 탐색 및 교통/날씨/미세먼지 데이터 수집 중..."):
            s_lat, s_lon, s_full = get_coordinates(start_address)
            e_lat, e_lon, e_full = get_coordinates(end_address)

            if not s_lat or not e_lat:
                st.error("주소를 찾을 수 없습니다. (예: '서울특별시 중구 태평로1가 31', '강남역', '부산시청' 등 명확히 입력해 주세요.)")
            else:
                # 1. 경로 계산
                dist_km, dur_min, err = get_route_info(s_lat, s_lon, e_lat, e_lon)
                
                # 2. 날씨 및 미세먼지 조회
                weather = get_weather_and_air(e_lat, e_lon)

                # 3. 알림 메시지 및 테마 배경 출력
                render_weather_alerts(weather)

                # 4. 소요시간 및 요약 정보
                st.subheader("📊 핵심 교통 및 소요시간 리포트")
                m1, m2, m3, m4 = st.columns(4)

                hours = int(dur_min // 60)
                mins = int(dur_min % 60)
                dur_str = f"{hours}시간 {mins}분" if hours > 0 else f"{mins}분"

                m1.metric("⏱️ 예상 소요시간", dur_str)
                m2.metric("📏 총 이동거리", f"{dist_km} km")
                m3.metric("🌡️ 목적지 기온", f"{weather['temp']} °C")
                m4.metric("😷 미세먼지(PM10)", f"{weather['pm10']:.1f} µg/m³")

                st.write(f"**출발지**: {s_full}")
                st.write(f"**목적지**: {e_full}")

                st.divider()

                # 5. 지도 표시
                st.subheader("📍 이동 경로 지도 (출발지 ➔ 목적지)")
                map_df = pd.DataFrame({
                    "lat": [s_lat, e_lat],
                    "lon": [s_lon, e_lon]
                })
                st.map(map_df, zoom=6)
                
    
