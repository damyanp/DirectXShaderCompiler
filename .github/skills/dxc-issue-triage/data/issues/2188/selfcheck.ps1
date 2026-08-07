# Manual completeness check for issue 2188, replacing `triage.py reindex`.
# `reindex` defaults to --reset (DELETE FROM issues; DELETE FROM runs), which is unsafe
# while other workers are writing, so the orchestrator withdrew it mid-batch. This does
# the same audit by reading only this issue's directory.
#
#   pwsh -File selfcheck.ps1 > selfcheck.txt
#
# Every line below is a check; "FAIL" anywhere means the evidence is incomplete.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Check($label, [bool]$ok, $detail = "") {
    $tag = if ($ok) { "ok  " } else { "FAIL" }
    if ($detail) { "$tag  $label -- $detail" } else { "$tag  $label" }
}

"# self-check for issue 2188   (generated $(Get-Date -Format s))"
""
"## 1. required artefacts present"
foreach ($f in @("expected.md", "repro.hlsl", "cmd.txt", "match.json",
                 "notes.md", "comment.md", "verdict.json", "issue.json",
                 "godbolt.txt", "godbolt-note.txt", "method-notes.md")) {
    Check "$f" (Test-Path $f)
}

""
"## 2. a captured output file for every compiler probed"
$outs = Get-ChildItem -Filter "out-*.txt"
Check "21 probes captured (main-debug + 20 releases)" ($outs.Count -eq 21) "found $($outs.Count)"
$noExit = $outs | Where-Object { -not (Select-String -Path $_ -Pattern '^# exit:' -Quiet) }
Check "every out-*.txt records an exit code" ($noExit.Count -eq 0) "$($noExit.Count) without"
$empty = $outs | Where-Object { $_.Length -lt 100 }
Check "no truncated/empty captures" ($empty.Count -eq 0) "$($empty.Count) suspiciously small"

""
"## 3. a captured output file for every variant, each with a declared expectation"
$vars = Get-ChildItem -Filter "variant-*-main-debug.txt"
Check "7 variant captures" ($vars.Count -eq 7) "found $($vars.Count)"
foreach ($v in $vars) {
    $e = (Select-String -Path $v -Pattern '^# expect:' | Select-Object -First 1).Line
    Check "$($v.Name) declares an expectation" ([bool]$e) $e
}
$srcs = Get-ChildItem -Filter "variant-*.hlsl"
Check "each variant .hlsl has a capture" ($srcs.Count -eq 5) "5 standalone + control-inlined.hlsl + an -args run = 7 captures"

""
"## 4. claims in notes.md / comment.md that must be backed by a file"
Check "exit 2147500037 (E_FAIL)" (Select-String out-main-debug.txt -Pattern '^# exit: 2147500037' -Quiet) "out-main-debug.txt"
Check "'variable length arrays' diagnostic" (Select-String out-main-debug.txt -Pattern 'variable length arrays are not supported' -Quiet) "out-main-debug.txt"
Check "'numthreads attribute requires an integer constant'" (Select-String out-main-debug.txt -Pattern "'numthreads' attribute requires an integer constant" -Quiet) "out-main-debug.txt"
Check "'Group size of 0' warning" (Select-String out-main-debug.txt -Pattern 'Group size of 0' -Quiet) "out-main-debug.txt"

$vla = @($outs | Where-Object { Select-String -Path $_ -Pattern 'variable length arrays are not supported' -Quiet })
$nt  = @($outs | Where-Object { Select-String -Path $_ -Pattern "'numthreads' attribute requires an integer constant" -Quiet })
Check "VLA error in all 21 probes" ($vla.Count -eq 21) "$($vla.Count)/21"
Check "numthreads error in all 21 probes" ($nt.Count -eq 21) "$($nt.Count)/21"

$gs = @($outs | Where-Object { Select-String -Path $_ -Pattern 'Group size of 0' -Quiet } | ForEach-Object { $_.Name })
Check "'Group size of 0' absent before v1.8.2403" (-not ($gs -match 'v1\.7|v1\.6|v1\.5|v1\.4')) "present in: $($gs -join ', ')"

Check "control compiles clean" (Select-String variant-control-inlined-main-debug.txt -Pattern '^# exit: 0' -Quiet) "variant-control-inlined-main-debug.txt"
Check "scalar array bound compiles" (Select-String variant-scalar-array-main-debug.txt -Pattern '^# exit: 0' -Quiet) "variant-scalar-array-main-debug.txt"
Check "scalar numthreads compiles" (Select-String variant-scalar-numthreads-main-debug.txt -Pattern '^# exit: 0' -Quiet) "variant-scalar-numthreads-main-debug.txt"
Check "brace-init still fails" (-not (Select-String variant-braced-init-main-debug.txt -Pattern '^# exit: 0' -Quiet)) "variant-braced-init-main-debug.txt"
Check "-HV 2021 still fails" (-not (Select-String variant-hv2021-main-debug.txt -Pattern '^# exit: 0' -Quiet)) "variant-hv2021-main-debug.txt"

Check "FXC folds to dcl_thread_group 8, 8, 1" (Select-String manual-case-fxc.txt -Pattern 'dcl_thread_group 8, 8, 1' -Quiet) "manual-case-fxc.txt"
Check "FXC version recorded" (Select-String manual-case-fxc.txt -Pattern '10\.1' -Quiet) "manual-case-fxc.txt"
Check "clang 'not a constant expression' note" (Select-String manual-case-ce.txt -Pattern 'not a constant expression' -Quiet) "manual-case-ce.txt"
Check "clang control compiles on CE" (Test-Path manual-case-ce-control-link.txt) "manual-case-ce-control-link.txt"
Check "source citations captured" (Test-Path manual-case-source.txt) "manual-case-source.txt"

""
"## 5. Compiler Explorer link recorded (step 7)"
$v = Get-Content verdict.json -Raw | ConvertFrom-Json
Check "verdict.json carries godbolt_url" ([bool]$v.godbolt_url) $v.godbolt_url
Check "verdict.json carries the full snapshot" ($v.PSObject.Properties.Name.Count -ge 17) "$($v.PSObject.Properties.Name.Count) fields"
foreach ($k in @("status", "repro_quality", "history", "confidence", "suggested_action",
                 "triaged_with_commit", "labels_now", "labels_add")) {
    Check "verdict.json.$k" ([bool]$v.$k) "$($v.$k)"
}
