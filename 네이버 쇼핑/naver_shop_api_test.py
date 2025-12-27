import os
import urllib.request
import urllib.parse
import json

# 환경 변수에서 API 키 가져오기 (없으면 빈 문자열)
client_id = os.getenv("NAVER_CLIENT_ID", "")
client_secret = os.getenv("NAVER_CLIENT_SECRET", "")

if not client_id or not client_secret:
    print("⚠️  경고: API 키가 설정되지 않았습니다.")
    print("환경 변수를 설정하거나 코드에서 직접 입력해주세요.")
    print("예: export NAVER_CLIENT_ID='your_client_id'")
    print("    export NAVER_CLIENT_SECRET='your_client_secret'")
    exit(1)

query = "라면"
encText = urllib.parse.quote(query)
url = f"https://openapi.naver.com/v1/search/shop.json?query={encText}&display=30"

request = urllib.request.Request(url)
request.add_header("X-Naver-Client-Id", client_id)
request.add_header("X-Naver-Client-Secret", client_secret)

try:
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if rescode == 200:
        print("✅ API 호출 성공!")
        response_body = response.read().decode('utf-8')
        print(response_body)
    else:
        print(f"❌ API 오류: {rescode}")
        print(response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(f"❌ HTTP 오류: {e.code} - {e.reason}")
    error_body = e.read().decode('utf-8') if hasattr(e, 'read') else ""
    print(error_body)
except urllib.error.URLError as e:
    print(f"❌ URL 오류: {str(e)}")
except Exception as e:
    print(f"❌ 예상치 못한 오류: {str(e)}")
