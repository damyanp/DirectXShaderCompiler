# Notes — #5105 "Allow unused registers to be output to reflection"

## Ground truth

- Compiler: `main-debug`, registered in `.cache/compilers/main-debug.json`.
- `dxc --version`: `dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)`.
  The binary self-reports the fork-local build hash `7665270b9`; the publicly-resolvable
  upstream commit it corresponds to is **89e2f98e29c289ae8ad9e00dd310104fea9fd7df**
  (`ced72eee3` on the triage branch is 5 commits ahead of it, all triage-skill-only).
- Verified by **tree**, not by SHA lookup alone, per the skill's provenance-correction guidance:
  `git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df` touches **5315**
  files, **0** of them outside `.github/skills/dxc-issue-triage/`. Control (to prove the diff
  mechanism actually discriminates rather than silently matching everything): the same command
  against a commit ~500 revisions older shows **1096** files changed outside the skill directory.
  So the ground-truth build's tree is source-identical to public `89e2f98e...` everywhere outside
  the triage skill tree.

## The request

Feature request (labelled `enhancement`), filed 2023-03-20. The reporter builds a visual
scripting tool on top of HLSL shaders; each declared resource register is exposed as a stable
node in a graph. DXC's normal dead-code elimination removes an unreferenced resource's
declaration entirely, so:

- an unused resource silently disappears from DXIL reflection, breaking a previously-saved
  graph that referenced its node;
- a resource that starts being used reappears, and its ID/ordinal can shift relative to
  neighbours, again breaking saved graphs.

The reporter explicitly asks for "O0 or a flag to avoid stripping this". Thread comments narrow
the scope to **DXIL** (not SPIR-V) and record two design suggestions from maintainers/contributors
(tex3d: a rewriter mode with a pre-assigned binding table via the hidden
`-binding-table-define` option; suggestion to contribute the feature externally per
CONTRIBUTING.md) — no commitment from the project to build it in-tree at the time of the last
comment (2024-04-29).

## Repro and instrument

`repro.hlsl` (agent-constructed, since the issue carries no code) declares two `Texture2D` and
one `SamplerState`, all with explicit `register()` bindings; only `usedTex`/`samp` are read by
`main`, `unusedTex` (`t1`) is declared but never referenced. `cmd.txt` is
`-T ps_6_0 -E main repro.hlsl` — no extra flags, so `dxc` prints its disassembly (including the
`; Resource Bindings:` comment table) straight to stdout, which `run` captures.

`dxa.exe` (which would drive `ID3D12ShaderReflection` directly, as the skill recommends for
reflection questions) is **not present** in this build tree, and building it would mean
rebuilding/relinking a shared target, which is out of scope for this session. The disassembly's
`Resource Bindings` comment table is generated from the same `!dx.resources` metadata that
backs `ID3D12ShaderReflection`, so it is used as the reflection proxy instead; this is recorded
as a limitation, not silently substituted.

`match.json` is `all_of[contains "usedTex", not_contains "unusedTex"]`. The `usedTex` clause is
a required anchor (the skill's absence-predicate hazard: without it, any release that simply
fails to compile `ps_6_0` at all would trivially satisfy the bare absence clause and manufacture
a "fixed" reading).

## Controls

- **Ground truth probe** (`out-main-debug.txt`): exit 0, disassembly's Resource Bindings table
  lists only `samp` (s0) and `usedTex` (t0); `unusedTex` has no row. Predicate: **match**
  (symptom present — the request is still unmet).
