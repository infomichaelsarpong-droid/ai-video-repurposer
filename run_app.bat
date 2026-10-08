@echo off
title AI 4K Viral Shorts Factory Launcher
echo ========================================================
echo   Launching AI 4K Viral Shorts Factory (100%% Free Local)
echo ========================================================
echo.

echo [1/2] Verifying packages & FFmpeg engine...
pip install -q streamlit yt-dlp youtube-transcript-api imageio-ffmpeg

echo.
echo [2/2] Starting Web Dashboard at http://localhost:8501 ...
echo.
streamlit run app.py

pause
