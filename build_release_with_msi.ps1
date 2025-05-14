# PowerShell Build Script for Text Rotator with MSI and Updater Support
# 1. Собирает .exe через PyInstaller
# 2. Собирает .msi через WiX Toolset Core v4.0.0
# 3. (Опционально) Публикует .msi на GitHub или сервер

Write-Host "Starting Text Rotator Release Build..." -ForegroundColor Green

# --- Configuration ---
$ProjectName = "TextRotator"
$PythonScriptToBuild = "text_rotator.py" # Главный Python скрипт для PyInstaller
$IconPath = "assets/app.ico"
$RequirementsFile = "requirements.txt"
$WxsTemplateFile = "product_v4.wxs" # Имя файла шаблона WiX v4.0 в папке installer

# --- Script Setup ---
$ErrorActionPreference = "Stop" # Останавливать скрипт при ошибках
$PROJECT_ROOT = $PSScriptRoot # Корень проекта - это папка, где лежит этот скрипт

# Убедимся, что PROJECT_ROOT заканчивается на слэш для корректного соединения путей
if (-not $PROJECT_ROOT.EndsWith("\")) { $PROJECT_ROOT = "$PROJECT_ROOT\" }

Write-Host "Project Root: $PROJECT_ROOT" -ForegroundColor DarkGray

# --- Version Extraction ---
Write-Host "Extracting version information from '$PythonScriptToBuild'..." -ForegroundColor Yellow
$VersionRegex = "__version__\s*=\s*[\""']([0-9]+\.[0-9]+\.[0-9]+)[\""']"
$VersionLine = Get-Content -Path (Join-Path -Path $PROJECT_ROOT -ChildPath $PythonScriptToBuild) | Where-Object { $_ -match $VersionRegex }

if (-not $VersionLine) {
    Write-Error "ERROR: Version line not found in '$PythonScriptToBuild' matching regex '$VersionRegex'."
    exit 1
}

$VersionMatch = $VersionLine -match $VersionRegex
if (-not $matches -or -not $matches[1]) {
    Write-Error "ERROR: Could not extract version number from line: '$VersionLine'."
    exit 1
}
$VERSION = $matches[1]
Write-Host "Detected version: [$VERSION]" -ForegroundColor Cyan

# --- Directory Setup ---
$DistDir = Join-Path -Path $PROJECT_ROOT -ChildPath "dist"
$BuildDir = Join-Path -Path $PROJECT_ROOT -ChildPath "build" # Папка для временных файлов PyInstaller
$InstallerDir = Join-Path -Path $PROJECT_ROOT -ChildPath "installer"
$WxsPath = Join-Path -Path $InstallerDir -ChildPath $WxsTemplateFile
$MsiOutputPath = Join-Path -Path $InstallerDir -ChildPath "$($ProjectName)-$($VERSION)-Setup.msi"
$BuiltExePath = Join-Path -Path $DistDir -ChildPath "$($ProjectName).exe"

# Создаем папку для установщика, если ее нет
if (-not (Test-Path $InstallerDir)) {
    Write-Host "Creating installer directory: $InstallerDir" -ForegroundColor DarkGray
    New-Item -ItemType Directory -Force -Path $InstallerDir | Out-Null
}

# --- Dependencies ---
Write-Host "Installing/Updating Python dependencies from '$RequirementsFile'..." -ForegroundColor Yellow
pip install -r (Join-Path -Path $PROJECT_ROOT -ChildPath $RequirementsFile)
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to install Python dependencies."; exit 1 }

# --- PyInstaller Build ---
Write-Host "Running PyInstaller to build '$($ProjectName).exe'..." -ForegroundColor Yellow
# Очищаем предыдущие сборки PyInstaller (папки dist и build)
if (Test-Path $DistDir) { Remove-Item -Recurse -Force $DistDir }
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }

