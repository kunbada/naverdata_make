import streamlit as st
import pandas as pd
import io

# 페이지 설정
st.set_page_config(page_title="부동산 데이터 가공 앱", layout="wide")

st.title("🏢 아파트 단지별 타입 선택 및 엑셀 추출기")
st.write("엑셀 파일을 업로드하고, 원하는 단지와 타입을 선택하여 리스트를 만드세요.")

# 1. 파일 업로드
uploaded_file = st.file_uploader("엑셀(CSV) 파일을 선택하세요", type=['csv', 'xlsx'])

if uploaded_file:
    # 데이터 로드 (제공된 예시가 CSV 형태이므로 기본적으로 read_csv 사용)
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
        st.stop()

    # 필수 컬럼 확인 및 정리
    # 제공된 데이터 기준: complexName(단지명), pyName(타입명/평형)
    col_map = {
        'complexName': '단지명',
        'pyName': '타입',
        'supplyArea': '공급면적',
        'kbDealPrice': 'KB매매시세',
        'kbDepositPrice': 'KB전세시세',
        'realAvgPrice': '실거래평균가'
    }
    
    # 선택 목록을 저장할 session_state 초기화
    if 'selected_list' not in st.session_state:
        st.session_state.selected_list = pd.DataFrame(columns=col_map.values())

    # --- 데이터 선택 UI ---
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📍 데이터 선택")
        # 단지 선택
        all_complexes = sorted(df['complexName'].unique())
        selected_complex = st.selectbox("단지를 선택하세요", all_complexes)

        # 해당 단지의 타입 선택
        filtered_types = df[df['complexName'] == selected_complex]
        all_types = sorted(filtered_types['pyName'].unique())
        selected_type = st.selectbox("타입을 선택하세요", all_types)

        if st.button("➕ 선택 목록에 추가"):
            # 선택한 단지와 타입에 해당하는 데이터 행 추출
            target_row = filtered_types[filtered_types['pyName'] == selected_type].iloc[0]
            
            # 필요한 정보만 추출하여 딕셔너리 생성
            new_data = {
                '단지명': target_row['complexName'],
                '타입': target_row['pyName'],
                '공급면적': target_row['supplyArea'],
                'KB매매시세': target_row['kbDealPrice'],
                'KB전세시세': target_row['kbDepositPrice'],
                '실거래평균가': target_row['realAvgPrice']
            }
            
            # 중복 체크 후 추가
            is_duplicate = ((st.session_state.selected_list['단지명'] == new_data['단지명']) & 
                            (st.session_state.selected_list['타입'] == new_data['타입'])).any()
            
            if not is_duplicate:
                st.session_state.selected_list = pd.concat([st.session_state.selected_list, pd.DataFrame([new_data])], ignore_index=True)
                st.success(f"{selected_complex} {selected_type} 추가 완료!")
            else:
                st.warning("이미 목록에 있는 데이터입니다.")

    with col2:
        st.subheader("📋 현재 선택된 목록")
        if not st.session_state.selected_list.empty:
            st.dataframe(st.session_state.selected_list, use_container_width=True)
            if st.button("🗑️ 목록 전체 삭제"):
                st.session_state.selected_list = pd.DataFrame(columns=col_map.values())
                st.rerun()
        else:
            st.info("추가된 데이터가 없습니다.")

    # --- 파일 저장 UI ---
    if not st.session_state.selected_list.empty:
        st.divider()
        st.subheader("💾 엑셀 저장")
        
        # 엑셀 파일로 변환 (메모리 버퍼 사용)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.selected_list.to_excel(writer, index=False, sheet_name='Sheet1')
        
        processed_data = output.getvalue()

        st.download_button(
            label="엑셀 파일 다운로드",
            data=processed_data,
            file_name="selected_apartment_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )