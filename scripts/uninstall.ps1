[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param([string]$PetId = 'xiaocheng', [string]$CodexHome)
. (Join-Path $PSScriptRoot 'common.ps1')
Assert-PetId $PetId
$petsDir = Get-PetsDirectory $CodexHome
$target = Get-PetTarget $petsDir $PetId
if (-not (Test-Path -LiteralPath $target)) { Write-Host "未找到 $PetId，无需卸载。"; return }
Assert-InstalledPet $target $PetId
if ($PSCmdlet.ShouldProcess($target, "卸载 $PetId")) {
    Remove-Item -LiteralPath $target -Recurse -Force
    Write-Host "已卸载：$PetId"
}
