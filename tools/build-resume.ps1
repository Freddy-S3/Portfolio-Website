<#
.SYNOPSIS
    Compile resume/resume.tex to Certificates/Freddy_Shaikh_Resume.pdf and cascade it into the site.

.DESCRIPTION
    Runs xelatex twice (awesome-cv needs two passes for its layout), copies the PDF to
    Certificates/ where both "Download CV" buttons point, then regenerates index.html
    from the .tex sources.

    Requires MiKTeX:  winget install MiKTeX.MiKTeX

.PARAMETER Open
    Open the PDF when the build succeeds.

.PARAMETER SkipSite
    Compile the PDF only; leave index.html alone.

.EXAMPLE
    .\tools\build-resume.ps1 -Open
#>
[CmdletBinding()]
param(
    [switch]$Open,
    [switch]$SkipSite
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$resumeDir = Join-Path $root 'resume'
$buildDir = Join-Path $resumeDir 'build'
$target = Join-Path $root 'Certificates\Freddy_Shaikh_Resume.pdf'

# Tectonic is preferred: one self-contained binary that fetches the packages it
# needs, and it does not depend on the local MiKTeX package database.
$tectonic = (Get-Command tectonic -ErrorAction SilentlyContinue).Source
if (-not $tectonic) {
    $candidate = "$env:LOCALAPPDATA\tectonic\tectonic.exe"
    if (Test-Path $candidate) { $tectonic = $candidate }
}

$xelatex = $null
if (-not $tectonic) {
    $xelatex = (Get-Command xelatex -ErrorAction SilentlyContinue).Source
    if (-not $xelatex) {
        $candidate = "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\xelatex.exe"
        if (Test-Path $candidate) { $xelatex = $candidate }
    }
    if (-not $xelatex) {
        Write-Error @"
No LaTeX engine found. Install Tectonic (recommended):
  gh release download tectonic@0.17.0 --repo tectonic-typesetting/tectonic ``
    --pattern "*x86_64-pc-windows-msvc.zip" --dir "`$env:LOCALAPPDATA\tectonic"
  Expand-Archive "`$env:LOCALAPPDATA\tectonic\*.zip" -DestinationPath "`$env:LOCALAPPDATA\tectonic"
"@
    }
}

if (-not (Test-Path $buildDir)) { New-Item -ItemType Directory -Path $buildDir | Out-Null }

Push-Location $resumeDir
try {
    # Start-Process keeps the engine's stderr from being wrapped in NativeCommandError.
    if ($tectonic) {
        Write-Host "Compiling with tectonic..."
        # Tectonic reruns internally until references settle; one invocation is enough.
        $proc = Start-Process -FilePath $tectonic -NoNewWindow -Wait -PassThru `
            -ArgumentList '-X', 'compile', 'resume.tex', '--outdir', 'build', '--keep-logs' `
            -RedirectStandardOutput (Join-Path $buildDir 'tectonic.out') `
            -RedirectStandardError (Join-Path $buildDir 'tectonic.err')
        if ($proc.ExitCode -ne 0) {
            Get-Content (Join-Path $buildDir 'tectonic.err') -Tail 20
            Write-Error "tectonic failed. Log: $(Join-Path $buildDir 'resume.log')"
        }
    }
    else {
        # Two passes: awesome-cv resolves its section layout on the second run.
        foreach ($pass in 1, 2) {
            Write-Host "xelatex pass $pass..."
            $proc = Start-Process -FilePath $xelatex -NoNewWindow -Wait -PassThru `
                -ArgumentList '-interaction=nonstopmode', '-halt-on-error', '-output-directory=build', 'resume.tex' `
                -RedirectStandardOutput (Join-Path $buildDir "pass$pass.out") `
                -RedirectStandardError (Join-Path $buildDir "pass$pass.err")
            if ($proc.ExitCode -ne 0) {
                $log = Join-Path $buildDir 'resume.log'
                if (Test-Path $log) {
                    Write-Host "--- last errors from resume.log ---"
                    Select-String -Path $log -Pattern '^!' -Context 0, 3 | Select-Object -First 5
                }
                Write-Error "xelatex failed on pass $pass. Full log: $log"
            }
        }
    }
}
finally {
    Pop-Location
}

Copy-Item (Join-Path $buildDir 'resume.pdf') $target -Force
Write-Host "PDF written to Certificates\Freddy_Shaikh_Resume.pdf"

if (-not $SkipSite) {
    & py (Join-Path $PSScriptRoot 'resume_to_site.py')
    if ($LASTEXITCODE -ne 0) { Write-Error "index.html generation failed." }
}

if ($Open) { Invoke-Item $target }
