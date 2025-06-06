# Запускаем Docker контейнеры, если они не запущены
$containersRunning = docker ps --format '{{.Names}}' | Select-String -Pattern 'news_scrapper_postgres'
if (-not $containersRunning) {
    Write-Host "Starting Docker containers..."
    docker-compose up -d
    
    # Ждем 5 секунд, чтобы контейнеры успели запуститься
    Start-Sleep -Seconds 5
}

# Проверяем готовность PostgreSQL
Write-Host "Waiting for PostgreSQL to be ready..."
$maxAttempts = 30
$attempt = 1
$ready = $false

while (-not $ready -and $attempt -le $maxAttempts) {
    try {
        $result = docker exec news_scrapper_postgres pg_isready
        if ($result -match "accepting connections") {
            $ready = $true
            Write-Host "PostgreSQL is ready!"
        }
    }
    catch {
        Write-Host "Waiting for PostgreSQL... Attempt $attempt of $maxAttempts"
        Start-Sleep -Seconds 1
        $attempt++
    }
}

if (-not $ready) {
    Write-Host "Error: PostgreSQL failed to start after $maxAttempts attempts"
    exit 1
}

# Активируем виртуальное окружение, если оно существует
if (Test-Path "venv\Scripts\Activate.ps1") {
    . .\venv\Scripts\Activate.ps1
}

# Запускаем тесты с подробным выводом
Write-Host "Running tests..."
pytest -v

# Деактивируем виртуальное окружение
if (Test-Path "venv\Scripts\Activate.ps1") {
    deactivate
}
