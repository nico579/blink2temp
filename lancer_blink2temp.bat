@echo off
chcp 65001 >nul
title Blink2Temp - Relevé des Températures Outdoor

cd /d "%~dp0"

echo ========================================================
echo    Blink2Temp : Surveillance des Caméras Outdoor
echo ========================================================
echo.
echo  1. Démarrer la surveillance horaire + Tableau de bord Web (http://localhost:8770)
echo  2. Démarrer la surveillance horaire seule (Console)
echo  3. Effectuer un relevé immédiat unique (--once)
echo  4. Consulter les statistiques et l'historique
echo  5. Installer la tâche planifiée Windows (arrière-plan 24/7)
echo  6. Supprimer la tâche planifiée Windows
echo  7. Quitter
echo.
set /p choix="Votre choix [1-7] (défaut: 1) : "

if "%choix%"=="" set choix=1
if "%choix%"=="1" goto option1
if "%choix%"=="2" goto option2
if "%choix%"=="3" goto option3
if "%choix%"=="4" goto option4
if "%choix%"=="5" goto option5
if "%choix%"=="6" goto option6
if "%choix%"=="7" goto fin

:option1
start http://localhost:8770
python blink2temp.py --loop 60 --web
goto pause_fin

:option2
python blink2temp.py --loop 60
goto pause_fin

:option3
python blink2temp.py --once
goto pause_fin

:option4
python blink2temp.py --stats
python blink2temp.py --history 24
goto pause_fin

:option5
python blink2temp.py --install-task
goto pause_fin

:option6
python blink2temp.py --uninstall-task
goto pause_fin

:pause_fin
echo.
pause

:fin
