@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0run_validation_suite.ps1" %*
exit /b %ERRORLEVEL%
