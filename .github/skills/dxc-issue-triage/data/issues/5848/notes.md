# Notes — issue #5848

## What was reported

`[raypayload]` struct `AOPayload` declares `ddxRay`/`ddyRay` as
`read(anyhit) : write(caller)`. In the reporter's `RaygenShader()`, both
fields are assigned directly (`payload.ddxRay = (AuxilliaryRay)ddx;`),
and then a helper function `TraceRadianceRay(ray, payload)` — not
`RaygenShader` itself — calls `TraceRay(...)`. DXC 1.7.2308.7 is reported
to warn that both fields are "'write' for 'caller' stage but field is
never written for TraceRay call", which the reporter calls a false
positive, since the fields ARE written, just in the caller of the
function that contains the `TraceRay` call. A maintainer (`llvm-beanz`)
asked for a real reproduction case; the reporter linked an external
multi-file game-engine repository (`MaicoDeBlasio/Win32GameDR.git`)
instead of a minimal repro, and the thread has no further maintainer
follow-up. Repro quality is therefore `agent-constructed`: no compilable
single-file repro exists in the issue thread.

## What was tested

`repro.hlsl` reconstructs the described shape as closely as the snippet
allows: an `AOPayload` with `normalAndDepth`/`occlusion`/`ddxRay`/`ddyRay`
fields, a `TraceRadianceRay` helper containing the `TraceRay` call, and
`RaygenShader`/`ClosestHit`/`Miss`/`AnyHit` stages. Two assignment idioms
were tried for the writes — member-wise (`payload.ddxRay.origin = ...`)
and whole-struct cast-assignment (`payload.ddxRay = (AuxRay)ddx;`,
matching the reporter's literal idiom more closely) — both captured in
`out-main-debug.txt` (`cmd.txt`: `-T lib_6_7 repro.hlsl`). Both produce
**zero warnings** on ground truth (`main-debug`, commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`). `-enable-payload-qualifiers`
defaults to on for `lib_6_7`+ (`lib/DxcSupport/HLSLOptions.cpp:902-904`),
so the reporter's command line (no explicit flag) is not the reason the
diagnostic is inactive.

The same repro was also compiled with the reporter's own historical
build, `v1.7.2308.7` (cached at
`build/tools/clang/test/dxc_releases/v1.7.2308/dxc_2023_08_14/bin/x64/dxc.exe`,
version confirmed via `--version`) — also zero warnings. **The
reconstructed repro does not produce the reported warning on either
ground truth or the reporter's own compiler build.**

## Why: source-level explanation, not just an observed absence

`tools/clang/lib/Sema/SemaDXR.cpp` was read to understand the mechanism
rather than continue blind trial-and-error:

- `DXRShaderVisitor::VisitFunctionDecl` (~line 1139) sets
  `Info.Payload = nullptr` for `raygeneration` shaders — raygen has no
  incoming payload *parameter*; it declares payload as a local variable.
- `DiagnosePayloadAccess` (~line 982) gates its entire write/read
  tracking, and the recursive `DiagnosePayloadAsFunctionArg` call
  (~line 1027) — the only mechanism that descends into a helper
  function's own body to analyze a `TraceRay` call inside it — behind
  `if (Info.Payload)` (~line 999). Since raygen's `Info.Payload` is
  always null, **this recursion never runs for a raygeneration shader.**
- `DiagnoseBuiltinCallsWithPayload` (~line 1044, called unconditionally)
  only detects `TraceRay`/`HitObject::TraceRay`/`HitObject::Invoke` calls
  that are literal `CallExpr` nodes in the *current* function's own body
  (`CollectBuiltinCallsWithPayload`/`IsBuiltinWithPayload`) — a
  user-defined helper such as `TraceRadianceRay` is invisible to this
  scan too, since Sema does not inline function bodies.

Net effect: whenever a shader stage that carries a freshly-declared
*local* payload (in practice: `raygeneration`) calls `TraceRay` through a
wrapper/helper function rather than directly, the entire
`-Wpayload-access-trace` "write field never written for TraceRay call"
check for that call is **silently skipped** — not suppressed correctly,
not producing a false positive, simply never evaluated.

## Empirical confirmation (not just source reading)

Three controls were captured through `triage.py run --shader ... --label
... --expect ...` against `main-debug` so they are re-checkable and
re-scoreable by `reindex`/`audit`, not just asserted from scrollback:

- `variant-control-direct-unwritten-main-debug.txt`
  (`control-direct-genuinely-unwritten.hlsl`, `--expect match`,
  **result: repro/match**) — `ddxRay`/`ddyRay` are genuinely never
  written anywhere, and `TraceRay` is called **directly** in
  `RaygenShader` (no helper). This produces the exact
  `-Wpayload-access-trace` "never written for TraceRay call" warnings
  for both fields. This is the self-test / anti-vacuity check: it proves
  the diagnostic, the compiler, and `match.json`'s regex are all capable
  of firing on this exact class of violation, so the absence seen
  elsewhere is not an instrument defect.
- `variant-control-direct-cast-assign-main-debug.txt`
  (`variant-direct-trace-cast-assign.hlsl`, `--expect no-match`,
  **result: no-repro, as expected**) — isolates the whole-struct
  cast-assignment idiom with a **direct** `TraceRay` call: the fields
  are written via `payload.ddxRay = (AuxRay)ddx;` and the check correctly
  recognizes this as a write (no `-Wpayload-access-trace` warning; only
  two unrelated, expected `-Wpayload-access-perf` warnings about
  `normalAndDepth`/`occlusion` never being read after the call). Rules
  out the cast-assignment idiom as a contributing factor.
- `variant-helper-genuinely-unwritten-main-debug.txt`
  (`variant-genuinely-unwritten.hlsl`, `--hypothesis`, `--expect
  no-match`, **outcome: supported**) — same fields **genuinely never
  written anywhere** (a real violation, unlike the reporter's claim), but
  `TraceRay` is invoked through the `TraceRadianceRay` helper, exactly as
  in the reporter's scenario. Zero warnings, on ground truth. This is a
  **verified, different defect** from what the reporter describes: not a
  false positive, but a genuine, silent loss of coverage for a common
  code-organization pattern (wrapping `TraceRay` in a helper).

The public Compiler Explorer link
(https://godbolt.org/z/d1a7E9Mxj, `dxc_trunk`, banner in
`godbolt-note.txt`) publishes this last case: `dxc_trunk` compiles it
with **zero warnings** even though the fields are genuinely never
written. CE's oldest DXC (`dxc_1_6_2112`) cannot run it —
`error: invalid profile lib_6_7` (SM 6.7 profile did not exist yet;
correctly excluded as `invalid-probe`, not evidence of a fix or absence).

Because the reporter's exact snippet **and** the reporter's exact
compiler build cannot be made to emit the reported warning, and because
the underlying gating (`Info.Payload = nullptr` for raygen) is
foundational to how the analysis is structured rather than a
recently-changed code path, this does not look like a regression that
`bisect` would usefully date — both tested endpoints (v1.7.2308.7 and
main-debug at `89e2f98e2`) already agree (no warning), so a release
bisect over `match.json`'s literal `ddxRay`/`ddyRay` text would report
`never-repro'd-in-releases` for this specific reconstruction, which is
not informative beyond what is already shown here.

## Assessment

The reported false positive cannot be reproduced from a faithful,
best-effort reconstruction of the reporter's own code snippet, on either
their exact compiler version or current `main`. Two explanations remain
open, and the evidence here cannot distinguish between them:

1. The reporter's actual project code (only available as an external,
   multi-file, unbuildable-here game-engine repository) differs from the
   inline snippet in some load-bearing way not captured by the snippet —
   plausible, since the maintainer already noted the snippets were "too
   brief" and no minimal repro was ever supplied.
2. The warning came from a different configuration or DXC version not
   represented by this reconstruction.

Separately, and not something the reporter asked about, this
investigation did surface a real, verified defect in the same
diagnostic: `-Wpayload-access-trace`'s "field never written for TraceRay
call" check is unconditionally skipped whenever the call reaching
`TraceRay` is one function away from a shader stage carrying a freshly
declared local payload (i.e., `raygeneration`) rather than an inline
`TraceRay` call — verified with both a correct case (`no-repro`,
correctly) and a genuinely-broken case (`no-repro`, incorrectly — should
warn and does not). This is a missing-diagnostic-coverage gap, the
opposite direction of problem from what #5848 reports, so it is recorded
here as a related observation rather than folded into this issue's
verdict.

## Verdict

`inconclusive` / `agent-constructed` repro. The reported false positive
was not observed on the reconstructed repro against ground truth
(`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`) or against the reporter's
own historical build (v1.7.2308.7). No minimal repro was ever supplied
despite being requested. Suggested action: `needs-repro-from-reporter`.
