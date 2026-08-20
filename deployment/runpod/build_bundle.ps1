[CmdletBinding()]
param(
    [string]$OutputDirectory = "artifacts/deployment",
    [string]$OutputName = "taniadaptif_runpod_deployment.zip"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ExpectedModelSha256 = "0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a"
$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$OutputRoot = [System.IO.Path]::GetFullPath((Join-Path $RepositoryRoot $OutputDirectory))
[System.IO.Directory]::CreateDirectory($OutputRoot) | Out-Null

$StagingRoot = Join-Path $OutputRoot (".runpod_bundle_" + [guid]::NewGuid().ToString("N"))
$BundleRoot = Join-Path $StagingRoot "TaniAdaptif"
[System.IO.Directory]::CreateDirectory($BundleRoot) | Out-Null

function Copy-BundlePath {
    param([Parameter(Mandatory = $true)][string]$RelativePath)
    $Source = Join-Path $RepositoryRoot $RelativePath
    if (-not (Test-Path -LiteralPath $Source)) {
        throw "Required bundle input is missing: $RelativePath"
    }
    $Destination = Join-Path $BundleRoot $RelativePath
    $DestinationParent = Split-Path -Parent $Destination
    [System.IO.Directory]::CreateDirectory($DestinationParent) | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
}

function Remove-StagingPath {
    param([Parameter(Mandatory = $true)][string]$LiteralPath)
    $Resolved = [System.IO.Path]::GetFullPath($LiteralPath)
    $ResolvedStagingRoot = [System.IO.Path]::GetFullPath($StagingRoot)
    if (-not $Resolved.StartsWith($ResolvedStagingRoot + [System.IO.Path]::DirectorySeparatorChar)) {
        throw "Refusing to remove a path outside bundle staging: $Resolved"
    }
    Remove-Item -LiteralPath $Resolved -Recurse -Force
}

try {
    $ModelRelativePath = "artifacts/models/multisource_multicrop_lora_sd15/multisource_multicrop_lora.safetensors"
    $ModelPath = Join-Path $RepositoryRoot $ModelRelativePath
    if (-not (Test-Path -LiteralPath $ModelPath -PathType Leaf)) {
        throw "Final LoRA is missing: $ModelRelativePath"
    }
    $ModelHash = (Get-FileHash -LiteralPath $ModelPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($ModelHash -ne $ExpectedModelSha256) {
        throw "Final LoRA SHA-256 mismatch: $ModelHash"
    }

    @(
        "backend-nodejs/package.json",
        "backend-nodejs/package-lock.json",
        "backend-nodejs/.env.example",
        "backend-nodejs/src",
        "inference_api/.env.example",
        "inference_api/gpu.env.example",
        "inference_api/requirements.txt",
        "inference_api/requirements-diffusers.txt",
        "inference_api/app",
        "inference_api/scripts",
        "deployment/runpod/runtime.env.example",
        "deployment/runpod/bootstrap_runpod.sh",
        "deployment/runpod/start_stack.sh",
        "docs/API_CONTRACT.md",
        "docs/DEPLOYMENT_RUNBOOK.md",
        $ModelRelativePath
    ) | ForEach-Object { Copy-BundlePath $_ }

    Get-ChildItem -LiteralPath $BundleRoot -Recurse -Directory -Filter "__pycache__" |
        ForEach-Object { Remove-StagingPath $_.FullName }
    Get-ChildItem -LiteralPath $BundleRoot -Recurse -File |
        Where-Object { $_.Extension -eq ".pyc" -or $_.Name -eq ".env" } |
        ForEach-Object { Remove-StagingPath $_.FullName }

    $Files = Get-ChildItem -LiteralPath $BundleRoot -Recurse -File | Sort-Object FullName
    $StagedModelPath = Join-Path $BundleRoot $ModelRelativePath
    if ($Files.Count -lt 30) {
        throw "Bundle staging contains too few files: $($Files.Count)"
    }
    if (-not (Test-Path -LiteralPath $StagedModelPath -PathType Leaf)) {
        throw "Bundle staging lost the final LoRA file."
    }
    $StagedModelHash = (Get-FileHash -LiteralPath $StagedModelPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($StagedModelHash -ne $ExpectedModelSha256) {
        throw "Staged LoRA SHA-256 mismatch: $StagedModelHash"
    }
    $ManifestFiles = foreach ($File in $Files) {
        $ResolvedFile = [System.IO.Path]::GetFullPath($File.FullName)
        $ResolvedBundleRoot = [System.IO.Path]::GetFullPath($BundleRoot)
        if (-not $ResolvedFile.StartsWith($ResolvedBundleRoot + [System.IO.Path]::DirectorySeparatorChar)) {
            throw "Bundle file escaped staging root: $ResolvedFile"
        }
        $Relative = $ResolvedFile.Substring($ResolvedBundleRoot.Length).TrimStart("\").Replace("\", "/")
        [ordered]@{
            path = $Relative
            size_bytes = $File.Length
            sha256 = (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    $Manifest = [ordered]@{
        schema_version = 1
        purpose = "TaniAdaptif remote GPU inference deployment; no training"
        final_run_id = "20260820T143551Z"
        base_model = "stable-diffusion-v1-5/stable-diffusion-v1-5"
        lora_filename = "multisource_multicrop_lora.safetensors"
        lora_sha256 = $ExpectedModelSha256
        includes_dataset = $false
        includes_checkpoint = $false
        includes_secret = $false
        files = $ManifestFiles
    }
    $ManifestPath = Join-Path $BundleRoot "DEPLOYMENT_MANIFEST.json"
    $Manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ManifestPath -Encoding utf8

    $OutputPath = Join-Path $OutputRoot $OutputName
    $CandidatePath = Join-Path $StagingRoot $OutputName
    Compress-Archive -LiteralPath $BundleRoot -DestinationPath $CandidatePath -CompressionLevel Optimal

    $ArchiveHash = (Get-FileHash -LiteralPath $CandidatePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $ArchiveSize = (Get-Item -LiteralPath $CandidatePath).Length
    if ($ArchiveSize -lt 1MB) {
        throw "Deployment ZIP is unexpectedly small: $ArchiveSize bytes"
    }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $Archive = [System.IO.Compression.ZipFile]::OpenRead($CandidatePath)
    try {
        $FileEntries = @($Archive.Entries | Where-Object { -not [string]::IsNullOrEmpty($_.Name) })
        $ModelEntry = $Archive.Entries | Where-Object {
            $_.FullName.Replace("\", "/") -eq "TaniAdaptif/$ModelRelativePath"
        }
        if ($FileEntries.Count -lt 31) {
            throw "Deployment ZIP contains too few file entries: $($FileEntries.Count)"
        }
        if ($null -eq $ModelEntry -or $ModelEntry.Length -ne (Get-Item -LiteralPath $ModelPath).Length) {
            throw "Deployment ZIP does not contain the complete final LoRA."
        }
        $Sha256 = [System.Security.Cryptography.SHA256]::Create()
        $ModelStream = $ModelEntry.Open()
        try {
            $ArchiveModelHash = ([System.BitConverter]::ToString(
                $Sha256.ComputeHash($ModelStream)
            )).Replace("-", "").ToLowerInvariant()
        }
        finally {
            $ModelStream.Dispose()
            $Sha256.Dispose()
        }
        if ($ArchiveModelHash -ne $ExpectedModelSha256) {
            throw "LoRA SHA-256 inside deployment ZIP is invalid: $ArchiveModelHash"
        }
        $ForbiddenEntries = @($FileEntries | Where-Object {
            $_.Name -eq ".env" -or
            $_.FullName -match "(^|[\\/])checkpoint-" -or
            $_.FullName -match "dataset_multicrop"
        })
        if ($ForbiddenEntries.Count -ne 0) {
            throw "Deployment ZIP contains forbidden runtime inputs: $($ForbiddenEntries.FullName -join ', ')"
        }
    }
    finally {
        $Archive.Dispose()
    }
    Copy-Item -LiteralPath $CandidatePath -Destination $OutputPath -Force
    $PublishedHash = (Get-FileHash -LiteralPath $OutputPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($PublishedHash -ne $ArchiveHash) {
        throw "Published deployment ZIP hash changed after atomic staging copy."
    }
    $ShaPath = Join-Path $OutputRoot ($OutputName + ".sha256")
    "$ArchiveHash  $OutputName" | Set-Content -LiteralPath $ShaPath -Encoding ascii
    $ReportPath = Join-Path $OutputRoot "DEPLOYMENT_BUNDLE_REPORT.md"
    @"
# RunPod Deployment Bundle

- Archive: ``$OutputPath``
- Size: $ArchiveSize bytes
- SHA-256: ``$ArchiveHash``
- File entries: $($FileEntries.Count)
- Final run: ``20260820T143551Z``
- LoRA SHA-256: ``$ExpectedModelSha256``
- Dataset/checkpoint included: no
- Secrets included: no
- Training performed: no
"@ | Set-Content -LiteralPath $ReportPath -Encoding utf8

    Write-Output "Bundle: $OutputPath"
    Write-Output "SHA-256: $ArchiveHash"
    Write-Output "Size: $ArchiveSize bytes"
}
finally {
    $ResolvedStaging = [System.IO.Path]::GetFullPath($StagingRoot)
    if ($ResolvedStaging.StartsWith($OutputRoot + [System.IO.Path]::DirectorySeparatorChar) -and
        (Split-Path -Leaf $ResolvedStaging).StartsWith(".runpod_bundle_")) {
        if (Test-Path -LiteralPath $ResolvedStaging) {
            Remove-Item -LiteralPath $ResolvedStaging -Recurse -Force
        }
    }
    else {
        throw "Refusing to clean unexpected staging path: $ResolvedStaging"
    }
}
