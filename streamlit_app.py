import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
import pytz  # For timezone conversion

# 한국 표준시 (KST) 설정
kst = pytz.timezone('Asia/Seoul')

# 데이터베이스 연결 설정
conn = sqlite3.connect('reservations.db', check_same_thread=False)
c = conn.cursor()

# 예약 및 사용자 테이블 생성 함수
def create_tables():
    # 테이블 생성
    c.execute('''CREATE TABLE IF NOT EXISTS reservations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 desk INTEGER,
                 date TEXT,
                 start_time TEXT,
                 end_time TEXT,
                 reserved_by TEXT,
                 student_id TEXT,
                 canceled TEXT DEFAULT 'N')''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (student_id TEXT PRIMARY KEY,
                 password TEXT,
                 name TEXT)''')
    conn.commit()

create_tables()

# 사용자 등록 함수
def register_user(student_id, password, name):
    try:
        c.execute('INSERT INTO users (student_id, password, name) VALUES (?, ?, ?)',
                  (student_id, password, name))
        conn.commit()
        st.success('회원가입이 완료되었습니다.')
    except sqlite3.IntegrityError:
        st.error('이미 존재하는 학번입니다.')

# 사용자 인증 함수
def authenticate_user(student_id, password):
    c.execute('SELECT * FROM users WHERE student_id = ? AND password = ?', (student_id, password))
    user = c.fetchone()
    return user

# 예약 추가 함수
def add_reservation(desk, date_str, start_time, end_time, reserved_by, student_id):
    c.execute('INSERT INTO reservations (desk, date, start_time, end_time, reserved_by, student_id) VALUES (?, ?, ?, ?, ?, ?)',
              (desk, date_str, start_time, end_time, reserved_by, student_id))
    conn.commit()

# 예약 가능 여부 확인 함수
def is_available(desk, date_str, start_time, end_time):
    c.execute('''SELECT * FROM reservations 
                 WHERE desk = ? AND date = ? 
                 AND ((start_time < ? AND end_time > ?) 
                 OR (start_time >= ? AND start_time < ?)) 
                 AND canceled = 'N' ''',
              (desk, date_str, end_time, start_time, start_time, end_time))
    data = c.fetchall()
    return len(data) == 0

# 특정 날짜와 책상의 예약된 시간대 가져오기 함수
def get_reserved_time_slots(desk, date_str):
    c.execute('''SELECT start_time, end_time FROM reservations
                 WHERE desk = ? AND date = ? AND canceled = 'N' ''',
              (desk, date_str))
    data = c.fetchall()
    reserved_slots = []
    for start_time_str, end_time_str in data:
        start_hour = int(start_time_str.split(':')[0])
        end_hour = int(end_time_str.split(':')[0])
        # Adjust for times spanning midnight
        if end_hour <= start_hour:
            end_hour += 24
        for hour in range(start_hour, end_hour):
            reserved_slots.append(hour % 24)
    return reserved_slots

# 사용자의 예약 가져오기 함수
def get_user_reservations(student_id):
    c.execute('SELECT * FROM reservations WHERE student_id = ? ORDER BY date, start_time', (student_id,))
    data = c.fetchall()
    df = pd.DataFrame(data, columns=['ID', '책상 번호', '날짜', '시작 시간', '종료 시간', '예약자', '학번', '취소 상태'])
    return df

# 모든 예약 가져오기 함수 (관리자용)
def get_all_reservations():
    c.execute('SELECT * FROM reservations ORDER BY date, start_time')
    data = c.fetchall()
    df = pd.DataFrame(data, columns=['ID', '책상 번호', '날짜', '시작 시간', '종료 시간', '예약자', '학번', '취소 상태'])
    return df

# 사용자 정보 가져오기 함수 (관리자용)
def get_all_users():
    c.execute('SELECT * FROM users')
    data = c.fetchall()
    df = pd.DataFrame(data, columns=['학번', '비밀번호', '이름'])
    return df

# 예약 취소 함수
def cancel_reservation(reservation_id, cancel_type='Y'):
    c.execute('UPDATE reservations SET canceled = ? WHERE id = ?', (cancel_type, reservation_id))
    conn.commit()

# CSV 저장 함수
def save_to_csv(df, filename):
    df.to_csv(filename, index=False)
    st.success(f'{filename} 파일로 저장되었습니다.')

