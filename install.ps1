# One-command Windows setup. Installs per-user; no administrator, Git or Python needed.
[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'Necropsy\app'),
    [string]$BundleDirectory,
    [switch]$NoLaunch,
    [switch]$NoShortcuts,
    [switch]$NoPathChange
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 6) {
    # A PowerShell 7 parent can pass its module search path to Windows PowerShell.
    # Load the host's own security module so Astral's policy check works there.
    Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Security') -Force
}
$necropsyVersion = '0.2.1'
$releaseBase = "https://github.com/David-c0degeek/necropsy/releases/download/v$necropsyVersion"
$wheelName = "necropsy-$necropsyVersion-py3-none-any.whl"
$uvVersion = '0.11.21'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$workRoot = $null

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Setup step failed (exit $LASTEXITCODE). Run this installer again to retry." }
}

try {
    $appRoot = [IO.Path]::GetFullPath($InstallRoot)
    New-Item -ItemType Directory -Force -Path $appRoot | Out-Null
    $workRoot = Join-Path $appRoot ('.setup-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $workRoot | Out-Null
    Write-Host 'Necropsy setup - getting everything ready for you.' -ForegroundColor Cyan
    Write-Host '[1/4] Getting the app...'
    $wheel = Join-Path $workRoot $wheelName
    $sums = Join-Path $workRoot 'SHA256SUMS'
    if ($BundleDirectory) {
        Copy-Item -LiteralPath (Join-Path $BundleDirectory $wheelName) -Destination $wheel
        Copy-Item -LiteralPath (Join-Path $BundleDirectory 'SHA256SUMS') -Destination $sums
    } else {
        Invoke-WebRequest -UseBasicParsing "$releaseBase/$wheelName" -OutFile $wheel
        Invoke-WebRequest -UseBasicParsing "$releaseBase/SHA256SUMS" -OutFile $sums
    }
    $matching = @(Get-Content -LiteralPath $sums | Where-Object {
        $_ -match ('^([0-9a-fA-F]{64})\s+\*?' + [regex]::Escape($wheelName) + '$')
    })
    if ($matching.Count -ne 1) { throw 'The download checksum is missing or ambiguous. Please retry setup.' }
    $expected = ($matching[0] -split '\s+')[0]
    $hasher = [Security.Cryptography.SHA256]::Create()
    $wheelStream = [IO.File]::OpenRead($wheel)
    try { $actualHash = [BitConverter]::ToString($hasher.ComputeHash($wheelStream)).Replace('-', '') }
    finally { $wheelStream.Dispose(); $hasher.Dispose() }
    if ($actualHash -ne $expected) {
        throw 'The app download was damaged. Nothing was installed. Please retry setup.'
    }

    Write-Host '[2/4] Preparing the app runtime (no Python installation required)...'
    $uvRoot = Join-Path $appRoot 'runtime\uv'
    $uv = Join-Path $uvRoot 'uv.exe'
    if (-not (Test-Path -LiteralPath $uv -PathType Leaf)) {
        $previousUvRoot = $env:UV_INSTALL_DIR
        $previousNoPath = $env:UV_NO_MODIFY_PATH
        try {
            $env:UV_INSTALL_DIR = $uvRoot
            $env:UV_NO_MODIFY_PATH = '1'
            $uvInstaller = Join-Path $workRoot 'uv-install.ps1'
            Invoke-WebRequest -UseBasicParsing "https://astral.sh/uv/$uvVersion/install.ps1" -OutFile $uvInstaller
            & $uvInstaller
            if (-not (Test-Path -LiteralPath $uv -PathType Leaf)) { throw 'Could not prepare the app runtime.' }
        } finally {
            $env:UV_INSTALL_DIR = $previousUvRoot
            $env:UV_NO_MODIFY_PATH = $previousNoPath
        }
    }
    $environmentRoot = Join-Path $appRoot ('versions\' + $necropsyVersion + '-' + [guid]::NewGuid().ToString('N'))
    Invoke-Checked $uv @('--quiet', 'venv', '--python', '3.14', '--managed-python', $environmentRoot)
    $python = Join-Path $environmentRoot 'Scripts\python.exe'
    Write-Host '[3/4] Installing Necropsy...'
    Invoke-Checked $uv @('--quiet', 'pip', 'install', '--python', $python, $wheel)
    $installed = & $python -m necropsy --version
    if ($LASTEXITCODE -ne 0 -or $installed.Trim() -ne "necropsy $necropsyVersion") {
        throw 'The app could not start. Your previous launcher has been preserved.'
    }

    Write-Host '[4/4] Making it easy to open next time...'
    # Relative to the launcher: no user-controlled path is interpolated into batch code.
    $relativePython = $python.Substring($appRoot.Length).TrimStart('\')
    $launcher = Join-Path $appRoot 'necropsy.cmd'
    $launcherTemp = Join-Path $workRoot 'necropsy.cmd'
    $contents = "@echo off`r`n`"%~dp0$relativePython`" -m necropsy %*`r`nif errorlevel 1 pause`r`n"
    [IO.File]::WriteAllText($launcherTemp, $contents, [Text.Encoding]::ASCII)
    Move-Item -LiteralPath $launcherTemp -Destination $launcher -Force
    if (-not $NoPathChange) {
        $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
        $parts = @($userPath -split ';' | Where-Object { $_ -and $_ -ne $appRoot })
        [Environment]::SetEnvironmentVariable('Path', (@($appRoot) + $parts -join ';'), 'User')
        $env:Path = "$appRoot;$env:Path"
    }
    if (-not $NoShortcuts) {
        $shell = New-Object -ComObject WScript.Shell
        $programs = [Environment]::GetFolderPath('Programs')
        $desktop = [Environment]::GetFolderPath('Desktop')
        foreach ($folder in @($programs, $desktop)) {
            if ($folder) {
                $shortcut = $shell.CreateShortcut((Join-Path $folder 'Necropsy.lnk'))
                $shortcut.TargetPath = $env:ComSpec
                $shortcut.Arguments = "/c `"`"$launcher`"`""
                $shortcut.WorkingDirectory = $appRoot
                $shortcut.Description = 'Analyze your Warcraft Logs and continue saved analyses.'
                $shortcut.Save()
            }
        }
    }
    Write-Host 'Ready! Next time, open Necropsy from your desktop or Start menu.' -ForegroundColor Green
    if (-not $NoLaunch) { & $python -m necropsy tui }
} catch {
    Write-Host "Necropsy setup could not finish: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Check your internet connection and run the same setup command again. Your reports and sign-in are preserved.'
    exit 1
} finally {
    if ($workRoot -and (Test-Path -LiteralPath $workRoot)) {
        $checkedRoot = [IO.Path]::GetFullPath($appRoot).TrimEnd('\') + '\'
        $checkedWork = [IO.Path]::GetFullPath($workRoot)
        if ($checkedWork.StartsWith($checkedRoot, [StringComparison]::OrdinalIgnoreCase) -and
            ([IO.Path]::GetFileName($checkedWork)).StartsWith('.setup-')) {
            Remove-Item -LiteralPath $checkedWork -Recurse -Force
        }
    }
}
