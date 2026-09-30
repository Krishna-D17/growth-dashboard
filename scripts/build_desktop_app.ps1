# SocialScope Automated Desktop Application Build Script

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "     SocialScope Windows Packaging Build Script    " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$rootDir = Resolve-Path "."
$venvPython = Join-Path $rootDir "backend\.venv\Scripts\python.exe"
$pyinstallerExe = Join-Path $rootDir "backend\.venv\Scripts\pyinstaller.exe"

# Terminate any running SocialScope or postgres processes to release file locks
cmd /c "taskkill /F /IM SocialScope.exe 2>nul & taskkill /F /IM postgres.exe 2>nul & exit 0"
Start-Sleep -Seconds 1
if (Test-Path (Join-Path $rootDir "dist\SocialScope")) {
    Remove-Item -Path (Join-Path $rootDir "dist\SocialScope") -Recurse -Force -ErrorAction SilentlyContinue
}
if (Test-Path (Join-Path $rootDir "build\SocialScope")) {
    Remove-Item -Path (Join-Path $rootDir "build\SocialScope") -Recurse -Force -ErrorAction SilentlyContinue
}

# 1. Build Compiled Frontend SPA Static Bundle
Write-Host "`n[1/5] Building Frontend React SPA Bundle..." -ForegroundColor Yellow
npm --prefix frontend run build
if ($LASTEXITCODE -ne 0) {
    Write-Error "Frontend build failed."
}

# 2. Bundle PostgreSQL Runtime
Write-Host "`n[2/5] Verifying PostgreSQL runtime dependencies..." -ForegroundColor Yellow
$pgTarget = Join-Path $rootDir "postgres"
if (-not (Test-Path "$pgTarget\bin\initdb.exe")) {
    $pgSource = "C:\Program Files\PostgreSQL\18"
    if (Test-Path "$pgSource\bin\initdb.exe") {
        Write-Host "Populating postgres directory from $pgSource..." -ForegroundColor Gray
        New-Item -ItemType Directory -Force -Path "$pgTarget\bin", "$pgTarget\lib", "$pgTarget\share" | Out-Null
        Copy-Item -Path "$pgSource\bin\*" -Destination "$pgTarget\bin" -Recurse -Force
        Copy-Item -Path "$pgSource\lib\*" -Destination "$pgTarget\lib" -Recurse -Force
        Copy-Item -Path "$pgSource\share\*" -Destination "$pgTarget\share" -Recurse -Force
    } else {
        Write-Error "System PostgreSQL runtime not found at $pgSource to populate bundled binaries."
    }
}

# 3. Check / Install PyInstaller
Write-Host "`n[3/5] Checking PyInstaller availability..." -ForegroundColor Yellow
if (-not (Test-Path $pyinstallerExe)) {
    Write-Host "Installing pyinstaller in virtual environment..." -ForegroundColor Gray
    & $venvPython -m pip install pyinstaller
}

# 4. Execute PyInstaller Build with SocialScope.spec
Write-Host "`n[4/5] Building SocialScope PyInstaller executable bundle..." -ForegroundColor Yellow
$env:PYTHONPATH = "backend"
& $pyinstallerExe SocialScope.spec --noconfirm --clean

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed."
}

# Clean up intermediate build binary to prevent launching uncollected executable from build/
Remove-Item -Path (Join-Path $rootDir "build\SocialScope\SocialScope.exe") -Force -ErrorAction SilentlyContinue

# Ensure postgres folder exists in dist/SocialScope/postgres
$distPg = Join-Path $rootDir "dist\SocialScope\postgres"
if (-not (Test-Path "$distPg\bin\initdb.exe")) {
    Write-Host "Copying postgres binaries into dist output directory..." -ForegroundColor Gray
    Copy-Item -Path $pgTarget -Destination (Join-Path $rootDir "dist\SocialScope\") -Recurse -Force
}

# 5. Verify Built Executable and PostgreSQL Binaries
$distExe = Join-Path $rootDir "dist\SocialScope\SocialScope.exe"
$distInitDb = Join-Path $rootDir "dist\SocialScope\postgres\bin\initdb.exe"

if ((Test-Path $distExe) -and (Test-Path $distInitDb)) {
    Write-Host "`n==================================================" -ForegroundColor Green
    Write-Host " SUCCESS: SocialScope Standalone App Built!" -ForegroundColor Green
    Write-Host " Output Executable: $distExe" -ForegroundColor Green
    Write-Host " Bundled PostgreSQL: $distInitDb" -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green
} else {
    Write-Error "SocialScope.exe or bundled postgres binaries missing from build output."
}

