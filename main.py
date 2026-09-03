import streamlit as st
import requests
import pandas as pd

# 페이지 기본 설정
st.set_page_config(page_title="스마트 경로 & 날씨 가이드", page_icon="🌤️", layout="wide")

# -------------------------------------------------------------------
# 1. API 데이터 수집 함수들
# -------------------------------------------------------------------

def get_coordinates(location_name):
    """지명/주소를 입력받아 위도, 경도를 반환 (한국 검색 최적화)"""
    url = "https://nominatim.openstreetmap.org/search"
    
    # 입력어 검색 파라미터 (국가 제한 및 한국어 기본설정)
    params = {
        "q": location_name,
        "format": "json",
        "limit": 1,
        "countrycodes": "kr",
        "accept-language": "ko"
    }
    headers = {
        "User-Agent": "StreamlitWeatherApp/2.0 (contact@example.com)"
    }
    try:
        res = requests.get(url, params=params, headers=headers, timeout=5)
        if res.status_code == 200 and len(res.json()) > 0:
            data = res.json()[0]
            return float(data["lat"]), float(data["lon"]), data["display_name"]
    except Exception:
        pass
        
    # 한국 제한 없이 2차 시도
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
        return None, None, f"경로 계산 중 오류 발생: {str(e)}"
    return None, None, "경로를 찾을 수 없습니다."


def get_weather(lat, lon):
    """위도/경도 기반 현재 기온 및 날씨 정보 반환"""
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
            weather_code = weather_data.get("weathercode", 0)
            
            # WMO 날씨 코드 분석 및 상태 구분
            # types: 'clear' (맑음/더움), 'rain' (비), 'snow' (눈), 'cloud' (구름)
            status_type = "clear"
            status_desc = "☀️ 맑음"

            if weather_code in [1, 2, 3]:
                status_type = "cloud"
                status_desc = "⛅ 구름 조금 / 흐림"
            elif weather_code in [45, 48]:
                status_type = "cloud"
                status_desc = "🌫️ 안개"
            elif weather_code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99]:
                status_type = "rain"
                status_desc = "🌧️ 비"
            elif weather_code in [71, 73, 75, 77, 85, 86]:
                status_type = "snow"
                status_desc = "❄️ 눈"

            # 기온이 28도 이상이면 강제로 'hot' 그래픽/배경 처리
            if temp >= 28 and status_type == "clear":
                status_type = "hot"
                status_desc = "🔥 무더움"

            return {
                "temp": temp,
                "type": status_type,
                "desc": status_desc
            }, None
    except Exception as e:
        return None, f"날씨 조회 실패: {str(e)}"
    return None, "날씨 정보 응답 없음"


# -------------------------------------------------------------------
# 2. 동적 테마 CSS 및 커스텀 그래픽 적용 함수
# -------------------------------------------------------------------

