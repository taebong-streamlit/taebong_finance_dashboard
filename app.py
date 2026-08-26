"""
연금계좌 자산배분 & 실시간 리밸런싱 대시보드 (Streamlit)
- 네이버 금융 실시간 시세 연동
- 이평선 셀 배경 음영 제거 및 글자 색상(상단:빨강, 하단:파랑)만 표시
- 이평선 수정 시 동일 종목 전 계좌 자동 연동 (들여쓰기 에러 수정본)
"""

import os
import json
import time
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from bs4 import BeautifulSoup
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from st_aggrid.shared import JsCode

# ==========================================
# 0. 페이지 기본 설정 및 파일 저장 경로
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
        div[data-testid="stButton"] button:hover { border-color: #60a5fa !important; }
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
# 2. 포트폴리오 기본 데이터
# ==========================================
DEFAULT_PORTFOLIO = {
    "dc": [
        {"구분": "주식", "ETF명": "TIGER 미국S&P500타겟데일리커버드콜", "코드": "482730", "목표비율": 0.20, "보유수량": 5440, "이평선": "하단"},
        {"구분": "주식", "ETF명": "TIGER 미국나스닥100타겟데일리커버드콜", "코드": "486290", "목표비율": 0.10, "보유수량": 4094, "이평선": "하단"},
        {"구분": "주식", "ETF명": "TIGER 미국배당다우존스타겟데일리커버드콜", "코드": "0008S0", "목표비율": 0.10, "보유수량": 3300, "이평선": "하단"},
        {"구분": "주식", "ETF명": "KODEX 200타겟위클리커버드콜", "코드": "498400", "목표비율": 0.15, "보유수량": 2131, "이평선": "하단"},
        {"구분": "리츠", "ETF명": "KODEX 한국부동산리츠인프라", "코드": "476800", "목표비율": 0.05, "보유수량": 0, "이평선": "하단"},
        {"구분": "채권", "ETF명": "TIGER 미국30년국채커버드콜액티브(H)", "코드": "476550", "목표비율": 0.30, "보유수량": 14611, "이평선": "하단"},
        {"구분": "실물", "ETF명": "ACE KRX금현물", "코드": "411060", "목표비율": 0.10, "보유수량": 1235, "이평선": "하단"},
        {"구분": "현금", "ETF명": "KODEX 미국머니마켓액티브", "코드": "0048J0", "목표비율": 0.00, "보유수량": 0, "이평선": "-"},
        {"구분": "현금", "ETF명": "원화 현금", "코드": "", "목표비율": 0.00, "보유수량": 11241, "이평선": "-"},
    ],
    "pension": [
        {"구분": "주식", "ETF명": "TIGER 미국S&P500타겟데일리커버드콜", "코드": "482730", "목표비율": 0.20, "보유수량": 2174, "이평선": "하단"},
        {"구분": "주식", "ETF명": "TIGER 미국나스닥100타겟데일리커버드콜", "코드": "486290", "목표비율": 0.10, "보유수량": 1596, "이평선": "하단"},
        {"구분": "주식", "ETF명": "TIGER 미국배당다우존스타겟데일리커버드콜", "코드": "0008S0", "목표비율": 0.10, "보유수량": 1320, "이평선": "하단"},
        {"구분": "주식", "ETF명": "KODEX 200타겟위클리커버드콜", "코드": "498400", "목표비율": 0.15, "보유수량": 834, "이평선": "하단"},
        {"구분": "리츠", "ETF명": "KODEX 한국부동산리츠인프라", "코드": "476800", "목표비율": 0.05, "보유수량": 0, "이평선": "하단"},
        {"구분": "채권", "ETF명": "TIGER 미국30년국채커버드콜액티브(H)", "코드": "476550", "목표비율": 0.30, "보유수량": 5770, "이평선": "하단"},
        {"구분": "실물", "ETF명": "ACE KRX금현물", "코드": "411060", "목표비율": 0.10, "보유수량": 505, "이평선": "하단"},
        {"구분": "현금", "ETF명": "KODEX 미국머니마켓액티브", "코드": "0048J0", "목표비율": 0.00, "보유수량": 0, "이평선": "-"},
        {"구분": "현금", "ETF명": "원화 현금", "코드": "", "목표비율": 0.00, "보유수량": 5511, "이평선": "-"},
    ],
    "irp": [
        {"구분": "주식", "ETF명": "TIGER 미국S&P500타겟데일리커버드콜", "코드": "482730", "목표비율": 0.20, "보유수량": 925, "이평선": "하단"},
        {"구분": "주식", "ETF명": "TIGER 미국나스닥100타겟데일리커버드콜", "코드": "486290", "목표비율": 0.10, "보유수량": 693, "이평선": "하단"},
        {"구분": "주식", "ETF명": "TIGER 미국배당다우존스타겟데일리커버드콜", "코드": "0008S0", "목표비율": 0.10, "보유수량": 565, "이평선": "하단"},
        {"구분": "주식", "ETF명": "KODEX 200타겟위클리커버드콜", "코드": "498400", "목표비율": 0.15, "보유수량": 375, "이평선": "하단"},
        {"구분": "리츠", "ETF명": "KODEX 한국부동산리츠인프라", "코드": "476800", "목표비율": 0.05, "보유수량": 0, "이평선": "하단"},
        {"구분": "채권", "ETF명": "TIGER 미국30년국채커버드콜액티브(H)", "코드": "476550", "목표비율": 0.30, "보유수량": 2499, "이평선": "하단"},
        {"구분": "실물", "ETF명": "ACE KRX금현물", "코드": "411060", "목표비율": 0.10, "보유수량": 212, "이평선": "하단"},
        {"구분": "현금", "ETF명": "KODEX 미국머니마켓액티브", "코드": "0048J0", "목표비율": 0.00, "보유수량": 0, "이평선": "-"},
        {"구분": "현금", "ETF명": "원화 현금", "코드": "", "목표비율": 0.00, "보유수량": 7325, "이평선": "-"},
    ],
}

def load_portfolio_from_file():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
                portfolio = {}
                for key, items in saved_data.items():
                    df = pd.DataFrame(items)
                    if "현재가" not in df.columns:
                        df["현재가"] = df["코드"].apply(lambda c: 1 if c == "" else 0)
                    if "이평선" not in df.columns:
                        df["이평선"] = df["ETF명"].apply(lambda name: "-" if "머니마켓" in name or name == "원화 현금" else "하단")
                    portfolio[key] = df
                return portfolio
        except Exception:
            pass
    
    portfolio = {}
    for key, items in DEFAULT_PORTFOLIO.items():
        df = pd.DataFrame(items)
        df["현재가"] = df["코드"].apply(lambda c: 1 if c == "" else 0)
        portfolio[key] = df
    save_portfolio_to_file(portfolio)
    return portfolio

def save_portfolio_to_file(portfolio_dict):
    try:
        data_to_save = {}
        for key, df in portfolio_dict.items():
            sub_df = df[["구분", "ETF명", "코드", "목표비율", "보유수량", "이평선"]].copy()
            data_to_save[key] = sub_df.to_dict(orient="records")
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

ACCOUNT_LABELS = {"dc": "DC형 퇴직연금", "pension": "연금저축", "irp": "개인형 IRP"}
ACCOUNT_CSS = {"dc": "card-dc", "pension": "card-pension", "irp": "card-irp"}
CATEGORY_COLORS = {"주식": "#60a5fa", "채권": "#fb923c", "실물": "#facc15", "리츠": "#34d399", "현금": "#cbd5e1"}

# ==========================================
# 3. 세션 상태 초기화
# ==========================================
if "portfolio" not in st.session_state:
    st.session_state.portfolio = load_portfolio_from_file()

if "fetch_status" not in st.session_state:
    st.session_state.fetch_status = {"done": False, "success": 0, "total": 0}

# ==========================================
# 4. 실시간 시세 스크래핑
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

def fetch_all_prices(codes: list[str]):
    prices, success = {}, 0
    for code in codes:
        p = fetch_current_price(code)
        prices[code] = p
        if p is not None: success += 1
    return prices, success

def get_unique_codes():
    codes = set()
    for df in st.session_state.portfolio.values():
        codes.update(c for c in df["코드"].tolist() if c)
    return sorted(codes)

# ==========================================
# 5. 차트 및 AgGrid 자바스크립트 코드
# ==========================================
def render_donut(cat_totals: dict, key: str):
    labels = [k for k, v in cat_totals.items() if v > 0]
    values = [v for v in cat_totals.values() if v > 0]
    colors = [CATEGORY_COLORS.get(l, "#cbd5e1") for l in labels]
    fig = go.Figure(
        data=[go.Pie(
            labels=labels, 
            values=values, 
            hole=0.55,
            marker=dict(colors=colors, line=dict(color="#1e293b", width=2)),
            texttemplate="<b>%{label}</b><br><b>%{percent}</b>", 
            textfont=dict(size=14, color="#ffffff")
        )]
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=10, b=10, l=0, r=0), 
        height=320,
        showlegend=False 
    )
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{key}")

