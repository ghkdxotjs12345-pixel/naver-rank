import os
import sys
import urllib.request
import urllib.parse
import urllib.error
import json
import pandas as pd
import matplotlib.pyplot as plt
import time
import random
import requests
import hashlib
import hmac
import base64
import streamlit as st
import io
import contextlib
import traceback

# 페이지 설정 (반드시 첫 번째 Streamlit 명령이어야 함)
try:
    st.set_page_config(
        page_title="네이버 키워드 분석 도구",
        page_icon="🔍",
        layout="wide"
    )
except Exception:
    # 이미 설정된 경우 무시
    pass

# API 키 설정 (환경 변수 우선, 없으면 사이드바에서 입력받거나 기본값 사용)
st.sidebar.header("🔐 API 설정")
st.sidebar.caption("💡 환경 변수로 설정하면 자동으로 로드됩니다")

# 네이버 검색 API
st.sidebar.subheader("네이버 검색 API")
NAVER_CLIENT_ID = st.sidebar.text_input(
    "Client ID", 
    value=os.getenv("NAVER_CLIENT_ID", "Mk2eb19HWtprfnT8S3wm")
)
NAVER_CLIENT_SECRET = st.sidebar.text_input(
    "Client Secret", 
    value=os.getenv("NAVER_CLIENT_SECRET", "1_r7MLopWL"),
    type="password"
)


# 네이버 검색광고 API (입력값 앞뒤 공백 자동 제거)
st.sidebar.subheader("네이버 검색광고 API")
CUSTOMER_ID = st.sidebar.text_input(
    "Customer ID", 
    value=os.getenv("NAVER_CUSTOMER_ID", "4192153")
).strip()
API_KEY = st.sidebar.text_input(
    "API Key (Access License)", 
    value=os.getenv("NAVER_API_KEY", "01000000008527e6afa897dc4fad032d4c98ddeb675c97a972b44a427249b17b907dc9fe63"),
    type="password"
).strip()
SECRET_KEY = st.sidebar.text_input(
    "Secret Key", 
    value=os.getenv("NAVER_SECRET_KEY", "AQAAAACFJ+avqJfcT60DLUyY3etnPhum2k+zbDClp5dJsx2IcQ=="),
    type="password"
).strip()



# 네이버 검색광고 API 서명 생성 클래스 (동일)
class Signature:
    @staticmethod
    def generate(timestamp, method, uri, secret_key):
        message = "{}.{}.{}".format(timestamp, method, uri)
        hash = hmac.new(bytes(secret_key, "utf-8"), bytes(message, "utf-8"), hashlib.sha256)
        hash.hexdigest()
        return base64.b64encode(hash.digest())



# API 요청 헤더 생성 함수 (동일)
def get_header(method, uri, api_key, secret_key, customer_id):
    timestamp = str(round(time.time() * 1000))
    signature = Signature.generate(timestamp, method, uri, secret_key)
    # signature는 bytes이므로 문자열로 변환
    signature_str = signature.decode('utf-8') if isinstance(signature, bytes) else signature
    return {
        'Content-Type': 'application/json; charset=UTF-8',
        'X-Timestamp': timestamp,
        'X-API-KEY': api_key,
        'X-Customer': str(customer_id),
        'X-Signature': signature_str
    }



# 연관검색어(키워드) 분석 함수 (최신 예제 적용)
def get_keyword_results(hint_keywords, api_key, secret_key, customer_id):
    BASE_URL = 'https://api.naver.com'
    uri = '/keywordstool'
    method = 'GET'
    params = {}
    params['hintKeywords'] = hint_keywords
    params['showDetail'] = '1'
    try:
        r = requests.get(BASE_URL + uri, params=params,
                         headers=get_header(method, uri, api_key, secret_key, customer_id),
                         timeout=30)
        if r.status_code == 200:
            response_json = r.json()
            if 'keywordList' in response_json:
                return pd.DataFrame(response_json['keywordList']), None
            else:
                return None, f"응답에 'keywordList' 키가 없습니다. 응답: {response_json}"
        else:
            return None, f"API 오류: {r.status_code} - {r.text}"
    except requests.exceptions.Timeout:
        return None, "요청 시간 초과: API 응답이 너무 오래 걸렸습니다."
    except requests.exceptions.RequestException as e:
        return None, f"요청 실패: {str(e)}"
    except json.JSONDecodeError as e:
        return None, f"JSON 파싱 오류: {str(e)}"
    except Exception as e:
        return None, f"예상치 못한 오류: {str(e)}"


