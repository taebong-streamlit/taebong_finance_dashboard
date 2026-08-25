"""
연금계좌 자산배분 & 실시간 리밸런싱 대시보드 (Streamlit)
- 네이버 금융 실시간 시세 + 120일 이동평균선 실계산
- 전문 AgGrid 라이브러리 (데이터 및 헤더 완벽 중앙 정렬 적용)
필요 패키지: streamlit pandas requests beautifulsoup4 plotly lxml streamlit-aggrid
실행: streamlit run app.py
"""

import time
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from bs4 import BeautifulSoup
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from st_aggrid.shared import JsCode

# ==========================================
# 0. 페이지 기본 설정
# ==========================================
st.set_page_config(page_title="태봉의 연금자산 관리", page_icon="📈", layout="wide")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ==========================================
# 1. 스타일 세팅
# ==========================================
st.markdown(
    """
    <style>
        .block-container { padding-top: 0.8rem; padding-bottom: 1rem; max-width: 1400px; }
        .dash-header {
            display:flex; justify-content:space-between; align-items:center;
            background:#fff; padding:14px 28px; border-radius:16px;
            box-shadow:0 4px 6px -1px rgba(0,0,0,0.05); border:1px solid #e2e8f0;
            margin-bottom:6px;
        }
        .dash-header h1 { font-size:2.5rem; font-weight:800; color:#0f172a; margin:0; }
        .status-badge {
            font-size:0.85rem; padding:6px 14px; border-radius:20px; font-weight:600;
        }
        .status-loading { background:#fef9c3; color:#854d0e; }
        .status-success { background:#dcfce7; color:#166534; }
        .status-manual { background:#fee2e2; color:#991b1b; }
        .summary-card {
            background:#fff; padding:12px 20px; border-radius:14px;
            box-shadow:0 2px 4px rgba(0,0,0,0.03); border:1px solid #e2e8f0;
            border-left:5px solid #2563eb;
        }
        .summary-card label { font-size:1.1rem; color:#475569; font-weight:700; }
        .summary-card .value { font-size:1.35rem; font-weight:800; margin-top:4px; color:#0f172a; }
        .card-dc { border-left-color:#2563eb; }
        .card-pension { border-left-color:#10b981; }
        .card-irp { border-left-color:#8b5cf6; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# 2. 포트폴리오 기본 데이터
# ==========================================
BASE_PORTFOLIO = {
    "dc": [
        {"구분": "주식", "ETF명": "TIGER 미국S&P500타겟데일리커버드콜", "코드": "482730", "목표비율": 0.20, "보유수량": 5440},
        {"구분": "주식", "ETF명": "TIGER 미국나스닥100타겟데일리커버드콜", "코드": "486290", "목표비율": 0.10, "보유수량": 4094},
        {"구분": "주식", "ETF명": "TIGER 미국배당다우존스타겟데일리커버드콜", "코드": "0008S0", "목표비율": 0.10, "보유수량": 3300},
        {"구분": "주식", "ETF명": "KODEX 200타겟위클리커버드콜", "코드": "498400", "목표비율": 0.15, "보유수량": 2131},
        {"구분": "리츠", "ETF명": "KODEX 한국부동산리츠인프라", "코드": "476800", "목표비율": 0.05, "보유수량": 0},
        {"구분": "채권", "ETF명": "TIGER 미국30년국채커버드콜액티브(H)", "코드": "476550", "목표비율": 0.30, "보유수량": 14611},
        {"구분": "실물", "ETF명": "ACE KRX금현물", "코드": "411060", "목표비율": 0.10, "보유수량": 1235},
        {"구분": "현금", "ETF명": "KODEX 미국머니마켓액티브", "코드": "0048J0", "목표비율": 0.00, "보유수량": 0},
        {"구분": "현금", "ETF명": "원화 현금", "코드": "", "목표비율": 0.00, "보유수량": 11241},
    ],
    "pension": [
        {"구분": "주식", "ETF명": "TIGER 미국S&P500타겟데일리커버드콜", "코드": "482730", "목표비율": 0.20, "보유수량": 2174},
        {"구분": "주식", "ETF명": "TIGER 미국나스닥100타겟데일리커버드콜", "코드": "486290", "목표비율": 0.10, "보유수량": 1596},
        {"구분": "주식", "ETF명": "TIGER 미국배당다우존스타겟데일리커버드콜", "코드": "0008S0", "목표비율": 0.10, "보유수량": 1320},
        {"구분": "주식", "ETF명": "KODEX 200타겟위클리커버드콜", "코드": "498400", "목표비율": 0.15, "보유수량": 834},
        {"구분": "리츠", "ETF명": "KODEX 한국부동산리츠인프라", "코드": "476800", "목표비율": 0.05, "보유수량": 0},
        {"구분": "채권", "ETF명": "TIGER 미국30년국채커버드콜액티브(H)", "코드": "476550", "목표비율": 0.30, "보유수량": 5770},
        {"구분": "실물", "ETF명": "ACE KRX금현물", "코드": "411060", "목표비율": 0.10, "보유수량": 505},
        {"구분": "현금", "ETF명": "KODEX 미국머니마켓액티브", "코드": "0048J0", "목표비율": 0.00, "보유수량": 0},
        {"구분": "현금", "ETF명": "원화 현금", "코드": "", "목표비율": 0.00, "보유수량": 5511},
    ],
    "irp": [
        {"구분": "주식", "ETF명": "TIGER 미국S&P500타겟데일리커버드콜", "코드": "482730", "목표비율": 0.20, "보유수량": 925},
        {"구분": "주식", "ETF명": "TIGER 미국나스닥100타겟데일리커버드콜", "코드": "486290", "목표비율": 0.10, "보유수량": 693},
        {"구분": "주식", "ETF명": "TIGER 미국배당다우존스타겟데일리커버드콜", "코드": "0008S0", "목표비율": 0.10, "보유수량": 565},
        {"구분": "주식", "ETF명": "KODEX 200타겟위클리커버드콜", "코드": "498400", "목표비율": 0.15, "보유수량": 375},
        {"구분": "리츠", "ETF명": "KODEX 한국부동산리츠인프라", "코드": "476800", "목표비율": 0.05, "보유수량": 0},
        {"구분": "채권", "ETF명": "TIGER 미국30년국채커버드콜액티브(H)", "코드": "476550", "목표비율": 0.30, "보유수량": 2499},
        {"구분": "실물", "ETF명": "ACE KRX금현물", "코드": "411060", "목표비율": 0.10, "보유수량": 212},
        {"구분": "현금", "ETF명": "KODEX 미국머니마켓액티브", "코드": "0048J0", "목표비율": 0.00, "보유수량": 0},
        {"구분": "현금", "ETF명": "원화 현금", "코드": "", "목표비율": 0.00, "보유수량": 7325},
    ],
}

ACCOUNT_LABELS = {"dc": "DC형 퇴직연금", "pension": "연금저축", "irp": "개인형 IRP"}
ACCOUNT_CSS = {"dc": "card-dc", "pension": "card-pension", "irp": "card-irp"}
CATEGORY_COLORS = {
    "주식": "#2563eb", "채권": "#f59e0b", "실물": "#eab308", "리츠": "#10b981", "현금": "#94a3b8",
}

# ==========================================
# 3. 세션 상태 초기화
# ==========================================
if "portfolio" not in st.session_state:
    portfolio = {}
    for key, items in BASE_PORTFOLIO.items():
        df = pd.DataFrame(items)
        df["현재가"] = df["코드"].apply(lambda c: 1 if c == "" else 0)
        portfolio[key] = df
    st.session_state.portfolio = portfolio

if "fetch_status" not in st.session_state:
    st.session_state.fetch_status = {"done": False, "success": 0, "total": 0}

# ==========================================
# 4. 실시간 시세 & 120일 이동평균 스크래핑
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

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ma120(code: str):
    if not code: return None
    closes = []
    try:
        with requests.Session() as s:
            s.headers.update(HEADERS)
            page = 1
            while len(closes) < 125 and page <= 14:
                url = f"https://finance.naver.com/item/sise_day.naver?code={code}&page={page}"
                res = s.get(url, timeout=3)
                soup = BeautifulSoup(res.text, "html.parser")
                rows = soup.select("table.type2 tr")
                got_row = False
                for row in rows:
                    tds = row.find_all("td")
                    if len(tds) >= 2:
                        date_span = tds[0].find("span")
                        price_span = tds[1].find("span")
                        if date_span and price_span and date_span.text.strip():
                            try:
                                closes.append(int(price_span.text.strip().replace(",", "")))
                                got_row = True
                            except ValueError:
                                continue
                if not got_row: break
                page += 1
                time.sleep(0.05)
    except Exception:
        pass
    if len(closes) < 20: return None
    window = closes[: min(120, len(closes))]
    return sum(window) / len(window)

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
# 5. 차트 렌더링 함수 & AgGrid 자바스크립트 코드
# ==========================================
def render_donut(cat_totals: dict, key: str):
    labels = [k for k, v in cat_totals.items() if v > 0]
    values = [v for v in cat_totals.values() if v > 0]
    colors = [CATEGORY_COLORS.get(l, "#cbd5e1") for l in labels]
    fig = go.Figure(
        data=[go.Pie(labels=labels, values=values, hole=0.55,
                     marker=dict(colors=colors, line=dict(color="#fff", width=2)),
                     textinfo="label+percent")]
    )
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300,
                      showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.15))
    st.plotly_chart(fig, width="stretch", key=f"chart_{key}")

color_jscode = JsCode("""
function(params) {
    var val = params.value;
    if (val === '주식') { return {'color': '#2563eb', 'fontWeight': 'bold', 'textAlign': 'center'}; }
    if (val === '채권') { return {'color': '#f59e0b', 'fontWeight': 'bold', 'textAlign': 'center'}; }
    if (val === '실물') { return {'color': '#eab308', 'fontWeight': 'bold', 'textAlign': 'center'}; }
    if (val === '리츠') { return {'color': '#10b981', 'fontWeight': 'bold', 'textAlign': 'center'}; }
    if (val === '현금') { return {'color': '#94a3b8', 'fontWeight': 'bold', 'textAlign': 'center'}; }
    return {'textAlign': 'center'};
}
""")

chart_link = JsCode("""
function(params) {
    if (params.value && params.value !== '') {
        return '<a href="' + params.value + '" target="_blank" style="text-decoration:none; color:#2563eb; font-weight:bold;">📊 열기</a>';
    }
    return '-';
}
""")

currency_fmt = JsCode("function(params) { return Number(params.value).toLocaleString() + ' 원'; }")
amount_fmt = JsCode("function(params) { return Number(params.value).toLocaleString() + ' 주'; }")

# ==========================================
# 6. 헤더 및 시세 호출
# ==========================================
header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.markdown('<div class="dash-header"><div><h1>📈 태봉의 연금자산 관리</h1></div></div>', unsafe_allow_html=True)

do_refresh = st.button("🔄 실시간 시세 강제 새로고침", width="content")

if do_refresh:
    fetch_current_price.clear()
    fetch_ma120.clear()
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
st.markdown("<hr style='margin:0.3rem 0; border-color:#e2e8f0;'>", unsafe_allow_html=True)

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
    
    def ma_tag(r):
        if not r["코드"]: return "-"
        ma = fetch_ma120(r["코드"])
        if ma is None or not r["현재가"]: return "미확인"
        return "🔥 상단" if r["현재가"] >= ma else "🧊 하단"

    df_calc["조정필요"] = df_calc.apply(rebalance_text, axis=1)
    df_calc["이평선(120일)"] = df_calc.apply(ma_tag, axis=1)
    df_calc["네이버차트"] = df_calc["코드"].apply(lambda c: f"https://finance.naver.com/item/fchart.naver?code={c}" if c else "")
    
    cat_totals = df_calc.groupby("구분")["평가금액"].sum().to_dict()
    computed[key] = (df_calc, total_eval, cat_totals)

summary_cols = st.columns(4)
with summary_cols[0]:
    st.markdown(f'<div class="summary-card"><label>총 연금 자산 평가액</label><div class="value">{grand_total:,.0f} 원</div></div>', unsafe_allow_html=True)
for i, key in enumerate(["dc", "pension", "irp"]):
    with summary_cols[i + 1]:
        st.markdown(f'<div class="summary-card {ACCOUNT_CSS[key]}"><label>{ACCOUNT_LABELS[key]}</label><div class="value">{computed[key][1]:,.0f} 원</div></div>', unsafe_allow_html=True)
st.markdown("<hr style='margin:0.3rem 0; border-color:#e2e8f0;'>", unsafe_allow_html=True)


# 헤더를 완벽하게 중앙 정렬하기 위한 커스텀 CSS 주입 선언
custom_css = {
    ".ag-header-cell-label": {"justify-content": "center !important"},
    ".ag-header-cell": {"text-align": "center !important"}
}


tabs = st.tabs([ACCOUNT_LABELS[k] for k in ["dc", "pension", "irp"]])
for tab, key in zip(tabs, ["dc", "pension", "irp"]):
    with tab:
        df_calc, total_eval, cat_totals = computed[key]
        st.markdown(f"### {ACCOUNT_LABELS[key]} 포트폴리오")
        
        display_df = df_calc[['구분', 'ETF명', '목표비율', '현재가', '보유수량', '평가금액', '현재비율', '이평선(120일)', '목표수량', '조정필요', '네이버차트']].copy()
        
        display_df['현재비율'] = display_df['현재비율'].apply(lambda x: f"{x:.1f}%")
        display_df['목표비율'] = display_df['목표비율'].apply(lambda x: f"{x * 100:.0f}%")
        display_df['평가금액'] = display_df['평가금액'].apply(lambda x: f"{x:,.0f} 원")
        display_df['목표수량'] = display_df['목표수량'].apply(lambda x: f"{x:,.0f} 주")

        gb = GridOptionsBuilder.from_dataframe(display_df)
        
        # 모든 데이터 셀 중앙 정렬
        gb.configure_default_column(cellStyle={'textAlign': 'center'})
        
        gb.configure_column("구분", cellStyle=color_jscode, width=90, editable=False)
        gb.configure_column("ETF명", width=280, editable=False)
        gb.configure_column("목표비율", width=100, editable=False)
        
        gb.configure_column("현재가", editable=True, type=["numericColumn"], valueFormatter=currency_fmt, width=120)
        gb.configure_column("보유수량", editable=True, type=["numericColumn"], valueFormatter=amount_fmt, width=120)
        
        gb.configure_column("평가금액", width=130, editable=False)
        gb.configure_column("현재비율", width=100, editable=False)
        gb.configure_column("이평선(120일)", width=110, editable=False)
        gb.configure_column("목표수량", width=120, editable=False)
        gb.configure_column("조정필요", width=140, editable=False)
        gb.configure_column("네이버차트", cellRenderer=chart_link, width=100, editable=False)

        gridOptions = gb.build()

        # AgGrid 렌더링 및 커스텀 CSS 적용
        grid_response = AgGrid(
            display_df,
            gridOptions=gridOptions,
            update_mode=GridUpdateMode.VALUE_CHANGED, 
            allow_unsafe_jscode=True, 
            theme='alpine', 
            custom_css=custom_css, # 바로 이 부분이 헤더 중앙 정렬을 강제합니다
            key=f"grid_{key}"
        )

        edited_data = grid_response['data']
        if edited_data is not None:
            if isinstance(edited_data, dict):
                edited_df = pd.DataFrame(edited_data)
            else:
                edited_df = edited_data
                
            if not edited_df.empty:
                new_prices = pd.to_numeric(edited_df["현재가"], errors='coerce').fillna(0).astype(int).values
                new_amounts = pd.to_numeric(edited_df["보유수량"], errors='coerce').fillna(0).astype(int).values
                
                orig_prices = st.session_state.portfolio[key]["현재가"].values
                orig_amounts = st.session_state.portfolio[key]["보유수량"].values
                
                if not (new_prices == orig_prices).all() or not (new_amounts == orig_amounts).all():
                    st.session_state.portfolio[key]["현재가"] = new_prices
                    st.session_state.portfolio[key]["보유수량"] = new_amounts
                    st.rerun()

        st.markdown(f"**{ACCOUNT_LABELS[key]} 자산 비중**")
        render_donut(cat_totals, key)