# 사용자 로그인 및 관리자 권한 설정 함수
def user_login():
    with st.sidebar.expander('로그인', expanded=False):
        student_id = st.text_input('학번', key='login_student_id')
        password = st.text_input('비밀번호 (4자리)', type='password', key='login_password')
        if st.button('로그인', key='user_login_button'):
            if student_id == 'admin' and password == 'password':  # 관리자 계정 예시
                st.session_state['admin_logged_in'] = True
                st.session_state['user_logged_in'] = True  # 관리자도 사용자로 간주
                st.session_state['student_id'] = student_id
                st.session_state['user_name'] = "관리자"
                st.success('관리자 권한으로 로그인되었습니다.')
            else:
                user = authenticate_user(student_id, password)
                if user:
                    st.session_state['user_logged_in'] = True
                    st.session_state['student_id'] = user[0]
                    st.session_state['user_name'] = user[2]
                    st.session_state['admin_logged_in'] = False
                    st.success(f"{user[2]}님 환영합니다!")
                else:
                    st.error('학번 또는 비밀번호가 올바르지 않습니다.')

# 사용자 회원가입 함수
def user_register():
    with st.sidebar.expander('회원가입', expanded=False):
        name = st.text_input('이름', key='register_name')
        student_id = st.text_input('학번', key='register_student_id')
        password = st.text_input('비밀번호 (4자리)', type='password', key='register_password')
        if st.button('회원가입', key='register_button'):
            if name and student_id and password:
                register_user(student_id, password, name)
            else:
                st.error('모든 필드를 입력해 주세요.')

# Streamlit 애플리케이션 시작
st.set_page_config(page_title='강의실 예약 시스템', page_icon='📚', layout='wide')

# HTML과 CSS를 사용해 폰트를 적용
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Jua&display=swap" rel="stylesheet">
    <style>
    body, h1, h2, h3, h4, p, button, label, input, select, textarea, .stButton>button, .stDataFrame, .stAlert {
        font-family: 'Jua', sans-serif !important;
    }
    .title {
        text-align: center;
        font-size:50px !important;
        color: #4C72B0;
    }
    .header {
        font-size:30px !important;
        color: #4C72B0;
    }
    .subheader {
        font-size:25px !important;
        color: #4C72B0;
    }
    .available {
        background-color: #90EE90 !important;
        color: black !important;
        border: none;
        border-radius: 10px;
        padding: 5px;
        text-align: center;
        width: 100%;
    }
    .used {
        background-color: #1E90FF !important;
        color: white !important;
        border: none;
        border-radius: 10px;
        padding: 5px;
        text-align: center;
        width: 100%;
    }
    .time-slot {
        text-align: center;
        font-size: 14px;
    }
    .legend-box {
        display: inline-block;
        width: 15px;
        height: 15px;
        margin-right: 5px;
        border-radius: 5px;
    }
    .legend {
        display: flex;
        justify-content: center;
        gap: 15px;
        padding: 10px;
        border-radius: 8px;
        font-size: 14px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
    }
    td {
        padding: 8px;
    }
    .desk-status {
        text-align: center;
        padding: 20px;
        border-radius: 10px;
        color: white;
        font-weight: bold;
        margin: 10px;
        cursor: pointer;
    }
    </style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'desk' not in st.session_state:
    st.session_state['desk'] = None
if 'admin_logged_in' not in st.session_state:
    st.session_state['admin_logged_in'] = False
if 'user_logged_in' not in st.session_state:
    st.session_state['user_logged_in'] = False
if 'selected_date' not in st.session_state:
    st.session_state['selected_date'] = None

# 페이지 선택 먼저 사이드바에 추가
pages = ["홈", "예약 페이지"]
if st.session_state['admin_logged_in']:
    pages.append("관리자")

page = st.sidebar.radio("페이지 선택", pages)

# 사용자 회원가입 및 로그인
user_register()
if not st.session_state['user_logged_in']:
    user_login()
else:
    st.sidebar.write(f"**{st.session_state['user_name']}님 로그인 중**")
    if st.sidebar.button('로그아웃'):
        st.session_state['user_logged_in'] = False
        st.session_state['student_id'] = None
        st.session_state['user_name'] = None
        st.session_state['admin_logged_in'] = False
        st.session_state['desk'] = None  # 로그아웃 시 선택한 책상 초기화
        st.session_state['selected_date'] = None  # 로그아웃 시 선택한 날짜 초기화
        st.success('로그아웃되었습니다.')

# 새로운 책상 배치 정의 (4행 3열)
desk_layout = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9],
    [10, 11, 12]
]

