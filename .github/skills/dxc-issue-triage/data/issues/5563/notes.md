# Notes — #5563 "found unregistered decl" partial template specialization (SPIR-V)

## Summary

Filed 2023-08-17 against DXC 1.7.0.3939 (5e080a772). Complete repro: a two-parameter
class template `TEST_STRUCT<bool, bool>` partially specialized on its second
parameter (`TEST_STRUCT<PARAM1, true>`), with a `static const bool FIELD = PARAM1;`
member referenced from a pixel shader. Compiling with
`-T ps_6_0 -E PSMain -spirv -HV 2021` was reported to fail with DXC's own
defensive SPIR-V-backend diagnostic:

```
repro.hlsl:7:16: fatal error: found unregistered decl
template <bool PARAM1>
               ^
note: please file a bug report on ... with source code if possible
```

`ground truth: main-debug @ 89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (the local
Debug binary self-reports fork-local merge `7665270b9`; see `expected.md` for the
tree-equivalence discussion carried over from the batch).

## Repro fidelity

`repro.hlsl` and `cmd.txt` reproduce the issue body's shader and command
verbatim, including the reporter's exact target profile (`ps_6_0`, inferred
from `PSMain`/`SV_TARGET` since the Shader Playground link does not name a
profile explicitly, but this is the only sensible choice for a pixel shader
entry point).

## Ground-truth result: does not reproduce

`out-main-debug.txt`: exit 0, complete SPIR-V module ending `OpFunctionEnd`, no
`found unregistered decl` diagnostic.

Because the default optimizer completely eliminates the unused local `test`
(the filed shader never reads it), a clean default-flags result alone would be
weak evidence -- an eliminated `DeclStmt` never re-enters the code path that
crashed in the first place, and "no symptom" could be an artifact of dead-code
elimination rather than a fix. `variant-unoptimized-main-debug.txt`
(`--args ... -Od`, `--expect no-match`) is the control that rules this out: at
`-Od` the front end still cannot eliminate the local, and the capture shows the
static member reference actually resolved -- `OpConstantTrue`, `%test =
OpVariable`, `OpStore %test %true` -- i.e. `FIELD` was correctly folded to
`true` and no fatal error fired. The code path that previously hit
`DeclResultIdMapper`'s `found unregistered decl` fatal error (line 1048 of
`tools/clang/lib/SPIRV/DeclResultIdMapper.cpp` on `main-debug`) is genuinely
exercised and succeeds, not merely skipped.

`variant-no-template-main-debug.txt` (`control-no-template.hlsl`, `--expect
no-match`) is the negative control for the predicate itself: an unrelated,
non-templated valid shader does not trip `contains "found unregistered
decl"`, so the predicate discriminates rather than matching everything.

## History: fixed in v1.9.2602

```
python scripts/triage.py bisect --issue 5563
```

```
v1.4.1907      invalid-probe (Unknown HLSL version: 2021)
v1.5.2010      invalid-probe (Unknown HLSL version: 2021)
v1.6.2104      invalid-probe (Unknown HLSL version: 2021)
v1.6.2106      invalid-probe (Unknown HLSL version: 2021)
v1.6.2112      repro   (exit 0x80004005; "found unregistered decl", matches the filed text)
v1.9.2607      no-repro
v1.8.2403.2    repro
v1.8.2505      repro
v1.9.2602      no-repro
v1.8.2505.1    repro   (last reproducing release)
```

