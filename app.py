import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# ==========================================
# 0. 페이지 기본 설정 (가장 위에 위치해야 함)
# ==========================================
st.set_page_config(page_title="연금 리밸런싱 대시보드", page_icon="📈", layout="wide")

# ==========================================
# 1. 포트폴리오 기본 데이터
# ==========================================
portfolio_data = {
    'DC형 퇴직연금': [
        {"구분": "주식", "ETF명": "TIGER 미국S&P500타겟데일리커버드콜", "코드": "482730", "목표비율": 0.20, "보유수량": 5440},
        {"구분": "주식", "ETF명": "TIGER 미국나스닥100타겟데일리커버드콜", "코드": "486290", "목표비율": 0.15, "보유수량": 4094},
        {"구분": "주식", "ETF명": "TIGER 미국배당다우존스타겟데일리커버드콜", "코드": "0008S0", "목표비율": 0.10, "보유수량": 3300},
        {"구분": "주식", "ETF명": "KODEX 200타겟위클리커버드콜", "코드": "498400", "목표비율": 0.15, "보유수량": 2131},
        {"구분": "채권", "ETF명": "TIGER 미국30년국채커버드콜액티브(H)", "코드": "476550", "목표비율": 0.30, "보유수량": 14611},
        {"구분": "실물", "ETF명": "ACE KRX금현물", "코드": "411060", "목표비율": 0.10, "보유수량": 1235},
        {"구분": "현금", "ETF명": "KODEX 미국머니마켓액티브", "코드": "0048J0", "목표비율": 0.00, "보유수량": 0},
        {"구분": "현금", "ETF명": "원화 현금", "코드": "", "목표비율": 0.00, "보유수량": 11241}
    ],
    '연금저축': [
        {"구분": "주식", "ETF명": "TIGER 미국S&P500타겟데일리커버드콜", "코드": "482730", "목표비율": 0.20, "보유수량": 2174},
        {"구분": "주식", "ETF명": "TIGER 미국나스닥100타겟데일리커버드콜", "코드": "486290", "목표비율": 0.15, "보유수량": 1596},
        {"구분": "주식", "ETF명": "TIGER 미국배당다우존스타겟데일리커버드콜", "코드": "0008S0", "목표비율": 0.10, "보유수량": 1320},
        {"구분": "주식", "ETF명": "KODEX 200타겟위클리커버드콜", "코드": "498400", "목표비율": 0.15, "보유수량": 834},
        {"구분": "채권", "ETF명": "TIGER 미국30년국채커버드콜액티브(H)", "코드": "476550", "목표비율": 0.30, "보유수량": 5770},
        {"구분": "실물", "ETF명": "ACE KRX금현물", "코드": "411060", "목표비율": 0.10, "보유수량": 505},
        {"구분": "현금", "ETF명": "KODEX 미국머니마켓액티브", "코드": "0048J0", "목표비율": 0.00, "보유수량": 0},
        {"구분": "현금", "ETF명": "원화 현금", "코드": "", "목표비율": 0.00, "보유수량": 5511}
    ],
    '개인형 IRP': [
        {"구분": "주식", "ETF명": "TIGER 미국S&P500타겟데일리커버드콜", "코드": "482730", "목표비율": 0.20, "보유수량": 925},
        {"구분": "주식", "ETF명": "TIGER 미국나스닥100타겟데일리커버드콜", "코드": "486290", "목표비율": 0.15, "보유수량": 693},
        {"구분": "주식", "ETF명": "TIGER 미국배당다우존스타겟데일리커버드콜", "코드": "0008S0", "목표비율": 0.10, "보유수량": 565},
        {"구분": "주식", "ETF명": "KODEX 200타겟위클리커버드콜", "코드": "498400", "목표비율": 0.15, "보유수량": 375},
        {"구분": "채권", "ETF명": "TIGER 미국30년국채커버드콜액티브(H)", "코드": "476550", "목표비율": 0.30, "보유수량": 2499},
        {"구분": "실물", "ETF명": "ACE KRX금현물", "코드": "411060", "목표비율": 0.10, "보유수량": 212},
        {"구분": "현금", "ETF명": "KODEX 미국머니마켓액티브", "코드": "0048J0", "목표비율": 0.00, "보유수량": 0},
        {"구분": "현금", "ETF명": "원화 현금", "코드": "", "목표비율": 0.00, "보유수량": 7325}
    ]
}