$pyInstallerArgs = @(
    "--name", $ProjectName,
    "--onefile",
    "--windowed",
    "--icon", (Join-Path -Path $PROJECT_ROOT -ChildPath $IconPath),
    # Добавление данных: используем Join-Path для кроссплатформенной совместимости разделителей
    # Формат для --add-data: "source{0}destination" где {0} это os.pathsep (';' для Windows)
    "--add-data", ("{0}{1}assets" -f (Join-Path -Path $PROJECT_ROOT -ChildPath "assets"), [System.IO.Path]::PathSeparator),
    "--add-data", ("{0}{1}models" -f (Join-Path -Path $PROJECT_ROOT -ChildPath "models"), [System.IO.Path]::PathSeparator),
    "--add-data", ("{0}{1}ui" -f (Join-Path -Path $PROJECT_ROOT -ChildPath "ui"), [System.IO.Path]::PathSeparator),
    "--add-data", ("{0}{1}utils" -f (Join-Path -Path $PROJECT_ROOT -ChildPath "utils"), [System.IO.Path]::PathSeparator),
    "--distpath", $DistDir,
    "--workpath", $BuildDir,
    "--specpath", $PROJECT_ROOT, # Куда положить .spec файл
    "--clean", # Очистить кэш PyInstaller и временные файлы перед сборкой
    (Join-Path -Path $PROJECT_ROOT -ChildPath $PythonScriptToBuild)
)
Write-Host "PyInstaller arguments: $($pyInstallerArgs -join ' ')" -ForegroundColor DarkGray
pyinstaller $pyInstallerArgs
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller build FAILED."; exit 1 }
Write-Host "PyInstaller build completed successfully! EXE is at $BuiltExePath" -ForegroundColor Green

# --- WiX Toolset MSI Build ---
Write-Host "Checking for WiX Toolset..." -ForegroundColor Yellow
$wixExe = Get-Command wix.exe -ErrorAction SilentlyContinue
if (-not $wixExe) {
    Write-Error "ERROR: WiX Toolset 'wix.exe' (v4.0.0) not found in PATH."
    Write-Warning "Please install WiX Toolset Core v4.0.0 from https://wixtoolset.org/releases/ and ensure 'wix.exe' is in your PATH."
    exit 1
}

# Verify WiX version
$wixVersion = & wix --version
Write-Host "WiX Toolset version: $wixVersion" -ForegroundColor DarkGray
if (-not $wixVersion.StartsWith("4.0")) {
    Write-Warning "WARNING: This script is optimized for WiX Toolset Core v4.0.0. You are using $wixVersion."
    Write-Warning "Some commands may not work as expected."
}

Write-Host "WiX Toolset found at: $($wixExe.Source)" -ForegroundColor DarkGray

# Проверяем наличие .exe файла от PyInstaller
if (-not (Test-Path -Path $BuiltExePath -PathType Leaf)) {
    Write-Error "ERROR: Built executable not found at '$BuiltExePath'. PyInstaller might have failed."
    exit 1
}

# Проверяем наличие .wxs файла шаблона
if (-not (Test-Path -Path $WxsPath -PathType Leaf)) {
    Write-Error "ERROR: WiX template file not found at '$WxsPath'."
    exit 1
}

Write-Host "Patching '$WxsTemplateFile' with version $VERSION..." -ForegroundColor Yellow
# Заменяем версию в .wxs файле. Убедимся, что кодировка сохраняется (UTF-8).
$WxsContent = Get-Content -Path $WxsPath -Raw
$UpdatedWxsContent = $WxsContent -replace 'Version="[0-9]+\.[0-9]+\.[0-9]+"', "Version=`"$VERSION`""

# Также обновляем версию в реестре
$UpdatedWxsContent = $UpdatedWxsContent -replace 'Name="Version" Value="[0-9]+\.[0-9]+\.[0-9]+"', "Name=`"Version`" Value=`"$VERSION`""

Set-Content -Path $WxsPath -Value $UpdatedWxsContent -Encoding UTF8 -Force
Write-Host "'$WxsTemplateFile' patched successfully." -ForegroundColor DarkGray

