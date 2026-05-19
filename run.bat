@echo off
echo ==========================================
echo   🌟 丽声自然拼读打卡系统
echo ==========================================
echo.
echo 正在启动...请稍候
echo.
cd /d "%~dp0"
streamlit run app.py --server.port 8501 --server.headless true
echo.
pause