# ==========================================
# 2. 실시간 시세 스크래핑 함수 (Streamlit 캐시 적용)
# ==========================================
@st.cache_data(ttl=60) # 60초 동안은 같은 가격을 캐싱(저장)해서 속도 향상 및 차단 방지
def get_current_price(code):
    if not code:
        return 1  # 현금
    
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        res = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        no_today = soup.find('p', class_='no_today')
        if no_today:
            price_str = no_today.find('span', class_='blind').text
            return int(price_str.replace(',', ''))
    except Exception:
        pass
    return 0

# ==========================================
# 3. 데이터 가공 및 테이블 생성 함수
# ==========================================
def process_portfolio(acc_name, items):
    df = pd.DataFrame(items)
    
    # 실시간 가격 가져오기
    df['현재가(원)'] = df['코드'].apply(get_current_price)
    
    # 평가금액 및 총액 계산
    df['평가금액(원)'] = df['현재가(원)'] * df['보유수량']
    total_eval = df['평가금액(원)'].sum()
    
    # 각종 비율 및 조정 수량 계산
    df['현재비율'] = (df['평가금액(원)'] / total_eval * 100).fillna(0)
    df['목표금액(원)'] = total_eval * df['목표비율']
    
    # 목표수량 (현금 제외)
    df['목표수량'] = df.apply(lambda x: round(x['목표금액(원)'] / x['현재가(원)']) if x['현재가(원)'] > 1 else 0, axis=1)
    
    # 차이 수량 계산
    df['조정수량'] = df['목표수량'] - df['보유수량']
    
    # 화면 표시용 텍스트 변환 (현금은 제외)
    df['조정필요'] = df.apply(
        lambda x: "-" if x['코드'] == "" or x['목표비율'] == 0 else 
                 (f"🔴 +{x['조정수량']:,.0f} 매수" if x['조정수량'] > 0 else 
                 (f"🔵 {x['조정수량']:,.0f} 매도" if x['조정수량'] < 0 else "유지")), 
        axis=1
    )
    
    # 포맷팅
    df_display = df[['구분', 'ETF명', '목표비율', '현재가(원)', '보유수량', '평가금액(원)', '현재비율', '목표수량', '조정필요']].copy()
    df_display['목표비율'] = (df_display['목표비율'] * 100).apply(lambda x: f"{x:.0f}%")
    df_display['현재비율'] = df_display['현재비율'].apply(lambda x: f"{x:.1f}%")
    
    return df_display, total_eval

# ==========================================
# 4. Streamlit 화면 구성
# ==========================================
st.title("📈 연금계좌 자산배분 & 실시간 리밸런싱 대시보드")
st.markdown("네이버 금융 실시간 시세 스크래핑 기반 (파이썬 백엔드)")

# 수동 새로고침 버튼 (캐시 삭제)
if st.button("🔄 실시간 시세 강제 새로고침"):
    st.cache_data.clear()
    st.rerun()

st.divider()

# 데이터를 탭(Tab) 형태로 깔끔하게 구성
tabs = st.tabs(list(portfolio_data.keys()))
grand_total = 0

for i, (acc_name, items) in enumerate(portfolio_data.items()):
    with tabs[i]:
        st.subheader(f"{acc_name} 포트폴리오")
        
        with st.spinner('실시간 시세를 불러오는 중입니다...'):
            df_display, total_eval = process_portfolio(acc_name, items)
            grand_total += total_eval
            
            # 요약 정보 카드 형태로 표시
            st.metric(label=f"💰 {acc_name} 총 평가액", value=f"{total_eval:,.0f} 원")
            
            # 데이터프레임 (표) 스타일링 적용
            st.dataframe(
                df_display.style.format({
                    '현재가(원)': '{:,.0f}',
                    '보유수량': '{:,.0f}',
                    '평가금액(원)': '{:,.0f}',
                    '목표수량': '{:,.0f}'
                }),
                use_container_width=True,
                hide_index=True
            )

st.divider()
st.subheader(f"💎 전체 연금 자산 총합: {grand_total:,.0f} 원")