import streamlit as st
import requests

# 페이지 설정
st.set_page_config(page_title="브롤스타즈 전적 검색", page_icon="🥊", layout="centered")

st.title("🥊 브롤스타즈 승률 조회기")
st.caption("최근 25경기 기록을 바탕으로 일반전 및 경쟁전 승률을 분석합니다.")

# 사이드바 API 키 입력
api_key = st.sidebar.text_input("Supercell API Key 입력", type="password")
st.sidebar.markdown("[API 키 발급 안내](https://developer.brawlstars.com/)")

# 검색 입력
player_tag = st.text_input("플레이어 태그 입력 (예: #2R20PL0UR 또는 2R20PL0UR)", value="")

def fetch_data(endpoint, token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"https://api.brawlstars.com/v1/{endpoint}", headers=headers)
    return response.json() if response.status_code == 200 else None

if st.button("승률 조회"):
    if not api_key:
        st.error("사이드바에 API 키를 입력해 주세요.")
    elif not player_tag:
        st.warning("플레이어 태그를 입력해 주세요.")
    else:
        # 태그 정제 (# 보장 및 URL 인코딩 %23)
        formatted_tag = player_tag.strip().upper()
        if not formatted_tag.startswith("#"):
            formatted_tag = "#" + formatted_tag
        encoded_tag = formatted_tag.replace("#", "%23")

        # 1. 플레이어 프로필 조회
        player_info = fetch_data(f"players/{encoded_tag}", api_key)
        # 2. 전투 기록 조회
        battle_log = fetch_data(f"players/{encoded_tag}/battlelog", api_key)

        if not player_info or not battle_log:
            st.error("플레이어 정보를 불러올 수 없습니다. 태그 또는 API 키를 확인하세요.")
        else:
            # 프로필 기본 정보 표시
            st.subheader(f"👤 {player_info.get('name', 'Unknown')} 님의 통계")
            col1, col2, col3 = st.columns(3)
            col1.metric("현재 트로피", f"{player_info.get('trophies', 0):,}개")
            col2.metric("최고 트로피", f"{player_info.get('highestTrophies', 0):,}개")
            col3.metric("3v3 승리 수", f"{player_info.get('3vs3Victories', 0):,}회")

            st.divider()

            # 전투 기록 파싱
            normal_wins, normal_total = 0, 0
            ranked_wins, ranked_total = 0, 0

            for battle in battle_log.get("items", []):
                event = battle.get("event", {})
                b_detail = battle.get("battle", {})
                mode = b_detail.get("mode", "")
                result = b_detail.get("result", "")

                # 경쟁전/솔로레포드 구분 (soloRanked, teamRanked 등)
                is_ranked = "ranked" in mode.lower() or b_detail.get("type") == "soloRanked"

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
            st.subheader("📊 최근 경기 승률 (최근 25경기 기준)")
            res_col1, res_col2 = st.columns(2)

            with res_col1:
                st.markdown("**일반전**")
                if normal_total > 0:
                    st.metric("일반전 승률", f"{normal_rate:.1f}%", f"{normal_wins}승 {normal_total - normal_wins}패")
                else:
                    st.info("최근 일반전 기록 없음")

            with res_col2:
                st.markdown("**경쟁전**")
                if ranked_total > 0:
                    st.metric("경쟁전 승률", f"{ranked_rate:.1f}%", f"{ranked_wins}승 {ranked_total - ranked_wins}패")
                else:
                    st.info("최근 경쟁전 기록 없음")
