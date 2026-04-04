@echo off
echo ============================================================
echo Customer Success FTE - 24 Hour Stability Test
echo ============================================================
echo.
echo Starting test at: %date% %time%
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if Node.js is available (for frontend)
node --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Node.js not found - frontend tests will be skipped
)

REM Create results directory
mkdir load_test_results 2>nul

REM Check if Locust is installed
locust --version >nul 2>&1
if errorlevel 1 (
    echo Locust not found. Installing...
    pip install locust
    if errorlevel 1 (
        echo ERROR: Failed to install Locust
        pause
        exit /b 1
    )
)

REM Check if pandas is installed (for analysis)
python -c "import pandas" >nul 2>&1
if errorlevel 1 (
    echo Installing pandas for report generation...
    pip install pandas
)

echo.
echo ============================================================
echo Test Configuration
echo ============================================================
echo.
echo Load Test Settings:
echo   - Concurrent Users: 100
echo   - Spawn Rate: 10 users/second
echo   - Duration: 24 hours (86400 seconds)
echo   - Target: http://localhost:8000
echo.
echo Output:
echo   - CSV Results: load_test_results/
echo   - HTML Report: load_test_report.html
echo.
echo ============================================================
echo.

REM Ask user to confirm
echo BEFORE STARTING:
echo 1. Ensure backend is running (python run_both.py)
echo 2. Ensure frontend is running (npm run dev)
echo 3. Close any other applications using port 8000
echo.
pause

REM Start load test
echo Starting Locust load test...
echo This will run for 24 hours. Press Ctrl+C to stop early.
echo.

locust -f tests/load_test.py ^
  --host=http://localhost:8000 ^
  --headless ^
  -u 100 ^
  -r 10 ^
  -t 86400s ^
  --csv=load_test_results/ ^
  --html=load_test_report.html

if errorlevel 1 (
    echo.
    echo Load test encountered an error or was stopped early.
    echo Proceeding with report generation...
    echo.
)

echo.
echo Test completed at: %date% %time%
echo.

REM Generate report
echo Generating report...
python tests/analyze_load_test.py --input=load_test_results/ --output=load_test_report.html

if errorlevel 1 (
    echo.
    echo WARNING: Failed to generate HTML report
    echo CSV files are still available in load_test_results/
    echo.
)

echo.
echo ============================================================
echo Test Complete!
echo ============================================================
echo.
echo Results saved to:
echo   - CSV: load_test_results/
echo   - HTML Report: load_test_report.html
echo.
echo To view the report:
echo   start load_test_report.html
echo.
echo ============================================================
pause
