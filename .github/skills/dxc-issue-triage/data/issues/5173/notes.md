# Notes — #5173 "IDxcCursor misses semantics"

## Ground truth

`main-debug`, registered previously (batch-018) at public upstream commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`. Re-verified for this issue, without
rebuilding:

- `dxc --version` self-reports the fork-local build commit (`7665270b9`), as
  expected for a local build (see the general provenance-correction guidance).
- `git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD | Select-String
  -NotMatch '^\.github/skills/dxc-issue-triage/'` returns **0** results — no compiler
  source differs from the cited upstream commit.
- Control: diffing against an older SHA (used in batch-018) shows real
  differences outside the skill directory, so the empty diff above is not an
  artefact of a query that cannot detect anything.
- `build\Debug\bin\dxc.exe` / `dxcompiler.dll` already existed (timestamp
  2026-08-18); **not rebuilt** for this triage, per the no-rebuilds
  constraint for this session.

## What the issue asks

Full statement in `expected.md` (write-once, written before any probe ran).
Summary: walking the AST through `IDxcTranslationUnit`/`IDxcCursor` never
surfaces the HLSL semantic annotation (`SV_Target`, `TEXCOORD0`, ...) on a
struct field, a function parameter, or a function's return type — no cursor
kind identifies it and no accessor returns the semantic string. A maintainer
(llvm-beanz) replied on 2023-07-13 (~81 days after the 2023-04-23 filing)
that this is unlikely to be prioritized because the long-term plan is to
move client tooling to LSP instead of `IDxcCursor`, but a patch would be
accepted.

This is a feature-request / API-surface question, not a crash or a
wrong-codegen bug, and it is not measurable through `dxc.exe`'s command line —
`IDxcCursor` is a COM/libclang-style AST-walking API with no CLI surface.
`cmd.txt`/`match.json` are intentionally absent; see the harness section
below for the actual measuring instrument.

## Source-level chain of evidence

Read, not modified:

1. `include\dxc\dxcisense.h` — `DxcCursorKind` is a near-verbatim mirror of
   libclang's `CXCursorKind`. `DxcCursor_FirstAttr` .. `DxcCursor_LastAttr`
   (`DxcCursor_CUDASharedAttr` = 416) is the complete attribute-kind range;
   there is no HLSL-specific entry in it.
   `git log --all -- include/dxc/dxcisense.h` shows the cursor-kind enum has
   never been extended since the repository's first commit (`6ee4074a4`).
2. `tools\clang\include\clang\Basic\Attr.td` (~line 793) — `HLSLSemantic` is
   defined as an `InheritableAttr` on Function/ParmVar/Field, with
   `Spellings = []` (i.e. it was never meant to be written or seen as
   ordinary attribute syntax).
3. `tools\clang\tools\libclang\CXCursor.cpp` (~lines 45-66) — the
   `attr::Kind` → `CXCursor_*Attr` switch has no case for any HLSL attribute
   kind, so if one were ever constructed it would map to the generic
   `CXCursor_UnexposedAttr`.
4. Repo-wide search of `tools\clang\lib` for `HLSLSemanticAttr` (the class
   `Attr.td` would generate): **zero matches**. Nothing in the compiler ever
   constructs or attaches this attribute — the `Attr.td` entry is dead.
5. `tools\clang\lib\Sema\SemaHLSL.cpp` (~lines 12028-12030) is where
   semantics are actually recorded: via
   `hlsl::UnusualAnnotation::UA_SemanticDecl` / `hlsl::SemanticDecl`
   (`tools\clang\include\clang\AST\HlslTypes.h`, lines 229 / 318), a
   completely separate side-channel from the standard `Attr` list.
6. `tools\clang\include\clang\AST\Decl.h` (lines 188-196) —
   `setUnusualAnnotations`/`getUnusualAnnotations` are members patched
   directly onto `clang::Decl`, entirely independent of `Decl::attrs()`.
7. `tools\clang\tools\libclang\CIndex.cpp` — `CursorVisitor::VisitAttributes`
   (line 1726) walks exactly `D->attrs()`, and `line 502`
   (`return VisitAttributes(D) || Visit(D);`) is the only place attributes
   enter the cursor tree. Since `UnusualAnnotation`s are not in `attrs()`,
   they are **structurally invisible** to the mechanism `IDxcCursor::GetChildren`
   relies on (`clang_visitChildren` → `CursorVisitor::VisitChildren`) — not
   merely unexposed-but-present.
8. `git log --all -S "HLSLSemantic" -- tools/clang/tools/libclang/CXCursor.cpp
   tools/clang/tools/libclang/CIndex.cpp`: **zero commits** ever touched
   HLSL-specific cursor-kind support in libclang. Combined with (1), this
   supports treating the absence as unchanged for as long as this repository
   has existed, not merely "as far back as releases can be probed".

## Harness ("measuring instrument")

`IDxcCursor` has no CLI surface, so per this skill's guidance for a symptom
no compiler driver can reach, a small standalone program is the instrument.
It was **not** registered via `triage.py compiler`: this is a single ground
truth confirmation plus a coarse three-point historical check, not a
bisectable release matrix, and `IDxcTranslationUnit::ParseTranslationUnit`
takes no command-line arguments to vary (confirmed against
`tools\clang\unittests\HLSL\DXIsenseTest.cpp`'s usage pattern), so there is no
meaningful `cmd.txt` to hold constant across releases. Per the reindex
section's explicit guidance for this case: **this choice is stated here
rather than hidden** — `manual-case-*.txt`/`variant-*.txt` in this directory
are outside `triage.py run`/`bisect`/`reindex`'s automatic re-scoring.

Being outside automatic re-scoring does not mean being outside the
completeness check: `triage.py audit --issue 5173` wants a tool-made capture
for every `.hlsl` beside it, the same requirement SKILL.md states for a
matrix "driven by a hand-written script". `measure.py` now stamps every
capture it writes with `# variant: <label> (<source file>)`, the same
header key `triage.py`'s own labelled `run --shader` uses, so `audit`
recognises `repro.hlsl` and `control-numthreads.hlsl` as backed by this
generator rather than by a script nobody can point `audit` at. This closes
the two gaps `audit` previously reported here without changing any measured
result: the added `variant-*-main-debug.txt`/regenerated captures are
byte-identical in `# diagnostics:`/`# cursor tree:`/`# exit:` to the ones
this section's table already cites, and `repro.hlsl`'s official evidence
remains the `manual-case-*.txt` trio below, not the extra
`variant-repro-main-debug.txt` representative capture added solely to
satisfy `audit`. Re-run `measure.py` deliberately if this issue is
revisited.

