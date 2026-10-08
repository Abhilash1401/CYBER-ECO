# PowerShell script to cleanly stop all Cyber Eco servers (backend and frontend)

Write-Host "Stopping Cyber Eco servers..." -ForegroundColor Yellow

# 1. Stop any Docker containers if docker was used
if (Get-Command docker -ErrorAction SilentlyContinue) {
    try {
        docker compose down
    } catch {
        # ignore if not running
    }
}

# 2. Stop processes listening on port 8000 (Backend)
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($port8000) {
    foreach ($pid_to_kill in $port8000) {
        if ($pid_to_kill -gt 0) {
            Write-Host "Stopping Backend process (PID: $pid_to_kill)..." -ForegroundColor Cyan
            Stop-Process -Id $pid_to_kill -Force -ErrorAction SilentlyContinue
        }
    }
}

# 3. Stop processes listening on port 3000 (Frontend)
$port3000 = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($port3000) {
    foreach ($pid_to_kill in $port3000) {
        if ($pid_to_kill -gt 0) {
            Write-Host "Stopping Frontend process (PID: $pid_to_kill)..." -ForegroundColor Cyan
            Stop-Process -Id $pid_to_kill -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "All Cyber Eco services have been stopped successfully." -ForegroundColor Green