color_jscode = JsCode("""
function(params) {
    var val = params.value;
    if (val === '주식') { return {'color': '#2563eb', 'fontWeight': 'bold', 'textAlign': 'center'}; }
    if (val === '채권') { return {'color': '#d97706', 'fontWeight': 'bold', 'textAlign': 'center'}; }
    if (val === '실물') { return {'color': '#ca8a04', 'fontWeight': 'bold', 'textAlign': 'center'}; }
    if (val === '리츠') { return {'color': '#059669', 'fontWeight': 'bold', 'textAlign': 'center'}; }
    if (val === '현금') { return {'color': '#475569', 'fontWeight': 'bold', 'textAlign': 'center'}; }
    return {'textAlign': 'center', 'color': '#000000'};
}
""")

ma_color_jscode = JsCode("""
function(params) {
    var val = params.value;
    if (val === '상단') {
        return {'color': '#dc2626', 'fontWeight': 'bold', 'textAlign': 'center'};
    } else if (val === '하단') {
        return {'color': '#2563eb', 'fontWeight': 'bold', 'textAlign': 'center'};
    }
    return {'textAlign': 'center', 'color': '#64748b'};
}
""")

chart_link = JsCode("""
class ChartLinkRenderer {
    init(params) {
        this.eGui = document.createElement('div');
        if (params.value && params.value !== '') {
            this.eGui.innerHTML = '<a href="' + params.value + '" target="_blank" style="text-decoration:none; color:#2563eb; font-weight:bold;">📊 열기</a>';
        } else {
            this.eGui.innerHTML = '<span style="color: #475569;">-</span>';
        }
    }
    getGui() {
        return this.eGui;
    }
}
""")