- `isense_probe.cpp` (committed) — loads a given `dxcompiler.dll` via
  `dxcapi.use.h`'s `SpecificDllLoader` (`LoadLibrary`/`GetProcAddress`, no
  import-lib linking), creates `IDxcIntelliSense`/`IDxcIndex`, calls
  `ParseTranslationUnit` on an unsaved source file (no compiler flags), and
  recursively walks the cursor tree via `GetChildren`, printing each cursor's
  kind/spelling/display-name and flagging `[ATTR]` for any kind in the
  attribute range.
- `measure.py` (committed) — generator script: builds the harness from the
  committed `.cpp` only if stale (into the gitignored
  `.cache\scratch\5173\`, never into `data\issues\`), runs it against
  `--dxcompiler <path> --source <file>`, and writes
  `manual-case-<label>.txt` (primary repro) or `variant-<label>.txt`
  (control), stamping the exact `subprocess.list2cmdline` argv, exit code,
  and captured stdout/stderr, plus `# variant: <label> (<source file>)` and
  an optional documentary `# expect:` line (this harness has no
  `match.json` predicate for `reindex` to re-check it against, so `expect`
  here records the already-measured result rather than an unverified
  prediction). Absolute paths under this checkout's repo root are
  mechanically rewritten to `<repo>` at capture time (`redact()`), the same
  convention `triage.py` itself uses, so committed captures stay portable
  across machines. `cl.exe`/`vcvars64.bat` build the harness; no DXC source
  is modified or rebuilt.

## Repro result — `repro.hlsl`

`repro.hlsl`: `struct PSInput { float4 position : SV_POSITION; float2 uv :
TEXCOORD0; };` and `float4 main(PSInput input, float3 normal : NORMAL0) :
SV_TARGET` — one shader covering all three surfaces named in the issue
(struct field, function parameter, function return type).

Ran against three points, oldest-to-newest, chosen because git history (item
8 above) shows the relevant libclang code paths were never touched, so a full
20-release bisection would be pure repetition of the same measurement:

| label | dxcompiler.dll | diagnostics | attribute cursors seen for any of the 3 semantics |
| --- | --- | --- | --- |
| `main-debug` (ground truth, `89e2f98e2...`) | `manual-case-main-debug.txt` | 0 | **0** |
| `v1.4.1907` (oldest catalogued release, 2019-07) | `manual-case-v1.4.1907.txt` | 0 | **0** |
| `v1.9.2607` (newest catalogued release) | `manual-case-v1.9.2607.txt` | 0 | **0** |

All three produce byte-identical cursor-tree shapes for `repro.hlsl`: the
`PSInput` struct's two `FieldDecl`s, and `main`'s two `ParmDecl`s plus its
return type, each show only a `TypeRef` child — **no attribute-kind cursor
of any kind appears anywhere in the tree**, despite three semantic
annotations being present in the source and despite the compile succeeding
(0 diagnostics, so the annotations were parsed and accepted).

**Correction of `expected.md`'s prediction.** `expected.md` predicted the
best case would be a generic, empty-spelling `DxcCursor_UnexposedAttr` child
(reasoning from `HLSLSemanticAttr`'s `Attr.td` definition falling through the
`CXCursor.cpp` switch). The harness shows something stronger: **no attribute
cursor is emitted at all**, not even an unexposed one. Source item 5 above
resolves the discrepancy — `HLSLSemanticAttr` is never actually constructed;
semantics are carried entirely through `UnusualAnnotation`/`SemanticDecl`, a
side-channel `Decl::attrs()`/`VisitAttributes` never sees. So the true
mechanism is one layer further removed from `IDxcCursor` than `expected.md`
assumed: it is not "attribute exposed poorly", it is "not an `Attr` at all".

## Control — `control-numthreads.hlsl`

Positive control: `[numthreads(8,8,1)] void main(uint3 id : SV_DispatchThreadID)`.
`numthreads` is a real `Attr` subclass (`HLSLNumThreads`) constructed through
the ordinary `Attr` mechanism, unlike `HLSLSemantic`. This proves the harness
and `GetChildren` walk genuinely surface an attribute cursor when the
compiler creates one, ruling out "the harness/traversal simply never visits
attributes" as an alternative explanation for the repro's empty result.

| label | dxcompiler.dll | attribute cursor for `[numthreads(...)]` | attribute cursor for `SV_DispatchThreadID` on the same parameter |
| --- | --- | --- | --- |
| `main-debug` | `variant-main-debug.txt` | `DxcCursor_UnexposedAttr` (kind 400) | none |
| `v1.4.1907` | `variant-v1.4.1907.txt` | `DxcCursor_UnexposedAttr` (kind 400) | none |
| `v1.9.2607` | `variant-v1.9.2607.txt` | `DxcCursor_UnexposedAttr` (kind 400) | none |

The control shader carries **both** an `Attr`-based annotation
(`[numthreads]`) and a semantic (`SV_DispatchThreadID`) on the same function.
Only the former produces a cursor; the latter produces none, in the very
same tree, at all three build points — the sharpest available contrast, and
consistent with the source-level finding rather than merely "attributes are
never expanded by this compiler at all" (`expect no-match` self-test: the
compiler-level attribute mechanism *is* visible via `IDxcCursor` when it is
genuinely used, which is why the semantic side is not simply an ordinary
gap in the harness).

