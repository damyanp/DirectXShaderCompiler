# microsoft/DirectXShaderCompiler#2188 -- capture FXC's answer to the same shaders.
#
# The `fxc-disagrees` label asserts FXC accepts what DXC rejects. That is a claim about a
# compiler this skill does not build, so it is measured rather than repeated. FXC is not a
# `dxc` invocation, so it cannot go through `triage.py run`; the output is filed as
# manual-case-fxc.txt per the SKILL.md naming rule.
#
# Re-runnable from the repo alone: the compiler path comes from $env:FXC (or the newest
# fxc.exe found under the Windows 10 SDK), never a hardcoded per-machine path.
#
#   pwsh -File run-fxc.ps1            # from data/issues/2188/
#   $env:FXC = 'C:\...\fxc.exe'; pwsh -File run-fxc.ps1

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$fxc = $env:FXC
if (-not $fxc) {
    $fxc = Get-ChildItem -Path "${env:ProgramFiles(x86)}\Windows Kits\10\bin" `
        -Filter fxc.exe -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match '\\x64\\' } |
        Sort-Object FullName | Select-Object -Last 1 -ExpandProperty FullName
}
if (-not $fxc -or -not (Test-Path $fxc)) {
    throw "fxc.exe not found; set `$env:FXC to a Windows SDK fxc.exe"
}

# cs_5_0: FXC has no Shader Model 6 profiles, so the DXC command's cs_6_0 cannot be reused
# verbatim. This is the closest equivalent and is the profile the 2019 report predates.
$cases = @(
    @{ file = 'repro.hlsl';                     why = 'the reported shader' }
    @{ file = 'control-inlined.hlsl';           why = "reporter's inlined-constant control" }
    @{ file = 'variant-array-only.hlsl';        why = 'const vector element as array bound only' }
    @{ file = 'variant-numthreads-only.hlsl';   why = 'const vector element in [numthreads] only' }
    @{ file = 'variant-scalar-array.hlsl';      why = 'const *scalar* as array bound' }
    @{ file = 'variant-scalar-numthreads.hlsl'; why = 'const *scalar* in [numthreads]' }
)

$out = "# compiler: fxc (not a dxc invocation -- see SKILL.md on manual-case-* naming)`n"
$out += "# exe: $fxc`n"
$out += "# ran: $((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))`n"
$out += "# profile: cs_5_0 (FXC has no SM6 profiles, so cmd.txt's cs_6_0 cannot be reused)`n"
$out += "# note: NOT scored by match.json -- this is a different compiler, not a probe of DXC`n`n"
$out += "$ fxc /nologo /T cs_5_0 /E csMain <file>`n`n"
$out += "--- fxc version banner ---`n"
$banner = & { $ErrorActionPreference = 'Continue'; & $fxc /? 2>&1 } |
    Where-Object { $_ -match '\S' } | Select-Object -First 3
$out += (($banner | ForEach-Object { "$_" }) -join "`n") + "`n"

foreach ($c in $cases) {
    $text = & { $ErrorActionPreference = 'Continue'
                & $fxc /nologo /T cs_5_0 /E csMain $c.file 2>&1 | Out-String }
    $rc = $LASTEXITCODE
    $head = ($text -split "`r?`n" | Where-Object { $_ -match '\S' } | Select-Object -First 6) -join "`n"
    # The interesting part is not "it compiled" but "it folded the constants": the thread
    # group declaration and the groupshared allocation carry the values DXC could not
    # evaluate.
    $key = ($text -split "`r?`n" | Where-Object { $_ -match 'dcl_thread_group|dcl_tgsm' }) -join "`n"
    $out += "`n==== $($c.file)  [$($c.why)]`n"
    $out += "[exit] $rc`n"
    $out += "[folded constants]`n$key`n"
    $out += "[first lines]`n$head`n"
}

Set-Content -Path 'manual-case-fxc.txt' -Value $out -Encoding utf8
Write-Host $out