def search_naver_shopping(query, client_id, client_secret, display=100):
    """네이버 쇼핑 검색 API 호출"""
    try:
        encText = urllib.parse.quote(query)
        url = f"https://openapi.naver.com/v1/search/shop.json?query={encText}&display={display}"
        
        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", client_id)
        request.add_header("X-Naver-Client-Secret", client_secret)
        
        response = urllib.request.urlopen(request)
        rescode = response.getcode()
        
        if rescode == 200:
            response_body = response.read()
            result = json.loads(response_body.decode('utf-8'))
            return result, None
        else:
            error_body = response.read().decode('utf-8')
            return None, f"API 오류: {rescode} - {error_body}"
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if hasattr(e, 'read') else str(e.reason)
        return None, f"HTTP 오류: {e.code} - {error_body}"
    except urllib.error.URLError as e:
        return None, f"URL 오류: {str(e)}"
    except json.JSONDecodeError as e:
        return None, f"JSON 파싱 오류: {str(e)}"
    except Exception as e:
        return None, f"검색 오류: {str(e)}"


# 메인 타이틀
st.title("🔍 네이버 키워드 분석 도구")
st.markdown("---")



# 로그 출력을 위한 StringIO 객체 (전역)
if 'log_stream' not in st.session_state:
    st.session_state['log_stream'] = io.StringIO()
log_stream = st.session_state['log_stream']


# 탭 생성 (네이버 블로그 순위 추가)
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 키워드 분석 (검색광고 API)",
    "🛒 쇼핑 검색 (검색 API)",
    "🔎 통합검색 트렌드",
    "🏆 블로그 순위",
    "📝 로그(콘솔)"
])
# 탭 4: 네이버 블로그 순위
with tab4:
    st.header("🏆 네이버 블로그 순위")
    st.write("네이버 블로그 검색 API를 사용하여 키워드별 인기 블로그를 확인합니다.")

    blog_query = st.text_input("블로그 검색 키워드", value="아이스크림")
    display_count = st.slider("검색 결과 수", min_value=10, max_value=100, value=10, step=10)
    sort_type = st.selectbox("정렬 방식", ["sim", "date"])
    search_btn = st.button("블로그 순위 조회", key="blog_search")

    def getresult(client_id, client_secret, query, display=10, start=1, sort='sim'):
        try:
            encText = urllib.parse.quote(query)
            url = "https://openapi.naver.com/v1/search/blog?query=" + encText + \
                "&display=" + str(display) + "&start=" + str(start) + "&sort=" + sort
            request = urllib.request.Request(url)
            request.add_header("X-Naver-Client-Id", client_id)
            request.add_header("X-Naver-Client-Secret", client_secret)
            response = urllib.request.urlopen(request)
            rescode = response.getcode()
            if rescode == 200:
                response_body = response.read()
                response_json = json.loads(response_body.decode('utf-8'))
                if 'items' in response_json:
                    return pd.DataFrame(response_json['items']), None
                else:
                    return None, "응답에 'items' 키가 없습니다."
            else:
                return None, f"API 오류: {rescode}"
        except urllib.error.HTTPError as e:
            return None, f"HTTP 오류: {e.code} - {e.reason}"
        except urllib.error.URLError as e:
            return None, f"URL 오류: {str(e)}"
        except json.JSONDecodeError as e:
            return None, f"JSON 파싱 오류: {str(e)}"
        except Exception as e:
            return None, f"예상치 못한 오류: {str(e)}"

    if search_btn and blog_query:
        with st.spinner("블로그 검색 중..."):
            try:
                df_blog, error = getresult(NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, blog_query, display_count, 1, sort_type)
                if error:
                    st.error(error)
                elif df_blog is not None and not df_blog.empty:
                    st.success(f"{len(df_blog)}개의 블로그 글을 찾았습니다!")
                    st.dataframe(df_blog, use_container_width=True, height=400)
                else:
                    st.warning("검색 결과가 없습니다.")
            except Exception as e:
                st.error(f"API 호출 오류: {e}")


