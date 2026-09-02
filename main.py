import streamlit as st
import requests

st.set_page_config(page_title="무료 브롤스타즈 승률 & 전적", page_icon="🥊", layout="centered")

st.title("🥊 브롤스타즈 승률 & 최근 10경기 조회기")
st.caption("API 키 없이 태그만 입력하면 승률 분석 및 최근 10판 전적을 보여줍니다.")

player_tag = st.text_input("플레이어 태그 입력 (예: #2R20PL0UR 또는 2R20PL0UR)", value="")

def fetch_brawl_data(tag):
    clean_tag = tag.strip().upper().replace("#", "")
    
    # 1차 시도: 공개 게이트웨이 엔드포인트
    urls = [
        f"https://brawlify.nates.org/v1/players/%23{clean_tag}",
        f"https://api.brawlify.com/v1/player/{clean_tag}"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
                return res.json(), None
        except Exception:
            continue
            
    return None, "전적 정보를 가져올 수 없습니다. 태그가 정확한지 확인해 주세요."

if st.button("전적 및 승률 조회"):
    if not player_tag:
        st.warning("태그를 입력해 주세요.")
    else:
        with st.spinner("전적 데이터 불러오는 중..."):
            data, error = fetch_brawl_data(player_tag)
            
            if error:
                st.error(error)
                st.info("💡 **태그 입력 팁**: 숫자 `0`과 알파벳 `O`를 헷갈리지 않았는지 확인해 보세요! 브롤스타즈 태그에는 알파벳 O가 사용되지 않습니다.")
            else:
                # 1. 플레이어 프로필 요약
                name = data.get("name", "Unknown")
                trophies = data.get("trophies", 0)
                highest = data.get("highestTrophies", data.get("highest_trophies", 0))
                
                st.subheader(f"👤 {name} 님의 전적 리포트")
                c1, c2 = st.columns(2)
                c1.metric("현재 트로피", f"{trophies:,}개")
                c2.metric("최고 트로피", f"{highest:,}개")
                
                st.divider()
                
                # 2. 전투 기록 추출 (최근 경기 데이터)
                battles = data.get("battles", data.get("battleLog", []))
                
                if not battles:
                    st.warning("최근 진행한 경기 데이터가 존재하지 않습니다.")
                else:
                    normal_wins, normal_total = 0, 0
                    ranked_wins, ranked_total = 0, 0
                    
                    for b in battles:
                        battle_info = b.get("battle", {})
                        mode = str(battle_info.get("mode", "")).lower()
                        b_type = str(battle_info.get("type", "")).lower()
                        result = str(battle_info.get("result", "")).lower()
                        
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
                    
                    # 승률 요약 출력
                    st.subheader("📊 일반전 vs 경쟁전 승률")
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
                    
                    st.divider()
                    
                    # 3. 최근 10판 상세 전적
                    st.subheader("⚔️ 최근 10판 상세 전적")
                    
                    recent_10 = battles[:10]
                    for idx, b in enumerate(recent_10, 1):
                        event = b.get("event", {})
                        battle = b.get("battle", {})
                        
                        mode_name = battle.get("mode", event.get("mode", "일반")).upper()
                        map_name = event.get("map", "알 수 없는 맵")
                        result = str(battle.get("result", "결과 없음")).lower()
                        
                        # 승패 표기 설정
                        if result == "victory":
                            res_text = "🟢 승리 (VICTORY)"
                        elif result == "defeat":
                            res_text = "🔴 패배 (DEFEAT)"
                        else:
                            res_text = "⚪ 무승부/기타"
                            
                        # 모드 구분 (경쟁전/일반전 표시)
                        b_type = str(battle.get("type", "")).lower()
                        is_ranked = "ranked" in mode_name.lower() or "ranked" in b_type
                        mode_tag = "[경쟁전]" if is_ranked else "[일반전]"
                        
                        st.write(f"**{idx}. {res_text}** | {mode_tag} {mode_name} - {map_name}")
    
                
                
    
