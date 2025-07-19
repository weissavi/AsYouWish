@echo off
echo === CLEAN GIT PUSH START ===

:: Step 1: Create orphan branch
echo [1/6] Creating orphan branch...
git checkout --orphan clean-main

:: Step 2: Add current files only
echo [2/6] Adding current files...
git add .

:: Step 3: Commit clean state
echo [3/6] Creating clean commit...
git commit -m "Clean commit without secrets"

:: Step 4: Delete old main branch
echo [4/6] Deleting old main branch...
git branch -D main

:: Step 5: Rename current branch to main
echo [5/6] Renaming branch to main...
git branch -m main

:: Step 6: Push force to GitHub
echo [6/6] Pushing to GitHub with force...
git push -f origin main

echo === CLEAN PUSH COMPLETE ===
pause
