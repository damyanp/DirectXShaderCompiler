# Method notes — #5258

## `--compiler <release-tag>` is a built-in per-release history mechanism

`run --compiler` accepts a raw catalogued release tag (e.g. `v1.8.2502`), not just a registered
compiler id: `resolve_compiler()` falls back to `ensure_release(tag)` when the id isn't already
registered. Combined with `--shader/--label/--match/--hypothesis`, this drives a full
history-across-releases matrix through the tool itself (proper subprocess capture, correct
headers, `expectation-kind`/`outcome` tracking) with no hand-rolled matrix script — used here to
bracket Example 2's fix (v1.8.2502 fails, v1.8.2505 onward passes) and to confirm Example 3's
always-repro across all 16 catalogued releases. `bisect` cannot do this for a non-primary shader:
it always reads `cmd.txt`/`repro.hlsl`. Worth calling out in the skill's "measuring history for a
non-primary shader" guidance, since the text mostly implies a bespoke matrix script is needed.

## `run --shader` invalid-probe detection isn't limited to feature-absence

Running the as-filed (typo'd, uncompilable) Example 2 snippet through `run --shader ... --match
match-example2.json` scored `invalid-probe`, not `no-match`, because its unrelated
"use of undeclared identifier" errors matched the same unsupported-marker heuristic used for
feature-absence (`-HV` unknown, etc.). That's the right call here too: an unrelated compile
error prevents any meaningful evaluation of the predicate under test, exactly the situation
`invalid-probe` exists to flag, even though the cause isn't a version/feature gap. Confirmed by
re-running with `--expect invalid-probe` (clean) after an initial `--expect no-match` run printed
the expected disagreement warning.

## Re-confirmed: PowerShell `Select-Object -First` truncates `$LASTEXITCODE`

Hit again while hand-verifying captures before running them through the tool: piping dxc's output
through `Select-Object -First N` ends the pipeline early and leaves `$LASTEXITCODE` reporting a
stale/wrong value (saw `-2147467259` for an invocation that actually exited 0). Capture full
output via `Out-String` first, then read `$LASTEXITCODE` immediately after, as the skill already
documents — this is a "yes, it really does happen" data point, not a new lesson.
