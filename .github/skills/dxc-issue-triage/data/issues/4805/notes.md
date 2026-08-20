# #4805 — Compiler does not use the custom include handler when compiling with `-Zi`

**Verdict: `changed-behavior`.** The core defect the title names is real,
confirmed at the API level, and has never worked on any build tested — but the
2022 report's actual symptom (a crash) does not reproduce as reported, and a
second, worse-shaped failure mode (introduced by a 2025 fix for a different,
related issue) now exists that the original reporter never saw.

| what | on `main-debug` (`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`) |
| --- | --- |
| custom `IDxcIncludeHandler`'s content embedded as an included file's SPIR-V `DebugSource` text | **no** — content is silently discarded; container carries no trace of it |
| the literal 2022 crash | does not reproduce; compile succeeds cleanly (`S_OK`) |
| a *different*, newly-discovered failure: same-named disk file with different content than the handler served | **fatal compile failure** — DXC's own SPIR-V validator rejects the module (regressed 2025-07-24, PR #7662) |

## Why a harness, not `dxc.exe`

The issue is entirely about `IDxcCompiler::Compile`'s `pIncludeHandler`
parameter — an interface `dxc.exe`'s command-line driver never exposes. Its
CLI always constructs its own disk-backed default handler, so no combination
of CWD/`-I` can make the substitution point under test reachable from the
command line; a purpose-built API harness is required (SKILL.md,
"harness-as-compiler", the #2918/#4619/#4256 precedent).

`handler4805.cpp` implements the simplest possible custom, **non-disk-backed**
`IDxcIncludeHandler`: it serves exactly one `#include` candidate
(`Includes/Uniforms.hlsl`) from an in-process string literal carrying a unique
marker (`HANDLER4805_MARKER_f3c9a1`), never touching disk for that filename,
and fails `LoadSource` for anything else. It calls the real
`IDxcCompiler::Compile` the reporter's application calls, and does a raw
byte-search over the resulting SPIR-V container for the marker — valid
because SPIR-V `OpString`/`DebugSource` literals are packed as contiguous
ASCII words with no compression, confirmed once via `dxc.exe -Fc` text
disassembly. Every `LoadSource` call is logged, so "the handler was never
asked" is distinguishable in the transcript from "the handler was asked,
answered, and was still ignored" — it is the latter.

Registered as the compiler `main-debug-inc4805` via `run-handler4805.cmd`
(built on demand from `handler4805.cpp`, no absolute paths, nothing binary
committed — same pattern as `run-refl4619.cmd`), so `triage.py run`,
`--shader`/`--expect` controls and `--hypothesis` all apply normally.

## An important, non-obvious correction to the initial theory

The front end was initially assumed to receive the bare `#include` spelling
(`Includes/Uniforms.hlsl`). It does not: `LoadSource` is called with a
candidate **already resolved relative to the including file's own directory**
(e.g. `.\Includes\Uniforms.hlsl` for `repro.hlsl` at the issue root). This
means DXC's front end **does** correctly implement file-relative include
resolution for a custom handler at parse time — the defect is isolated to the
**separate, later** SPIR-V debug-source re-read (`ReadSourceCode` in
`EmitVisitor.cpp`), not to `#include` resolution itself. `expected.md` records
this as a mid-investigation correction, not a silent rewrite.

## Ground truth — ways the defect actually shows, measured with 3 scenarios

The same repro shader (`#include "Includes/Uniforms.hlsl"`, a
`RWStructuredBuffer`+`cbuffer` include, `cs_6_0`,
`-fspv-debug=vulkan-with-source`) run three ways, only the on-disk state of
the resolved candidate path varying:

| scenario | disk state at the resolved path | compile | marker in container |
| --- | --- | --- | --- |
| `repro.hlsl` (**the reported case**) | nothing there | `S_OK` | **absent** |
| `control-identical/main.hlsl` | a real file, byte-identical to what the handler serves | `S_OK` | **present** |
| `control-mismatch/main.hlsl` | a real file, same name, *different* text/line-count | **fatal**: `generated SPIR-V is invalid` | n/a (compile never completes) |

`control-identical` is the load-bearing positive control (SKILL.md,
"anti-vacuity" / "a control cannot catch a broken reader"): it proves the
harness, the real `IDxcCompiler::Compile` path and the byte-search all work —
when the raw disk re-read (`ReadSourceCode`) coincidentally finds a byte-exact
copy of what the handler served, the marker naturally appears. Run through
`triage.py run --match match.json --shader control-identical/main.hlsl
--expect no-match` — passes.

`repro.hlsl` is the reported case exactly: a custom handler resolving a path
that genuinely has no on-disk counterpart. The container compiles cleanly but
carries **no trace at all** of the handler's content for that file's
`DebugSource` — confirmed via `triage.py run --match match.json` → scored
`repro`.

`control-mismatch` is a scenario the harness surfaced during this triage, not
one the reporter described: a real, differently-formatted file happens to sit
at the resolved candidate path (plausible for anyone using a custom handler
over an otherwise-normal project tree, exactly the reporter's stated use
case). `ReadSourceCode`'s raw re-read finds *that* file's text and embeds it —
but the line/column references baked into the rest of the debug-info module
were computed against the buffer the parser actually used (the handler's), so
the two disagree and DXC's own SPIR-V validator now rejects the module:

    fatal error: generated SPIR-V is invalid: NonSemantic.Shader.DebugInfo.100
    DebugTypeMember: operand Column End (41) is larger then Line 3 column
    length of 2 found in the DebugSource text

Run through `triage.py run --match match-regression.json --shader
control-mismatch/main.hlsl --expect match --hypothesis` → hypothesis
supported, scored `repro`.

## Root cause — read from source, not just inferred from behaviour

`tools/clang/lib/SPIRV/EmitVisitor.cpp`'s `ReadSourceCode(filePath, spvOptions)`
(~line 136) is the *only* place a SPIR-V `DebugSource`'s text comes from. It
does an entirely independent, freshly-initialized `IDxcLibrary::
CreateBlobFromFile` raw disk read of the resolved path — it never receives or
reuses whatever buffer the caller-supplied `IDxcIncludeHandler` already
returned to the parser. There is no code path anywhere in this file that
falls back to the handler's buffer.

* Before PR #7662 (`97b5edbc4398317a6c50437cee06393c1fd94b74`, 2025-07-24):
  on a raw-read failure, the `catch (...)` returned `spvOptions.origSource`
  (the **main file's** text) for *any* file, not just the main one — so a
  disk-read failure on an *included* file would silently substitute the main
  file's text as if it were the included file's `DebugSource`. Measured: this
  is why `control-mismatch` does **not** fail on v1.7.2207/v1.8.2502 — the
  substitution happens quietly there too, just with the wrong-but-plausible
  main-file text instead of the handler's, and nothing catches the resulting
  inconsistency.
* PR #7662 narrowed that fallback to the main file only, returning `""` for
  anything else. This is a **strict correctness improvement** for the
  "wrong file's text embedded" shape of the bug — but it changed what an
  included-file mismatch now produces: instead of a silent (if wrong)
  substitution, a `""` `DebugSource` for the include, which apparently
  interacts with the *already-baked* line/column references from the earlier,
  handler-backed parse to fail SPIR-V validation outright when the numbers
  no longer line up with whatever the raw-read step separately obtained (the
  `control-mismatch` scenario). `control-identical` and `repro.hlsl` are
  unaffected by this either way, since they never hit that inconsistency.

The try/catch itself (i.e., *some* non-crashing handling of a disk-read
failure) existed since 2020-09-22 (`7f985ff47`, #3155) — well before this
issue was filed (2022-11-20). `catch (...)` in standard, non-`/EHa` C++
catches thrown C++ exceptions (which is what DXC's `IFT()` HRESULT-failure
macro throws) but not raw Win32 structured exceptions. The reported 2022
callstack terminates mid-way through the normal `ReadBinaryFile` call chain
with no fault-specific frames, which is also exactly what a debugger's
break-on-first-chance-C++-exception setting looks like for an exception that
*is* legitimately caught one frame up — I cannot prove this is what the
reporter saw (I did not have their debugger session), but it is at least as
plausible as an actual unhandled fault, given the surrounding try/catch
already existed at the time. I could not reproduce a genuine crash on any
build tested (v1.7.2207 through `main-debug`); the second commenter's 2025
report ("ignored", no crash) is consistent with the silent/empty-content
shape measured here, not the original crash shape.

## History — a small, source-bounded matrix, not a full `bisect`

Two real, official release `dxcompiler.dll` builds were downloaded (public
GitHub release assets, extracted under this issue's `scratch/` — gitignored,
not authored evidence) and probed with the same fixed harness, `DXC_INCLUDE_DLL`
swapped between them: **v1.7.2207** (current release when the issue was
filed, 2022-07-14) and **v1.8.2502** (2025-02-21, the last release before PR
#7662). Full transcript generator and output: `measure-history.py` /
`manual-case-release-history.txt`.

* **Core defect** (`repro.hlsl`, marker absent despite `S_OK`): present on
  **both** historical releases and on `main-debug` — **always-repro'd**
  across the entire sampled history, from before the issue was filed through
  today. No `bisect` was run: `bisect` drives each release's `dxc.exe`, which
  (like current `dxc.exe`) never exposes a custom `IDxcIncludeHandler`, so it
  would have scored every release `no-repro` and confidently reported the
  inverse of the truth — exactly the `refl4619`/#4619 trap, pre-registered in
  `expected.md` and avoided here by holding the harness fixed and swapping the
  DLL instead.
* **Mismatched-content fatal validator rejection**: **absent** on both
  v1.7.2207 and v1.8.2502 (compiles cleanly there, same shape as `repro.hlsl`);
  **present only on `main-debug`**. `git merge-base --is-ancestor
  97b5edbc4398317a6c50437cee06393c1fd94b74 v1.8.2502` exits 1 (absent);
  `... 89e2f98e29c289ae8ad9e00dd310104fea9fd7df` exits 0 (present) — the
  commit (PR #7662, merged 2025-07-24, between the two sampled releases) sits
  exactly inside this boundary and its diff (narrowing the fallback condition,
  shown above) mechanically explains the change. Attribution is **strong but
  not built-at-the-commit** — I did not compile `97b5edbc4` and its parent
  directly; the two-release bracket plus the diff reading carries this,
  following the #4619 precedent for the same caveat.

This is a small, targeted matrix (2 releases, not the full 20+ used for some
other issues' history), because the code-level cause was already isolated
precisely via `git log -S`/`git show` before any binaries were downloaded, and
the two chosen releases bracket the one commit that matters. A wider sweep
would not change either conclusion.

## Compiler Explorer — explicitly skipped

Recorded via `triage.py godbolt --issue 4805 --skip "..."`. CE's `dxc` panes
compile a single pasted HLSL source through `dxc.exe`, which — like the CLI —
only ever builds its own disk-backed default include handler; there is no way
to supply a custom, non-disk-backed `IDxcIncludeHandler` through CE's
interface. A pane compiling `repro.hlsl` alone (with no way to resolve
`Includes/Uniforms.hlsl` at all) would show a plain file-not-found error,
which demonstrates nothing about whether a *supplied* handler's content is
honored — the entire question under test.

## DXIL / `-Zi -Qembed_debug` — checked, but inconclusive, left out of the verdict

`llvm-beanz`'s 2024 comment says this "doesn't seem SPIR-V specific." A quick
check was made: point the same custom-handler harness at `-Zi -Qembed_debug`
(DXIL, not `-spirv`) instead. The byte-search methodology itself failed its
own positive control here — even `control-identical`'s byte-for-byte-matching
disk file did not produce a marker hit in the DXIL container — meaning DXIL's
embedded-debug-source representation is not a contiguous ASCII run the way
SPIR-V's `OpString` is (most likely compressed or PDB-shaped). Without a
working positive control this harness cannot assert anything about the DXIL
side one way or the other, so it is **not** part of the scored verdict and is
recorded here only as an open question for a future pass with a different
instrument (e.g. reading the embedded PDB part directly rather than raw
byte-searching the container).

## Labels

Current: `bug`, `api` — both accurate; this is genuinely a defect in the
compiler library's handling of a documented API contract
(`IDxcIncludeHandler`), not an enhancement request. `debug info` (an existing
repo label) would also fit and is suggested in the draft comment, but is not
applied here (GitHub is read-only for this triage).

## What I could not measure, and what changed along the way

* **Not built at `97b5edbc4` or its parent.** See History above; attribution
  rests on the two-release bracket plus the diff, not a direct build.
* **DXIL side unmeasured** — see above; the byte-search instrument's own
  positive control failed there, so nothing is asserted about it.
* **The literal 2022 crash was never reproduced** by this harness on any
  tested build, including v1.7.2207 (contemporary with the report). The
  debugger-break explanation offered above is inference, clearly labelled as
  such, not a proven finding.
* **Chronology note on `expected.md`:** one early, since-fixed build of the
  harness was run once (to shake out a candidate-matching bug in the harness
  itself) before `expected.md` was written; it produced a plain parse error
  and no evidence about the actual defect either way. The source-code read
  that produced `expected.md`'s prediction came first and is unaffected. See
  `expected.md`'s own chronology note and `method-notes.md` item 1.
* **`reviewed_by` is recorded as pending independent batch review**, not as
  a review having occurred — this triage pass did not include step 10's
  independent model review, and the verdict schema's `reviewed_by` field is
  the only place that fact is visible later if left unclaimed.
* **Nothing was posted to GitHub.** `comment.md` is a draft. All `gh` use was
  read-only (`gh release list/view/download`, `gh issue view` via `fetch`).