## Verdict reasoning

- **Status**: `repros` — the described gap is present exactly as the
  reporter describes it, confirmed both by reading the source (semantics
  never enter the `Attr` list `IDxcCursor` walks) and by direct measurement
  (0 attribute cursors for 3 semantic annotations, against a working
  attribute-cursor path proven live in the same tree by the control).
- **Repro quality**: `agent-constructed` (no repro shipped with the issue).
- **History**: `always-repro'd`. Source history shows the relevant libclang
  code was never touched (`git log --all -S`, item 8); the empirical
  3-point check (oldest catalogued release, newest catalogued release,
  current `main-debug`) agrees and shows no boundary. This is reported over
  the catalogued-release checkable range plus current `main`, per the
  method's floor for `always-repro'd` claims — the underlying design choice
  (dead `Attr.td` entry, `UnusualAnnotation` side-channel) predates the
  bisection floor and is not newly introduced.
- **Confidence**: `high` — corroborated by source (an absence proven by
  reading every place an `Attr`-kind cursor could be produced, not just by
  one shader not producing one) and by measurement with a same-tree
  positive control.
- **Suggested action**: `enhancement-not-bug`. This is not a defect in
  behaviour the compiler ever intended to provide; it is a maintainer-visible
  design gap (already labelled `enhancement`) that the project has
  explicitly declined to schedule, while stating a patch would be accepted.
  Nothing needs fixing to match documented behaviour, and nothing regressed;
  what remains is a product-direction decision already on record in the
  thread, which is not this triage's job to make.
- Labels: current `enhancement` is accurate and kept. Proposing to add `api`
  ("Issues related to compiler library API") — this is precisely a
  `IDxcIntelliSense`/`IDxcCursor` library-surface question, not a shader
  compile behaviour, and no more specific existing label covers it. No
  removal proposed.
- Compiler Explorer: deliberately skipped (`godbolt --skip`, recorded). CE's
  panes show compiler diagnostic/output text; there is no artifact for a
  COM AST-walking API to produce there.

## Method notes

See `method-notes.md` for the tooling-facing observations from this issue
(kept separate from this write-up per the skill's guidance that method
observations belong in their own file, not folded into the verdict write-up).
