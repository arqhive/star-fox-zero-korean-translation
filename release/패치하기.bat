@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"

rem 배포 묶음 구조:
rem   패치하기.bat
rem   python\python.exe      (python.org embeddable + numpy, Pillow)
rem   tools\ translation\
rem   data003.cpk            (사용자가 직접 넣는 원본)

set PY=python\python.exe
if not exist "%PY%" set PY=python

echo.
echo  스타폭스 제로 한글 패치
echo  -----------------------
echo.

if not exist "data003.cpk" (
  echo  원본 data003.cpk 를 이 폴더에 넣고 다시 실행해 주세요.
  echo.
  pause
  exit /b 1
)

"%PY%" tools\patch.py data003.cpk -o out
if errorlevel 1 (
  echo.
  echo  실패했습니다. 위 메시지를 확인해 주세요.
  pause
  exit /b 1
)

echo.
echo  끝났습니다. out\data003.cpk 를 SD카드나 Cemu 그래픽 팩에 넣으세요.
echo  자세한 위치는 README_한국어.txt 를 봐 주세요.
echo.
pause
