@echo off
rem Dreams v3: after base finishes, train agent_finetune (resumed from base's final snapshot), then agent_scratch.
rem   start "" /min scripts\dreams_v3_chain.bat       (from the repo root; waits for base's kimg-3000 snapshot)
setlocal enabledelayedexpansion
cd /d "%~dp0.."
set BASEDIR=runs\global_baseline_s0\dreams_v3\gan\base
:wait
set FOUND=
for /f "delims=" %%f in ('dir /b /s "%BASEDIR%\network-snapshot-003000.pkl" 2^>nul') do set FOUND=%%f
if "!FOUND!"=="" (
    timeout /t 600 /nobreak >nul
    goto wait
)
rem let the base trainer write its last files and exit
timeout /t 300 /nobreak >nul
echo %date% %time% base done: !FOUND! >> logs\gan_chain.log
call scripts\dreams_v3_train.bat agent_finetune 800 "!FOUND!"
echo %date% %time% agent_finetune done >> logs\gan_chain.log
call scripts\dreams_v3_train.bat agent_scratch 3000
echo %date% %time% agent_scratch done >> logs\gan_chain.log
endlocal
