@echo off
chcp 65001 > nul
title QUAN AI BRAIN — Mo Trap Tri Nho Chuyen Sau (SQLite)
echo ======================================================================
echo    QUAN AI BRAIN — MO TRAP TRI NHO CHUYEN SAU (DB BROWSER FOR SQLITE)
echo ======================================================================
echo Dang mo kho tri nho: data\brain.db ...
start "" "%~dp0tools\DBBrowser\DB Browser for SQLite.exe" "%~dp0data\brain.db"
exit