currency_fmt = JsCode("function(params) { return Number(params.value).toLocaleString() + ' 원'; }")
amount_fmt = JsCode("function(params) { return Number(params.value).toLocaleString() + ' 주'; }")

# ==========================================
# 6. 헤더 및 시세 호출
# ==========================================
header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.markdown("<h1 style='font-size:2.8rem; font-weight:800; color:#ffffff; margin-top: 5px; margin-bottom: 20px; line-height: 1.4;'>📈 태봉의 연금자산 관리</h1>", unsafe_allow_html=True)

do_refresh = st.button("🔄 실시간 시세 강제 새로고침", width="content")

if do_refresh:
    fetch_current_price.clear()
    st.session_state.fetch_status["done"] = False

if not st.session_state.fetch_status["done"] or do_refresh:
    codes = get_unique_codes()
    with st.spinner("실시간 시세를 불러오는 중입니다..."):
        prices, success = fetch_all_prices(codes)
        for key, df in st.session_state.portfolio.items():
            df["현재가"] = df.apply(lambda r: prices.get(r["코드"], r["현재가"]) if r["코드"] else 1, axis=1)
        st.session_state.fetch_status = {"done": True, "success": success, "total": len(codes)}

status = st.session_state.fetch_status
if status["total"] == 0:
    st.markdown('<span class="status-badge status-loading">🌐 대기 중</span>', unsafe_allow_html=True)
elif status["success"] == status["total"]:
    st.markdown(f'<span class="status-badge status-success">✅ 시세 연동 성공 ({status["success"]}/{status["total"]})</span>', unsafe_allow_html=True)
else:
    st.markdown(f'<span class="status-badge status-loading">⚠️ 일부 연동 성공 ({status["success"]}/{status["total"]})</span>', unsafe_allow_html=True)
st.markdown("<hr style='margin:0.3rem 0; border-color:#334155;'>", unsafe_allow_html=True)

# ==========================================
# 7. 통합 로직 및 UI 렌더링
# ==========================================
grand_total = 0
computed = {}

