param(
    [Parameter(Mandatory = $true)]
    [string]$GpuUrl
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$backendRoot = Join-Path $repoRoot "backend-nodejs"
$envPath = Join-Path $backendRoot ".env"
$healthUrl = "http://127.0.0.1:3000/api/kesehatan"
$readyUrl = "http://127.0.0.1:3000/api/visual/ready"

function Normalize-GpuUrl([string]$Value) {
    $uri = $null
    if (-not [Uri]::TryCreate($Value.Trim(), [UriKind]::Absolute, [ref]$uri)) {
        throw "GpuUrl bukan URL absolut yang valid."
    }
    if ($uri.Scheme -ne "https" -or $uri.UserInfo -or $uri.Query -or $uri.Fragment) {
        throw "GpuUrl harus HTTPS tanpa credential, query, atau fragment."
    }
    if ($uri.Host -notmatch "^[a-z0-9-]+\.trycloudflare\.com$") {
        throw "GpuUrl harus berasal dari Cloudflare Quick Tunnel (*.trycloudflare.com)."
    }
    if ($uri.AbsolutePath -ne "/") {
        throw "GpuUrl harus berupa origin tanpa path tambahan."
    }
    return $uri.GetLeftPart([UriPartial]::Authority)
}

function Read-DotEnv([string[]]$Lines) {
    $values = @{}
    foreach ($line in $Lines) {
        if ($line -match "^\s*([^#=\s]+)=(.*)$") {
            $values[$matches[1]] = $matches[2].Trim()
        }
    }
    return $values
}

function Write-Environment([string[]]$Lines, [string]$Url) {
    $indices = @()
    for ($index = 0; $index -lt $Lines.Count; $index++) {
        if ($Lines[$index] -match "^\s*INFERENCE_API_BASE_URL=") {
            $indices += $index
        }
    }
    if ($indices.Count -gt 1) {
        throw "INFERENCE_API_BASE_URL muncul lebih dari sekali pada backend .env."
    }
    $updated = @($Lines)
    if ($indices.Count -eq 1) {
        $updated[$indices[0]] = "INFERENCE_API_BASE_URL=$Url"
    }
    else {
        $updated += "INFERENCE_API_BASE_URL=$Url"
    }
    $temporary = "$envPath.tmp"
    [IO.File]::WriteAllLines($temporary, $updated, [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temporary -Destination $envPath -Force
}

function Test-BackendHealth {
    try {
        return (Invoke-RestMethod -Uri $healthUrl -TimeoutSec 5).status -eq "baik"
    }
    catch {
        return $false
    }
}

function Stop-TaniAdaptifBackend {
    $listeners = @(Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue)
    foreach ($listener in $listeners) {
        $process = Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f $listener.OwningProcess)
        if (-not $process -or $process.Name -ne "node.exe" -or $process.CommandLine -notmatch "src/index\.js") {
            throw "Port 3000 digunakan proses yang bukan backend TaniAdaptif; proses tidak dihentikan."
        }
        Stop-Process -Id $process.ProcessId -Force
    }
}

function Start-TaniAdaptifBackend {
    $node = Get-Command node.exe -CommandType Application -ErrorAction Stop
    $process = Start-Process -FilePath $node.Source -ArgumentList "src/index.js" -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        if (Test-BackendHealth) { return $process }
        if ($process.HasExited) { break }
        Start-Sleep -Seconds 1
    }
    throw "Backend gagal sehat setelah restart."
}

$normalizedUrl = Normalize-GpuUrl $GpuUrl
if (-not (Test-Path -LiteralPath $envPath -PathType Leaf)) {
    throw "Konfigurasi backend tidak ditemukan: $envPath"
}

$publicHealth = Invoke-RestMethod -Uri "$normalizedUrl/health" -TimeoutSec 20
if (
    $publicHealth.status -ne "ok" -or
    $publicHealth.provider -ne "diffusers" -or
    $publicHealth.device -ne "cuda" -or
    $publicHealth.model_loaded -ne $true
) {
    throw "Tunnel aktif tetapi health GPU tidak sesuai kontrak Diffusers CUDA."
}

$originalText = [IO.File]::ReadAllText($envPath)
$originalLines = [IO.File]::ReadAllLines($envPath)
$values = Read-DotEnv $originalLines
$inferenceToken = [string]$values["INFERENCE_API_TOKEN"]
if ($inferenceToken.Length -lt 32 -or $inferenceToken.ToLowerInvariant().StartsWith("replace-with")) {
    throw "INFERENCE_API_TOKEN backend harus sama dengan Kaggle Secret dan minimal 32 karakter."
}

try {
    Write-Environment $originalLines $normalizedUrl
    Stop-TaniAdaptifBackend
    $backendProcess = Start-TaniAdaptifBackend

    $headers = @{}
    if ([string]$values["BACKEND_VISUAL_REQUIRE_TOKEN"] -eq "true") {
        $clientToken = [string]$values["BACKEND_VISUAL_API_TOKEN"]
        if ($clientToken.Length -lt 32) {
            throw "BACKEND_VISUAL_API_TOKEN tidak valid."
        }
        $headers["X-Client-Token"] = $clientToken
    }
    $ready = Invoke-RestMethod -Uri $readyUrl -Headers $headers -TimeoutSec 30
    if (
        $ready.status -ne "ready" -or
        $ready.provider -ne "diffusers" -or
        $ready.device -ne "cuda" -or
        $ready.model_loaded -ne $true
    ) {
        throw "Express hidup tetapi inference GPU belum ready."
    }
}
catch {
    [IO.File]::WriteAllText($envPath, $originalText, [Text.UTF8Encoding]::new($false))
    Stop-TaniAdaptifBackend
    try { [void](Start-TaniAdaptifBackend) } catch {}
    throw
}

Write-Host "GPU URL tersimpan dan backend berhasil direstart." -ForegroundColor Green
Write-Host "INFERENCE_API_BASE_URL=$normalizedUrl"
Write-Host "Backend health: PASS"
Write-Host "GPU readiness: PASS (diffusers/cuda)"
Write-Host "Backend PID: $($backendProcess.Id)"
