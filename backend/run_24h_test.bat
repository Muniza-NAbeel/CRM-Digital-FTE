@echo off
REM 24-Hour Load Test Runner for Customer Success Digital FTE
REM This script runs continuous load testing for 24 hours

echo ========================================
echo 24-Hour Load Test Starting
echo ========================================

REM Configuration
set HOST=%HOST:-http://localhost:8000%
set DURATION=%DURATION:-24h%
set USERS=%USERS:-50%
set SPAWN_RATE=%SPAWN_RATE:-10%

echo Host: %HOST%
echo Duration: %DURATION%
echo Users: %USERS%
echo Spawn Rate: %SPAWN_RATE%
echo ========================================

REM Check if locust is installed
python -m pip show locust >nul 2>&1
if errorlevel 1 (
    echo Locust not found. Installing...
    pip install locust
)

REM Create results directory
if not exist "test_results" mkdir test_results

REM Get timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%_%datetime:~8,6%

REM Run load test
echo Starting 24-hour load test...
locust ^
    -f tests\test_load.py ^
    --host %HOST% ^
    --headless ^
    --users %USERS% ^
    --spawn-rate %SPAWN_RATE% ^
    --run-time %DURATION% ^
    --html "test_results\load_test_report_%TIMESTAMP%.html" ^
    --csv "test_results\load_test_%TIMESTAMP%" ^
    --autoquit 60

echo ========================================
echo 24-Hour Load Test Complete!
echo ========================================
echo Results saved to: test_results\
echo   - HTML Report: test_results\load_test_report_%TIMESTAMP%.html
echo   - CSV Files: test_results\load_test_%TIMESTAMP%*.csv
echo ========================================

echo.
echo Test Summary:
echo   - Total Duration: %DURATION%
echo   - Concurrent Users: %USERS%
echo   - Spawn Rate: %SPAWN_RATE% users/second
echo.
echo Metrics to Check:
echo   ^✓ Response time (P95 less than 3 seconds)
echo   ^✓ Success rate (greater than 99 percent)
echo   ^✓ Error rate (less than 1 percent)
echo   ^✓ Requests per second
echo.
echo Hackathon Requirements:
echo   ^✓ Web Form: 100+ submissions over 24h
echo   ^✓ Email: 50+ messages processed
echo   ^✓ WhatsApp: 50+ messages processed
echo   ^✓ Cross-channel: 10+ customers
echo   ^✓ Uptime: greater than 99.9 percent
echo   ^✓ P95 latency: less than 3 seconds
echo   ^✓ Escalation rate: less than 25 percent
echo ========================================

pause