for key, df in st.session_state.portfolio.items():
    df_calc = df.copy()
    df_calc["평가금액"] = df_calc["현재가"] * df_calc["보유수량"]
    total_eval = df_calc["평가금액"].sum()
    grand_total += total_eval
    
    df_calc["현재비율"] = (df_calc["평가금액"] / total_eval * 100).fillna(0) if total_eval else 0
    df_calc["목표금액"] = total_eval * df_calc["목표비율"]
    df_calc["목표수량"] = df_calc.apply(lambda r: round(r["목표금액"] / r["현재가"]) if r["현재가"] and r["현재가"] > 1 else 0, axis=1)
    df_calc["조정수량"] = df_calc["목표수량"] - df_calc["보유수량"]
    
    def rebalance_text(r):
        if r["코드"] == "" or r["목표비율"] == 0: return "-"
        if r["조정수량"] > 0: return f"🔴 +{r['조정수량']:,.0f}주 매수"
        if r["조정수량"] < 0: return f"🔵 {r['조정수량']:,.0f}주 매도"
        return "유지"

    df_calc["조정필요"] = df_calc.apply(rebalance_text, axis=1)
    df_calc["차트"] = df_calc["코드"].apply(lambda c: f"https://finance.naver.com/item/fchart.naver?code={c}" if c else "")
    
    cat_totals = df_calc.groupby("구분")["평가금액"].sum().to_dict()
    computed[key] = (df_calc, total_eval, cat_totals)

summary_cols = st.columns(4)
with summary_cols[0]:
    st.markdown(f'<div class="summary-card"><label>총 연금 자산 평가액</label><div class="value">{grand_total:,.0f} 원</div></div>', unsafe_allow_html=True)
for i, key in enumerate(["dc", "pension", "irp"]):
    with summary_cols[i + 1]:
        st.markdown(f'<div class="summary-card {ACCOUNT_CSS[key]}"><label>{ACCOUNT_LABELS[key]}</label><div class="value">{computed[key][1]:,.0f} 원</div></div>', unsafe_allow_html=True)
st.markdown("<hr style='margin:0.3rem 0; border-color:#334155;'>", unsafe_allow_html=True)

custom_css = {
    ".ag-header-cell-label": {"justify-content": "center !important"},
    ".ag-header-cell": {"text-align": "center !important"}
}

