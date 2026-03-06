@echo off
title Allennetic WhatsApp Bot
color 0A
echo.
echo  ==========================================
echo   ALLENNETIC WHATSAPP AUTO-REPLY BOT
echo  ==========================================
echo.
REM ANTHROPIC_API_KEY is loaded from .env — do not hardcode here
REM Copy .env.example to .env and add your key: ANTHROPIC_API_KEY=sk-ant-...
for /f "tokens=2 delims==" %%a in ('findstr "ANTHROPIC_API_KEY" "%~dp0.env"') do set ANTHROPIC_API_KEY=%%a
cd /d "C:\Users\Allen\Desktop\Marketing Campaign\whatsapp-mcp-ts"
node --experimental-strip-types src/main.ts
pause
