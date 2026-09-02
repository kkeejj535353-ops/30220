import streamlit as st
import requests
from bs4 import BeautifulSoup
import json

# 페이지 기본 설정
st.set_page_config(page_title="브롤스타즈 승률 조회기", page_icon="🥊", layout="centered")

st.title("🥊 무료 브롤스타즈 승률 조회기")
st.caption("API 키 없이 태그 입력만으로 최근 일반전/경쟁전 승률을 계산합니다.")

# 플레이어 태그 입력
player_tag = st.text_input("플레이어 태그 입력 (예: #2R20PL0UR 또는 2R20PL0UR)", value="")

def get_brawl_data(tag):
    # 태그 정제 (# 제거 및 대문자 변환)
    clean_tag = tag.strip().upper().replace("#", "")
    url = f"https://brawltime.ninja/profile/{clean_tag}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None, "전적 정보를 찾을 수 없습니다. 태그를 올바르게 입력했는지 확인해 주세요."
    
    soup = BeautifulSoup(response.text, "html.parser")
    script_tag = soup.find("script", id="__NEXT_DATA__")
    
    if not script_tag:
        return None, "데이터를 불러오는 중 오류가 발생했습니다."
        
    try:
        data = json.loads(script_tag.string)
        page_props = data.get("props", {}).get("pageProps", {})
        player_info = page_props.get("player", {})
        battle_log = page_props.get("battlelog", [])
        return {"player": player_info, "battles": battle_log}, None
    except Exception as e:
        return None, f"데이터 분석 실패: {str(e)}"

if st.button("승률 즉시 조회"):
    if not player_tag:
        st.warning("태그를 입력해 주세요.")
    else:
        with st.spinner("전적 데이터 수집 중..."):
            data, error = get_brawl_data(player_tag)
            
            if error:
                st.error(error)
            else:
                player = data["player"]
                battles = data["battles"]
                
                # 프로필 요약
                st.subheader(f"👤 {player.get('name', 'Unknown')} 님의 최근 전적")
                col1, col2, col3 = st.columns(3)
                col1.metric("현재 트로피", f"{player.get('trophies', 0):,}개")
                col2.metric("최고 트로피", f"{player.get('highestTrophies', 0):,}개")
                col3.metric("3v3 승리 수", f"{player.get('3vs3Victories', 0):,}회")
                
                st.divider()
                
                # 최근 경기 파싱 (일반전 / 경쟁전 분리)
                normal_wins, normal_total = 0, 0
                ranked_wins, ranked_total = 0, 0
                
                for b in battles:
                    battle_info = b.get("battle", {})
                    mode = str(battle_info.get("mode", "")).lower()
                    b_type = str(battle_info.get("type", "")).lower()
                    result = str(battle_info.get("result", "")).lower()
                    
                    # 경쟁전 판별
                    is_ranked = "ranked" in mode or "ranked" in b_type
                    
                    if result in ["victory", "defeat"]:
                        if is_ranked:
                            ranked_total += 1
                            if result == "victory":
                                ranked_wins += 1
                        else:
                            normal_total += 1
                            if result == "victory":
                                normal_wins += 1
                
                # 승률 계산
                normal_rate = (normal_wins / normal_total * 100) if normal_total > 0 else 0
                ranked_rate = (ranked_wins / ranked_total * 100) if ranked_total > 0 else 0
                
                # 결과 출력
                st.subheader("📊 최근 경기 승률 분석")
                res_col1, res_col2 = st.columns(2)
                
                with res_col1:
                    st.markdown("**🎮 일반전**")
                    if normal_total > 0:
                        st.metric("승률", f"{normal_rate:.1f}%", f"{normal_wins}승 {normal_total - normal_wins}패 (총 {normal_total}전)")
                    else:
                        st.info("최근 기록에 일반전이 없습니다.")
                        
                with res_col2:
                    st.markdown("**🏆 경쟁전**")
                    if ranked_total > 0:
                        st.metric("승률", f"{ranked_rate:.1f}%", f"{ranked_wins}승 {ranked_total - ranked_wins}패 (총 {ranked_total}전)")
                    else:
                        st.info("최근 기록에 경쟁전이 없습니다.")
    
