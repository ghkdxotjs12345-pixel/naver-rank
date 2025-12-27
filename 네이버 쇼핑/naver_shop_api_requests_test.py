import os
import requests

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
url = f"https://openapi.naver.com/v1/search/shop.json?query={query}&display=10"
headers = {
    "X-Naver-Client-Id": client_id,
    "X-Naver-Client-Secret": client_secret
}

try:
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status code: {r.status_code}")
    if r.status_code == 200:
        print("✅ API 호출 성공!")
        print(r.text)
    else:
        print(f"❌ API 오류: {r.status_code}")
        print(r.text)
except requests.exceptions.Timeout:
    print("❌ 요청 시간 초과")
except requests.exceptions.RequestException as e:
    print(f"❌ 요청 실패: {e}")
except Exception as e:
    print(f"❌ 예상치 못한 오류: {e}")
