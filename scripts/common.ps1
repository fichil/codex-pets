Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
function Assert-PetId([string]$PetId) {
    if ($PetId -cnotmatch '^[a-z0-9]+(?:-[a-z0-9]+)*$') { throw "无效的宠物 ID：$PetId" }
}
function Assert-NoReparsePoint([string]$Path) {
    $cursor = [IO.Path]::GetFullPath($Path)
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            if ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "拒绝符号链接或目录联接：$cursor" }
        }
        $cursor = Split-Path -Parent $cursor
    }
}
function Get-PetPackage([string]$PetId) {
    Assert-PetId $PetId
    $root = Join-Path (Split-Path -Parent $PSScriptRoot) "pets/$PetId/pet"
    Assert-NoReparsePoint $root
    $manifestPath = Join-Path $root 'pet.json'
    $spritePath = Join-Path $root 'spritesheet.webp'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf) -or -not (Test-Path -LiteralPath $spritePath -PathType Leaf)) { throw "宠物不存在或安装包不完整：$PetId" }
    Assert-NoReparsePoint $manifestPath
    Assert-NoReparsePoint $spritePath
    $manifest = Get-Content -Raw -Encoding utf8 -LiteralPath $manifestPath | ConvertFrom-Json
    if ($manifest.id -cne $PetId -or $manifest.spritesheetPath -cne 'spritesheet.webp' -or $manifest.spriteVersionNumber -ne 2) { throw "宠物清单不符合 V2 约定：$PetId" }
    [pscustomobject]@{ Id = $PetId; Manifest = $manifest; Directory = $root; ManifestPath = $manifestPath; SpritePath = $spritePath }
}
function Get-PetsDirectory([string]$CodexHome) {
    if ([string]::IsNullOrWhiteSpace($CodexHome)) {
        if (-not [string]::IsNullOrWhiteSpace($env:CODEX_HOME)) { $CodexHome = $env:CODEX_HOME }
        else { $CodexHome = Join-Path $env:USERPROFILE '.codex' }
    }
    $petsPath = [IO.Path]::GetFullPath((Join-Path ([IO.Path]::GetFullPath($CodexHome)) 'pets'))
    Assert-NoReparsePoint $petsPath
    return $petsPath
}
function Get-PetTarget([string]$PetsDirectory, [string]$PetId) {
    Assert-PetId $PetId
    $target = [IO.Path]::GetFullPath((Join-Path $PetsDirectory $PetId))
    if ((Split-Path -Parent $target) -ne $PetsDirectory) { throw '目标越出 Codex Pets 目录。' }
    Assert-NoReparsePoint $target
    return $target
}
function Assert-InstalledPet([string]$Target, [string]$PetId) {
    $manifestPath = Join-Path $Target 'pet.json'
    Assert-NoReparsePoint $manifestPath
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw '目标缺少 pet.json，拒绝更改未知目录。' }
    $manifest = Get-Content -Raw -Encoding utf8 -LiteralPath $manifestPath | ConvertFrom-Json
    if ($manifest.id -cne $PetId) { throw '目标属于其他宠物，拒绝更改。' }
    foreach ($item in Get-ChildItem -LiteralPath $Target -Recurse -Force) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "目标中包含符号链接：$($item.FullName)" }
    }
}
