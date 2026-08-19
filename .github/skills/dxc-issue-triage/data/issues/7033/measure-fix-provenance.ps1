$ErrorActionPreference = "Stop"

function Invoke-Recorded([string[]]$Command) {
  Write-Output ('> ' + ($Command -join ' '))
  & $Command[0] $Command[1..($Command.Length - 1)] 2>&1
  $code = $LASTEXITCODE
  Write-Output "exit: $code"
}

Invoke-Recorded @(
  "git", "--no-pager", "show", "--stat", "--oneline",
  "61de7411f952cb0c4b6c73091555dad6419180ee"
)
Invoke-Recorded @(
  "git", "--no-pager", "show", "--format=fuller",
  "61de7411f952cb0c4b6c73091555dad6419180ee", "--",
  "tools/clang/lib/SPIRV/DebugTypeVisitor.cpp",
  "tools/clang/test/CodeGenSPIRV/rayquery_debug.hlsl"
)
Invoke-Recorded @(
  "git", "merge-base", "--is-ancestor",
  "61de7411f952cb0c4b6c73091555dad6419180ee", "v1.9.2602"
)
Invoke-Recorded @(
  "git", "merge-base", "--is-ancestor",
  "61de7411f952cb0c4b6c73091555dad6419180ee", "v1.8.2505.1"
)
Invoke-Recorded @(
  "git", "merge-base", "--is-ancestor",
  "61de7411f952cb0c4b6c73091555dad6419180ee",
  "89e2f98e29c289ae8ad9e00dd310104fea9fd7df"
)