# 홈 페이지 구현
if page == "홈":
    # 메인 제목 표시
    st.markdown('<h1 class="title">📚 강의실 예약 시스템</h1>', unsafe_allow_html=True)
    
    # 배너 추가
    # 배너 이미지 URL과 링크를 원하는 대로 변경하세요.
    banner_links = [
        "https://bigdata.hannam.ac.kr/",
        "https://www.example.com/link2",
        "https://www.example.com/link3"
    ]
    banner_images = [
        "https://via.placeholder.com/300x100?text=배너+1",
        "https://via.placeholder.com/300x100?text=배너+2",
        "https://via.placeholder.com/300x100?text=배너+3"
    ]
    
    # 배너를 3개의 동일한 크기의 컬럼에 배치
    banner_cols = st.columns(3)
    for col, link, img in zip(banner_cols, banner_links, banner_images):
        col.markdown(
            f'<a href="{link}" target="_blank"><img src="{img}" width="300" height="100" style="border:0;"></a>',
            unsafe_allow_html=True
        )
    
    # 책상 실시간 상태 표시
    st.markdown('<h3 class="subheader">책상 실시간 상태</h3>', unsafe_allow_html=True)

    # 범례 표시 (책상 실시간 상태 아래에 위치)
    st.markdown("""
        <div class="legend">
            <div><span class="legend-box" style="background-color: #90EE90;"></span>예약 가능</div>
            <div><span class="legend-box" style="background-color: #1E90FF;"></span>사용 중</div>
        </div>
    """, unsafe_allow_html=True)
    
    current_datetime = datetime.now(kst)
    current_date = current_datetime.strftime('%Y-%m-%d')
    current_time = current_datetime.strftime('%H:%M')
    
    for row in desk_layout:
        cols = st.columns(len(row))
        for desk_num, col in zip(row, cols):
            # 현재 시간에 해당하는 예약이 있는지 확인
            c.execute('''SELECT * FROM reservations 
                         WHERE desk = ? AND date = ? 
                         AND start_time <= ? AND end_time > ?
                         AND canceled = 'N' ''',
                      (desk_num, current_date, current_time, current_time))
            current_reservation = c.fetchone()

            if current_reservation:
                # 사용 중인 책상
                color = '#1E90FF'  # Dodger Blue
                status = '사용 중'
            else:
                # 예약 가능 여부 확인
                color = '#90EE90'  # Light Green
                status = '예약 가능'

            with col:
                st.markdown(f"""
                    <div class="desk-status" style="background-color: {color};">
                        책상 {desk_num}<br>{status}
                    </div>
                """, unsafe_allow_html=True)
    
    # 공지사항 추가
    st.markdown('---')
    st.markdown('<h3 style="text-align: center;">⭐ 공지 사항 ⭐</h3>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center;">여기에 공지 내용을 작성하세요. 예: 예약 취소는 1시간 전에 해주시기 바랍니다.</p>', unsafe_allow_html=True)