Write-Host "Creating MSI installer using WiX Toolset..." -ForegroundColor Yellow
# Команда сборки MSI для WiX установленного через .NET CLI
# Использует команду 'wix build' для сборки .msi из .wxs файла

$wixBuildArgs = @(
    "build",
    $WxsPath,
    "-out", $MsiOutputPath,
    "-bindpath", $PROJECT_ROOT,
    "-bindpath", $DistDir,
    "-bindpath", (Join-Path -Path $PROJECT_ROOT -ChildPath "assets")
    # "-cultures", "ru-ru" # Раскомментируйте, если нужна локализация установщика
)
Write-Host "WiX command: wix $($wixBuildArgs -join ' ')" -ForegroundColor DarkGray

& wix $wixBuildArgs
if ($LASTEXITCODE -ne 0) { 
    Write-Error "MSI build FAILED." 
    Write-Warning "If you see errors about missing files, check that the paths in $WxsTemplateFile are correct."
    Write-Warning "The relative paths in the .wxs file should be relative to the bindpath parameters."
    exit 1
}
Write-Host "MSI installer created successfully! Path: $MsiOutputPath" -ForegroundColor Green

# --- Optional: Publish to GitHub ---
Write-Host "Do you want to publish this release to GitHub? (y/n)" -ForegroundColor Yellow
$publishToGitHub = Read-Host

if ($publishToGitHub -eq "y") {
    Write-Host "Checking GitHub authentication status..." -ForegroundColor Yellow
    $ghStatus = gh auth status 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "You need to authenticate with GitHub first. Run 'gh auth login' and follow the prompts." -ForegroundColor Red
        Write-Host "After authentication, run this script again." -ForegroundColor Red
        exit 1
    }
    
    # Проверяем, находимся ли мы в git репозитории
    if (-not (Test-Path -Path (Join-Path -Path $PROJECT_ROOT -ChildPath ".git"))) {
        Write-Host "This directory is not a git repository. Please initialize a git repository first." -ForegroundColor Red
        exit 1
    }
    
    # Получаем имя репозитория
    $remoteUrl = git remote get-url origin
    if (-not $remoteUrl) {
        Write-Host "No remote 'origin' found. Please set up a remote repository." -ForegroundColor Red
        exit 1
    }
    
    # Создаем релизные заметки
    $releaseNotes = "Release v$VERSION\n\nChanges in this version:\n- Built with WiX Toolset 4.0\n- Improved installer\n- Bug fixes and performance improvements"
    
    # Создаем тег и релиз
    Write-Host "Creating GitHub release v$VERSION..." -ForegroundColor Yellow
    
    # Проверяем, существует ли тег
    $tagExists = git tag -l "v$VERSION"
    if ($tagExists) {
        Write-Host "Tag v$VERSION already exists. Do you want to delete it and create a new one? (y/n)" -ForegroundColor Yellow
        $deleteTag = Read-Host
        if ($deleteTag -eq "y") {
            git tag -d "v$VERSION"
            git push origin --delete "v$VERSION" 2>$null
        } else {
            Write-Host "Using existing tag v$VERSION" -ForegroundColor Yellow
        }
    }
    
    # Создаем новый тег, если нужно
    if (-not $tagExists -or $deleteTag -eq "y") {
        git tag -a "v$VERSION" -m "Release v$VERSION"
        git push origin "v$VERSION"
    }
    
    # Создаем релиз и загружаем файлы
    Write-Host "Uploading release files to GitHub..." -ForegroundColor Yellow
    gh release create "v$VERSION" "$MsiOutputPath" "$BuiltExePath" --title "Text Rotator v$VERSION" --notes "$releaseNotes"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "GitHub release created successfully!" -ForegroundColor Green
    } else {
        Write-Host "Failed to create GitHub release." -ForegroundColor Red
    }
} else {
    Write-Host "Skipping GitHub release." -ForegroundColor DarkGray
}

Write-Host "Text Rotator Release Build process finished for version $VERSION!" -ForegroundColor Green
exit 0
