<#
.SYNOPSIS
    Compile every resume/rendition-*.tex and verify each PDF before accepting it.

.DESCRIPTION
    Renditions are alternate cuts of the same true content - different keyword density,
    section order, and length - kept side by side so they can be compared as PDFs.

    Every rendition is gated on tools/check_resume.py, which fails the build on empty
    entries, blank bands, orphaned final pages, and mis-aligned table rows. A rendition
    that does not pass is reported and does not stop the others from building.

.PARAMETER Only
    Build a single rendition by slug, e.g. -Only ats-dense.

.EXAMPLE
    .\tools\build-renditions.ps1
#>
[CmdletBinding()]
param(
    [string]$Only
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$resumeDir = Join-Path $root 'resume'
$outDir = Join-Path $resumeDir 'build\renditions'

$tectonic = (Get-Command tectonic -ErrorAction SilentlyContinue).Source
if (-not $tectonic) {
    $candidate = "$env:LOCALAPPDATA\tectonic\tectonic.exe"
    if (Test-Path $candidate) { $tectonic = $candidate }
}
if (-not $tectonic) { Write-Error "tectonic not found. See tools/build-resume.ps1 for install steps." }

if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force $outDir | Out-Null }

# Same reproducibility pinning as the main build: no clock churn in the PDF bytes.
$epoch = git -C $root log -1 --format=%ct -- resume/
if (-not $epoch) { $epoch = '1700000000' }
$env:SOURCE_DATE_EPOCH = $epoch.Trim()
$env:FORCE_SOURCE_DATE = '1'

$mains = Get-ChildItem (Join-Path $resumeDir 'rendition-*.tex') | Sort-Object Name
if ($Only) { $mains = $mains | Where-Object { $_.BaseName -eq "rendition-$Only" } }
if (-not $mains) { Write-Error "No renditions matched." }

$failed = @()

Push-Location $resumeDir
try {
    foreach ($main in $mains) {
        $slug = $main.BaseName -replace '^rendition-', ''
        Write-Host "`n=== $slug ===" -ForegroundColor Cyan

        $proc = Start-Process -FilePath $tectonic -NoNewWindow -Wait -PassThru `
            -ArgumentList '-X', 'compile', $main.Name, '--outdir', 'build/renditions', '--keep-logs' `
            -RedirectStandardOutput (Join-Path $outDir "$slug.out") `
            -RedirectStandardError (Join-Path $outDir "$slug.err")

        if ($proc.ExitCode -ne 0) {
            Get-Content (Join-Path $outDir "$slug.err") -Tail 20
            $failed += "$slug (compile)"
            continue
        }

        $pdf = Join-Path $outDir "$($main.BaseName).pdf"
        $log = Join-Path $outDir "$($main.BaseName).log"
        & py (Join-Path $PSScriptRoot 'check_resume.py') $pdf `
            --sources (Join-Path $resumeDir "renditions\$slug") --log $log
        if ($LASTEXITCODE -ne 0) { $failed += "$slug (verify)" }

        $pages = & py -c "import pymupdf,sys; print(pymupdf.open(sys.argv[1]).page_count)" $pdf
        Write-Host "  $pdf  ($pages page(s))"

        # Publish a copy next to the rendition's own sources. build/ is gitignored, so
        # this is the copy that is committed and the one to hand to a job board.
        $slugDir = Join-Path $resumeDir "renditions\$slug"
        if (Test-Path $slugDir) {
            Copy-Item $pdf (Join-Path $slugDir "$slug.pdf") -Force
            Write-Host "  -> renditions\$slug\$slug.pdf"
        }
        else {
            Write-Warning "  no renditions\$slug directory; skipped publishing the PDF"
        }
    }
}
finally {
    Pop-Location
}

if ($failed.Count) {
    Write-Error "Renditions failed: $($failed -join ', ')"
}
Write-Host "`nAll renditions built and verified." -ForegroundColor Green
