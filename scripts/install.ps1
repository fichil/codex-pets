[CmdletBinding(SupportsShouldProcess = $true)]
param([string]$PetId = 'xiaocheng', [string]$CodexHome, [switch]$Force, [switch]$List)
. (Join-Path $PSScriptRoot 'common.ps1')
if ($List) {
    $root = Join-Path (Split-Path -Parent $PSScriptRoot) 'pets'
    Get-ChildItem -LiteralPath $root -Directory | Sort-Object Name | ForEach-Object {
        $package = Get-PetPackage $_.Name
        [pscustomobject]@{ Id = $package.Id; DisplayName = $package.Manifest.displayName }
    }
    return
}
$package = Get-PetPackage $PetId
$petsDir = Get-PetsDirectory $CodexHome
$target = Get-PetTarget $petsDir $PetId
$exists = Test-Path -LiteralPath $target
if ($exists) {
    Assert-InstalledPet $target $PetId
    if (-not $Force) { throw "目标已存在：$target。使用 -Force 覆盖同 ID 宠物。" }
}
if (-not $PSCmdlet.ShouldProcess($target, "安装 $($package.Manifest.displayName)")) { return }
New-Item -ItemType Directory -Force -Path $petsDir | Out-Null
$nonce = [guid]::NewGuid().ToString('N')
$stage = Get-PetTarget $petsDir "$PetId-stage-$nonce"
$backup = Get-PetTarget $petsDir "$PetId-backup-$nonce"
$backedUp = $false
try {
    New-Item -ItemType Directory -Path $stage | Out-Null
    if ($exists) { Get-ChildItem -LiteralPath $target -Force | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $stage -Recurse -Force } }
    Copy-Item -LiteralPath $package.ManifestPath -Destination (Join-Path $stage 'pet.json') -Force
    Copy-Item -LiteralPath $package.SpritePath -Destination (Join-Path $stage 'spritesheet.webp') -Force
    foreach ($file in @('pet.json', 'spritesheet.webp')) {
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $package.Directory $file)).Hash -ne (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $stage $file)).Hash) { throw "文件校验失败：$file" }
    }
    if ($exists) { Move-Item -LiteralPath $target -Destination $backup; $backedUp = $true }
    try { Move-Item -LiteralPath $stage -Destination $target }
    catch {
        if ($backedUp -and -not (Test-Path -LiteralPath $target)) { Move-Item -LiteralPath $backup -Destination $target; $backedUp = $false }
        throw
    }
    if ($backedUp) { Remove-Item -LiteralPath $backup -Recurse -Force; $backedUp = $false }
    Write-Host "已安装 $($package.Manifest.displayName) 到：$target"
    Write-Host '请在 Codex 的宠物选择界面刷新并手动选择；脚本不会更改当前选择。'
}
finally { if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force } }