# 예약 페이지 구현
elif page == "예약 페이지":
    st.markdown('<h2 class="header">강의실 예약하기</h2>', unsafe_allow_html=True)

    # 예약 시간대 선택 기능을 기존 예약 기능 위에 추가
    st.markdown('<h3 class="subheader">책상 선택 및 예약 시간대 확인</h3>', unsafe_allow_html=True)
    
    # 책상 선택을 새로운 배치에 맞게 표시
    for row in desk_layout:
        cols = st.columns(len(row))
        for desk_num, col in zip(row, cols):
            with col:
                button_key = f'reservation_page_desk_{desk_num}'
                if st.button(f'책상 {desk_num}', key=button_key):
                    selected_desk = desk_num
                    st.session_state['desk'] = selected_desk
                    st.session_state['selected_date'] = None  # 새로운 책상을 선택하면 날짜 초기화

    # 선택된 책상이 있을 경우
    if st.session_state['desk'] is not None:
        st.success(f"책상 {st.session_state['desk']}을(를) 선택하셨습니다.")
        selected_date = st.date_input('날짜 선택', value=datetime.now(kst).date(), min_value=datetime.now(kst).date())
        st.session_state['selected_date'] = selected_date.strftime('%Y-%m-%d')

        if st.session_state['selected_date']:
            # 예약 현황 테이블 표시
            reserved_slots = get_reserved_time_slots(st.session_state['desk'], st.session_state['selected_date'])

            # 실시간 예약 상태 표시
            st.markdown(f"**예약된 시간대:** {reserved_slots}")

            time_slots = list(range(24))  # 0~23시
            morning_slots = time_slots[:12]  # 0~11시
            afternoon_slots = time_slots[12:]  # 12~23시

            def generate_time_table(slots):
                table_html = '<table style="width:100%; border-collapse: collapse;"><tr>'
                for hour in slots:
                    time_str = f"{hour:02d}:00"
                    if hour in reserved_slots:
                        table_html += f'<td style="border: 1px solid #ddd;"><div class="used">{time_str}</div></td>'
                    else:
                        table_html += f'<td style="border: 1px solid #ddd;"><div class="available">{time_str}</div></td>'
                table_html += '</tr></table>'
                return table_html

            st.markdown('<h4 class="subheader">오전 시간대</h4>', unsafe_allow_html=True)
            st.markdown(generate_time_table(morning_slots), unsafe_allow_html=True)
            st.markdown('<h4 class="subheader">오후 시간대</h4>', unsafe_allow_html=True)
            st.markdown(generate_time_table(afternoon_slots), unsafe_allow_html=True)

    # 기존 예약 기능
    if st.session_state['user_logged_in']:
        st.markdown('---')
        st.markdown('<h3 class="subheader">예약하기</h3>', unsafe_allow_html=True)

        with st.form('reservation_form'):
            cols = st.columns(2)
            with cols[0]:
                date = st.date_input('날짜 선택', datetime.now(kst), min_value=datetime.now(kst).date())
                start_time = st.time_input('시작 시간', datetime.now(kst))
                end_time = st.time_input('종료 시간', datetime.now(kst) + timedelta(hours=1))
                desk = st.number_input('책상 번호', min_value=1, max_value=12, step=1)
            with cols[1]:
                st.write(f"예약자: {st.session_state['user_name']} ({st.session_state['student_id']})")
            submitted = st.form_submit_button('예약하기')

        if submitted:
            if start_time >= end_time:
                st.error('시작 시간은 종료 시간보다 이전이어야 합니다.')
            else:
                if is_available(desk, date.strftime('%Y-%m-%d'), start_time.strftime('%H:%M'), end_time.strftime('%H:%M')):
                    add_reservation(
                        desk,
                        date.strftime('%Y-%m-%d'),
                        start_time.strftime('%H:%M'),
                        end_time.strftime('%H:%M'),
                        st.session_state['user_name'],
                        st.session_state['student_id']
                    )
                    st.success(f'책상 {desk}번 예약이 완료되었습니다.')
                else:
                    st.error('선택한 시간에 해당 책상은 이미 예약되어 있습니다.')

        st.markdown('---')

        # 사용자 예약 관리
        st.markdown('<h2 class="header">내 예약 관리</h2>', unsafe_allow_html=True)
        user_reservations = get_user_reservations(st.session_state['student_id'])
        if not user_reservations.empty:
            st.dataframe(user_reservations.style.set_properties(**{'text-align': 'center'}))

            # 예약 취소
            reservation_ids = user_reservations[user_reservations['취소 상태'] == 'N']['ID'].tolist()
            if reservation_ids:
                selected_reservation = st.selectbox('취소할 예약을 선택하세요 (ID):', reservation_ids, key='cancel_reservation_selectbox')
                if st.button('예약 취소', key='cancel_reservation_button'):
                    cancel_reservation(selected_reservation, cancel_type='Y')
                    st.success('예약이 취소되었습니다.')
            else:
                st.info('취소 가능한 예약이 없습니다.')
        else:
            st.info('현재 예약된 내역이 없습니다.')
    else:
        st.info('예약을 하려면 로그인해 주세요.')

# 관리자 페이지 구현
elif page == "관리자" and st.session_state['admin_logged_in']:
    st.markdown('<h2 class="header">관리자 페이지</h2>', unsafe_allow_html=True)

    # 전체 예약 현황 보기
    st.markdown('<h3 class="subheader">전체 예약 현황</h3>', unsafe_allow_html=True)
    all_reservations = get_all_reservations()
    if not all_reservations.empty:
        st.dataframe(all_reservations.style.set_properties(**{'text-align': 'center'}))

        # 예약 내역을 CSV 파일로 저장
        if st.button('예약 내역 CSV로 저장'):
            save_to_csv(all_reservations, 'all_reservations.csv')
    else:
        st.info('예약된 내역이 없습니다.')

    # 사용자 정보 보기 및 저장
    st.markdown('<h3 class="subheader">사용자 정보</h3>', unsafe_allow_html=True)
    all_users = get_all_users()
    if not all_users.empty:
        st.dataframe(all_users.style.set_properties(**{'text-align': 'center'}))

        # 사용자 정보를 CSV 파일로 저장
        if st.button('회원 정보 CSV로 저장'):
            save_to_csv(all_users, 'all_users.csv')
    else:
        st.info('사용자 정보가 없습니다.')
