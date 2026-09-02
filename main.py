import streamlit as st
import requests
import pandas as pd

# 페이지 기본 설정
st.set_page_config(page_title="실시간 경로 소요시간 & 날씨 안내", page_icon="🗺️", layout="wide")

st.title("🗺️ 경로 소요시간 계산 & 목적지 날씨 안내")
st.caption("출발지와 목적지를 입력하면 예상 이동 시간, 거리 및 목적지의 현재 날씨를 보여줍니다.")

# 1. 지명(주소/장소) -> 위도/경도 변환 함수 (Nominatim 무료 API)
def get_coordinates(location_name):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": location_name,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "StreamlitTrafficWeatherApp/1.0"
    }
    try:
        res = requests.get(url, params=params, headers=headers, timeout=5)
        if res.status_code == 200 and len(res.json()) > 0:
            data = res.json()[0]
            return float(data["lat"]), float(data["lon"]), data["display_name"]
    except Exception:
        pass
    return None, None, None

# 2. 경로 소요 시간 및 거리 계산 함수 (OSRM 무료 경로 API)
def get_route_info(start_lat, start_lon, end_lat, end_lon):
    # lon,lat 순서로 전달
    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=false"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if "routes" in data and len(data["routes"]) > 0:
                route = data["routes"][0]
                distance_km = route["distance"] / 1000.0  # 미터 -> km
                duration_min = route["duration"] / 60.0    # 초 -> 분
                return round(distance_km, 1), round(duration_min), None
    except Exception as e:
        return None, None, f"경로 계산 오류: {str(e)}"
    return None, None, "경로를 찾을 수 없습니다."

# 3. 목적지 실시간 날씨 조회 함수 (Open-Meteo 무료 API)
def get_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "timezone": "Asia/Tokyo"
    }
    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            weather_data = res.json().get("current_weather", {})
            temp = weather_data.get("temperature")
            wind_speed = weather_data.get("windspeed")
            weather_code = weather_data.get("weathercode", 0)
            
            # WMO 날씨 코드 해석
            weather_desc = "☀️ 맑음"
            if weather_code in [1, 2, 3]:
                weather_desc = "⛅ 구름 조금 / 흐림"
            elif weather_code in [45, 48]:
                weather_desc = "🌫️ 안개"
            elif weather_code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
                weather_desc = "🌧️ 비"
            elif weather_code in [71, 73, 75, 77, 85, 86]:
                weather_desc = "❄️ 눈"
            elif weather_code in [95, 96, 99]:
                weather_desc = "🌩️ 뇌우"

            return {
                "temp": temp,
                "wind": wind_speed,
                "desc": weather_desc
            }, None
    except Exception as e:
        return None, f"날씨 정보 조회 실패: {str(e)}"
    return None, "날씨 정보를 불러올 수 없습니다."

# 사용자 입력 화면
col_input1, col_input2 = st.columns(2)

with col_input1:
    start_point = st.text_input("🚩 출발지 입력", value="서울역")
with col_input2:
    end_point = st.text_input("🏁 목적지 입력", value="부산역")

if st.button("🚗 경로 및 날씨 조회하기", use_container_width=True):
    if not start_point or not end_point:
        st.warning("출발지와 목적지를 모두 입력해 주세요.")
    else:
        with st.spinner("위치 확인 및 경로/날씨 데이터 수집 중..."):
            # 1. 출발지 / 목적지 좌표 조회
            start_lat, start_lon, start_address = get_coordinates(start_point)
            end_lat, end_lon, end_address = get_coordinates(end_point)

            if not start_lat or not end_lat:
                st.error("출발지 또는 목적지 주소를 찾을 수 없습니다. (예: 서울역, 강남역, 부산시청 등 명확한 지명으로 입력해 보세요.)")
            else:
                # 2. 경로 소요 시간 계산
                distance, duration, route_err = get_route_info(start_lat, start_lon, end_lat, end_lon)
                # 3. 목적지 날씨 조회
                weather_data, weather_err = get_weather(end_lat, end_lon)

                st.success("조회가 완료되었습니다!")
                
                st.subheader("📊 경로 및 소요 시간 결과")
                m1, m2, m3 = st.columns(3)
                
                # 시간 포맷 변경 (분 -> 시간/분)
                hours = duration // 60
                mins = duration % 60
                duration_str = f"{hours}시간 {mins}분" if hours > 0 else f"{mins}분"

                m1.metric("⏱️ 예상 소요 시간", duration_str)
                m2.metric("📏 총 이동 거리", f"{distance} km")
                m3.metric("🎯 목적지 좌표", f"{end_lat:.2f}, {end_lon:.2f}")

                st.caption(f"**출발지**: {start_address}")
                st.caption(f"**목적지**: {end_address}")

                st.divider()

                # 4. 목적지 날씨 안내
                st.subheader(f"🌤️ 목적지({end_point}) 현재 날씨")
                
                if weather_err or not weather_data:
                    st.warning("날씨 정보를 불러오지 못했습니다.")
                else:
                    w1, w2, w3 = st.columns(3)
                    w1.metric("상태", weather_data["desc"])
                    w2.metric("현재 기온", f"{weather_data['temp']} °C")
                    w3.metric("풍속", f"{weather_data['wind']} km/h")

                st.divider()

                # 5. 지도로 위치 표시
                st.subheader("📍 출발지 및 목적지 지도 위치")
                map_df = pd.DataFrame({
                    "lat": [start_lat, end_lat],
                    "lon": [start_lon, end_lon]
                })
                st.map(map_df)
        
    
                
                
    