- **`-O0` was tried by hand first** (the reporter's own suggested workaround) and is *not* a
  separate registered flag on any known compiler, so it could not go through `run --shader`
  directly; the identical `dxc.exe -T ps_6_0 -E main repro.hlsl -O0` was run manually and
  produces the same Resource Bindings table (only `samp`/`usedTex`), confirming `-O0` does
  **not** prevent the stripping the reporter hoped it would. (Manual result, reproducible by
  re-running the same command by hand; not captured through `run` because `-O0` is not a labelled
  variant of interest for bisection — it changes optimisation, not the question being asked.)
- **Negative control** (`variant-control-used-main-debug.txt`, `--expect no-match`,
  `control-both-used.hlsl`): identical declarations, but `unusedTex` is also read by `main`.
  Predicate scores **no-match** as declared — `unusedTex` now has a row (`T1`/`t1`) in the
  Resource Bindings table, proving the absence clause discriminates real removal from a broken
  reader, and that the anchor/absence pair is not vacuously satisfied.
- **Unknown-flag check**: both flags named in the two open PRs that target this issue were run
  directly against the ground-truth build and both are rejected as unrecognised:
  `dxc failed : Unknown argument: '-keep-all-resources'` and
  `dxc failed : Unknown argument: '-fhlsl-unused-resource-bindings=reserve-all'`. `--help-hidden`
  also has no matching entry. A source grep for both option strings and for `reserve-all` finds
  no hits in this tree (`reserve-all` false-positives once, on the unrelated
  `hlsl-dxil-preserve-all-outputs` pass name).

## History

`bisect --issue 5105` (no `--match-crash`/second predicate needed; single question):
`always-repro'd across v1.4.1907..v1.9.2607` (5 probeable prereleases excluded from the search
by policy, none named explicitly in the issue text so none opt in via `release-policy.json`).
Both endpoints and both re-probes score `repro`, not `invalid-probe`, so v1.4.1907 could and did
express the repro (`ps_6_0` has existed since the floor release) — this is a genuine "no release
has ever had this feature" result, not a regression. That reading matches the issue's own
history: no comment claims the behaviour ever differed, and the two candidate fixes (#7643,
#7734) are still open PRs, not merged commits, as of the ground-truth commit.

## Cross-references (read during fetch, `gh api .../timeline`)

- `microsoft/hlsl-specs#192` "Auto binding register indices are very confusing" (2024-04-07) —
  a related design discussion, not a direct fix.
- `microsoft/DirectXShaderCompiler#7643` "[DXIL] Add `-fhlsl-unused-resource-bindings=reserve-all`
  to ensure consistent binding assignments" (2025-07-16) — **open**, unmerged. Its own body says
  `Fixes microsoft/DirectXShaderCompiler#7931` (a different, narrower issue about *which* register
  an unused-but-undeclared-register resource gets assigned), not #5105 directly, though it is the
  same subsystem (`DCE removes only symbols initially... unused resources stripped at the end`).
- `microsoft/DirectXShaderCompiler#7734` "`-keep-all-resources` option to preserve optimized-out
  resources in DXIL reflection" (2025-09-04) — **open**, unmerged. Its own body says
  `Step 2/2 to solve microsoft/DirectXShaderCompiler#5105` — this is the PR that most directly
  targets this issue, and would satisfy the request as described (unused resources appear in
  reflection, no `createHandle` emitted) if/when merged.
- `microsoft/DirectXShaderCompiler#7931` "[DXIL] Inconsistent register assignments for unused
  resources without explicit register annotations" (2025-11-19, filed *after* #7643) — a
  related, narrower defect about non-determinism when registers are implicit, fixed by #7643.
  Checked with `gh pr view --json state,mergedAt` for both PRs on 2026-08-19: both `state: OPEN`,
  `mergedAt` empty — confirmed not yet landed, consistent with the grep/flag-rejection evidence
  above from the ground-truth build itself (which is the load-bearing check; the PR state is
  corroborating, not the primary evidence, since a PR's open/closed state can change after this
  write-up and the flag-rejection test is what's actually reproducible from this build).

## Verdict reasoning

The reported gap is real and still open on `main` as of the ground-truth commit: no shipped
release and no flag on this build lets an unused, explicitly-registered resource remain visible
in DXIL reflection. This is not a regression (`always-repro'd` = "never implemented", confirmed
by the source grep finding no trace of either proposed flag) and the issue text is not stale —
the symptom described in 2023 is exactly what was measured in 2026, and the request has since
attracted a two-part, in-progress upstream design (#7643 + #7734, the second of which explicitly
targets this issue number) rather than being abandoned. `still-valid-keep-open` is the correct
suggested action; `close-fixed` would be wrong (neither PR has merged) and `needs-repro-from-
reporter` would be wrong (the request itself, not a missing repro, is what's incomplete —
the constructed repro above is sufficient to demonstrate the gap).

## What could not be determined

- Whether `#7643`/`#7734` (or a successor PR) fully satisfy the reporter's stability requirement
  once merged — that depends on review outcomes not yet settled, and is out of scope to predict.
- `ID3D12ShaderReflection`'s exact behaviour (as opposed to the disassembly comment proxy) is not
  directly measured here, since `dxa.exe` is not built in this tree and building it was avoided
  per the constraint on rebuilding/relinking shared targets during this session.
