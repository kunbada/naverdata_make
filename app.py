import streamlit as st
import pandas as pd
import time
import random
import io
import os
from curl_cffi import requests
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium

# --- 1. 페이지 설정 및 세션 초기화 ---
st.set_page_config(page_title="부동산 대시보드", layout="wide", initial_sidebar_state="collapsed")

if 'selected_items' not in st.session_state:
    st.session_state.selected_items = []
if 'current_complexes' not in st.session_state:
    st.session_state.current_complexes = []

# --- 2. CSS 스타일 (스크롤 및 레이아웃 유지) ---
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stColumn > div {
        padding: 10px;
    }
    /* 왼쪽 섹션 스크롤 박스 */
    .scroll-container {
        height: 85vh;
        overflow-y: auto;
        padding: 15px;
        background-color: white;
        border-radius: 10px;
        border: 1px solid #ddd;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 데이터 로드 및 함수 (생략 없이 유지) ---
@st.cache_data
def load_region_data():
    csv_path = 'region.csv'
    if os.path.exists(csv_path):
        try:
            # 1. 인코딩 시도 (utf-8 -> cp949 순서)
            try:
                df = pd.read_csv(csv_path, encoding='utf-8')
            except:
                df = pd.read_csv(csv_path, encoding='cp949')
            
            # 2. 데이터 청소 (매우 중요!)
            # 문자열 컬럼들의 양끝 공백을 제거하여 검색 실패 방지
            for col in ['sigungu', 'region']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
            
            # 3. 비어있는 행 제거
            return df.dropna(subset=['sigungu', 'region', 'dongcode'])
            
        except Exception as e:
            st.error(f"❌ CSV 파일을 읽는 중 오류가 발생했습니다: {e}")
            return pd.DataFrame(columns=['sigungu', 'region', 'dongcode'])
    else:
        st.error(f"⚠️ '{csv_path}' 파일을 찾을 수 없습니다. GitHub 업로드 여부를 확인하세요.")
        return pd.DataFrame(columns=['sigungu', 'region', 'dongcode'])

# [기존 쿠키/헤더 설정]
COOKIES = {
    'NNB': 'SIPX7NECP75WQ',
    'ASID': '70a80e240000019a2987080e00000024',
    '_fwb': '218bibhOl21HAJWSp3eLpQv.1762392726096',
    'NAC': 'jj7NB0QvmVgv',
    'nstore_session': 'n3n+Cq7FP64qws7PpvW5uzrj',
    '_fbp': 'fb.1.1763441507932.36677618909861448',
    'NV_WETR_LAST_ACCESS_RGN_M': '"MDIxMTMxMjc="',
    'NV_WETR_LOCATION_RGN_M': '"MDIxMTMxMjc="',
    'bnb_tooltip_shown_payment_v1': 'true',
    'ba.uuid': '96ea4bfa-381f-4c4b-9efd-717e1adadf38',
    'nstore_pagesession': 'jhqoYsqlLqgdKdsL3bl-169333',
    'cto_bundle': 'w6V7_V9lNHZRU3dDWGslMkJUOGIlMkI3OW9yNHRMOFk2anFXc3R6N1VObXhaYlBpOG9QaUdrMWY0NDFkN2t0cXNoZXlBbjdjRU9wWmVUNnFKY2dwenJpSTd3OTUwczVCWDhBYTdWUmNZMWtXWmNPdzF6RUg3WGdxMDFKMXZtaUNMSU1IOGVjTSUyQmx3Yk5DakhjaExxUGtWWUFRRDdBd1ElM0QlM0Q',
    'nhn.realestate.article.ipaddress_city': '4100000000',
    'SHOW_FIN_BADGE': 'Y',
    'NACT': '1',
    'bnb_tooltip_shown_finance_v1': 'true',
    'landHomeFlashUseYn': 'N',
    'nhn.realestate.article.trade_type_cd': 'all',
    'nhn.realestate.article.rlet_type_cd': 'A01',
    'realestate.beta.lastclick.cortar': '4161010100',
    'PROP_TEST_KEY': '1771306773960.245ff641e510fb7eb593db1a7e0f78ccbc4da40d607357d22c05a48eb610413b',
    'PROP_TEST_ID': '07d80c6cf5c49ab7615f21c3ee894eed55c4b6c134a628373bb789024cdffd7a',
    'SRT30': '1771316369',
    'SRT5': '1771316369',
    'BUC': '47ogVLRbNFYSvJgPBe5oXfw50HGF4jS5YzyYhx6bdy0=',
}
    
# 기존 HEADERS를 더 정교하게 바꿉니다.
HEADERS = {
    'authority': 'fin.land.naver.com',
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'referer': 'https://fin.land.naver.com/regions',
    'sec-ch-ua': '"Not A(Branch";v="99", "Google Chrome";v="121", "Chromium";v="121"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
}
# --- 데이터 수집 함수 (기존 로직 유지) ---
def fetch_recent_kb_price(complex_num, pyeong_num):
    today = datetime.now()
    six_months_ago = today - timedelta(days=180)
    url = "https://fin.land.naver.com/front-api/v1/complex/marketPrice/list"
    params = {'complexNumber': str(complex_num), 'pyeongTypeNumber': str(pyeong_num), 
              'startDate': six_months_ago.strftime('%Y-%m-%d'), 'endDate': today.strftime('%Y-%m-%d'), 'cpList[]': 'kbstar'}
    try:
        res = requests.get(url, params=params, cookies=COOKIES, headers=HEADERS, impersonate="chrome120").json()
        if res.get('isSuccess') and res.get('result'):
            kb_data = res['result'][0]
            deal_dict = kb_data.get('dealPrices', {})
            deposit_dict = kb_data.get('depositPrices', {})
            if deal_dict:
                recent_date = sorted(deal_dict.keys())[-1]
                return {'kbDate': recent_date, 'kbDealPrice': deal_dict.get(recent_date), 'kbDepositPrice': deposit_dict.get(recent_date)}
    except: pass
    return {'kbDate': '', 'kbDealPrice': '', 'kbDepositPrice': ''}

def fetch_real_price_summary(complex_num, pyeong_num):
    url = "https://fin.land.naver.com/front-api/v1/complex/pyeong/realPrice/summary"
    params = {'complexNumber': str(complex_num), 'pyeongTypeNumber': str(pyeong_num), 'realEstateType': 'A01', 'tradeType': 'A1'}
    try:
        res = requests.get(url, params=params, cookies=COOKIES, headers=HEADERS, impersonate="chrome120").json()
        if res.get('isSuccess') and res.get('result'):
            r = res['result']
            return {'realMaxPrice': r.get('maxPrice', {}).get('dealPrice', ''), 'realMaxDate': r.get('maxPrice', {}).get('tradeDate', ''), 'realAvgPrice': r.get('avgPrice', '')}
    except: pass
    return {'realMaxPrice': '', 'realMaxDate': '', 'realAvgPrice': ''}

def fetch_recent_5_real_prices(complex_num, pyeong_num):
    url = "https://fin.land.naver.com/front-api/v1/complex/pyeong/realPrice"
    params = {'complexNumber': str(complex_num), 'pyeongTypeNumber': str(pyeong_num), 'page': '1', 'size': '5', 'tradeType': 'A1'}
    results = {}
    for i in range(1, 6):
        results[f'real{i}_date'] = ''; results[f'real{i}_price'] = ''; results[f'real{i}_floor'] = ''
    try:
        res = requests.get(url, params=params, cookies=COOKIES, headers=HEADERS, impersonate="chrome120").json()
        if res.get('isSuccess') and res.get('result'):
            trades = res['result'].get('list', [])
            for i, t in enumerate(trades[:5], 1):
                results[f'real{i}_date'] = t.get('tradeDate', ''); results[f'real{i}_price'] = t.get('dealPrice', ''); results[f'real{i}_floor'] = t.get('floor', '')
    except: pass
    return results

@st.cache_data(ttl=600)
def fetch_full_complex_list(dong_code):
    # 코드 전처리 (10자리 고정)
    clean_code = str(dong_code).split('.')[0].ljust(10, '0')[:10]
    url = "https://fin.land.naver.com/front-api/v1/complex/region"
    
    params = {
        'eupLegalDivisionNumber': clean_code,
        'size': '100',
        'sortType': 'HOUSEHOLD',
        'page': '0'
    }
    
    all_complexes = []
    try:
        # ⚠️ 중요: impersonate="chrome120" 옵션을 반드시 유지하세요.
        response = requests.get(
            url, 
            params=params, 
            cookies=COOKIES, 
            headers=HEADERS, 
            impersonate="chrome120",
            timeout=15
        )
        
        # 만약 성공하지 못했다면 화면에 에러 코드 출력
        if response.status_code != 200:
            st.error(f"❌ 네이버 응답 에러: {response.status_code}")
            return []

        res = response.json()
        
        if 'result' in res and res['result']:
            curr_list = res['result'].get('list', [])
            for item in curr_list:
                if item.get('complexInfo', {}).get('type') in ['A01', 'A02']:
                    all_complexes.append(item['complexInfo'])
                    
        if not all_complexes:
            st.warning("⚠️ 해당 지역에 아파트 단지 정보가 없습니다.")
            
    except Exception as e:
        st.error(f"⚠️ 연결 중 오류 발생: {e}")
        
    return all_complexes

@st.cache_data(ttl=3600)
def get_pyeong_details_full(complex_num, complex_name):
    list_url = "https://fin.land.naver.com/front-api/v1/complex/building/pyeongList"
    detail_url = "https://fin.land.naver.com/front-api/v1/complex/pyeong"
    headers = HEADERS.copy()
    headers['referer'] = f'https://fin.land.naver.com/complexes/{complex_num}'
    results = []
    try:
        res_list = requests.get(list_url, params={'complexNumber': str(complex_num)}, cookies=COOKIES, headers=headers, impersonate="chrome120").json()
        py_nums = list(res_list.get('result', {}).keys())
        if not py_nums: return []
        for p_num in py_nums:
            time.sleep(0.2)
            res_detail = requests.get(detail_url, params={'complexNumber': str(complex_num), 'pyeongTypeNumber': str(p_num)}, cookies=COOKIES, headers=headers, impersonate="chrome120").json()
            if res_detail.get('isSuccess') and 'result' in res_detail:
                base = res_detail['result']
                row = {'complexNumber': complex_num, 'complexName': complex_name, 'pyName': base.get('name'), 'supplyArea': base.get('supplyArea'), 'exclusiveArea': base.get('exclusiveArea')}
                row.update(fetch_recent_kb_price(complex_num, p_num))
                row.update(fetch_real_price_summary(complex_num, p_num))
                row.update(fetch_recent_5_real_prices(complex_num, p_num))
                results.append(row)
    except: pass
    return results

def fetch_complex_coords(complex_num):
    url = f"https://new.land.naver.com/api/complexes/overview/{complex_num}"
    headers = HEADERS.copy()
    headers['referer'] = f'https://new.land.naver.com/complexes/{complex_num}'
    try:
        res = requests.get(url, cookies=COOKIES, headers=headers, impersonate="chrome120").json()
        return {'latitude': res.get('latitude'), 'longitude': res.get('longitude')}
    except:
        return {'latitude': None, 'longitude': None}

def render_apt_map(selected_df, map_type):
    # 기본 위치: 서울시청
    center = [37.5665, 126.9780]
    if not selected_df.empty and 'latitude' in selected_df.columns:
        valid_coords = selected_df.dropna(subset=['latitude', 'longitude'])
        if not valid_coords.empty:
            center = [valid_coords['latitude'].mean(), valid_coords['longitude'].mean()]
    
    # 지도 객체 생성 (tiles=None으로 설정하여 수동 제어)
    m = folium.Map(location=center, zoom_start=15, tiles=None)

    # 타일 설정
    if map_type == "Mapbox 커스텀":
        ACCESS_TOKEN = 'pk.eyJ1Ijoia215b29uIiwiYSI6ImNtbHJtY2dvZDBhcGIzZXNic2VicTV4NmoifQ.hhyafHwBYChN-nV3k3rr3w' 
        STYLE_ID = 'cmlsq5s1g000z01sogzpwb3de'
        USER_ID = 'kmyoon'
        mapbox_tiles = f'https://api.mapbox.com/styles/v1/{USER_ID}/{STYLE_ID}/tiles/{{z}}/{{x}}/{{y}}?access_token={ACCESS_TOKEN}'
        
        folium.TileLayer(
            tiles=mapbox_tiles,
            attr='Mapbox Custom Style',
            name='Mapbox',
            overlay=False,
            control=True
        ).add_to(m)
    else:
        # 오픈스트리트맵 기반 CartoDB Positron (깔끔한 화이트 톤)
        folium.TileLayer(
            tiles='cartodbpositron',
            attr='CartoDB',
            name='OpenStreetMap',
            overlay=False,
            control=True
        ).add_to(m)

    # 마커 표시 (단지별 중복 제거)
    if not selected_df.empty:
        map_data = selected_df.dropna(subset=['latitude', 'longitude']).drop_duplicates(subset=['complexNumber'])
        for _, row in map_data.iterrows():
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=f"<b>{row['complexName']}</b>",
                tooltip=row['complexName'],
                icon=folium.Icon(color='red', icon='home', prefix='fa')
            ).add_to(m)
            
    return m