tabs = st.tabs([ACCOUNT_LABELS[k] for k in ["dc", "pension", "irp"]])
for tab, key in zip(tabs, ["dc", "pension", "irp"]):
    with tab:
        df_calc, total_eval, cat_totals = computed[key]
        
        display_df = df_calc[['구분', 'ETF명', '목표비율', '현재가', '보유수량', '평가금액', '현재비율', '이평선', '목표수량', '조정필요', '차트']].copy()
        
        display_df['현재비율'] = display_df['현재비율'].apply(lambda x: f"{x:.1f}%")
        display_df['목표비율'] = display_df['목표비율'].apply(lambda x: f"{x * 100:.0f}%")
        display_df['평가금액'] = display_df['평가금액'].apply(lambda x: f"{x:,.0f} 원")
        display_df['목표수량'] = display_df['목표수량'].apply(lambda x: f"{x:,.0f} 주")

        gb = GridOptionsBuilder.from_dataframe(display_df)
        
        gb.configure_default_column(cellStyle={'textAlign': 'center', 'color': '#000000'})
        
        gb.configure_column("구분", cellStyle=color_jscode, width=90, editable=False)
        gb.configure_column("ETF명", width=340, editable=False, cellStyle={'textAlign': 'left', 'color': '#000000', 'fontWeight': '600'})
        gb.configure_column("목표비율", width=100, editable=False)
        
        gb.configure_column("현재가", editable=True, type=["numericColumn"], valueFormatter=currency_fmt, width=130, cellStyle={'textAlign': 'right', 'color': '#000000'})
        gb.configure_column("보유수량", editable=True, type=["numericColumn"], valueFormatter=amount_fmt, width=130, cellStyle={'textAlign': 'right', 'color': '#000000'})
        gb.configure_column("평가금액", width=150, editable=False, cellStyle={'textAlign': 'right', 'color': '#000000'})
        gb.configure_column("현재비율", width=110, editable=False, cellStyle={'textAlign': 'right', 'color': '#000000'})
        
        gb.configure_column(
            "이평선", 
            editable=True, 
            cellEditor="agSelectCellEditor", 
            cellEditorParams={"values": ["상단", "하단"]}, 
            cellStyle=ma_color_jscode, 
            width=120
        )
        
        gb.configure_column("목표수량", width=130, editable=False, cellStyle={'textAlign': 'right', 'color': '#000000'})
        gb.configure_column("조정필요", width=170, editable=False, cellStyle={'textAlign': 'left', 'color': '#000000'})
        gb.configure_column("차트", cellRenderer=chart_link, width=100, editable=False)

        gridOptions = gb.build()

        grid_response = AgGrid(
            display_df,
            gridOptions=gridOptions,
            update_mode=GridUpdateMode.VALUE_CHANGED, 
            allow_unsafe_jscode=True, 
            theme='alpine', 
            custom_css=custom_css,
            fit_columns_on_grid_load=True, 
            key=f"grid_{key}"
        )

        edited_data = grid_response['data']
        if edited_data is not None:
            if isinstance(edited_data, dict):
                edited_df = pd.DataFrame(edited_data)
            else:
                edited_df = edited_data
                
            if not edited_df.empty:
                def clean_numeric(val):
                    if pd.isna(val): return 0
                    s = str(val).replace(',', '').replace('원', '').replace('주', '').replace('%', '').strip()
                    try:
                        return float(s)
                    except ValueError:
                        return 0

                new_prices = edited_df["현재가"].apply(clean_numeric).astype(int).values
                new_amounts = edited_df["보유수량"].apply(clean_numeric).astype(int).values
                new_mas = edited_df["이평선"].values
                
                orig_prices = st.session_state.portfolio[key]["현재가"].values
                orig_amounts = st.session_state.portfolio[key]["보유수량"].values
                orig_mas = st.session_state.portfolio[key]["이평선"].values
                
                if not (new_prices == orig_prices).all() or not (new_amounts == orig_amounts).all() or not (new_mas == orig_mas).all():
                    st.session_state.portfolio[key]["현재가"] = new_prices
                    st.session_state.portfolio[key]["보유수량"] = new_amounts
                    
                    updated_mas = []
                    for idx, row in st.session_state.portfolio[key].iterrows():
                        etf_name = row["ETF명"]
                        new_val = new_mas[idx]
                        updated_mas.append(new_val)
                        
                        # 전 계좌 동일 종목 연동 처리
                        for other_k in st.session_state.portfolio.keys():
                            mask = st.session_state.portfolio[other_k]["ETF명"] == etf_name
                            st.session_state.portfolio[other_k].loc[mask, "이평선"] = new_val
                            
                    st.session_state.portfolio[key]["이평선"] = updated_mas
                    save_portfolio_to_file(st.session_state.portfolio)
                    st.rerun()

        st.write("") 
        chart_col, info_col = st.columns([1, 1.3]) 
        
        with chart_col:
            st.markdown(f"<h4 style='text-align: center; color: #f8fafc;'>{ACCOUNT_LABELS[key]} 자산 비중</h4>", unsafe_allow_html=True)
            render_donut(cat_totals, key)
            
        with info_col:
            rule_html = """
            <div style="background-color: #1e293b; padding: 25px 30px; border-radius: 12px; border: 1px solid #334155; height: 95%; box-shadow: 0 4px 10px rgba(0,0,0,0.2); display: flex; flex-direction: column; justify-content: center;">
                <h4 style="margin-top: 0; color: #f8fafc; margin-bottom: 18px; font-size: 1.3rem;">⚙️ 리밸런싱 가이드</h4>
                <p style="font-size: 1.1rem; font-weight: 700; color: #cbd5e1; margin-bottom: 12px;">📌 리밸런싱 주기 : <span style="color:#60a5fa;">매월 1일</span></p>
                <p style="font-size: 1.1rem; font-weight: 700; color: #cbd5e1; margin-bottom: 10px;">📌 리밸런싱 방법 :</p>
                <ul style="font-size: 1.05rem; font-weight: 600; color: #94a3b8; line-height: 1.8; margin-top: 0; padding-left: 25px;">
                    <li><b>일봉차트 120일 이동평균선 <span style="color:#dc2626;">상단</span></b> : 해당 ETF 보유</li>
                    <li><b>일봉차트 120일 이동평균선 <span style="color:#2563eb;">하단</span></b> : 해당 ETF 매각 후 <span style="color:#ffffff; font-weight:800; background-color:#334155; padding:2px 8px; border-radius:6px; margin-left: 4px;">KODEX 미국머니마켓액티브</span>로 변경</li>
                </ul>
            </div>
            """
            st.markdown(rule_html, unsafe_allow_html=True)
