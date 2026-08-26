"""
태봉의 연금자산 관리 대시보드 (Streamlit 순정 데이터 에디터 적용본)
- AgGrid 패키지 의존성 완전 제거 (Oh no 에러 원천 차단)
- 이평선 수정 시 전 계좌 동일 종목 자동 동기화 기능 포함
"""

import os
import json
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from bs4 import BeautifulSoup

# ==========================================
# 0. 페이지 기본 설정
# ==========================================
st.set_page_config(page_title="태봉의 연금자산 관리", page_icon="📈", layout="wide")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
DATA_FILE = "portfolio_data.json"

# ==========================================
# 1. 스타일 세팅
# ==========================================
st.markdown(
    """
    <style>
        .stApp { background-color: #0f172a; color: #f8fafc; }
        .block-container { padding-top: 3.5rem !important; padding-bottom: 1rem; max-width: 95%; }
        div[data-testid="stButton"] button {
            background-color: #1e293b !important; border: 1px solid #475569 !important;
        }
        div[data-testid="stButton"] button p { color: #ffffff !important; font-weight: 700 !important; }
        .summary-card {
            background:#1e293b; padding:12px 20px; border-radius:14px;
            box-shadow:0 4px 10px rgba(0,0,0,0.2); border:1px solid #334155;
            border-left:5px solid #3b82f6;
        }
        .summary-card label { font-size:1.1rem; color:#94a3b8; font-weight:700; }
        .summary-card .value { font-size:1.35rem; font-weight:800; margin-top:4px; color:#f8fafc; }
        .card-dc { border-left-color:#3b82f6; } 
        .card-pension { border-left-color:#10b981; } 
        .card-irp { border-left-color:#8b5cf6; } 
        .status-badge { font-size:0.85rem; padding:6px 14px; border-radius:20px; font-weight:600; }
        .status-loading { background:#78350f; color:#fef3c7; }
        .status-success { background:#064e3b; color:#d1fae5; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# 2. 기본 데이터 및 파일 로드
# ==========================================
DEFAULT_PORTFOLIO = {
    "dc": [
        {"구분": "주식", "ETF명": "TIGER 미국S&P500타겟데일리커버드콜", "코드": "482730", "목표비율": 0.20, "현재가": 0, "보유수량": 5440, "이평선": "하단"},
        {"구분": "주식", "ETF명": "TIGER 미국나스닥100타겟데일리커버드콜", "코드": "486290", "목표비율": 0.10, "현재가": 0, "보유수량": 4094, "이평선": "하단"},
        {"구분": "주식", "ETF명": "TIGER 미국배당다우존스타겟데일리커버드콜", "코드": "0008S0", "목표비율": 0.10, "현재가": 0, "보유수량": 3300, "이평선": "하단"},
        {"구분": "주식", "ETF명": "KODEX 200타겟위클리커버드콜", "코드": "498400", "목표비율": 0.15, "현재가": 0, "보유수량": 2131, "이평선": "하단"},
        {"구분": "리츠", "ETF명": "KODEX 한국부동산리츠인프라", "코드": "476800", "목표비율": 0.05, "현재가": 0, "보유수량": 0, "이평선": "하단"},
        {"구분": "채권", "ETF명": "TIGER 미국30년국채커버드콜액티브(H)", "코드": "476550", "목표비율": 0.30, "현재가": 0, "보유수량": 14611, "이평선": "하단"},
        {"구분": "실물", "ETF명": "ACE KRX금현물", "코드": "411060", "목표비율": 0.10, "현재가": 0, "보유수량": 1235, "이평선": "하단"},
        {"구분": "현금", "ETF명": "KODEX 미국머니마켓액티브", "코드": "0048J0", "목표비율": 0.00, "현재가": 0, "보유수량": 0, "이평선": "-"},
        {"구분": "현금", "ETF명": "원화 현금", "코드": "", "목표비율": 0.00, "현재가": 1, "보유수량": 11241, "이평선": "-"},
    ],
    "pension": [
        {"구분": "주식", "ETF명": "TIGER 미국S&P500타겟데일리커버드콜", "코드": "482730", "목표비율": 0.20, "현재가": 0, "보유수량": 2174, "이평선": "하단"},
        {"구분": "주식", "ETF명": "TIGER 미국나스닥100타겟데일리커버드콜", "코드": "486290", "목표비율": 0.10, "현재가": 0, "보유수량": 1596, "이평선": "하단"},
        {"구분": "주식", "ETF명": "TIGER 미국배당다우존스타겟데일리커버드콜", "코드": "0008S0", "목표비율": 0.10, "현재가": 0, "보유수량": 1320, "이평선": "하단"},
        {"구분": "주식", "ETF명": "KODEX 200타겟위클리커버드콜", "코드": "498400", "목표비율": 0.15, "현재가": 0, "보유수량": 834, "이평선": "하단"},
        {"구분": "리츠", "ETF명": "KODEX 한국부동산리츠인프라", "코드": "476800", "목표비율": 0.05, "현재가": 0, "보유수량": 0, "이평선": "하단"},
        {"구분": "채권", "ETF명": "TIGER 미국30년국채커버드콜액티브(H)", "코드": "476550", "목표비율": 0.30, "현재가": 0, "보유수량": 5770, "이평선": "하단"},
        {"구분": "실물", "ETF명": "ACE KRX금현물", "코드": "411060", "목표비율": 0.10, "현재가": 0, "보유수량": 505, "이평선": "하단"},
        {"구분": "현금", "ETF명": "KODEX 미국머니마켓액티브", "코드": "0048J0", "목표비율": 0.00, "현재가": 0, "보유수량": 0, "이평선": "-"},
        {"구분": "현금", "ETF명": "원화 현금", "코드": "", "목표비율": 0.00, "현재가": 1, "보유수량": 5511, "이평선": "-"},
    ],
    "irp": [
        {"구분": "주식", "ETF명": "TIGER 미국S&P500타겟데일리커버드콜", "코드": "482730", "목표비율": 0.20, "현재가": 0, "보유수량": 925, "이평선": "하단"},
        {"구분": "주식", "ETF명": "TIGER 미국나스닥100타겟데일리커버드콜", "코드": "486290", "목표비율": 0.10, "현재가": 0, "보유수량": 693, "이평선": "하단"},
        {"구분": "주식", "ETF명": "TIGER 미국배당다우존스타겟데일리커버드콜", "코드": "0008S0", "목표비율": 0.10, "현재가": 0, "보유수량": 565, "이평선": "하단"},
        {"구분": "주식", "ETF명": "KODEX 200타겟위클리커버드콜", "코드": "498400", "목표비율": 0.15, "현재가": 0, "보유수량": 375, "이평선": "하단"},
        {"구분": "리츠", "ETF명": "KODEX 한국부동산리츠인프라", "코드": "476800", "목표비율": 0.05, "현재가": 0, "보유수량": 0, "이평선": "하단"},
        {"구분": "채권", "ETF명": "TIGER 미국30년국채커버드콜액티브(H)", "코드": "476550", "목표비율": 0.30, "현재가": 0, "보유수량": 2499, "이평선": "하단"},
        {"구분": "실물", "ETF명": "ACE KRX금현물", "코드": "411060", "목표비율": 0.10, "현재가": 0, "보유수량": 212, "이평선": "하단"},
        {"구분": "현금", "ETF명": "KODEX 미국머니마켓액티브", "코드": "0048J0", "목표비율": 0.00, "현재가": 0, "보유수량": 0, "이평선": "-"},
        {"구분": "현금", "ETF명": "원화 현금", "코드": "", "목표비율": 0.00, "현재가": 1, "보유수량": 7325, "이평선": "-"},
    ],
}

def load_portfolio():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
                portfolio = {}
                for key, items in saved_data.items():
                    df = pd.DataFrame(items)
                    portfolio[key] = df
                return portfolio
        except Exception:
            pass
    
    portfolio = {k: pd.DataFrame(v) for k, v in DEFAULT_PORTFOLIO.items()}
    save_portfolio(portfolio)
    return portfolio

def save_portfolio(portfolio_dict):
    try:
        data_to_save = {}
        for key, df in portfolio_dict.items():
            # 저장할 때 불필요한 연산 컬럼은 빼고 핵심만 저장합니다.
            sub_df = df[["구분", "ETF명", "코드", "목표비율", "현재가", "보유수량", "이평선"]].copy()
            data_to_save[key] = sub_df.to_dict(orient="records")
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

ACCOUNT_LABELS = {"dc": "DC형 퇴직연금", "pension": "연금저축", "irp": "개인형 IRP"}
ACCOUNT_CSS = {"dc": "card-dc", "pension": "card-pension", "irp": "card-irp"}
CATEGORY_COLORS = {"주식": "#60a5fa", "채권": "#fb923c", "실물": "#facc15", "리츠": "#34d399", "현금": "#cbd5e1"}

if "portfolio" not in st.session_state:
    st.session_state.portfolio = load_portfolio()
if "fetch_status" not in st.session_state:
    st.session_state.fetch_status = {"done": False, "success": 0, "total": 0}

# ==========================================
# 3. 실시간 시세 스크래핑
# ==========================================
@st.cache_data(ttl=60, show_spinner=False)
def fetch_current_price(code: str):
    if not code: return 1
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=3)
        soup = BeautifulSoup(res.text, "html.parser")
        no_today = soup.find("p", class_="no_today")
        if no_today:
            return int(no_today.find("span", class_="blind").text.replace(",", ""))
    except Exception:
        pass
    return None

# ==========================================
# 4. 헤더 및 시세 업데이트
# ==========================================
header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.markdown("<h1 style='font-size:2.8rem; font-weight:800; color:#ffffff; margin-top: 5px; margin-bottom: 20px;'>📈 태봉의 연금자산 관리</h1>", unsafe_allow_html=True)

do_refresh = st.button("🔄 실시간 시세 강제 새로고침")

if do_refresh:
    fetch_current_price.clear()
    st.session_state.fetch_status["done"] = False

if not st.session_state.fetch_status["done"] or do_refresh:
    codes = set()
    for df in st.session_state.portfolio.values():
        codes.update(c for c in df["코드"].tolist() if c)
    
    with st.spinner("실시간 시세를 불러오는 중입니다..."):
        success = 0
        prices = {}
        for code in codes:
            p = fetch_current_price(code)
            prices[code] = p
            if p is not None: success += 1
            
        for key, df in st.session_state.portfolio.items():
            df["현재가"] = df.apply(lambda r: prices.get(r["코드"], r["현재가"]) if r["코드"] else 1, axis=1)
            
        st.session_state.fetch_status = {"done": True, "success": success, "total": len(codes)}
        save_portfolio(st.session_state.portfolio)

status = st.session_state.fetch_status
if status["total"] == 0:
    st.markdown('<span class="status-badge status-loading">🌐 대기 중</span>', unsafe_allow_html=True)
elif status["success"] == status["total"]:
    st.markdown(f'<span class="status-badge status-success">✅ 시세 연동 성공 ({status["success"]}/{status["total"]})</span>', unsafe_allow_html=True)
else:
    st.markdown(f'<span class="status-badge status-loading">⚠️ 일부 연동 성공 ({status["success"]}/{status["total"]})</span>', unsafe_allow_html=True)
st.markdown("<hr style='margin:0.3rem 0; border-color:#334155;'>", unsafe_allow_html=True)

# ==========================================
# 5. 연산 및 요약 카드
# ==========================================
grand_total = 0
computed = {}

for key, df in st.session_state.portfolio.items():
    df_calc = df.copy()
    
    df_calc["현재가"] = pd.to_numeric(df_calc["현재가"], errors='coerce').fillna(0).astype(int)
    df_calc["보유수량"] = pd.to_numeric(df_calc["보유수량"], errors='coerce').fillna(0).astype(int)
    
    df_calc["평가금액"] = df_calc["현재가"] * df_calc["보유수량"]
    total_eval = df_calc["평가금액"].sum()
    grand_total += total_eval
    
    df_calc["현재비율(%)"] = (df_calc["평가금액"] / total_eval * 100).fillna(0) if total_eval else 0
    df_calc["목표금액"] = total_eval * df_calc["목표비율"]
    df_calc["목표수량"] = df_calc.apply(lambda r: round(r["목표금액"] / r["현재가"]) if r["현재가"] > 1 else 0, axis=1)
    df_calc["조정수량"] = df_calc["목표수량"] - df_calc["보유수량"]
    
    def rebalance_text(r):
        if r["코드"] == "" or r["목표비율"] == 0: return "-"
        if r["조정수량"] > 0: return f"🔴 +{r['조정수량']:,.0f}주 매수"
        if r["조정수량"] < 0: return f"🔵 {r['조정수량']:,.0f}주 매도"
        return "유지"

    df_calc["조정필요"] = df_calc.apply(rebalance_text, axis=1)
    df_calc["차트보기"] = df_calc["코드"].apply(lambda c: f"https://finance.naver.com/item/fchart.naver?code={c}" if c else "")
    
    cat_totals = df_calc.groupby("구분")["평가금액"].sum().to_dict()
    computed[key] = (df_calc, total_eval, cat_totals)

summary_cols = st.columns(4)
with summary_cols[0]:
    st.markdown(f'<div class="summary-card"><label>총 연금 자산 평가액</label><div class="value">{grand_total:,.0f} 원</div></div>', unsafe_allow_html=True)
for i, key in enumerate(["dc", "pension", "irp"]):
    with summary_cols[i + 1]:
        st.markdown(f'<div class="summary-card {ACCOUNT_CSS[key]}"><label>{ACCOUNT_LABELS[key]}</label><div class="value">{computed[key][1]:,.0f} 원</div></div>', unsafe_allow_html=True)
st.markdown("<hr style='margin:0.3rem 0; border-color:#334155;'>", unsafe_allow_html=True)

# ==========================================
# 6. 메인 표 (st.data_editor) 및 도넛 차트
# ==========================================
tabs = st.tabs([ACCOUNT_LABELS[k] for k in ["dc", "pension", "irp"]])
for tab, key in zip(tabs, ["dc", "pension", "irp"]):
    with tab:
        df_calc, total_eval, cat_totals = computed[key]
        
        # UI에 보여줄 데이터 세팅
        view_df = df_calc[['구분', 'ETF명', '목표비율', '현재가', '보유수량', '평가금액', '현재비율(%)', '이평선', '목표수량', '조정필요', '차트보기']].copy()
        
        edited_df = st.data_editor(
            view_df,
            column_config={
                "구분": st.column_config.TextColumn("구분", disabled=True),
                "ETF명": st.column_config.TextColumn("ETF명", disabled=True, width="large"),
                "목표비율": st.column_config.NumberColumn("목표비율", format="%.2f", disabled=True),
                "현재가": st.column_config.NumberColumn("현재가(원)", format="%d", disabled=True),
                "보유수량": st.column_config.NumberColumn("보유수량(주)", format="%d", step=1),
                "평가금액": st.column_config.NumberColumn("평가금액(원)", format="%d", disabled=True),
                "현재비율(%)": st.column_config.NumberColumn("현재비율(%)", format="%.1f %%", disabled=True),
                "이평선": st.column_config.SelectboxColumn("이평선", options=["상단", "하단", "-"]),
                "목표수량": st.column_config.NumberColumn("목표수량(주)", format="%d", disabled=True),
                "조정필요": st.column_config.TextColumn("조정필요", disabled=True),
                "차트보기": st.column_config.LinkColumn("차트보기", display_text="📊 네이버 차트")
            },
            hide_index=True,
            use_container_width=True,
            key=f"editor_{key}"
        )

        # 사용자가 수량이나 이평선을 변경했을 때 처리 로직
        changed = False
        new_amounts = edited_df["보유수량"].fillna(0).astype(int).tolist()
        new_mas = edited_df["이평선"].tolist()
        
        orig_amounts = st.session_state.portfolio[key]["보유수량"].fillna(0).astype(int).tolist()
        orig_mas = st.session_state.portfolio[key]["이평선"].tolist()

        if new_amounts != orig_amounts or new_mas != orig_mas:
            for idx, row in st.session_state.portfolio[key].iterrows():
                etf_name = row["ETF명"]
                
                # 수량 업데이트
                st.session_state.portfolio[key].at[idx, "보유수량"] = new_amounts[idx]
                
                # 이평선 업데이트 및 전 계좌 동기화
                if orig_mas[idx] != new_mas[idx]:
                    new_ma_val = new_mas[idx]
                    st.session_state.portfolio[key].at[idx, "이평선"] = new_ma_val
                    
                    # 다른 계좌(tab)에 있는 동일 ETF도 이평선 동일하게 변경
                    for other_k in ["dc", "pension", "irp"]:
                        if other_k != key:
                            mask = st.session_state.portfolio[other_k]["ETF명"] == etf_name
                            st.session_state.portfolio[other_k].loc[mask, "이평선"] = new_ma_val
                            
            save_portfolio(st.session_state.portfolio)
            st.rerun()

        # 도넛 차트 및 가이드 영역
        st.write("") 
        chart_col, info_col = st.columns([1, 1.3]) 
        
        with chart_col:
            st.markdown(f"<h4 style='text-align: center; color: #f8fafc;'>{ACCOUNT_LABELS[key]} 자산 비중</h4>", unsafe_allow_html=True)
            labels = [k for k, v in cat_totals.items() if v > 0]
            values = [v for v in cat_totals.values() if v > 0]
            colors = [CATEGORY_COLORS.get(l, "#cbd5e1") for l in labels]
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.55, marker=dict(colors=colors, line=dict(color="#1e293b", width=2)), texttemplate="<b>%{label}</b><br><b>%{percent}</b>", textfont=dict(size=14, color="#ffffff"))])
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=10, b=10, l=0, r=0), height=320, showlegend=False)
            st.plotly_chart(fig, use_container_width=True, key=f"chart_{key}")
            
        with info_col:
            st.markdown("""
            <div style="background-color: #1e293b; padding: 25px 30px; border-radius: 12px; border: 1px solid #334155; height: 95%; box-shadow: 0 4px 10px rgba(0,0,0,0.2); display: flex; flex-direction: column; justify-content: center;">
                <h4 style="margin-top: 0; color: #f8fafc; margin-bottom: 18px; font-size: 1.3rem;">⚙️ 리밸런싱 가이드</h4>
                <p style="font-size: 1.1rem; font-weight: 700; color: #cbd5e1; margin-bottom: 12px;">📌 리밸런싱 주기 : <span style="color:#60a5fa;">매월 1일</span></p>
                <p style="font-size: 1.1rem; font-weight: 700; color: #cbd5e1; margin-bottom: 10px;">📌 리밸런싱 방법 :</p>
                <ul style="font-size: 1.05rem; font-weight: 600; color: #94a3b8; line-height: 1.8; margin-top: 0; padding-left: 25px;">
                    <li><b>일봉차트 120일 이동평균선 <span style="color:#dc2626;">상단</span></b> : 해당 ETF 보유</li>
                    <li><b>일봉차트 120일 이동평균선 <span style="color:#2563eb;">하단</span></b> : 해당 ETF 매각 후 <span style="color:#ffffff; font-weight:800; background-color:#334155; padding:2px 8px; border-radius:6px; margin-left: 4px;">KODEX 미국머니마켓액티브</span>로 변경</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