# --- 4. 메인 UI 레이아웃 (구조 변경) ---
# 화면을 1:1.2 비율로 나눕니다.
col_left, col_right = st.columns([1, 1.2])
region_df = load_region_data()
# 왼쪽: 데이터 관리
with col_left:
    st.title("🏢 단지 선택 및 관리")
    
    # 지역 선택
    with st.container():
        st.subheader("📍 지역 선택")
        c1, c2 = st.columns(2)
        with c1:
            sigungu_list = sorted(region_df['sigungu'].astype(str).unique())
            sel_sigungu = st.selectbox("시/군/구", options=sigungu_list, key="sigungu_sel")
        with c2:
            dong_opts = region_df[region_df['sigungu'] == sel_sigungu]
            sel_dong = st.selectbox("읍/면/동", options=dong_opts['region'].tolist(), key="dong_sel")
            target_code = dong_opts[dong_opts['region'] == sel_dong].iloc[0]['dongcode']
        
        if st.button("🔍 단지 목록 불러오기", use_container_width=True):
            st.session_state.current_complexes = fetch_full_complex_list(target_code)

    st.divider()

    # 단지 및 타입 선택
    if st.session_state.current_complexes:
        st.subheader("📑 단지 및 타입 선택")
        cp_dict = {c['name']: c['complexNumber'] for c in st.session_state.current_complexes}
        sel_cp_name = st.selectbox("아파트 단지", options=list(cp_dict.keys()), key="cp_sel")
        
        if sel_cp_name:
            types = get_pyeong_details_full(cp_dict[sel_cp_name], sel_cp_name)
            if types:
                type_names = [t['pyName'] for t in types]
                sel_type = st.selectbox("타입(평형) 선택", options=type_names, key="type_sel")
                
                if st.button("➕ 리스트에 추가", use_container_width=True, key=f"add_{cp_dict[sel_cp_name]}"):
                    item = next(t for t in types if t['pyName'] == sel_type).copy()
                    coords = fetch_complex_coords(cp_dict[sel_cp_name])
                    item.update(coords)
                    st.session_state.selected_items.append(item)
                    st.toast(f"{sel_cp_name} 추가됨!")

    st.divider()

    # 리스트 테이블 (여기에 스크롤 적용)
    st.subheader("📋 장바구니 리스트")
    if st.session_state.selected_items:
        # 상단 버튼
        bc1, bc2 = st.columns(2)
        with bc1:
            df_final = pd.DataFrame(st.session_state.selected_items)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False)
            st.download_button("💾 엑셀 저장", data=output.getvalue(), file_name="apt_data.xlsx", use_container_width=True)
        with bc2:
            if st.button("🗑️ 전체 초기화", use_container_width=True):
                st.session_state.selected_items = []
                st.rerun()
        
        # 데이터프레임
        st.dataframe(pd.DataFrame(st.session_state.selected_items)[['complexName', 'pyName', 'kbDealPrice', 'realMaxPrice']], 
                     use_container_width=True, height=300)
    else:
        st.info("추가된 단지가 없습니다.")

# 오른쪽: 지도
with col_right:
    st.subheader("🗺️ 부동산 통합 지도")
    
    # 지도 종류 선택 라디오 버튼 (가로로 배치)
    map_option = st.radio(
        "지도 스타일 선택",
        options=["OpenStreetMap", "Mapbox 커스텀"],
        horizontal=True,
        key="map_style_choice"
    )

    # 세션 상태 데이터를 기반으로 지도 렌더링
    current_df = pd.DataFrame(st.session_state.selected_items)
    
    # 선택된 map_option을 함수에 전달
    m = render_apt_map(current_df, map_option)
    
    # 지도 출력
    st_folium(m, width="100%", height=800, key=f"map_{map_option}") 
    # key값에 map_option을 포함시켜 스타일 변경 시 지도가 새로 그려지도록 함
