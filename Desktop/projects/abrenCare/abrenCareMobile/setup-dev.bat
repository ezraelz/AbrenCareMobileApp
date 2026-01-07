@echo off
setlocal enabledelayedexpansion

REM ======================================================
REM One-command dev setup for React Native + Expo + Django
REM ======================================================

echo ======================================================
echo REACT NATIVE + EXPO + DJANGO DEV SETUP
echo ======================================================

REM ======================================================
REM Step 0: Detect local PC IP
REM ======================================================
echo [0/8] Detecting local IP address...
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /i "IPv4"') do (
    set "IP=%%A"
    set "IP=!IP: =!"
    goto :ip_found
)
echo ❌ ERROR: Could not detect IP address
pause
exit /b 1

:ip_found
echo ✅ Detected IP: %IP%
echo.

REM ======================================================
REM Step 1: Clean node_modules
REM ======================================================
echo [1/8] Cleaning node_modules...
if exist node_modules (
    echo Removing node_modules...
    rd /s /q node_modules 2>nul
    if exist node_modules (
        echo ❌ WARNING: Failed to delete node_modules
    ) else (
        echo ✅ node_modules removed
    )
) else (
    echo ℹ️ node_modules not found, skipping...
)
echo.

REM ======================================================
REM Step 2: Install packages
REM ======================================================
echo [2/8] Installing npm packages...
call npm install
if errorlevel 1 (
    echo ❌ ERROR: npm install failed
    pause
    exit /b 1
)
echo ✅ Packages installed
echo.

REM ======================================================
REM Step 3: Clean Gradle cache (FIX for plugin resolution error)
REM ======================================================
echo [3/8] Cleaning Gradle cache...
echo Cleaning global Gradle cache...
if exist "%USERPROFILE%\.gradle\caches" (
    rd /s /q "%USERPROFILE%\.gradle\caches" 2>nul
    echo ✅ Global Gradle cache cleaned
) else (
    echo ℹ️ Global Gradle cache not found
)

if exist android (
    echo Cleaning project Gradle cache...
    cd android
    if exist .gradle (
        rd /s /q .gradle 2>nul
        echo ✅ Project Gradle cache cleaned
    )
    cd ..
)
echo.

REM ======================================================
REM Step 4: Clean Gradle build
REM ======================================================
echo [4/8] Cleaning Gradle build...
if exist android (
    cd android
    echo Running gradlew clean...
    call gradlew clean --no-daemon >nul 2>&1
    if errorlevel 1 (
        echo ⚠️ WARNING: Gradle clean failed - trying without --no-daemon
        call gradlew clean >nul 2>&1
        if errorlevel 1 (
            echo ⚠️ WARNING: Gradle clean failed - continuing anyway
        ) else (
            echo ✅ Gradle clean completed
        )
    ) else (
        echo ✅ Gradle clean completed
    )
    cd ..
) else (
    echo ℹ️ Android folder not found, skipping...
)
echo.

REM ======================================================
REM Step 5: Clear Expo cache
REM ======================================================
echo [5/8] Clearing Expo cache...
call npx expo start --clear --no-interactive >nul 2>&1
timeout /t 3 /nobreak >nul
taskkill /F /IM node.exe >nul 2>&1
taskkill /F /IM java.exe >nul 2>&1
echo ✅ Expo cache cleared
echo.

REM ======================================================
REM Step 6: Update API endpoint (FIXED PowerShell syntax)
REM ======================================================
echo [6/8] Updating API endpoints to use IP: %IP%...
set "API_FILE=services\api.ts"

if exist "%API_FILE%" (
    echo Updating %API_FILE%...
    
    REM Create a PowerShell script file
    echo $content = Get-Content '%API_FILE%' -Raw > "%TEMP%\update_api.ps1"
    echo $updated = $content -replace 'http://[0-9\.]+:8000','http://%IP%:8000' >> "%TEMP%\update_api.ps1"
    echo $updated = $updated -replace 'http://localhost:8000','http://%IP%:8000' >> "%TEMP%\update_api.ps1"
    echo $updated = $updated -replace 'http://127.0.0.1:8000','http://%IP%:8000' >> "%TEMP%\update_api.ps1"
    echo Set-Content '%API_FILE%' $updated -Encoding UTF8 >> "%TEMP%\update_api.ps1"
    echo Write-Host '✅ API endpoints updated' -ForegroundColor Green >> "%TEMP%\update_api.ps1"
    
    REM Execute PowerShell script
    powershell -ExecutionPolicy Bypass -File "%TEMP%\update_api.ps1"
    
    REM Clean up
    del "%TEMP%\update_api.ps1" 2>nul
) else (
    echo ⚠️ WARNING: %API_FILE% not found
)
echo.

