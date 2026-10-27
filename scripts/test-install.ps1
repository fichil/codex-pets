[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$testRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot ('output/install-tests-' + [guid]::NewGuid().ToString('N'))))
if (-not $testRoot.StartsWith([IO.Path]::GetFullPath((Join-Path $repoRoot 'output')) + [IO.Path]::DirectorySeparatorChar)) { throw 'Unsafe test path' }
$install = Join-Path $PSScriptRoot 'install.ps1'
$uninstall = Join-Path $PSScriptRoot 'uninstall.ps1'
$checks = 0
function Assert-Test([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw "FAIL: $Message" }
    $script:checks++
}
function Expect-Failure([scriptblock]$Action, [string]$Message) {
    $failed = $false
    try { & $Action | Out-Null } catch { $failed = $true }
    Assert-Test $failed $Message
}
try {
    $listing = @(& $install -List)
    Assert-Test (($listing.Id -contains 'xiaocheng') -and ($listing.Id -contains 'dafeiyu')) 'list both pets'
    & $install -PetId dafeiyu -CodexHome $testRoot -WhatIf
    Assert-Test (-not (Test-Path -LiteralPath $testRoot)) 'WhatIf creates no directories'
    & $install -CodexHome $testRoot
    & $install -PetId dafeiyu -CodexHome $testRoot
    $xiaochengPath = Join-Path $testRoot 'pets/xiaocheng'
    $dafeiyuPath = Join-Path $testRoot 'pets/dafeiyu'
    foreach ($id in @('xiaocheng', 'dafeiyu')) {
        foreach ($file in @('pet.json', 'spritesheet.webp')) {
            $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $repoRoot "pets/$id/pet/$file")).Hash
            $installedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $testRoot "pets/$id/$file")).Hash
            Assert-Test ($sourceHash -eq $installedHash) "installed $id/$file matches"
        }
    }
    Expect-Failure { & $install -PetId dafeiyu -CodexHome $testRoot } 'duplicate install rejected'
    $extra = Join-Path $dafeiyuPath 'user-note.txt'
    'keep this file' | Set-Content -LiteralPath $extra
    & $install -PetId dafeiyu -CodexHome $testRoot -Force
    Assert-Test ((Get-Content -LiteralPath $extra) -eq 'keep this file') 'force preserves unrelated ordinary files'
    Expect-Failure { & $install -PetId '../escape' -CodexHome $testRoot } 'path traversal rejected'
    Expect-Failure { & $uninstall -PetId '..\escape' -CodexHome $testRoot -Confirm:$false } 'uninstall traversal rejected'
    Expect-Failure { & $install -PetId missing -CodexHome $testRoot } 'unknown pet rejected'
    Expect-Failure { & $install -PetId Dafeiyu -CodexHome $testRoot } 'uppercase ID rejected'
    $outside = Join-Path $testRoot 'unrelated-home'
    New-Item -ItemType Directory -Path $outside | Out-Null
    $sentinel = Join-Path $outside 'keep.txt'
    'untouched' | Set-Content -LiteralPath $sentinel
    $linkedHome = Join-Path $testRoot 'linked-home'
    New-Item -ItemType Junction -Path $linkedHome -Target $outside | Out-Null
    try {
        Expect-Failure { & $install -PetId dafeiyu -CodexHome $linkedHome } 'junction home rejected'
        Expect-Failure { & $uninstall -PetId dafeiyu -CodexHome $linkedHome -Confirm:$false } 'junction uninstall rejected'
        Assert-Test ((Get-Content -LiteralPath $sentinel) -eq 'untouched') 'junction target untouched'
    }
    finally { [IO.Directory]::Delete($linkedHome) }
    $manifest = Join-Path $dafeiyuPath 'pet.json'
    $originalManifest = [IO.File]::ReadAllBytes($manifest)
    '{"id":"another-pet"}' | Set-Content -LiteralPath $manifest -Encoding UTF8
    Expect-Failure { & $install -PetId dafeiyu -CodexHome $testRoot -Force } 'wrong owner force rejected'
    Expect-Failure { & $uninstall -PetId dafeiyu -CodexHome $testRoot -Confirm:$false } 'wrong owner uninstall rejected'
    [IO.File]::WriteAllBytes($manifest, $originalManifest)
    # Simulate a directory-switch failure after the old version has been backed up.
    $script:failSwitch = $true
    function Move-Item {
        [CmdletBinding()]
        param([string]$LiteralPath, [string]$Destination)
        if ($script:failSwitch -and $LiteralPath -match '-stage-') {
            $script:failSwitch = $false
            throw 'Simulated switch failure'
        }
        Microsoft.PowerShell.Management\Move-Item -LiteralPath $LiteralPath -Destination $Destination
    }
    try { Expect-Failure { & $install -PetId dafeiyu -CodexHome $testRoot -Force } 'switch failure reported' }
    finally { Remove-Item Function:\Move-Item }
    Assert-Test (Test-Path -LiteralPath $manifest) 'failed switch restores old package'
    Assert-Test ((Get-Content -LiteralPath $extra) -eq 'keep this file') 'rollback preserves extras'
    Assert-Test (@(Get-ChildItem -LiteralPath (Join-Path $testRoot 'pets') -Directory | Where-Object Name -match '-(stage|backup)-').Count -eq 0) 'no abandoned staging directories'
    & $uninstall -PetId dafeiyu -CodexHome $testRoot -WhatIf
    Assert-Test (Test-Path -LiteralPath $dafeiyuPath) 'uninstall WhatIf preserves pet'
    & $uninstall -PetId dafeiyu -CodexHome $testRoot -Confirm:$false
    Assert-Test (-not (Test-Path -LiteralPath $dafeiyuPath)) 'selected pet removed'
    Assert-Test (Test-Path -LiteralPath (Join-Path $xiaochengPath 'spritesheet.webp')) 'other pet untouched'
    & $uninstall -PetId dafeiyu -CodexHome $testRoot -Confirm:$false
    New-Item -ItemType Directory -Path $dafeiyuPath | Out-Null
    Expect-Failure { & $install -PetId dafeiyu -CodexHome $testRoot -Force } 'unknown directory rejected'
    Expect-Failure { & $uninstall -PetId dafeiyu -CodexHome $testRoot -Confirm:$false } 'missing manifest rejected'
    & $uninstall -CodexHome $testRoot -Confirm:$false
    Assert-Test (-not (Test-Path -LiteralPath $xiaochengPath)) 'default uninstall remains xiaocheng'
    Write-Host "PASS: $checks installation and isolation checks."
}
finally {
    if (Test-Path -LiteralPath $testRoot) { Remove-Item -LiteralPath $testRoot -Recurse -Force }
}
