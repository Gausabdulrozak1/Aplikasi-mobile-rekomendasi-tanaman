param(
    [string]$ApkPath = "",
    [string]$DeviceSerial = "",
    [string]$PackageName = "com.hamzanwadi.tani_adaptif"
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

if (-not (Test-Path -LiteralPath $ApkPath -PathType Leaf)) {
    throw "APK sidang tidak ditemukan: $ApkPath"
}
if ((Get-Item -LiteralPath $ApkPath).Length -le 0) {
    throw "APK sidang kosong: $ApkPath"
}

$adb = Resolve-Adb
$serial = Resolve-Device $adb
$selector = @("-s", $serial)

& $adb @selector reverse "tcp:3000" "tcp:3000"
if ($LASTEXITCODE -ne 0) { throw "Gagal menyiapkan adb reverse port 3000." }

$reverseList = & $adb @selector reverse --list
if ($reverseList -notmatch "tcp:3000\s+tcp:3000") { throw "Verifikasi adb reverse gagal." }

& $adb @selector install -r $ApkPath
if ($LASTEXITCODE -ne 0) { throw "Instalasi APK gagal." }

$packagePath = & $adb @selector shell pm path $PackageName
if ($LASTEXITCODE -ne 0 -or $packagePath -notmatch "^package:") {
    throw "Package $PackageName tidak ditemukan setelah instalasi."
}

Write-Host "APK terinstal pada $serial." -ForegroundColor Green
Write-Host "adb reverse tcp:3000 aktif." -ForegroundColor Green
Write-Host $packagePath