REM ======================================================
REM Step 7: Test Django connection (FIXED PowerShell syntax)
REM ======================================================
echo [7/8] Testing Django connection...
echo Testing http://%IP%:8000/...

REM Create a PowerShell script for testing
echo $url = 'http://%IP%:8000/' > "%TEMP%\test_django.ps1"
echo try { >> "%TEMP%\test_django.ps1"
echo     $response = Invoke-WebRequest -Uri $url -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue >> "%TEMP%\test_django.ps1"
echo     if ($response.StatusCode -eq 200) { >> "%TEMP%\test_django.ps1"
echo         Write-Host '✅ Django server is responding' -ForegroundColor Green >> "%TEMP%\test_django.ps1"
echo     } else { >> "%TEMP%\test_django.ps1"
echo         Write-Host '⚠️ WARNING: Django returned status ' + $response.StatusCode -ForegroundColor Yellow >> "%TEMP%\test_django.ps1"
echo     } >> "%TEMP%\test_django.ps1"
echo } catch { >> "%TEMP%\test_django.ps1"
echo     Write-Host '⚠️ WARNING: Cannot reach Django server' -ForegroundColor Yellow >> "%TEMP%\test_django.ps1"
echo     Write-Host '   Make sure Django is running: python manage.py runserver 0.0.0.0:8000' -ForegroundColor Yellow >> "%TEMP%\test_django.ps1"
echo } >> "%TEMP%\test_django.ps1"

REM Execute PowerShell script
powershell -ExecutionPolicy Bypass -File "%TEMP%\test_django.ps1"

REM Clean up
del "%TEMP%\test_django.ps1" 2>nul
echo.

REM ======================================================
REM Step 8: Build dev client (with retry logic)
REM ======================================================
echo [8/8] Building Android dev client...
echo This may take several minutes...
echo.

set choice=Y
REM Comment the line below if you want to manually choose
REM set /p choice=Build Android dev client now? (Y/N): 

if /i "!choice!"=="Y" (
    echo Starting build process...
    echo.
    echo Tip: If build fails, try these manual fixes:
    echo 1. Delete android/.gradle folder
    echo 2. Run: cd android && gradlew clean
    echo 3. Run: npx expo prebuild --clean
    echo.
    
    REM Try building with clean option
    call npx expo run:android --clean
    if errorlevel 1 (
        echo.
        echo ⚠️ Build failed! Trying alternative approach...
        echo Running gradlew clean and retrying...
        
        cd android
        call gradlew clean
        cd ..
        
        timeout /t 2 /nobreak >nul
        
        echo Retrying build...
        call npx expo run:android
    )
) else (
    echo Skipping build. You can run manually with: npx expo run:android
)
echo.

REM ======================================================
REM Final instructions
REM ======================================================
echo ======================================================
echo ✅ SETUP COMPLETE!
echo ======================================================
echo Next steps:
echo 1. Start Django server: python manage.py runserver 0.0.0.0:8000
echo 2. Start Expo dev server: npx expo start
echo 3. Scan QR code with Expo Go app
echo 4. Make sure your phone is on the same Wi-Fi as %IP%
echo.
echo If Gradle build fails again, try:
echo 1. Delete android/.gradle and android/.idea folders
echo 2. Delete %USERPROFILE%\.gradle\caches folder
echo 3. Run: npx expo prebuild --clean
echo 4. Run: cd android && gradlew clean
echo.
echo Quick fix for Gradle errors:
echo npx expo prebuild --clean
echo npx expo run:android --clean
echo ======================================================
echo.

pause