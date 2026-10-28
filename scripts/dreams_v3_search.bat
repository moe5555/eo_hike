@echo off
rem Dreams v3 searches and report, started as each GAN's final snapshot appears (runs beside the training chain).
rem   start "" /min scripts\dreams_v3_search.bat
rem B, C (+ base plain samples) after base; A (+ finetune samples) after agent_finetune; A0 (+ scratch samples) and
rem the report after agent_scratch. Same R sweep, seeds and betas for every condition.
setlocal enabledelayedexpansion
cd /d "%~dp0.."
set G=runs\global_baseline_s0
set C=runs\confined_baseline_s0
set GAN=%G%\dreams_v3\gan
set SWEEP=--reach 0.7 1.0 1.5 2.0 3.0 --seed 0 1 2 --beta 0.3 0
set REF=%G%\dreams_v3\reference
set LOG=logs\dreams_v3_search.log

call :waitfor "%GAN%\base" network-snapshot-003000.pkl
set BASE=!FOUND!
call :waitfor "%GAN%\agent_finetune" network-snapshot-000800.pkl
set FT=!FOUND!
call :waitfor "%GAN%\agent_scratch" network-snapshot-003000.pkl
set SC=!FOUND!
echo %date% %time% all done >> %LOG%
call .venv\Scripts\python.exe -m gen.dreams_v3_report %G% %C% >> logs\dreams_v3_report.log 2>&1
echo %date% %time% report done >> %LOG%
goto :eof

:waitfor
set FOUND=
for /f "delims=" %%f in ('dir /b /s "%~1\%~2" 2^>nul') do set FOUND=%%f
if "!FOUND!"=="" (
    timeout /t 600 /nobreak >nul
    goto waitfor
)
timeout /t 120 /nobreak >nul
echo %date% %time% found !FOUND! >> %LOG%
if "%~2"=="network-snapshot-003000.pkl" if "%~1"=="%GAN%\base" (
    call scripts\sg.bat -m gen.dream_search --gan "!FOUND!" --plain 64 --tag base --out %REF% >> %LOG% 2>&1
    call scripts\sg.bat -m gen.dream_search --gan "!FOUND!" --gan_name base --agent_run %G% --condition B %SWEEP% >> %LOG% 2>&1
    call scripts\sg.bat -m gen.dream_search --gan "!FOUND!" --gan_name base --agent_run %C% --condition C %SWEEP% >> %LOG% 2>&1
)
if "%~1"=="%GAN%\agent_finetune" (
    call scripts\sg.bat -m gen.dream_search --gan "!FOUND!" --plain 64 --tag agent_finetune --out %REF% >> %LOG% 2>&1
    call scripts\sg.bat -m gen.dream_search --gan "!FOUND!" --gan_name agent_finetune --agent_run %G% --condition A %SWEEP% >> %LOG% 2>&1
)
if "%~1"=="%GAN%\agent_scratch" (
    call scripts\sg.bat -m gen.dream_search --gan "!FOUND!" --plain 64 --tag agent_scratch --out %REF% >> %LOG% 2>&1
    call scripts\sg.bat -m gen.dream_search --gan "!FOUND!" --gan_name agent_scratch --agent_run %G% --condition A0 %SWEEP% >> %LOG% 2>&1
)
goto :eof