def apply_weather_theme(temp, weather_type):
    """기온 및 날씨 상태에 따라 배경색 변경 및 그래픽 이펙트 적용"""
    
    # 1. 날씨 유형별 테마 설정
    if weather_type == "hot" or temp >= 28:
        # 더움 / 태양 배경
        bg_color = "linear-gradient(135deg, #ff7e5f, #feb47b)"
        text_color = "#ffffff"
        graphic_html = """
        <div style="text-align: center; margin-bottom: 20px;">
            <div style="display: inline-block; width: 100px; height: 100px; background: #ffea00; border-radius: 50%; box-shadow: 0 0 40px #ff9800; animation: pulse 2s infinite alternate;"></div>
            <p style="font-size: 20px; font-weight: bold; margin-top: 10px; color: #fff;">☀️ 이글거리는 태양 (현재 기온: {temp}°C)</p>
        </div>
        """
    elif weather_type == "rain":
        # 비 배경
        bg_color = "linear-gradient(135deg, #3a6073, #16222a)"
        text_color = "#ffffff"
        graphic_html = """
        <div style="text-align: center; margin-bottom: 20px;">
            <div style="font-size: 70px; line-height: 1.1;">🌧️💧</div>
            <p style="font-size: 20px; font-weight: bold; color: #b3e5fc;">비가 내리는 중입니다 (현재 기온: {temp}°C)</p>
        </div>
        """
    elif weather_type == "snow":
        # 눈 배경
        bg_color = "linear-gradient(135deg, #e6dada, #274046)"
        text_color = "#ffffff"
        graphic_html = """
        <div style="text-align: center; margin-bottom: 20px;">
            <div style="font-size: 70px; line-height: 1.1;">❄️☃️</div>
            <p style="font-size: 20px; font-weight: bold; color: #e0f7fa;">눈이 내리고 있습니다 (현재 기온: {temp}°C)</p>
        </div>
        """
    else:
        # 일반 / 흐림 배경
        bg_color = "linear-gradient(135deg, #757f9a, #d7dde8)"
        text_color = "#222222"
        graphic_html = """
        <div style="text-align: center; margin-bottom: 20px;">
            <div style="font-size: 70px; line-height: 1.1;">⛅</div>
            <p style="font-size: 20px; font-weight: bold; color: #333333;">온화한 날씨 (현재 기온: {temp}°C)</p>
        </div>
        """

    graphic_rendered = graphic_html.format(temp=temp)

    # CSS 동적 주입
    css = f"""
    <style>
    .stApp {{
        background: {bg_color};
        color: {text_color};
    }}
    .bg-temp-banner {{
        background: rgba(0, 0, 0, 0.3);
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        margin-bottom: 25px;
        backdrop-filter: blur(5px);
    }}
    .bg-temp-banner h1 {{
        font-size: 45px !important;
        margin: 0;
        color: #ffffff !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    st.markdown(f'<div class="bg-temp-banner">{graphic_rendered}<h1>목적지 기온: {temp}°C</h1></div>', unsafe_allow_html=True)


# -------------------------------------------------------------------
# 3. Streamlit 메인 화면 구성
# -------------------------------------------------------------------

st.title("🗺️ 스마트 경로 소요시간 & 동적 날씨 가이드")
st.caption("출발지와 목적지를 입력하면 예상 소요시간과 함께 목적지 날씨 테마(태양/비/눈) 배경을 표시합니다.")

col_in1, col_in2 = st.columns(2)

with col_in1:
    start_input = st.text_input("🚩 출발지 입력", value="서울역")
with col_in2:
    end_input = st.text_input("🏁 목적지 입력", value="부산역")

# 입력 팁 안내
st.caption("💡 **입력 팁**: 정확한 검색을 위해 '서울역', '부산시청', '강남역', '해운대'처럼 주요 명칭으로 입력해 보세요.")

if st.button("🚀 경로 계산 & 날씨 확인하기", use_container_width=True):
    if not start_input or not end_input:
        st.warning("출발지와 목적지를 모두 입력해 주세요.")
    else:
        with st.spinner("위치 탐색 및 경로/날씨 데이터 수집 중..."):
            # 좌표 가져오기
            s_lat, s_lon, s_addr = get_coordinates(start_input)
            e_lat, e_lon, e_addr = get_coordinates(end_input)

            if not s_lat and not e_lat:
                st.error(f"출발지('{start_input}')와 목적지('{end_input}')를 모두 찾을 수 없습니다. 더 명확한 주소나 명칭으로 변경해 보세요.")
            elif not s_lat:
                st.error(f"출발지('{start_input}') 위치를 찾을 수 없습니다. (예: 서울특별시청, 서울역 등)")
            elif not e_lat:
                st.error(f"목적지('{end_input}') 위치를 찾을 수 없습니다. (예: 부산시청, 해운대해수욕장 등)")
            else:
                # 1. 경로 소요 시간 계산
                dist_km, dur_min, route_err = get_route_info(s_lat, s_lon, e_lat, e_lon)
                
                # 2. 목적지 날씨 가져오기
                weather, weather_err = get_weather(e_lat, e_lon)

                # 3. 날씨별 배경 및 그래픽 이펙트 적용
                if weather:
                    apply_weather_theme(weather["temp"], weather["type"])

                st.success("조회가 완료되었습니다!")

                # 4. 소요시간 및 요약 정보 출력
                st.subheader("📊 경로 및 소요시간")
                m1, m2, m3 = st.columns(3)

                hours = int(dur_min // 60)
                mins = int(dur_min % 60)
                dur_str = f"{hours}시간 {mins}분" if hours > 0 else f"{mins}분"

                m1.metric("⏱️ 예상 소요 시간", dur_str)
                m2.metric("📏 총 이동 거리", f"{dist_km} km")
                m3.metric("🌤️ 목적지 날씨", weather["desc"] if weather else "정보 없음")

                st.write(f"**출발지 위치**: {s_addr}")
                st.write(f"**목적지 위치**: {e_addr}")

                st.divider()

                # 5. 출발지 및 목적지 지도 출력
                st.subheader("📍 위치지도 (출발지 & 목적지)")
                
                # Streamlit 지도 데이터 프레임 생성
                map_data = pd.DataFrame({
                    "lat": [s_lat, e_lat],
                    "lon": [s_lon, e_lon],
                    "location": ["출발지", "목적지"]
                })
                
                st.map(map_data, zoom=6)
        
    
                
                
    
