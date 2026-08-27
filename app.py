import os
import json
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from bs4 import BeautifulSoup
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from st_aggrid.shared import JsCode  # JsCode 임포트 필수
import gspread
from google.oauth2.service_account import Credentials

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
            padding: 2px 10px !important; font-size: 0.75rem !important; min-height: 1.8rem !important;
        }
        div[data-testid="stButton"] button p { color: #ffffff !important; font-weight: 700 !important; font-size: 0.75rem !important; }
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
        .status-badge {
            font-size:0.78rem; padding:5px 14px; border-radius:14px; font-weight:700;
            white-space:nowrap; display:inline-flex; align-items:center; gap:5px;
            letter-spacing:0.2px; box-shadow:0 2px 6px rgba(0,0,0,0.25); border:1px solid rgba(255,255,255,0.08);
        }
        .status-loading { background:#78350f; color:#fef3c7; }
        .status-success { background:#065f46; color:#d1fae5; }
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            display: flex; gap: 4px; border-bottom: 1px solid #334155;
            padding-bottom: 0; align-items: center;
        }
        div[data-testid="stRadio"] > div[role="radiogroup"]::before {
            content: "🎈 포트폴리오";
            font-size: 1.05rem; font-weight: 800; color: #f8fafc;
            margin-right: 24px; white-space: nowrap;
        }
        div[data-testid="stRadio"] label { margin: 0 !important; }
        div[data-testid="stRadio"] label > div:first-child { display: none; }
        div[data-testid="stRadio"] label > div:last-child {
            padding: 10px 16px !important; font-size: 0.95rem !important;
            font-weight: 700 !important; color: #94a3b8 !important;
            border-bottom: 2px solid transparent; cursor: pointer;
        }
        div[data-testid="stRadio"] label:has(input:checked) > div:last-child {
            color: #ef4444 !important; border-bottom: 2px solid #ef4444;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# 1-2. AgGrid 렌더러 안전 JS 설정 (차트 버튼)
# ==========================================
chart_button_jscode = JsCode("""
class BtnCellRenderer {
    init(params) {
        // 컨테이너를 Flex로 설정하여 완벽한 중앙 정렬
        this.eGui = document.createElement('div');
        this.eGui.style.display = 'flex';
        this.eGui.style.alignItems = 'center';
        this.eGui.style.justifyContent = 'center';
        this.eGui.style.height = '100%'; 
        this.eGui.style.width = '100%';
        
        if (params.value && params.value !== '') {
            this.eButton = document.createElement('a');
            this.eButton.innerText = '📊 차트';
            this.eButton.href = params.value;
            this.eButton.target = '_blank';
            
            // 버튼 디자인 세련되게 다듬기
            this.eButton.style.display = 'inline-flex';
            this.eButton.style.alignItems = 'center';
            this.eButton.style.justifyContent = 'center';
            this.eButton.style.padding = '4px 8px';
            this.eButton.style.backgroundColor = '#3b82f6';
            this.eButton.style.color = '#ffffff';
            this.eButton.style.textDecoration = 'none';
            this.eButton.style.borderRadius = '4px';
            this.eButton.style.fontWeight = '600';
            this.eButton.style.fontSize = '11px';
            this.eButton.style.lineHeight = '1';
            this.eButton.style.cursor = 'pointer';
            this.eButton.style.boxShadow = '0 1px 3px rgba(0,0,0,0.2)';
            this.eButton.style.transition = 'all 0.15s ease-in-out';
            
            // 호버 및 클릭(Press) 애니메이션 효과
            this.eButton.addEventListener('mouseenter', () => { 
                this.eButton.style.backgroundColor = '#1d4ed8'; 
                this.eButton.style.boxShadow = '0 2px 4px rgba(0,0,0,0.3)';
            });
            this.eButton.addEventListener('mouseleave', () => { 
                this.eButton.style.backgroundColor = '#3b82f6'; 
                this.eButton.style.boxShadow = '0 1px 3px rgba(0,0,0,0.2)';
            });
            this.eButton.addEventListener('mousedown', () => {
                this.eButton.style.transform = 'scale(0.92)';
            });
            this.eButton.addEventListener('mouseup', () => {
                this.eButton.style.transform = 'scale(1)';
            });
            
            this.eGui.appendChild(this.eButton);
        }
    }
    getGui() { return this.eGui; }
}
""")

# ==========================================
# 1-3. 표 색상 강조 / 단위 포맷 JS (차트 버튼과 무관한 별도 렌더러)
# ==========================================
color_jscode = JsCode("""
function(params) {
    if (!params.value) return {'textAlign': 'center', 'color': '#000'};
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
    if (!params.value) return {'textAlign': 'center', 'color': '#64748b'};
    var val = params.value;
    if (val === '상단') { return {'color': '#dc2626', 'fontWeight': 'bold', 'textAlign': 'center'}; }
    if (val === '하단') { return {'color': '#2563eb', 'fontWeight': 'bold', 'textAlign': 'center'}; }
    return {'textAlign': 'center', 'color': '#64748b'};
}
""")

currency_fmt = JsCode("function(params) { return params.value != null ? Number(params.value).toLocaleString() + ' 원' : ''; }")
amount_fmt = JsCode("function(params) { return params.value != null ? Number(params.value).toLocaleString() + ' 주' : ''; }")

# 평가금액 = 현재가 x 보유수량을 같은 행 데이터만으로 실시간 계산 (엔터를 누르지 않아도 즉시 반영됨)
eval_amount_getter = JsCode("""
function(params) {
    var price = Number(params.data.현재가) || 0;
    var qty = Number(params.data.보유수량) || 0;
    return (price * qty).toLocaleString() + ' 원';
}
""")

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

SHEET_COLS = ["구분", "ETF명", "코드", "목표비율", "보유수량", "이평선"]

# ==========================================
# 2-1. Google Sheets 연동
# ==========================================
import pathlib
_SECRETS_PATHS = [
    pathlib.Path(".streamlit/secrets.toml"),
    pathlib.Path.home() / ".streamlit" / "secrets.toml",
]
_secrets_file_exists = any(p.exists() for p in _SECRETS_PATHS)

if _secrets_file_exists:
    try:
        GSHEET_ENABLED = "gcp_service_account" in st.secrets and "gsheet_url" in st.secrets
    except Exception:
        GSHEET_ENABLED = False
else:
    GSHEET_ENABLED = False

@st.cache_resource(show_spinner=False)
def get_gsheet():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    gc = gspread.authorize(creds)
    return gc.open_by_url(st.secrets["gsheet_url"])

def _worksheet_to_df(ws, key):
    records = ws.get_all_records()
    if not records:
        raise ValueError("empty sheet")
    df = pd.DataFrame(records)
    df["코드"] = df["코드"].astype(str)
    df["목표비율"] = df["목표비율"].astype(float)
    df["보유수량"] = df["보유수량"].astype(int)
    return df

def _ensure_worksheet(sh, key):
    try:
        ws = sh.worksheet(key)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=key, rows=20, cols=len(SHEET_COLS))
    df = pd.DataFrame(DEFAULT_PORTFOLIO[key])
    ws.clear()
    ws.update(values=[SHEET_COLS] + df[SHEET_COLS].values.tolist())
    return df

def load_portfolio_from_gsheet():
    sh = get_gsheet()
    portfolio = {}
    for key in DEFAULT_PORTFOLIO.keys():
        try:
            ws = sh.worksheet(key)
            df = _worksheet_to_df(ws, key)
        except (gspread.exceptions.WorksheetNotFound, ValueError):
            df = _ensure_worksheet(sh, key)
        df["현재가"] = df["코드"].apply(lambda c: 1 if c == "" else 0)
        portfolio[key] = df
    return portfolio

def save_portfolio_to_gsheet(portfolio_dict):
    sh = get_gsheet()
    for key, df in portfolio_dict.items():
        ws = sh.worksheet(key)
        sub_df = df[SHEET_COLS].copy()
        ws.clear()
        result = ws.update(values=[SHEET_COLS] + sub_df.values.tolist())
        if not result:
            raise RuntimeError(f"'{key}' 시트 저장 응답이 비어있습니다.")

# ==========================================
# 2-2. 로컬 파일 저장
# ==========================================
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

def load_portfolio():
    if GSHEET_ENABLED:
        try:
            return load_portfolio_from_gsheet(), "gsheet"
        except Exception as e:
            st.warning(f"⚠️ Google Sheets 연결 실패로 로컬 저장 방식으로 전환합니다: {e}")
    return load_portfolio_from_file(), "file"

def save_portfolio(portfolio_dict, mode):
    if mode == "gsheet":
        try:
            save_portfolio_to_gsheet(portfolio_dict)
            st.session_state["last_save_error"] = None
            return
        except Exception as e:
            st.session_state["last_save_error"] = str(e)
    save_portfolio_to_file(portfolio_dict)

ACCOUNT_LABELS = {"dc": "DC형 퇴직연금", "pension": "연금저축", "irp": "개인형 IRP"}
ACCOUNT_CSS = {"dc": "card-dc", "pension": "card-pension", "irp": "card-irp"}
CATEGORY_COLORS = {"주식": "#60a5fa", "채권": "#fb923c", "실물": "#facc15", "리츠": "#34d399", "현금": "#cbd5e1"}

if "portfolio" not in st.session_state:
    st.session_state.portfolio, st.session_state.storage_mode = load_portfolio()
if "fetch_status" not in st.session_state:
    st.session_state.fetch_status = {"done": False, "success": 0, "total": 0}

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


# 헤더 및 시세 호출
header_col1, _ = st.columns([4, 1])
with header_col1:
    st.markdown("<h1 style='font-size:2.8rem; font-weight:800; color:#ffffff; margin-top: 5px; margin-bottom: 20px; line-height: 1.4;'>📈 태봉의 연금자산 관리</h1>", unsafe_allow_html=True)

storage_badge = (
    '<span class="status-badge status-success">✅ Sheets 연동됨</span>'
    if st.session_state.storage_mode == "gsheet"
    else '<span class="status-badge status-loading">💾 로컬 저장 모드</span>'
)

col_btn, col_spacer, col_badges = st.columns([1.4, 3.6, 3], gap="small")

with col_btn:
    do_refresh = st.button("🔄 시세 새로고침", use_container_width=False)

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
    status_badge = '<span class="status-badge status-loading">🌐 대기 중</span>'
elif status["success"] == status["total"]:
    status_badge = f'<span class="status-badge status-success">✅ 시세 연동 성공 ({status["success"]}/{status["total"]})</span>'
else:
    status_badge = f'<span class="status-badge status-loading">⚠️ 일부 연동 성공 ({status["success"]}/{status["total"]})</span>'

with col_badges:
    st.markdown(
        f'<div style="display:flex; justify-content:flex-end; gap:8px; padding-top:6px;">{storage_badge}{status_badge}</div>',
        unsafe_allow_html=True,
    )

if st.session_state.get("last_save_error"):
    st.error(f"⚠️ 최근 수정사항이 Google Sheets에 저장되지 못했습니다 (로컬에만 임시 저장됨): {st.session_state['last_save_error']}")
elif st.session_state.get("last_save_ok"):
    st.success(f"✅ {st.session_state['last_save_ok']}")
elif st.session_state.get("last_no_change_debug"):
    debug_text = st.session_state["last_no_change_debug"]
    summary, _, detail = debug_text.partition(" | ")
    st.info(f"ℹ️ {summary} (수정한 값이 기존 값과 같거나, 편집이 셀에 반영되기 전에 다른 동작이 발생했을 수 있습니다)")
    if detail:
        with st.expander("비교 상세 로그 보기"):
            st.code(detail.replace(" / ", "\n"))

st.markdown("<hr style='margin:0.3rem 0; border-color:#334155;'>", unsafe_allow_html=True)

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

account_keys = ["dc", "pension", "irp"]
label_to_key = {ACCOUNT_LABELS[k]: k for k in account_keys}
selected_label = st.radio(
    "포트폴리오 계좌 선택",
    list(label_to_key.keys()),
    horizontal=True,
    label_visibility="collapsed",
    key="account_selector",
)
selected_key = label_to_key[selected_label]

for key in [selected_key]:
    df_calc, total_eval, cat_totals = computed[key]
        
    display_df = df_calc[['구분', 'ETF명', '목표비율', '현재가', '보유수량', '평가금액', '현재비율', '이평선', '목표수량', '조정필요', '차트']].copy()
    
    display_df['현재비율'] = display_df['현재비율'].apply(lambda x: f"{x:.1f}%")
    display_df['목표비율'] = display_df['목표비율'].apply(lambda x: f"{x * 100:.0f}%")
    display_df['평가금액'] = display_df['평가금액'].apply(lambda x: f"{x:,.0f} 원")
    display_df['목표수량'] = display_df['목표수량'].apply(lambda x: f"{x:,.0f} 주")

    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_default_column(cellStyle={'textAlign': 'center', 'color': '#000000'}, resizable=True)
    
    gb.configure_column("구분", cellStyle=color_jscode, width=80, editable=False)
    gb.configure_column("ETF명", width=300, editable=False, cellStyle={'textAlign': 'left', 'color': '#000000', 'fontWeight': '600'})
    gb.configure_column("목표비율", width=95, editable=False)
    gb.configure_column("현재가", editable=True, type=["numericColumn"], valueFormatter=currency_fmt, width=115, cellStyle={'textAlign': 'right', 'color': '#000000'})
    gb.configure_column("보유수량", editable=True, type=["numericColumn"], valueFormatter=amount_fmt, width=110, cellStyle={'textAlign': 'right', 'color': '#000000'})
    gb.configure_column("평가금액", width=140, editable=False, valueGetter=eval_amount_getter, cellStyle={'textAlign': 'right', 'color': '#000000'})
    gb.configure_column("현재비율", width=95, editable=False)
        
    gb.configure_column(
        "이평선", 
        editable=True, 
        cellEditor="agSelectCellEditor", 
        cellEditorParams={"values": ["상단", "하단", "-"]}, 
        cellStyle=ma_color_jscode,
        width=95
    )
        
    gb.configure_column("목표수량", width=110, editable=False, cellStyle={'textAlign': 'right', 'color': '#000000'})
    gb.configure_column("조정필요", width=175, editable=False, cellStyle={'textAlign': 'left', 'color': '#000000'})
    
    # 세련된 클래스형 커스텀 렌더러 적용
    gb.configure_column("차트", width=95, editable=False, cellRenderer=chart_button_jscode)

    gridOptions = gb.build()

    # 표 헤더(구분, ETF명 등) 텍스트를 모두 중앙정렬
    custom_css = {
        ".ag-header-cell-label": {"justify-content": "center"},
    }

    try:
        grid_response = AgGrid(
            display_df,
            gridOptions=gridOptions,
            update_mode=GridUpdateMode.VALUE_CHANGED | GridUpdateMode.MODEL_CHANGED,
            data_return_mode=DataReturnMode.AS_INPUT,
            theme='alpine', 
            fit_columns_on_grid_load=False,
            allow_unsafe_jscode=True,  # 버튼 렌더러를 위해 활성화
            custom_css=custom_css,
            key=f"grid_{key}_{st.session_state.get('data_version', 0)}"
        )

        edited_data = grid_response['data']
        if edited_data is not None:
            if isinstance(edited_data, dict):
                edited_df = pd.DataFrame(edited_data)
                # dict 형태({"컬럼": {"0": 값, "1": 값, ...}})로 오면 인덱스가 문자열로 잡히므로
                # 원래 세션 데이터와 같은 정수 인덱스로 맞춰준다.
                try:
                    edited_df.index = edited_df.index.astype(int)
                except (ValueError, TypeError):
                    edited_df = edited_df.reset_index(drop=True)
            elif isinstance(edited_data, list):
                edited_df = pd.DataFrame(edited_data)
            else:
                edited_df = edited_data
                if hasattr(edited_df, "reset_index"):
                    edited_df = edited_df.reset_index(drop=True)
                    
            if not edited_df.empty:
                def clean_numeric(val):
                    if pd.isna(val): return 0
                    s = str(val).replace(',', '').replace('원', '').replace('주', '').replace('%', '').strip()
                    try: return float(s)
                    except ValueError: return 0

                has_changes = False
                compare_log = []
                
                for idx, row in edited_df.iterrows():
                    new_price = int(clean_numeric(row["현재가"]))
                    new_amount = int(clean_numeric(row["보유수량"]))
                    new_ma = row["이평선"]
                    
                    orig_price = st.session_state.portfolio[key].at[idx, "현재가"]
                    orig_amount = st.session_state.portfolio[key].at[idx, "보유수량"]
                    orig_ma = st.session_state.portfolio[key].at[idx, "이평선"]

                    compare_log.append(
                        f"행{idx}: 보유수량 {orig_amount}→{new_amount}, 현재가 {orig_price}→{new_price}, 이평선 {orig_ma}→{new_ma}"
                    )
                    
                    if new_price != orig_price or new_amount != orig_amount or new_ma != orig_ma:
                        has_changes = True
                        st.session_state.portfolio[key].at[idx, "현재가"] = new_price
                        st.session_state.portfolio[key].at[idx, "보유수량"] = new_amount
                        st.session_state.portfolio[key].at[idx, "이평선"] = new_ma
                        
                        if new_ma != orig_ma:
                            etf_name = row["ETF명"]
                            for other_k in st.session_state.portfolio.keys():
                                if other_k != key:
                                    mask = st.session_state.portfolio[other_k]["ETF명"] == etf_name
                                    if mask.any():
                                        st.session_state.portfolio[other_k].loc[mask, "이평선"] = new_ma
                
                if has_changes:
                    st.session_state["data_version"] = st.session_state.get("data_version", 0) + 1
                    save_portfolio(st.session_state.portfolio, st.session_state.storage_mode)
                    if st.session_state.get("last_save_error") is None:
                        st.session_state["last_save_ok"] = f"'{ACCOUNT_LABELS[key]}' 계좌 저장 완료 (모드: {st.session_state.storage_mode})"
                    else:
                        st.session_state["last_save_ok"] = None
                    st.rerun()
                else:
                    st.session_state["last_save_ok"] = None
                    st.session_state["last_save_error"] = None
                    st.session_state["last_no_change_debug"] = (
                        f"편집 이벤트는 감지됐지만 값 변화가 없다고 판단됨 (계좌: {ACCOUNT_LABELS[key]}) | "
                        + " / ".join(compare_log)
                    )
                        
    except Exception as e:
        st.error(f"표를 렌더링하는 중 에러가 발생했습니다: {e}")

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
