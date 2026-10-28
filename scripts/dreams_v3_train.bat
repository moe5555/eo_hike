@echo off
rem Dreams v3 GAN training (NVlabs stylegan3 repo, --cfg=stylegan2 with ADA). Run from the repo root.
rem   scripts\dreams_v3_train.bat base           3000
rem   scripts\dreams_v3_train.bat agent_scratch  3000
rem   scripts\dreams_v3_train.bat agent_finetune 800  path\to\base-snapshot.pkl
rem   scripts\dreams_v3_train.bat timing         200     (base data, stops after 200 kimg: for the projection)
rem Outputs: runs\global_baseline_s0\dreams_v3\gan\<run>\<NNNNN-...>\ (every network-snapshot-*.pkl and fakes*.png kept)
setlocal
set RUN=%1
set KIMG=%2
set RESUME=%3
set AGENT=global_baseline_s0
set OUT=runs\%AGENT%\dreams_v3\gan\%RUN%
if "%RUN%"=="base" set DATA=data\v3\base_global\base_global.zip
if "%RUN%"=="timing" set DATA=data\v3\base_global\base_global.zip
if "%RUN%"=="agent_scratch" set DATA=data\v3\%AGENT%\agent_path\agent_path.zip
if "%RUN%"=="agent_finetune" set DATA=data\v3\%AGENT%\agent_path\agent_path.zip
rem batch 32 as in the brief, accumulated over 2 x 16 per GPU pass: at 32 per pass the Quadro RTX 5000 (16 GB, WDDM)
rem runs out of memory and spills into system RAM (measured 1,390 s/kimg). Override with set BATCH_GPU=32.
if "%BATCH_GPU%"=="" set BATCH_GPU=16
set EXTRA=
if not "%RESUME%"=="" set EXTRA=--resume=%RESUME%
if not exist logs mkdir logs
call "%~dp0sg.bat" third_party\stylegan3\train.py --outdir=%OUT% --cfg=stylegan2 --data=%DATA% --gpus=1 --batch=32 --batch-gpu=%BATCH_GPU% --gamma=1 --mirror=1 --aug=ada --metrics=none --snap=50 --kimg=%KIMG% %EXTRA% > logs\gan_%RUN%.log 2>&1
endlocal
