import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="브롤스타즈 무료 전적 조회기", page_icon="🥊", layout="centered")

st.title("🥊 브롤스타즈 전적 & 승률 조회기")
st.caption("API 키 없이 태그만 입력하면 즉시 최근 전적과 승률을 계산합니다.")

player_tag = st.text_input("플레이어 태그 입력 (예: #2R20PL0UR 또는 2R20PL0UR)", value="")

# 태그 자동 정제 (알파벳 O -> 숫자 0 변환, # 처리)
clean_tag = player_tag.strip().upper().replace("O", "0")
if clean_tag and not clean_tag.startswith("#"):
    clean_tag = "#" + clean_tag

if st.button("전적 및 승률 즉시 조회") or clean_tag:
    if not player_tag:
        st.warning("플레이어 태그를 입력해 주세요.")
    else:
        st.info(f"🔍 조회 중인 태그: **{clean_tag}** (알파벳 'O'는 숫자 '0'으로 자동 전환되었습니다)")
        
        # 브라우저 전송용 URL 인코딩 (%23)
        encoded_tag = clean_tag.replace("#", "%23")
        
        # 파이썬 서버 차단을 우회하기 위한 자바스크립트 기반 앱 로직
        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    color: #31333F;
                    background-color: transparent;
                    margin: 0;
                    padding: 10px;
                }}
                .card {{
                    background: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 10px;
                    padding: 15px;
                    margin-bottom: 15px;
                }}
                .metric-container {{
                    display: flex;
                    gap: 15px;
                    margin-bottom: 20px;
                }}
                .metric-box {{
                    flex: 1;
                    background: white;
                    padding: 12px;
                    border-radius: 8px;
                    border: 1px solid #dee2e6;
                    text-align: center;
                }}
                .metric-label {{ font-size: 13px; color: #6c757d; font-weight: 600; }}
                .metric-value {{ font-size: 20px; font-weight: bold; margin-top: 5px; color: #111; }}
                .metric-sub {{ font-size: 12px; color: #495057; margin-top: 3px; }}
                .win {{ color: #28a745; font-weight: bold; }}
                .loss {{ color: #dc3545; font-weight: bold; }}
                .battle-item {{
                    background: white;
                    padding: 10px 14px;
                    border-radius: 6px;
                    margin-bottom: 8px;
                    border-left: 5px solid #ccc;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    font-size: 14px;
                }}
                .battle-victory {{ border-left-color: #28a745; }}
                .battle-defeat {{ border-left-color: #dc3545; }}
                .tag-ranked {{ background: #ffd700; color: #000; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
                .tag-normal {{ background: #e9ecef; color: #495057; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
                .error-box {{ background: #f8d7da; color: #721c24; padding: 15px; border-radius: 8px; border: 1px solid #f5c6cb; }}
            </style>
        </head>
        <body>
            <div id="loading">⚡ 최신 전적 데이터를 불러오는 중...</div>
            <div id="content" style="display:none;"></div>

            <script>
            async function fetchData() {{
                const rawTag = "{encoded_tag}";
                // CORS 프록시 우회 요청
                const targetUrl = `https://api.brawlify.com/v1/player/${{rawTag.replace('%23', '')}}`;
                const proxyUrl = `https://corsproxy.io/?${{encodeURIComponent(targetUrl)}}`;

                try {{
                    const response = await fetch(proxyUrl);
                    if (!response.ok) throw new Error("플레이어를 찾을 수 없거나 서버 응답에 실패했습니다.");
                    
                    const data = await response.json();
                    renderData(data);
                }} catch (err) {{
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('content').style.display = 'block';
                    document.getElementById('content').innerHTML = `
                        <div class="error-box">
                            ❌ <b>오류 발생:</b> ${{err.message}}<br><br>
                            - 태그 코드가 정확한지 확인해 주세요.<br>
                            - 최근 경기를 플레이한 기록이 없을 경우 조회되지 않을 수 있습니다.
                        </div>
                    `;
                }}
            }}

            function renderData(data) {{
                document.getElementById('loading').style.display = 'none';
                const container = document.getElementById('content');
                container.style.display = 'block';

                const battles = data.battles || data.battleLog || [];
                
                let normalWins = 0, normalTotal = 0;
                let rankedWins = 0, rankedTotal = 0;

                battles.forEach(b => {{
                    const battle = b.battle || {{}};
                    const mode = (battle.mode || "").toLowerCase();
                    const bType = (battle.type || "").toLowerCase();
                    const result = (battle.result || "").toLowerCase();

                    const isRanked = mode.includes("ranked") || bType.includes("ranked") || bType.includes("soloranked");

                    if (result === "victory" || result === "defeat") {{
                        if (isRanked) {{
                            rankedTotal++;
                            if (result === "victory") rankedWins++;
                        }} else {{
                            normalTotal++;
                            if (result === "victory") normalWins++;
                        }}
                    }}
                }});

                const normalRate = normalTotal > 0 ? ((normalWins / normalTotal) * 100).toFixed(1) : 0;
                const rankedRate = rankedTotal > 0 ? ((rankedWins / rankedTotal) * 100).toFixed(1) : 0;

                // 1. 프로필 및 승률 요약 HTML
                let html = `
                    <div class="card">
                        <h3>👤 ${{data.name || '알 수 없음'}} 님의 통계</h3>
                        <p style="margin: 3px 0; color: #666; font-size: 14px;">현재 트로피: <b>${{(data.trophies || 0).toLocaleString()}}개</b> | 최고 트로피: <b>${{(data.highestTrophies || 0).toLocaleString()}}개</b></p>
                    </div>

                    <h3>📊 최근 승률 분석</h3>
                    <div class="metric-container">
                        <div class="metric-box">
                            <div class="metric-label">🎮 일반전 승률</div>
                            <div class="metric-value">${{normalTotal > 0 ? normalRate + '%' : '기록 없음'}}</div>
                            <div class="metric-sub">${{normalTotal > 0 ? normalWins + '승 ' + (normalTotal - normalWins) + '패' : '-'}}</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-label">🏆 경쟁전 승률</div>
                            <div class="metric-value">${{rankedTotal > 0 ? rankedRate + '%' : '기록 없음'}}</div>
                            <div class="metric-sub">${{rankedTotal > 0 ? rankedWins + '승 ' + (rankedTotal - rankedWins) + '패' : '-'}}</div>
                        </div>
                    </div>

                    <h3>⚔️ 최근 10경기 상세 전적</h3>
                `;

                // 2. 최근 10경기 데이터 리스트
                const recent10 = battles.slice(0, 10);
                if (recent10.length === 0) {{
                    html += `<p>최근 경기 기록이 없습니다.</p>`;
                }} else {{
                    recent10.forEach((b, i) => {{
                        const battle = b.battle || {{}};
                        const event = b.event || {{}};
                        const mode = (battle.mode || event.mode || "일반").toUpperCase();
                        const mapName = event.map || "기본 맵";
                        const result = (battle.result || "기타").toLowerCase();
                        const isRanked = mode.toLowerCase().includes("ranked") || (battle.type || "").toLowerCase().includes("ranked");

                        let resClass = "";
                        let resText = "";
                        if (result === "victory") {{
                            resClass = "battle-victory";
                            resText = "<span class='win'>승리</span>";
                        }} else if (result === "defeat") {{
                            resClass = "battle-defeat";
                            resText = "<span class='loss'>패배</span>";
                        }} else {{
                            resText = "<span>무승부/진행중</span>";
                        }}

                        const tagHtml = isRanked ? `<span class="tag-ranked">경쟁전</span>` : `<span class="tag-normal">일반전</span>`;

                        html += `
                            <div class="battle-item ${{resClass}}">
                                <div>
                                    <b>${{i + 1}}. ${{resText}}</b> &nbsp; ${{tagHtml}} <b>${{mode}}</b> - ${{mapName}}
                                </div>
                            </div>
                        `;
                    }});
                }}

                container.innerHTML = html;
            }}

            fetchData();
            </script>
        </body>
        </html>
        """
        
        # HTML 렌더링
        components.html(html_code, height=650, scrolling=True)
    
                
                
    
