@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 현재 디렉터리:
cd
echo.
echo Streamlit 앱을 시작합니다...
echo 브라우저에서 http://localhost:8501 로 접속하세요.
echo.
python -m streamlit run naver_keyword_app.py --server.port 8501
pause

