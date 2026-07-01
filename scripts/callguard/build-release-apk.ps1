# Monster Call Guard - Release APK build (no QR code)
# Developed by Suckbob | Monster AI Call Guard
# Compatible with Windows PowerShell 5.1
param(
    [string]$ProjectRoot = "",
    [switch]$Pause
)

$ErrorActionPreference = "Stop"
$logFile = ""

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $Message"
    if ($logFile) { Add-Content -Path $logFile -Value $line -Encoding UTF8 }
    if ($Color -eq "White") { Write-Host $Message } else { Write-Host $Message -ForegroundColor $Color }
}

function Stop-WithError {
    param([string]$Message)
    Write-Log $Message "Red"
    Write-Log "Log file: $logFile" "Yellow"
    if ($Pause) {
        Write-Host ""
        Read-Host "Press Enter to close"
    }
    exit 1
}

try {
    if (-not $ProjectRoot) {
        $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
    }

    $androidDir = Join-Path $ProjectRoot "apps\monstercallguard-android"
    $distDir = Join-Path $ProjectRoot "dist"
    $ksProps = Join-Path $androidDir "keystore.properties"
    $gradleFile = Join-Path $androidDir "app\build.gradle.kts"
    New-Item -ItemType Directory -Force -Path $distDir | Out-Null
    $logFile = Join-Path $distDir "build-apk-log.txt"
    Set-Content -Path $logFile -Value "=== MonsterCallGuard build $(Get-Date -Format o) ===" -Encoding UTF8

    Write-Log "=== MonsterCallGuard Release APK ===" "Cyan"
    Write-Log "Developed by Suckbob | Monster AI Call Guard" "DarkGray"
    Write-Log "Project: $ProjectRoot"

    if (-not (Test-Path $ksProps)) {
        Write-Log "Keystore missing, running generate-keystore.ps1 ..." "Yellow"
        & (Join-Path $PSScriptRoot "generate-keystore.ps1") -ProjectRoot $ProjectRoot
        if (-not (Test-Path $ksProps)) {
            Stop-WithError "Keystore setup failed. Run: scripts\callguard\generate-keystore.ps1"
        }
    }

    $version = "1.2.0"
    if (Test-Path $gradleFile) {
        $m = Select-String -Path $gradleFile -Pattern 'versionName\s*=\s*"([^"]+)"' | Select-Object -First 1
        if ($m) { $version = $m.Matches.Groups[1].Value }
    }
    Write-Log "Version: $version"

    $jbr = "C:\Program Files\Android\Android Studio\jbr"
    if (Test-Path $jbr) {
        $env:JAVA_HOME = $jbr
        Write-Log "JAVA_HOME: $jbr" "DarkGray"
    } elseif (-not $env:JAVA_HOME) {
        Stop-WithError "Java not found. Install Android Studio (JBR) or set JAVA_HOME."
    }

    if (-not $env:ANDROID_HOME -and (Test-Path "$env:LOCALAPPDATA\Android\Sdk")) {
        $env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
    }
    if (-not $env:ANDROID_HOME -or -not (Test-Path $env:ANDROID_HOME)) {
        Stop-WithError "Android SDK not found. Install Android Studio and SDK."
    }
    Write-Log "ANDROID_HOME: $env:ANDROID_HOME" "DarkGray"

    $localProps = Join-Path $androidDir "local.properties"
    $sdkEsc = $env:ANDROID_HOME -replace '\\', '\\'
    "sdk.dir=$sdkEsc" | Set-Content $localProps -Encoding ASCII

    $gradlew = Join-Path $androidDir "gradlew.bat"
    if (-not (Test-Path $gradlew)) {
        Stop-WithError "gradlew.bat missing. Open apps\monstercallguard-android in Android Studio and Sync Gradle."
    }

    Write-Log "Running Gradle assembleRelease (1-10 min) ..." "Cyan"
    Push-Location $androidDir
    try {
        $gradleOut = & $gradlew assembleRelease --no-daemon 2>&1
        $gradleExit = $LASTEXITCODE
        $gradleOut | ForEach-Object {
            $t = "$_"
            Write-Host $t
            Add-Content -Path $logFile -Value $t -Encoding UTF8
        }
        if ($gradleExit -ne 0) {
            Stop-WithError "Gradle failed (exit $gradleExit). See $logFile"
        }
    } finally {
        Pop-Location
    }

    $apkSrc = Join-Path $androidDir "app\build\outputs\apk\release\app-release.apk"
    if (-not (Test-Path $apkSrc)) {
        Stop-WithError "APK not found: $apkSrc"
    }

    $apkName = "MonsterCallGuard-v$version-signed.apk"
    $apkDst = Join-Path $distDir $apkName
    Copy-Item $apkSrc $apkDst -Force

    $hash = (Get-FileHash $apkDst -Algorithm SHA256).Hash.ToLower()
    $hashFile = "$apkDst.sha256"
    "$hash  $apkName" | Set-Content $hashFile -Encoding ASCII

    $manifestPath = Join-Path $distDir "callguard-release.json"
    @{
        version = $version
        apk = $apkName
        sha256 = $hash
        github_tag = "v$version"
        apk_url = "https://github.com/Suckbob/monster-ai/releases/download/v$version/$apkName"
        releases_page = "https://github.com/Suckbob/monster-ai/releases/latest"
        qr_code = $false
        connection = "cloudflare_tunnel"
    } | ConvertTo-Json | Set-Content $manifestPath -Encoding UTF8

    Write-Log ""
    Write-Log "[OK] APK: $apkDst" "Green"
    Write-Log "SHA256: $hash" "Green"
    Write-Log "Manifest: $manifestPath"
    Write-Log "Publish: scripts\callguard\publish-github-release.ps1 -Version $version" "Cyan"

    if ($Pause) {
        Write-Host ""
        Read-Host "Build done. Press Enter to close"
    }
    exit 0
} catch {
    $err = $_.Exception.Message
    if ($logFile) { Add-Content -Path $logFile -Value "FATAL: $err" -Encoding UTF8 }
    Write-Host "[ERROR] $err" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
    if ($Pause) { Read-Host "Press Enter to close" }
    exit 1
}