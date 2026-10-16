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
$necropsyVersion = '0.3.0'
$releaseBase = "https://github.com/David-c0degeek/necropsy/releases/download/v$necropsyVersion"
$wheelName = "necropsy-$necropsyVersion-py3-none-any.whl"
$guiName = "necropsy-desktop-$necropsyVersion-windows-x86_64.zip"
$uvVersion = '0.11.21'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$workRoot = $null

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Setup step failed (exit $LASTEXITCODE). Run this installer again to retry." }
}

function Test-WebView2 {
    $client = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
    foreach ($key in @("HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\$client", "HKCU:\Software\Microsoft\EdgeUpdate\Clients\$client")) {
        $runtime = Get-ItemProperty -LiteralPath $key -Name pv -ErrorAction SilentlyContinue
        if ($runtime -and $runtime.pv -and [version]$runtime.pv -gt [version]'0.0.0.0') { return $true }
    }
    return $false
}

function Ensure-WebView2 {
    param([string]$Directory)
    if (Test-WebView2) { return }
    Write-Host 'Preparing the Windows desktop display runtime...'
    $bootstrapper = Join-Path $Directory 'MicrosoftEdgeWebview2Setup.exe'
    Invoke-WebRequest -UseBasicParsing 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile $bootstrapper
    $signature = Get-AuthenticodeSignature -LiteralPath $bootstrapper
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation(?:,|$)') {
        throw 'The display runtime download is not trusted. Setup stopped; your previous app is preserved.'
    }
    $runtimeSetup = Start-Process -FilePath $bootstrapper -ArgumentList '/silent /install' -Wait -PassThru -WindowStyle Hidden
    if ($runtimeSetup.ExitCode -ne 0 -or -not (Test-WebView2)) {
        throw 'Could not prepare Microsoft WebView2. Install it from Microsoft, then retry Necropsy setup.'
    }
}

try {
    $appRoot = [IO.Path]::GetFullPath($InstallRoot)
    New-Item -ItemType Directory -Force -Path $appRoot | Out-Null
    $workRoot = Join-Path $appRoot ('.setup-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $workRoot | Out-Null
    Write-Host 'Necropsy setup - getting everything ready for you.' -ForegroundColor Cyan
    Write-Host '[1/4] Getting the app...'
    $wheel = Join-Path $workRoot $wheelName
    $guiArchive = Join-Path $workRoot $guiName
    $sums = Join-Path $workRoot 'SHA256SUMS'
    if ($BundleDirectory) {
        Copy-Item -LiteralPath (Join-Path $BundleDirectory $wheelName) -Destination $wheel
        Copy-Item -LiteralPath (Join-Path $BundleDirectory $guiName) -Destination $guiArchive
        Copy-Item -LiteralPath (Join-Path $BundleDirectory 'SHA256SUMS') -Destination $sums
    } else {
        Invoke-WebRequest -UseBasicParsing "$releaseBase/$wheelName" -OutFile $wheel
        Invoke-WebRequest -UseBasicParsing "$releaseBase/$guiName" -OutFile $guiArchive
        Invoke-WebRequest -UseBasicParsing "$releaseBase/SHA256SUMS" -OutFile $sums
    }
    foreach ($assetName in @($wheelName, $guiName)) {
        $matching = @(Get-Content -LiteralPath $sums | Where-Object {
            $_ -match ('^([0-9a-fA-F]{64})\s+\*?' + [regex]::Escape($assetName) + '$')
        })
        if ($matching.Count -ne 1) { throw 'The download checksum is missing or ambiguous. Please retry setup.' }
        $expected = ($matching[0] -split '\s+')[0]
        $hasher = [Security.Cryptography.SHA256]::Create()
        $assetStream = [IO.File]::OpenRead((Join-Path $workRoot $assetName))
        try { $actualHash = [BitConverter]::ToString($hasher.ComputeHash($assetStream)).Replace('-', '') }
        finally { $assetStream.Dispose(); $hasher.Dispose() }
        if ($actualHash -ne $expected) {
            throw 'The app download was damaged. Nothing was installed. Please retry setup.'
        }
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
    $guiRoot = Join-Path $environmentRoot 'gui'
    Expand-Archive -LiteralPath $guiArchive -DestinationPath $guiRoot
    $gui = Join-Path $guiRoot 'Necropsy\necropsy-desktop.exe'
    Ensure-WebView2 $workRoot
    $guiOutput = Join-Path $workRoot 'gui-check.txt'
    $guiError = Join-Path $workRoot 'gui-check-error.txt'
    $guiCheck = Start-Process -FilePath $gui -ArgumentList '--check-install' -Wait -PassThru -WindowStyle Hidden -RedirectStandardOutput $guiOutput -RedirectStandardError $guiError
    $guiVersion = Get-Content -Raw -LiteralPath $guiOutput
    if ($guiCheck.ExitCode -ne 0 -or "$guiVersion".Trim() -ne "necropsy $necropsyVersion") {
        throw 'The graphical app could not start. Your previous launcher has been preserved.'
    }

    Write-Host '[4/4] Making it easy to open next time...'
    # Relative to the launcher: no user-controlled path is interpolated into batch code.
    $relativePython = $python.Substring($appRoot.Length).TrimStart('\')
    $relativeGui = $gui.Substring($appRoot.Length).TrimStart('\')
    $launcher = Join-Path $appRoot 'necropsy.cmd'
    $launcherTemp = Join-Path $workRoot 'necropsy.cmd'
    $contents = "@echo off`r`nset `"NECROPSY_GUI_PATH=%~dp0$relativeGui`"`r`nif `"%~1`"==`"`" (`r`nstart `"`" `"%NECROPSY_GUI_PATH%`"`r`nexit /b`r`n)`r`n`"%~dp0$relativePython`" -m necropsy %*`r`nif errorlevel 1 pause`r`n"
    [IO.File]::WriteAllText($launcherTemp, $contents, [Text.Encoding]::ASCII)
    [IO.File]::WriteAllText((Join-Path $appRoot 'gui-path'), $gui)
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
                $shortcut.TargetPath = $gui
                $shortcut.Arguments = ''
                $shortcut.WorkingDirectory = Split-Path -Parent $gui
                $shortcut.IconLocation = Join-Path (Split-Path -Parent $gui) 'icon.ico'
                $shortcut.Description = 'Analyze your Warcraft Logs and continue saved analyses.'
                $shortcut.Save()
            }
        }
    }
    Write-Host 'Ready! Next time, open Necropsy from your desktop or Start menu.' -ForegroundColor Green
    if (-not $NoLaunch) { Start-Process -FilePath $gui -WorkingDirectory (Split-Path -Parent $gui) }
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
