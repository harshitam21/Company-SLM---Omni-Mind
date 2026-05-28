# OmniMind Enterprise OS Developer Orchestrator
# This script launches both the FastAPI backend and the Vite React frontend.

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "         OMNIMIND ENTERPRISE AI OPERATING SYSTEM        " -ForegroundColor Magenta
Write-Host "                 Local Dev Environment                  " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Start Python Backend
Write-Host "`n[1/2] Starting Python FastAPI Backend Server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.ui.RawUI.WindowTitle = 'OmniMind Core Gateway'; cd backend; py -m pip install -r requirements.txt; py -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

# Wait a brief moment for the backend gateway port to bind
Start-Sleep -Seconds 2
Write-Host "Backend triggered on http://127.0.0.1:8000" -ForegroundColor Green

# 2. Start Vite React Frontend
Write-Host "`n[2/2] Launching Frontend Vite Development Engine..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.ui.RawUI.WindowTitle = 'OmniMind Dashboard console'; cd frontend; npm run dev"

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "Both systems successfully initialized in separate windows." -ForegroundColor Green
Write-Host "Open your browser at http://localhost:5173 to explore." -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Green
