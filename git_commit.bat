@echo off
REM Git commit and push script

echo.
echo ================================
echo Fundamental Data Pipeline
echo Git Commit Script
echo ================================
echo.

REM Configure git
git config user.name "Development Team"
git config user.email "dev@fundamental-pipeline.local"

echo Adding all files...
git add -A

echo.
echo Committing changes...
git commit -F COMMIT_MESSAGE.txt

echo.
echo Commit completed!
echo.

REM Ask if user wants to push
echo Would you like to push to remote? (Y/N)
set /p push_choice=

if /i "%push_choice%"=="Y" (
    echo.
    echo Pushing to remote...
    git push
    echo.
    echo Push completed!
) else (
    echo.
    echo Skipping push. You can push later with: git push
)

echo.
echo Done!
pause

