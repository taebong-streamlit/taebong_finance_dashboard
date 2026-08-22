"""
연금계좌 자산배분 & 실시간 리밸런싱 대시보드 (Streamlit)
- 네이버 금융 실시간 시세 + 120일 이동평균선 실계산
- 계좌(DC/연금저축/IRP)별 탭, 편집 가능한 표, 도넛 차트
필요 패키지: streamlit pandas requests beautifulsoup4 plotly lxml
설치: pip install streamlit pandas requests beautifulsoup4 plotly lxml
실행: streamlit run app.py
"""

import time
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from bs4 import BeautifulSoup

# ==========================================
# 0. 페이지 기본 설정
# ==========================================
st.set_page_config(page_title="연금 리밸런싱 대시보드", page_icon="📈", layout="wide")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ==========================================
# 1. 스타일 (HTML 버전 톤앤매너 재현)
# ==========================================
st.markdown(
    """
    <style>
        .block-container { padding-top: 1.5rem; max-width: 1400px; }
        .dash-header {
            display:flex; justify-content:space-between; align-items:center;
            background:#fff; padding:20px 28px; border-radius:16px;
            box-shadow:0 4px 6px -1px rgba(0,0,0,0.05); border:1px solid #e2e8f0;
            margin-bottom:18px;
        }
        .dash-header h1 { font-size:1.4rem; font-weight:700; color:#0f172a; margin:0; }
        .dash-header p { font-size:0.85rem; color:#475569; margin:4px 0 0 0; }
        .status-badge {
            font-size:0.82rem; padding:6px 14px; border-radius:20px; font-weight:600;
        }
        .status-loading { background:#fef9c3; color:#854d0e; }
        .status-success { background:#dcfce7; color:#166534; }
        .status-manual { background:#fee2e2; color:#991b1b; }
        .summary-card {
            background:#fff; padding:18px 22px; border-radius:14px;
            box-shadow:0 2px 4px rgba(0,0,0,0.03); border:1px solid #e2e8f0;
            border-left:5px solid #2563eb; margin-bottom:10px;
        }
        .summary-card label { font-size:0.8rem; color:#475569; font-weight:600; text-transform:uppercase; }
        .summary-card .value { font-size:1.35rem; font-weight:800; margin-top:6px; color:#0f172a; }
        .card-dc { border-left-color:#2563eb; }
        .card-pension { border-left-color:#10b981; }
        .card-irp { border-left-color:#8b5cf6; }
        .source-info { margin-top:18px; text-align:center; font-size:0.8rem; color:#94a3b8; }
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
        {"구분": "주식", "ETF명": "TIGER 미국나스닥100타겟데일리커버드콜", "코드": "486290", "목표비율": 0.15, "보유수량": 4094},
        {"구분": "주식", "ETF명": "TIGER 미국배당다우존스타겟데일리커버드콜", "코드": "0008S0", "목표비율": 0.10, "보유수량": 3300},
        {"구분": "주식", "ETF명": "KODEX 200타겟위클리커버드콜", "코드": "498400", "목표비율": 0.15, "보유수량": 2131},
        {"구분": "채권", "ETF명": "TIGER 미국30년국채커버드콜액티브(H)", "코드": "476550", "목표비율": 0.30, "보유수량": 14611},
        {"구분": "실물", "ETF명": "ACE KRX금현물", "코드": "411060", "목표비율": 0.10, "보유수량": 1235},
        {"구분": "현금", "ETF명": "KODEX 미국머니마켓액티브", "코드": "0048J0", "목표비율": 0.00, "보유수량": 0},
        {"구분": "현금", "ETF명": "원화 현금", "코드": "", "목표비율": 0.00, "보유수량": 11241},
    ],
    "pension": [
        {"구분": "주식", "ETF명": "TIGER 미국S&P500타겟데일리커버드콜", "코드": "482730", "목표비율": 0.20, "보유수량": 2174},
        {"구분": "주식", "ETF명": "TIGER 미국나스닥100타겟데일리커버드콜", "코드": "486290", "목표비율": 0.15, "보유수량": 1596},
        {"구분": "주식", "ETF명": "TIGER 미국배당다우존스타겟데일리커버드콜", "코드": "0008S0", "목표비율": 0.10, "보유수량": 1320},
        {"구분": "주식", "ETF명": "KODEX 200타겟위클리커버드콜", "코드": "498400", "목표비율": 0.15, "보유수량": 834},
        {"구분": "채권", "ETF명": "TIGER 미국30년국채커버드콜액티브(H)", "코드": "476550", "목표비율": 0.30, "보유수량": 5770},
        {"구분": "실물", "ETF명": "ACE KRX금현물", "코드": "411060", "목표비율": 0.10, "보유수량": 505},
        {"구분": "현금", "ETF명": "KODEX 미국머니마켓액티브", "코드": "0048J0", "목표비율": 0.00, "보유수량": 0},
        {"구분": "현금", "ETF명": "원화 현금", "코드": "", "목표비율": 0.00, "보유수량": 5511},
    ],
    "irp": [
        {"구분": "주식", "ETF명": "TIGER 미국S&P500타겟데일리커버드콜", "코드": "482730", "목표비율": 0.20, "보유수량": 925},
        {"구분": "주식", "ETF명": "TIGER 미국나스닥100타겟데일리커버드콜", "코드": "486290", "목표비율": 0.15, "보유수량": 693},
        {"구분": "주식", "ETF명": "TIGER 미국배당다우존스타겟데일리커버드콜", "코드": "0008S0", "목표비율": 0.10, "보유수량": 565},
        {"구분": "주식", "ETF명": "KODEX 200타겟위클리커버드콜", "코드": "498400", "목표비율": 0.15, "보유수량": 375},
        {"구분": "채권", "ETF명": "TIGER 미국30년국채커버드콜액티브(H)", "코드": "476550", "목표비율": 0.30, "보유수량": 2499},
        {"구분": "실물", "ETF명": "ACE KRX금현물", "코드": "411060", "목표비율": 0.10, "보유수량": 212},
        {"구분": "현금", "ETF명": "KODEX 미국머니마켓액티브", "코드": "0048J0", "목표비율": 0.00, "보유수량": 0},
        {"구분": "현금", "ETF명": "원화 현금", "코드": "", "목표비율": 0.00, "보유수량": 7325},
    ],
}

ACCOUNT_LABELS = {"dc": "DC형 퇴직연금", "pension": "연금저축", "irp": "개인형 IRP"}
ACCOUNT_CSS = {"dc": "card-dc", "pension": "card-pension", "irp": "card-irp"}
CATEGORY_COLORS = {"주식": "#2563eb", "채권": "#f59e0b", "실물": "#eab308", "현금": "#94a3b8"}

# ==========================================
# 3. 세션 상태 초기화 (현재가/보유수량은 수정 가능해야 하므로 세션에 보관)
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
    """네이버 금융에서 현재가를 가져온다. 실패 시 None."""
    if not code:
        return 1
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=3)
        soup = BeautifulSoup(res.text, "html.parser")
        no_today = soup.find("p", class_="no_today")
        if no_today:
            price_str = no_today.find("span", class_="blind").text
            return int(price_str.replace(",", ""))
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ma120(code: str):
    """네이버 일별시세 페이지를 여러 장 긁어서 120일 단순이동평균을 계산한다."""
    if not code:
        return None
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
                if not got_row:
                    break
                page += 1
                time.sleep(0.05)
    except Exception:
        pass
    if len(closes) < 20:
        return None
    window = closes[: min(120, len(closes))]
    return sum(window) / len(window)


def fetch_all_prices(codes: list[str]):
    prices, success = {}, 0
    for code in codes:
        p = fetch_current_price(code)
        prices[code] = p
        if p is not None:
            success += 1
    return prices, success


def get_unique_codes():
    codes = set()
    for df in st.session_state.portfolio.values():
        codes.update(c for c in df["코드"].tolist() if c)
    return sorted(codes)


# ==========================================
# 5. 계산 로직 (평가금액 / 목표수량 / 조정필요 / 이평선 태그)
# ==========================================
def compute_table(df: pd.DataFrame) -> tuple[pd.DataFrame, float, dict]:
    df = df.copy()
    df["평가금액"] = df["현재가"] * df["보유수량"]
    total_eval = df["평가금액"].sum()

    df["현재비율"] = (df["평가금액"] / total_eval * 100).fillna(0) if total_eval else 0
    df["목표금액"] = total_eval * df["목표비율"]
    df["목표수량"] = df.apply(
        lambda r: round(r["목표금액"] / r["현재가"]) if r["현재가"] and r["현재가"] > 1 else 0, axis=1
    )
    df["조정수량"] = df["목표수량"] - df["보유수량"]

    def rebalance_text(r):
        if r["코드"] == "" or r["목표비율"] == 0:
            return "-"
        if r["조정수량"] > 0:
            return f"🔴 +{r['조정수량']:,.0f}주 매수"
        if r["조정수량"] < 0:
            return f"🔵 {r['조정수량']:,.0f}주 매도"
        return "유지"

    df["조정필요"] = df.apply(rebalance_text, axis=1)

    def ma_tag(r):
        if not r["코드"]:
            return "-"
        ma = fetch_ma120(r["코드"])
        if ma is None or not r["현재가"]:
            return "미확인"
        return "🔴 상단" if r["현재가"] >= ma else "🔵 하단"

    df["이평선(120일)"] = df.apply(ma_tag, axis=1)
    df["네이버차트"] = df["코드"].apply(
        lambda c: f"https://finance.naver.com/item/fchart.naver?code={c}" if c else ""
    )

    cat_totals = df.groupby("구분")["평가금액"].sum().to_dict()
    return df, total_eval, cat_totals


def render_donut(cat_totals: dict, key: str):
    labels = [k for k, v in cat_totals.items() if v > 0]
    values = [v for v in cat_totals.values() if v > 0]
    colors = [CATEGORY_COLORS.get(l, "#cbd5e1") for l in labels]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=colors, line=dict(color="#fff", width=2)),
                textinfo="label+percent",
            )
        ]
    )
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        height=300,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{key}")


# ==========================================
# 6. 헤더 + 새로고침
# ==========================================
header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.markdown(
        """
        <div class="dash-header">
            <div>
                <h1>📈 연금계좌 자산배분 & 실시간 리밸런싱 대시보드</h1>
                <p>네이버 금융 실시간 시세 및 120일 이동평균선 기반</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

do_refresh = st.button("🔄 실시간 시세 강제 새로고침", use_container_width=False)
status_placeholder = st.empty()

if do_refresh:
    fetch_current_price.clear()
    fetch_ma120.clear()
    st.session_state.fetch_status["done"] = False

if not st.session_state.fetch_status["done"] or do_refresh:
    codes = get_unique_codes()
    with st.spinner("실시간 시세를 불러오는 중입니다..."):
        prices, success = fetch_all_prices(codes)
        for key, df in st.session_state.portfolio.items():
            df["현재가"] = df.apply(
                lambda r: prices.get(r["코드"], r["현재가"]) if r["코드"] else 1, axis=1
            )
        st.session_state.fetch_status = {"done": True, "success": success, "total": len(codes)}

status = st.session_state.fetch_status
if status["total"] == 0:
    badge_html = '<span class="status-badge status-loading">🌐 대기 중</span>'
elif status["success"] == status["total"]:
    badge_html = f'<span class="status-badge status-success">✅ 시세 연동 성공 ({status["success"]}/{status["total"]})</span>'
elif status["success"] > 0:
    badge_html = f'<span class="status-badge status-loading">⚠️ 일부 연동 성공 ({status["success"]}/{status["total"]})</span>'
else:
    badge_html = '<span class="status-badge status-manual">⚠️ 실시간 연동 실패 (직접입력 모드)</span>'
status_placeholder.markdown(badge_html, unsafe_allow_html=True)

st.divider()

# ==========================================
# 7. 요약 카드 (전체 계산 먼저 수행)
# ==========================================
computed = {}
grand_total = 0
for key, df in st.session_state.portfolio.items():
    result_df, total_eval, cat_totals = compute_table(df)
    computed[key] = (result_df, total_eval, cat_totals)
    grand_total += total_eval

summary_cols = st.columns(4)
with summary_cols[0]:
    st.markdown(
        f'<div class="summary-card"><label>총 연금 자산 평가액</label>'
        f'<div class="value">{grand_total:,.0f} 원</div></div>',
        unsafe_allow_html=True,
    )
for i, key in enumerate(["dc", "pension", "irp"]):
    with summary_cols[i + 1]:
        total_eval = computed[key][1]
        st.markdown(
            f'<div class="summary-card {ACCOUNT_CSS[key]}"><label>{ACCOUNT_LABELS[key]}</label>'
            f'<div class="value">{total_eval:,.0f} 원</div></div>',
            unsafe_allow_html=True,
        )

st.divider()

# ==========================================
# 8. 탭별 표 + 도넛 차트
# ==========================================
tabs = st.tabs([ACCOUNT_LABELS[k] for k in ["dc", "pension", "irp"]])

DISPLAY_COLS = [
    "구분", "ETF명", "코드", "목표비율", "현재가", "보유수량",
    "평가금액", "현재비율", "이평선(120일)", "목표수량", "조정필요", "네이버차트",
]

for tab, key in zip(tabs, ["dc", "pension", "irp"]):
    with tab:
        result_df, total_eval, cat_totals = computed[key]
        st.subheader(f"{ACCOUNT_LABELS[key]} 포트폴리오")

        table_col, chart_col = st.columns([3.2, 1])
        with table_col:
            edited_df = st.data_editor(
                result_df[DISPLAY_COLS],
                use_container_width=True,
                hide_index=True,
                key=f"editor_{key}",
                column_config={
                    "구분": st.column_config.TextColumn("구분", disabled=True),
                    "ETF명": st.column_config.TextColumn("ETF명", disabled=True, width="medium"),
                    "코드": st.column_config.TextColumn("코드", disabled=True),
                    "목표비율": st.column_config.NumberColumn("목표비율", disabled=True, format="%.0f%%"),
                    "현재가": st.column_config.NumberColumn("현재가(원)", min_value=0, step=1, format="%d"),
                    "보유수량": st.column_config.NumberColumn("보유수량", min_value=0, step=1, format="%d"),
                    "평가금액": st.column_config.NumberColumn("평가금액(원)", disabled=True, format="%d"),
                    "현재비율": st.column_config.NumberColumn("현재비율", disabled=True, format="%.1f%%"),
                    "이평선(120일)": st.column_config.TextColumn("이평선(120일)", disabled=True),
                    "목표수량": st.column_config.NumberColumn("목표수량", disabled=True, format="%d"),
                    "조정필요": st.column_config.TextColumn("조정필요", disabled=True, width="medium"),
                    "네이버차트": st.column_config.LinkColumn(
                        "네이버 차트", display_text="📊 차트보기", width="small"
                    ),
                },
            )

            # 사용자가 현재가/보유수량을 직접 수정한 경우 세션에 반영
            if not edited_df[["현재가", "보유수량"]].equals(result_df[["현재가", "보유수량"]]):
                st.session_state.portfolio[key]["현재가"] = edited_df["현재가"].values
                st.session_state.portfolio[key]["보유수량"] = edited_df["보유수량"].values
                st.rerun()

        with chart_col:
            st.markdown(f"**{ACCOUNT_LABELS[key]} 자산 비중**")
            render_donut(cat_totals, key)

st.markdown(
    '<div class="source-info">시세 제공 데이터: 네이버 금융 스크래핑 (현재가 · 120일 이동평균) | '
    "차트 링크: 네이버 종합차트 연동</div>",
    unsafe_allow_html=True,
)
