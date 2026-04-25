Write-Host "=== GateMaster Startup ===" -ForegroundColor Cyan

# Ensure we are in the script directory
Set-Location -Path $PSScriptRoot

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Set Flask app path
Write-Host "Setting FLASK_APP..." -ForegroundColor Yellow
$env:FLASK_APP = "src/app.py"

# Run Flask server
Write-Host "Starting GateMaster backend..." -ForegroundColor Green
flask run --host=0.0.0.0 --port=5000