def log_print(*args, **kwargs):
    print(*args, **kwargs)
    print(*args, **kwargs, file=log_stream)

# 탭 1: 키워드 분석
with tab1:
    st.header("키워드 분석")
    st.write("네이버 검색광고 API를 사용하여 키워드의 검색량과 경쟁도를 분석합니다.")
    
    # 키워드 입력
    keyword_input = st.text_input(
        "분석할 키워드를 입력하세요 (여러 개는 쉼표로 구분)",
        placeholder="예: 노트북, 맥북, 갤럭시북"
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        analyze_btn = st.button("🔍 키워드 분석", type="primary", key="analyze")
    
    if analyze_btn and keyword_input:
        with st.spinner("키워드 분석 중..."):
            df, error = get_keyword_results(keyword_input, API_KEY, SECRET_KEY, CUSTOMER_ID)
            
            if error:
                st.error(error)
            elif df is not None and not df.empty:
                st.success(f"✅ {len(df)}개의 관련 키워드를 찾았습니다!")
                
                # 데이터프레임 컬럼명 한글화
                column_mapping = {
                    'relKeyword': '연관 키워드',
                    'monthlyPcQcCnt': '월간 PC 검색수',
                    'monthlyMobileQcCnt': '월간 모바일 검색수',
                    'monthlyAvePcClkCnt': '월평균 PC 클릭수',
                    'monthlyAveMobileClkCnt': '월평균 모바일 클릭수',
                    'monthlyAvePcCtr': '월평균 PC 클릭률',
                    'monthlyAveMobileCtr': '월평균 모바일 클릭률',
                    'plAvgDepth': '월평균 노출 광고수',
                    'compIdx': '경쟁정도'
                }
                
                df_display = df.rename(columns=column_mapping)
                
                # 검색수 합계 컬럼 추가
                if '월간 PC 검색수' in df_display.columns and '월간 모바일 검색수' in df_display.columns:
                    # '<10' 같은 값을 숫자로 변환
                    def convert_to_numeric(val):
                        if isinstance(val, str):
                            if val == '< 10':
                                return 5
                            return int(val.replace(',', ''))
                        return val
                    
                    df_display['월간 PC 검색수_num'] = df_display['월간 PC 검색수'].apply(convert_to_numeric)
                    df_display['월간 모바일 검색수_num'] = df_display['월간 모바일 검색수'].apply(convert_to_numeric)
                    df_display['총 검색수'] = df_display['월간 PC 검색수_num'] + df_display['월간 모바일 검색수_num']
                    
                    # 정렬
                    df_display = df_display.sort_values('총 검색수', ascending=False)
                
                # 데이터 테이블 표시
                st.dataframe(df_display, use_container_width=True, height=400)
                
                # 시각화
                st.subheader("📈 검색량 시각화")
                
                # 상위 20개만 시각화
                top_df = df_display.head(20)
                
                fig, ax = plt.subplots(figsize=(12, 6))
                
                # 한글 폰트 설정
                plt.rcParams['font.family'] = 'Malgun Gothic'
                plt.rcParams['axes.unicode_minus'] = False
                
                x = range(len(top_df))
                width = 0.35
                
                if '월간 PC 검색수_num' in top_df.columns:
                    bars1 = ax.bar([i - width/2 for i in x], top_df['월간 PC 검색수_num'], width, label='PC 검색수', color='#03C75A')
                    bars2 = ax.bar([i + width/2 for i in x], top_df['월간 모바일 검색수_num'], width, label='모바일 검색수', color='#1EC800')
                
                ax.set_xlabel('키워드')
                ax.set_ylabel('검색수')
                ax.set_title('키워드별 월간 검색수 (상위 20개)')
                ax.set_xticks(x)
                ax.set_xticklabels(top_df['연관 키워드'], rotation=45, ha='right')
                ax.legend()
                
                plt.tight_layout()
                st.pyplot(fig)
                
                # CSV 다운로드 버튼
                csv = df_display.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 CSV 다운로드",
                    data=csv,
                    file_name=f"keyword_analysis_{keyword_input.replace(',', '_')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("검색 결과가 없습니다. 다른 키워드를 시도해보세요.")

with tab2:
    st.header("쇼핑 검색")
    st.write("네이버 쇼핑 검색 API를 사용하여 상품을 검색합니다.")
    
    # 검색어 입력
    shopping_query = st.text_input(
        "검색할 상품을 입력하세요",
        placeholder="예: 맥북 프로"
    )
    
    display_count = st.slider("검색 결과 수", min_value=10, max_value=100, value=30, step=10)
    
    col1, col2 = st.columns([1, 4])
    with col1:
        search_btn = st.button("🛒 상품 검색", type="primary", key="search")
    
    if search_btn and shopping_query:
        with st.spinner("상품 검색 중..."):
            # 로그 출력을 위해 try-except로 감싸기
            result = None
            try:
                log_print(f"[INFO] 쇼핑 검색 API 호출: query={shopping_query}, display={display_count}")
                result, error = search_naver_shopping(shopping_query, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, display_count)
                log_print(f"[INFO] API 응답: {result}")
                
                if error:
                    st.error(error)
                    log_print(f"[ERROR] {error}")
            except Exception as e:
                st.error(f"API 호출 중 예외 발생: {e}")
                log_print(f"[ERROR] API 호출 중 예외 발생: {e}")
                log_print(traceback.format_exc())
                result = None
            
            if result and 'items' in result:
                items = result['items']
                st.success(f"✅ {len(items)}개의 상품을 찾았습니다!")
                
                # 데이터프레임 생성
                df_items = pd.DataFrame(items)
                
                # 필요한 컬럼만 선택하고 한글화
                columns_to_show = ['title', 'lprice', 'hprice', 'mallName', 'productId', 'productType', 'brand', 'maker', 'category1', 'category2', 'category3', 'category4']
                df_items = df_items[[col for col in columns_to_show if col in df_items.columns]]
                
                column_mapping = {
                    'title': '상품명',
                    'lprice': '최저가',
                    'hprice': '최고가',
                    'mallName': '쇼핑몰',
                    'productId': '상품ID',
                    'productType': '상품타입',
                    'brand': '브랜드',
                    'maker': '제조사',
                    'category1': '대분류',
                    'category2': '중분류',
                    'category3': '소분류',
                    'category4': '세분류'
                }
                
                df_items = df_items.rename(columns=column_mapping)
                
                # HTML 태그 제거
                if '상품명' in df_items.columns:
                    df_items['상품명'] = df_items['상품명'].str.replace('<[^<]+?>', '', regex=True)
                
                # 가격 숫자 변환
                if '최저가' in df_items.columns:
                    df_items['최저가'] = pd.to_numeric(df_items['최저가'], errors='coerce')
                
                # 데이터 테이블 표시
                st.dataframe(df_items, use_container_width=True, height=400)
                
                # 가격 분포 시각화
                if '최저가' in df_items.columns:
                    st.subheader("📈 가격 분포")
                    
                    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
                    
                    # 한글 폰트 설정
                    plt.rcParams['font.family'] = 'Malgun Gothic'
                    plt.rcParams['axes.unicode_minus'] = False
                    
                    # 히스토그램
                    axes[0].hist(df_items['최저가'].dropna(), bins=20, color='#03C75A', edgecolor='white')
                    axes[0].set_xlabel('가격 (원)')
                    axes[0].set_ylabel('상품 수')
                    axes[0].set_title('가격 분포')
                    
                    # 쇼핑몰별 상품 수
                    if '쇼핑몰' in df_items.columns:
                        mall_counts = df_items['쇼핑몰'].value_counts().head(10)
                        axes[1].barh(mall_counts.index, mall_counts.values, color='#1EC800')
                        axes[1].set_xlabel('상품 수')
                        axes[1].set_ylabel('쇼핑몰')
                        axes[1].set_title('쇼핑몰별 상품 수 (상위 10개)')
                    
                    plt.tight_layout()
                    st.pyplot(fig)
                
                # 통계 정보
                st.subheader("📊 가격 통계")
                col1, col2, col3, col4 = st.columns(4)
                
                if '최저가' in df_items.columns:
                    prices = df_items['최저가'].dropna()
                    col1.metric("최저가", f"{prices.min():,.0f}원")
                    col2.metric("최고가", f"{prices.max():,.0f}원")
                    col3.metric("평균가", f"{prices.mean():,.0f}원")
                    col4.metric("중간가", f"{prices.median():,.0f}원")
                
                # CSV 다운로드 버튼
                csv = df_items.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 CSV 다운로드",
                    data=csv,
                    file_name=f"shopping_search_{shopping_query}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("검색 결과가 없습니다. 다른 키워드를 시도해보세요.")


# 탭 3: 네이버 통합검색 트렌드
with tab3:
    st.header("🔎 네이버 통합검색 트렌드")
    st.write("네이버 DataLab 검색 트렌드 API를 사용하여 키워드 트렌드를 분석합니다.")

    # 입력 폼
    with st.form("trend_form"):
        start_date = st.date_input("시작일", value=pd.to_datetime("2017-01-01"))
        end_date = st.date_input("종료일", value=pd.to_datetime("2017-04-30"))
        time_unit = st.selectbox("시간 단위", ["date", "week", "month"], index=2)
        group1 = st.text_input("그룹1 이름", value="한글")
        keywords1 = st.text_input("그룹1 키워드(쉼표로 구분)", value="한글,korean")
        group2 = st.text_input("그룹2 이름", value="영어")
        keywords2 = st.text_input("그룹2 키워드(쉼표로 구분)", value="영어,english")
        device = st.selectbox("디바이스", ["all", "pc", "mo"], index=1)
        ages = st.multiselect("연령대", ["1","2","3","4","5","6"], default=["1","2"])
        gender = st.selectbox("성별", ["all", "m", "f"], index=2)
        submit_trend = st.form_submit_button("트렌드 조회")

    def get_naver_trend(client_id, client_secret, start_date, end_date, time_unit, group1, keywords1, group2, keywords2, device, ages, gender):
        url = "https://openapi.naver.com/v1/datalab/search"
        body = {
            "startDate": str(start_date),
            "endDate": str(end_date),
            "timeUnit": time_unit,
            "keywordGroups": [
                {"groupName": group1, "keywords": [k.strip() for k in keywords1.split(",") if k.strip()]},
                {"groupName": group2, "keywords": [k.strip() for k in keywords2.split(",") if k.strip()]}
            ],
            "device": device,
            "ages": ages,
            "gender": gender
        }
        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", client_id)
        request.add_header("X-Naver-Client-Secret", client_secret)
        request.add_header("Content-Type", "application/json")
        try:
            response = urllib.request.urlopen(request, data=json.dumps(body).encode("utf-8"))
            rescode = response.getcode()
            if rescode == 200:
                response_body = response.read()
                return json.loads(response_body.decode("utf-8"))
            else:
                error_body = response.read().decode("utf-8")
                return {"error": f"Error Code: {rescode}", "details": error_body}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if hasattr(e, 'read') else str(e.reason)
            return {"error": f"HTTP 오류: {e.code}", "details": error_body}
        except urllib.error.URLError as e:
            return {"error": f"URL 오류: {str(e)}"}
        except json.JSONDecodeError as e:
            return {"error": f"JSON 파싱 오류: {str(e)}"}
        except Exception as e:
            return {"error": f"예상치 못한 오류: {str(e)}"}

    if submit_trend:
        with st.spinner("트렌드 조회 중..."):
            result = get_naver_trend(
                NAVER_CLIENT_ID, NAVER_CLIENT_SECRET,
                start_date, end_date, time_unit,
                group1, keywords1, group2, keywords2,
                device, ages, gender
            )
            if "results" in result:
                st.success("트렌드 데이터 조회 성공!")
                st.json(result)
            else:
                st.error(f"트렌드 조회 실패: {result.get('error')}")

# 탭 5: 로그(콘솔)
with tab5:
    st.header("📝 로그(콘솔 출력)")
    st.code(log_stream.getvalue(), language="text")
    if st.button("로그 초기화"):
        log_stream.truncate(0)
        log_stream.seek(0)

# 푸터
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>네이버 API를 활용한 키워드 분석 도구</p>
    <p>⚠️ API 키는 안전하게 관리해주세요</p>
</div>
""", unsafe_allow_html=True)

# Streamlit은 모듈 레벨에서 실행되므로 if __name__ == "__main__" 블록은 필요 없음