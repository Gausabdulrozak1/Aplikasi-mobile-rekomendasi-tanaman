param(
    [string]$Source = "artifacts\dataset_packages\dataset_multicrop_v1.zip",
    [string]$OutputDirectory = "artifacts\colab_upload\dataset_multicrop_v1_upload_parts",
    [int]$ChunkSizeMiB = 8
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$expectedSha256 = "f6aa060658cf95e48996f10f0ffde200938d340dd15e6b60adace5bb5cecfb33"
$expectedSize = 188356224L
$chunkSize = $ChunkSizeMiB * 1MB
$sourcePath = (Resolve-Path -LiteralPath $Source).Path
$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$outputPath = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot $OutputDirectory))
$allowedRoot = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot "artifacts\colab_upload"))

if (-not $outputPath.StartsWith($allowedRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Output directory must stay inside $allowedRoot"
}
if ($ChunkSizeMiB -lt 1 -or $ChunkSizeMiB -gt 16) {
    throw "ChunkSizeMiB must be between 1 and 16."
}

$sourceInfo = Get-Item -LiteralPath $sourcePath
$sourceSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash.ToLowerInvariant()
if ($sourceInfo.Length -ne $expectedSize -or $sourceSha256 -ne $expectedSha256) {
    throw "Source ZIP is not the validated final package. size=$($sourceInfo.Length), sha256=$sourceSha256"
}

[System.IO.Directory]::CreateDirectory($outputPath) | Out-Null
Get-ChildItem -LiteralPath $outputPath -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "dataset_multicrop_v1.zip.part-*" -or $_.Name -eq "upload_manifest.json" } |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force }

$parts = [System.Collections.Generic.List[object]]::new()
$sourceStream = [System.IO.File]::OpenRead($sourcePath)
try {
    $buffer = New-Object byte[] $chunkSize
    $index = 0
    while (($bytesRead = $sourceStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
        $name = "dataset_multicrop_v1.zip.part-{0:D3}" -f $index
        $partPath = Join-Path $outputPath $name
        $partStream = [System.IO.File]::Create($partPath)
        try {
            $partStream.Write($buffer, 0, $bytesRead)
        }
        finally {
            $partStream.Dispose()
        }
        $parts.Add([ordered]@{
            name = $name
            size_bytes = $bytesRead
            sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $partPath).Hash.ToLowerInvariant()
        })
        $index++
    }
}
finally {
    $sourceStream.Dispose()
}

$manifest = [ordered]@{
    schema_version = 1
    source_filename = "dataset_multicrop_v1.zip"
    source_size_bytes = $sourceInfo.Length
    source_sha256 = $sourceSha256
    chunk_size_bytes = $chunkSize
    part_count = $parts.Count
    parts = $parts
}
$manifestPath = Join-Path $outputPath "upload_manifest.json"
$manifestJson = $manifest | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText(
    $manifestPath,
    $manifestJson,
    [System.Text.UTF8Encoding]::new($false)
)

$combinedHash = [System.Security.Cryptography.IncrementalHash]::CreateHash(
    [System.Security.Cryptography.HashAlgorithmName]::SHA256
)
$combinedSize = 0L
try {
    foreach ($part in $parts) {
        $partPath = Join-Path $outputPath $part.name
        $partStream = [System.IO.File]::OpenRead($partPath)
        try {
            $verifyBuffer = New-Object byte[] (1MB)
            while (($read = $partStream.Read($verifyBuffer, 0, $verifyBuffer.Length)) -gt 0) {
                $combinedHash.AppendData($verifyBuffer, 0, $read)
                $combinedSize += $read
            }
        }
        finally {
            $partStream.Dispose()
        }
    }
    $combinedSha256 = ([BitConverter]::ToString($combinedHash.GetHashAndReset())).Replace("-", "").ToLowerInvariant()
}
finally {
    $combinedHash.Dispose()
}

if ($combinedSize -ne $expectedSize -or $combinedSha256 -ne $expectedSha256) {
    throw "Chunk verification failed. size=$combinedSize, sha256=$combinedSha256"
}

Write-Output "Colab upload parts are ready."
Write-Output "Folder: $outputPath"
Write-Output "Parts: $($parts.Count)"
Write-Output "Chunk size: $ChunkSizeMiB MiB"
Write-Output "Combined size: $combinedSize"
Write-Output "Combined SHA-256: $combinedSha256"
