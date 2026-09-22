@echo off
title Build Android APK (Release)
echo ========================================================
echo  🔨 Building Release APK for Android...
echo ========================================================
set "JAVA_HOME=E:\Android_studio\jbr"
set "PATH=%JAVA_HOME%\bin;%PATH%"
call flutter build apk --release
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ APK successfully built!
    copy /Y "build\app\outputs\flutter-apk\app-release.apk" "app-release.apk" >nul
    echo 📱 Ready APK copied to: yndex_mobile\app-release.apk
) else (
    echo.
    echo ❌ Build failed with error code %ERRORLEVEL%
)
echo ========================================================
pause

