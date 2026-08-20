param(
    [string]$DeviceSerial = "",
    [string]$PackageName = "com.hamzanwadi.tani_adaptif",
    [string]$BackendHealthUrl = "http://127.0.0.1:3000/api/kesehatan"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$backendRoot = Join-Path $repoRoot "backend-nodejs"

function Resolve-Adb {
    $command = Get-Command adb.exe -CommandType Application -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $roots = @()
    if ($env:ANDROID_SDK_ROOT) { $roots += $env:ANDROID_SDK_ROOT }
    if ($env:ANDROID_HOME) { $roots += $env:ANDROID_HOME }
    $roots += Join-Path $env:LOCALAPPDATA "Android\Sdk"

    foreach ($root in $roots) {
        $candidate = Join-Path $root "platform-tools\adb.exe"
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return [IO.Path]::GetFullPath($candidate) }
    }
    throw "ADB tidak ditemukan. Pastikan Android SDK platform-tools terpasang."
}

function Resolve-Device([string]$AdbPath) {
    $lines = & $AdbPath devices 2>&1
    if ($lines -match "\tunauthorized$") { throw "HP unauthorized. Terima dialog USB debugging pada HP." }
    if ($lines -match "\toffline$") { throw "HP offline. Cabut-pasang USB lalu coba lagi." }
    $devices = @($lines | Where-Object { $_ -match "\tdevice$" } | ForEach-Object { ($_ -split "\t")[0] })
    if ($DeviceSerial) {
        if ($devices -notcontains $DeviceSerial) { throw "Perangkat $DeviceSerial tidak ditemukan." }
        return $DeviceSerial
    }
    if ($devices.Count -eq 0) { throw "Tidak ada HP Android yang terhubung." }
    if ($devices.Count -gt 1) { throw "Lebih dari satu perangkat terhubung. Gunakan -DeviceSerial." }
    return $devices[0]
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
$serial = Resolve-Device $adb
$selector = @("-s", $serial)

if (-not (Test-Backend)) {
    $node = Get-Command node.exe -ErrorAction SilentlyContinue
    if (-not $node) { throw "Node.js tidak ditemukan untuk menjalankan backend." }
    $process = Start-Process -FilePath $node.Source -ArgumentList "src/index.js" -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru
    Write-Host "Backend dimulai pada PID $($process.Id)."
    for ($attempt = 0; $attempt -lt 15 -and -not (Test-Backend); $attempt++) {
        Start-Sleep -Seconds 1
    }
}
if (-not (Test-Backend)) { throw "Backend tidak sehat pada $BackendHealthUrl" }

& $adb @selector reverse "tcp:3000" "tcp:3000"
if ($LASTEXITCODE -ne 0) { throw "Gagal menyiapkan adb reverse port 3000." }

$packagePath = & $adb @selector shell pm path $PackageName
if ($LASTEXITCODE -ne 0 -or $packagePath -notmatch "^package:") {
    throw "Aplikasi belum terinstal. Jalankan scripts\sidang_install.ps1 terlebih dahulu."
}

& $adb @selector shell am force-stop $PackageName
& $adb @selector shell monkey -p $PackageName -c android.intent.category.LAUNCHER 1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Aplikasi gagal diluncurkan." }

Write-Host "Backend sehat, adb reverse aktif, dan TaniAdaptif diluncurkan pada $serial." -ForegroundColor Green
