@echo off
title Build Android APK (Release)
echo ========================================================
echo  🔨 Building Release APK for Android...
echo ========================================================
flutter build apk --release
echo.
echo Ready APK will be located at:
echo build\app\outputs\flutter-apk\app-release.apk
echo ========================================================
pause
