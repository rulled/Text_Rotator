# Полная версия скрипта сборки на PowerShell
Write-Host "Starting Text Rotator Release Build..." -ForegroundColor Green

$PROJECT_ROOT = $PSScriptRoot
if (-not $PROJECT_ROOT.EndsWith("\")) {
    $PROJECT_ROOT = "$PROJECT_ROOT\"
}

Write-Host "Extracting version information..." -ForegroundColor Yellow
# Извлечение версии
$versionLine = Get-Content -Path "text_rotator.py" | Where-Object { $_ -match "^__version__\s*=" }

if (-not $versionLine) {
    Write-Host "ERROR: Version line not found in text_rotator.py" -ForegroundColor Red
    Read-Host "Press ENTER to exit"
    exit 1
}

$versionMatch = $versionLine -match "__version__\s*=\s*[""']([0-9]+\.[0-9]+\.[0-9]+)[""']"

if (-not $matches -or -not $matches[1]) {
    Write-Host "ERROR: Could not extract version number. Format should be: __version__ = ""X.Y.Z""" -ForegroundColor Red
    Read-Host "Press ENTER to exit"
    exit 1
}

$VERSION = $matches[1]
Write-Host "Detected version: [$VERSION]" -ForegroundColor Cyan

# Проверка предыдущей версии
$PREV_VERSION_FILE = "$env:TEMP\prev_version.txt"
if (Test-Path $PREV_VERSION_FILE) {
    $PREV_VERSION = Get-Content -Path $PREV_VERSION_FILE -Raw
    Write-Host "Previous built version: $PREV_VERSION" -ForegroundColor Cyan

    if ($PREV_VERSION -eq $VERSION) {
        Write-Host "WARNING: Current version ($VERSION) is the same as previous build." -ForegroundColor Yellow
        $CONTINUE = Read-Host "Are you sure you want to continue with the same version? (y/n)"
        if ($CONTINUE -ne "y") {
            Write-Host "Build aborted by user." -ForegroundColor Yellow
            Read-Host "Press ENTER to exit"
            exit 0
        }
    }
}

Write-Host "Installing/Updating dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host "Running PyInstaller..." -ForegroundColor Yellow
$pyInstallerArgs = @(
    "--name", "TextRotator",
    "--onefile",
    "--windowed",
    "--icon=assets/app.ico",
    "--add-data=assets;assets",
    "--add-data=models;models", 
    "--add-data=ui;ui",
    "--add-data=utils;utils",
    "--clean",
    "text_rotator.py"
)

pyinstaller $pyInstallerArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n!!!!! PyInstaller Build FAILED !!!!!" -ForegroundColor Red
    Read-Host "Press ENTER to exit"
    exit 1
}

Write-Host "`nBuild completed successfully!" -ForegroundColor Green
Write-Host "Your executable is located in the 'dist' folder: $($PROJECT_ROOT)dist\TextRotator.exe`n" -ForegroundColor Green

# Сохранение версии
$VERSION | Out-File -FilePath $PREV_VERSION_FILE -Encoding ASCII

$PUBLISH_TO_GITHUB = Read-Host "Do you want to publish this build to GitHub as release v$VERSION? (y/n)"
if ($PUBLISH_TO_GITHUB -ne "y") {
    Write-Host "`nBuild process completed without GitHub release." -ForegroundColor Cyan
    Write-Host "You can manually publish the release later." -ForegroundColor Cyan
    Read-Host "Press ENTER to exit"
    exit 0
}

# Проверка наличия GitHub CLI
$ghInstalled = Get-Command gh -ErrorAction SilentlyContinue
if (-not $ghInstalled) {
    Write-Host "ERROR: GitHub CLI (gh) is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install GitHub CLI from https://cli.github.com/" -ForegroundColor Yellow
    Write-Host "After installation, run 'gh auth login' to authenticate." -ForegroundColor Yellow
    Read-Host "Press ENTER to exit"
    exit 1
}

# Проверка авторизации
try {
    $authStatus = gh auth status 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Not authenticated"
    }
}
catch {
    Write-Host "ERROR: Not authenticated with GitHub." -ForegroundColor Red
    Write-Host "Please run 'gh auth login' to authenticate." -ForegroundColor Yellow
    Read-Host "Press ENTER to exit"
    exit 1
}

# Проверка существования тега версии
Write-Host "Checking if version tag v$VERSION already exists..." -ForegroundColor Yellow
try {
    $releaseExists = gh release view "v$VERSION" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "WARNING: Release v$VERSION already exists on GitHub." -ForegroundColor Yellow
        $CONTINUE = Read-Host "Do you want to continue and overwrite it? (y/n)"
        if ($CONTINUE -ne "y") {
            Write-Host "GitHub release aborted by user." -ForegroundColor Yellow
            Write-Host "Build is still available at: $($PROJECT_ROOT)dist\TextRotator.exe" -ForegroundColor Green
            Read-Host "Press ENTER to exit"
            exit 0
        }
    }
}
catch {
    # Релиз не существует, продолжаем
}

# Создание примечаний к релизу
Write-Host "Creating release notes..." -ForegroundColor Yellow
$NOTES_FILE = "$env:TEMP\release_notes_$VERSION.md"

$releaseNotes = @"
# Text Rotator v$VERSION

Release date: $(Get-Date -Format "yyyy-MM-dd")

## Что нового

- Обновление системы автоматических обновлений
- Улучшения стабильности

"@

# Используем UTF8 с BOM для правильного отображения кириллицы
[System.IO.File]::WriteAllText($NOTES_FILE, $releaseNotes, [System.Text.Encoding]::UTF8)

Write-Host "Release notes created. Please review and edit them if needed." -ForegroundColor Cyan
Write-Host "File location: $NOTES_FILE" -ForegroundColor Cyan
$EDIT_NOTES = Read-Host "Edit release notes now? (y/n)"
if ($EDIT_NOTES -eq "y") {
    Start-Process "notepad" -ArgumentList $NOTES_FILE -Wait
}

# Создание GitHub релиза
Write-Host "Creating GitHub release v$VERSION..." -ForegroundColor Yellow
gh release create "v$VERSION" "$($PROJECT_ROOT)dist\TextRotator.exe" --title "Text Rotator v$VERSION" --notes-file $NOTES_FILE --draft

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n!!!!! GitHub Release Creation FAILED !!!!!" -ForegroundColor Red
    Write-Host "Please check if you have correct permissions and authentication." -ForegroundColor Yellow
    Read-Host "Press ENTER to exit"
    exit 1
}

Write-Host "`nGitHub draft release v$VERSION created successfully!" -ForegroundColor Green
Write-Host "Please review the draft on GitHub and publish when ready.`n" -ForegroundColor Cyan

$PUBLISH = Read-Host "Publish release now? (y/n)"
if ($PUBLISH -eq "y") {
    Write-Host "Publishing release..." -ForegroundColor Yellow
    gh release edit "v$VERSION" --draft=false
    Write-Host "Release v$VERSION published successfully!" -ForegroundColor Green
}

Write-Host "`nBuild and release process completed!`n" -ForegroundColor Green
Read-Host "Press ENTER to exit" 