`fixed-in v1.9.2602` (last repro `v1.8.2505.1`). 4 releases invalid-probe
(genuinely predate `-HV 2021` -- see `out-v1.4.1907.txt`/`out-v1.5.2010.txt`/
`out-v1.6.2104.txt`/`out-v1.6.2106.txt`, all "`dxc failed : Unknown HLSL
version: 2021`", exit 1, not the assert/crash class). 5 stable prereleases
skipped from the search by policy (not named by the issue). Every reproducing
release (`v1.6.2112` through `v1.8.2505.1`) prints the identical diagnostic
text and E_FAIL exit status (`0x80004005`/`2147500037`) as the filed report --
this is DXC's own `DiagnosticsEngine::Fatal`-level `clang::Diag`
(`emitFatalError`), never a debugger-trapped assert or access violation, so
`internal_failure` was correctly not used for `match.json`.

**Window:** `v1.8.2505.1` (built 2025-07-14) to `v1.9.2602` (built 2026-02-20);
229 commits total (`git log --oneline v1.8.2505.1..v1.9.2602 | wc -l`), 28 of
which touch `tools/clang/lib/SPIRV/SpirvEmitter.cpp` and 10 of which touch
`tools/clang/lib/SPIRV/DeclResultIdMapper.cpp`.

## Fixing commit: strong candidate identified by source analysis, not build-verified

Per this batch's constraint (no rebuild of any tree -- shared or per-issue --
for this pass), the exact commit was **not** bracketed by building candidate
+ parent binaries, unlike the batch-018 precedent. The following is a
source-level attribution, and is stated as strong rather than certain.

[`1e3da156b`](https://github.com/microsoft/DirectXShaderCompiler/commit/1e3da156b7aeab25b7e891010e579902322845ed)
("[SPIRV] Handle partial template class specialization", PR #7673, merged
2025-07-30) is the best match:

- Its own commit message: *"The SpirvEmitter does not handle
  `ClassTemplatePartialSpecializationDecl`. Since it extends `RecordDecl`, DXC
  attempts to generate code for the partial specialization, but fails because
  that is not possible. We need to avoid trying to generate code for the
  partial specialization and wait for a full specialization."* -- this is
  exactly `#5563`'s shape: `TEST_STRUCT<PARAM1, true>` is a
  `ClassTemplatePartialSpecializationDecl`, and the diff changes `doDecl`
  (`SpirvEmitter.cpp`) to skip it entirely instead of falling through to the
  `RecordDecl` case, which previously walked (and mis-registered) the partial
  specialization's own dependent members -- including `FIELD` -- rather than
  waiting for the real instantiation `TEST_STRUCT<true, true>`.
- **`git merge-base --is-ancestor 1e3da156b v1.9.2602`** exits 0 (is an
  ancestor); **`git merge-base --is-ancestor 1e3da156b v1.8.2505.1`** exits 1
  (is not) -- the commit sits exactly inside the measured release window.
- It fixed **#7007**, filed 2025 and independently closed by this same PR, whose
  reported diagnostic is textually identical: `` fatal error: found
  unregistered decl N `` on a different partial specialization
  (`matrix_traits<matrix<T,N,M>>`) with a non-type template parameter. #7007
  is a near-duplicate of #5563's underlying defect (partial specialization +
  non-type template parameter), reported roughly two years later and fixed
  faster because it had an active repro. (`gh issue view 7007` /
  `gh pr view 7673` -- both read-only lookups; no comment or label was
  written to either issue.)

A second, related commit in the same window,
[`b9af1ec44`](https://github.com/microsoft/DirectXShaderCompiler/commit/b9af1ec44364a5d359af82bee5adce7ee7fca76a)
("[SPIRV] Folding global constant variables", PR #7786, "Fixes: #7049",
merged 2025-10-01, also confirmed an ancestor of `v1.9.2602` and not of
`v1.8.2505.1`), generalizes `DeclResultIdMapper::tryToCreateConstantVar`
(formerly `tryToCreateImplicitConstVar`) to fold **non-implicit**, `bool`-typed
compile-time-constant decls -- exactly `FIELD`'s shape (`static const bool`,
explicitly written, not compiler-generated) -- where the prior code only
handled implicit `unsigned int` decls. Either commit alone plausibly changes
the outcome for this repro; which one (or both together) is load-bearing for
`#5563` specifically was not determined, because doing so needs a built
before/after bracket, which this pass does not perform. State the release
boundary (`v1.9.2602`) as the measured fact and both commits as candidates,
not a single certain attribution.

## Compiler Explorer

[`https://godbolt.org/z/Y1W7q714v`](https://godbolt.org/z/Y1W7q714v)
(read-back verified against `GET /api/shortlinkinfo/Y1W7q714v`: both panes'
compiler ids, arguments and source match exactly what was sent). `dxc_1_6_2112`
(CE's oldest DXC) fails the filed command with the same `found unregistered
decl` diagnostic at the same source location; `dxc_trunk` compiles cleanly and
emits a complete SPIR-V module. `godbolt-note.txt` deliberately does not quote
the literal diagnostic text (`manual-case-godbolt-verify.txt` shows the CE
source-embedding hazard in practice: an earlier draft of the banner that did
quote it was echoed back into `dxc_trunk`'s own `OpSource` string via
`-Qembed_debug`, which would have made a naive grep for the diagnostic text
appear in the *fixed* pane's output too; the archived
`manual-case-godbolt-verify-ea871d741c96.txt` documents that iteration before
the banner was corrected).

## Labels

Current: `bug`, `spirv`. Both remain accurate descriptions of the historical
defect. No addition or removal proposed; `hlsl2021` was considered (the
templates feature exercised here is gated by `-HV 2021`) but not added,
because DXC's C++ template support is not itself an `hlsl2021`-labelled
feature area elsewhere in the backlog and the defect is specific to SPIR-V
partial-specialization handling, which `spirv` already covers.

## Text staleness

**Marked stale.** The issue is still **open**, and its title --
`"found unregistered decl" when compiling partial template specialization for
SPIR-V` -- reads as a present-tense description of current DXC behavior. A
reader spot-checking the open issue today would reasonably conclude the
compiler still fails this way; it does not, since v1.9.2602 (built ~2026-02).
The body and the sole comment (2023-11-27, "What are chances for this to be
fixed in next few months?") do not themselves misstate current behavior --
only the standing title does, read against an issue left open.

## Cross-reference timeline

`gh api repos/microsoft/DirectXShaderCompiler/issues/5563/timeline` (read-only)
shows four pre-existing cross-references, all predating this triage pass by
years: 2023-10-17 `#5826`, 2024-07-16 `#6787`, 2024-09-12
`Devsh-Graphics-Programming/Nabla#696`, 2025-03-12 `#7007`. No event was
created by this triage session; the commit for this batch uses a bare issue
number.
