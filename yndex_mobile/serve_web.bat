@echo off
title Yandex Music Analytics (Production Web)
echo ========================================================
echo  Запуск готовой веб-версии Flutter Web (Release Build)
echo  Адрес в браузере: http://localhost:8080
echo ========================================================
python -m http.server 8080 --directory build\web
pause
