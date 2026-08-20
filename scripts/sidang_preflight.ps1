param(
    [string]$ApkPath = "",
    [string]$BackendHealthUrl = "http://127.0.0.1:3000/api/kesehatan"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
if ([string]::IsNullOrWhiteSpace($ApkPath)) {
    $ApkPath = Join-Path $repoRoot "artifacts\apk\taniadaptif_sidang.apk"
}
$ApkPath = [IO.Path]::GetFullPath($ApkPath)

function Resolve-Adb {
    $command = Get-Command adb.exe -CommandType Application -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $candidates = @()
    if ($env:ANDROID_SDK_ROOT) {
        $candidates += Join-Path $env:ANDROID_SDK_ROOT "platform-tools\adb.exe"
    }
    if ($env:ANDROID_HOME) {
        $candidates += Join-Path $env:ANDROID_HOME "platform-tools\adb.exe"
    }
    $candidates += Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return [IO.Path]::GetFullPath($candidate)
        }
    }
    return $null
}

function Get-AdbDeviceState([string]$AdbPath) {
    if (-not $AdbPath) { return "adb tidak ditemukan" }
    $lines = & $AdbPath devices 2>&1
    $deviceLines = @($lines | Where-Object { $_ -match "\t(device|unauthorized|offline)$" })
    if ($deviceLines.Count -eq 0) { return "belum terhubung" }
    if ($deviceLines -match "\tunauthorized$") { return "unauthorized" }
    if ($deviceLines -match "\toffline$") { return "offline" }
    return "terhubung ($($deviceLines.Count))"
}

function Test-Backend {
    try {
        $response = Invoke-RestMethod -Uri $BackendHealthUrl -TimeoutSec 3
        return $response.status -eq "baik"
    }
    catch {
        return $false
    }
}

$adb = Resolve-Adb
$deviceState = Get-AdbDeviceState $adb
$backendReady = Test-Backend
$apkReady = (Test-Path -LiteralPath $ApkPath -PathType Leaf) -and ((Get-Item -LiteralPath $ApkPath).Length -gt 0)
$portReady = [bool](Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue)

$checks = @(
    [pscustomobject]@{ Pemeriksaan = "ADB"; Status = $(if ($adb) { "OK" } else { "GAGAL" }); Detail = $(if ($adb) { $adb } else { "Android platform-tools tidak ditemukan" }) },
    [pscustomobject]@{ Pemeriksaan = "Perangkat"; Status = $(if ($deviceState -like "terhubung*") { "OK" } else { "BELUM" }); Detail = $deviceState },
    [pscustomobject]@{ Pemeriksaan = "Backend"; Status = $(if ($backendReady) { "OK" } else { "BELUM" }); Detail = $BackendHealthUrl },
    [pscustomobject]@{ Pemeriksaan = "Port 3000"; Status = $(if ($portReady) { "OK" } else { "BELUM" }); Detail = $(if ($portReady) { "listening" } else { "tidak listening" }) },
    [pscustomobject]@{ Pemeriksaan = "APK sidang"; Status = $(if ($apkReady) { "OK" } else { "GAGAL" }); Detail = $ApkPath }
)

$checks | Format-Table -AutoSize

if ($deviceState -eq "unauthorized") {
    Write-Host "Buka kunci HP, terima dialog USB debugging, lalu jalankan ulang." -ForegroundColor Yellow
}
elseif ($deviceState -eq "offline") {
    Write-Host "Cabut-pasang kabel USB dan aktifkan kembali USB debugging." -ForegroundColor Yellow
}

$allReady = $adb -and ($deviceState -like "terhubung*") -and $backendReady -and $portReady -and $apkReady
if (-not $allReady) { exit 1 }

Write-Host "Preflight sidang siap." -ForegroundColor Green
