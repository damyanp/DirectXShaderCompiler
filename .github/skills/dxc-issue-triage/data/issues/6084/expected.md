# Expected symptom (#6084)

This is a CI/pipeline enhancement request, not a compiler defect. There is no HLSL
source, `dxc` invocation, or compiler output that could show "this reproduces" or
"this is fixed" — the thing being asked for is a change to `azure-pipelines.yml`
(add a `clang-cl` build on Windows to the regular test pipeline, not just release
builds).

"Reproduces" here means: the current CI pipeline definition on `main` still lacks
a `clang-cl` Windows build job (or lacks one that runs for non-release configs).
"Fixed" would mean `azure-pipelines.yml` (or an equivalent GitHub Actions workflow)
on `main` now builds with `clang-cl` on Windows outside of release-only builds.

Repro quality: **prose-only** — the issue is a plain feature request with no
shader, no command line, and nothing a compiler probe could exercise.

This will be classified `not-compiler-verifiable`. Evidence will come from reading
`azure-pipelines.yml` (and any GitHub Actions workflow files) at the ground-truth
commit, plus the public issue/PR timeline — not from running `dxc`.
