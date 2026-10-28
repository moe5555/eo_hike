@echo off
rem StyleGAN env: MSVC v143 (14.44, the VS 2022 toolset installed with Build Tools 18), English compiler
rem messages, and .venv-sg with ninja on PATH. Usage: scripts\sg.bat [python args]
set VSLANG=1033
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64 -vcvars_ver=14.44 >nul
set DISTUTILS_USE_SDK=1
set PATH=%~dp0..\.venv-sg\Scripts;%PATH%
"%~dp0..\.venv-sg\Scripts\python.exe" %*
