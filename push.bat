@echo off
setlocal

:: בדיקת פרמטר ראשון (שם הבראנץ')
if "%~1"=="" (
    echo ⚠️  לא הוזן שם לענף. יש להפעיל כך:
    echo     push my-feature-branch
    exit /b 1
)

set BRANCH=%1

echo === GIT PUSH: %BRANCH% ===

:: Step 1: בנה או עבור לענף בשם שניתן
git checkout -B %BRANCH%

:: Step 2: הוסף את כל השינויים כולל מחיקות
git add -A

:: Step 3: קומיט עם חותמת זמן
git commit -m "Auto update to branch [%BRANCH%] - %date% %time%"

:: Step 4: דחיפה
git push -u origin %BRANCH%

echo === PUSH TO [%BRANCH%] COMPLETE ===
pause
