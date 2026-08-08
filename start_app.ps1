# Start application via Docker
$max_attempts = 12
$attempt = 1
$started = $false

Write-Output "Checking if Docker is running..."
while ($attempt -le $max_attempts) {
    & docker info >$null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Output "Docker is ready! Starting containers..."
        & docker compose up -d --build
        $started = $true
        break
    }
    Write-Output "Waiting for Docker Desktop to start... (Attempt $attempt of $max_attempts)"
    Start-Sleep -Seconds 5
    $attempt++
}

if (-not $started) {
    Write-Error "Docker Desktop did not start in time. Please make sure Docker Desktop is running and try again."
    exit 1
}
