# DXC issue triage — batch 014

**Ground truth:** local Debug build `main-debug`, DXC `1.9.0.5433`,
compiler-source-identical to upstream
[`13730886e`](https://github.com/microsoft/DirectXShaderCompiler/commit/13730886e6a9019e4e0823746470f3ab75341d6b).

**Nothing was posted, edited, labelled or closed on GitHub. No DXC compiler
source was modified, and no commit or push was made.**

> [!IMPORTANT]
> **Sampling bias:** these ten reports come from the oldest open-issue sweep.
> They are deliberately enriched for long-lived behaviour, old design requests
> and issues whose original context has aged. Their closure rate and subsystem
> mix do not generalise to the full backlog.

## Headline

- Two issues are fixed with strong, independently re-derived attributions:
  **3954** in v1.8.2502 and **4168** in v1.7.2308. Both are recommended for
  closure as fixed.
- Seven issues still reproduce. **4036** is the eighth live issue, but its
  symptom changed from a source diagnostic to an internal compiler error.
- **3943 and 8527 are the same underlying file-identity defect.** The older
  3943 is the better canonical report; 8527 is the narrower case-spelling
  manifestation.
- **4168 and 4206 are not duplicates.** Reflection is only their common
  instrument: one loses type annotations during linking, while the other
  mis-attributes constant-buffer use during resource condensation.
- All ten verdicts are high confidence.

| Issue | Verdict | History | Recommendation | CE |
| --- | --- | --- | --- | --- |
| [3902](https://github.com/microsoft/DirectXShaderCompiler/issues/3902) | `repros` | all 19 stable releases with `RayQuery`, v1.5.2010–v1.9.2607 | keep open | [1bWP3sov6](https://godbolt.org/z/1bWP3sov6) |
| [3906](https://github.com/microsoft/DirectXShaderCompiler/issues/3906) | `repros` | all 20 stable releases hang; Debug `main` asserts | keep open | [M7Ex1s9b3](https://godbolt.org/z/M7Ex1s9b3) |
| [3943](https://github.com/microsoft/DirectXShaderCompiler/issues/3943) | `repros` | all 20 stable releases | keep open; consolidate 8527 here | n/a — two-file identity repro |
| [3954](https://github.com/microsoft/DirectXShaderCompiler/issues/3954) | `does-not-repro` | broken through v1.8.2407; fixed in v1.8.2502 | **close fixed** | [PT7Yqj1r6](https://godbolt.org/z/PT7Yqj1r6) |
| [4036](https://github.com/microsoft/DirectXShaderCompiler/issues/4036) | `changed-behavior` | diagnostic through v1.6.2112; ICE from v1.7.2207 | keep open | [f59x8P75v](https://godbolt.org/z/f59x8P75v) |
| [4096](https://github.com/microsoft/DirectXShaderCompiler/issues/4096) | `repros` | all 16 stable releases accepting `-HV 2021` | human/product judgement | [6Y38q1bn9](https://godbolt.org/z/6Y38q1bn9) |
| [4168](https://github.com/microsoft/DirectXShaderCompiler/issues/4168) | `does-not-repro` | broken through v1.7.2212.1; fixed in v1.7.2308 | **close fixed** | n/a — link plus reflection chain |
| [4206](https://github.com/microsoft/DirectXShaderCompiler/issues/4206) | `repros` | false negative in all 20 releases; reported false positive since v1.5.2010 | keep open | n/a — `STAT` reflection |
| [4256](https://github.com/microsoft/DirectXShaderCompiler/issues/4256) | `repros` | all four releases shipping `dxv.exe`, v1.8.2505–v1.9.2607 | enhancement, not a bug | n/a — doctored module input |
| [4273](https://github.com/microsoft/DirectXShaderCompiler/issues/4273) | `repros` | all 19 releases with the rewriter option, v1.5.2010–v1.9.2607 | enhancement, not a bug | n/a — rewriter API |

## Text that no longer matches behaviour

> [!CAUTION]
> These are the highest-value spot-check warnings in the batch.
>
> - **4036:** the body and its 2021 follow-up discuss a source diagnostic.
>   Since v1.7.2207 the same input instead terminates in
>   `llvm::cast<X>() argument of incompatible type!`, with no source location.
>   The original title's `[hlsl 2021]` qualifier is also incidental: removing
>   `-HV 2021` produces byte-identical results wherever both spellings run.
> - **4096:** the reported contextual-conversion error remains, but current DXC
>   now also rejects the conversion-operator declaration itself. A reader who
>   stops at the new first diagnostic will see different behaviour from the
>   body even though the original second diagnostic is still present.
> - **4206:** its title names only the unused field falsely marked `USED`.
>   The same offset fold also marks a genuinely read field unused, an opposite
>   and potentially more damaging failure. The title is not false, but it
>   materially under-scopes the live behaviour.

3906 is intentionally not classified as stale text: every shipped Release
binary still exhibits the reported infinite loop. The fast Debug assertion is
the same defect under a different build configuration, not evidence that the
report has stopped reproducing.

## Reindex and concurrency boundary

The orchestrator's single-writer reindex immediately before collation indexed
**76 issues / 1357 runs**. It reported exactly two expectation disagreements,
both documented hypothesis refutations rather than stale controls.

No collation reindex was run. Batch 015 workers remained live against the same
database, and `reindex` begins by deleting `issues` and `runs`. Completeness
checking therefore remained issue-scoped. No disagreement was accepted merely
to make the output quiet.

## Tooling repairs

All changes are additive and preserve the meaning of existing flags and
predicates.

### Controls and hypotheses are now distinct

`triage.py run` gained `--hypothesis`. A probe still declares its prediction
with `--expect`, but its capture now records:

```text
# expectation-kind: hypothesis
# outcome: supported|refuted
```

A contradicted control remains an error. A contradicted hypothesis is a
result, remains legible on disk, and no longer trains future readers to ignore
the reindex disagreement section. Rewriting a tested hypothesis after seeing
its answer is refused.

3902's `-Od` prediction was re-recorded correctly as **refuted**: preserving the
reported entry point and target still produces `Flags must match usage`.
4206's `variant-valver14` remains to be re-recorded with its reflection harness;
it must not be treated as an ordinary `dxc.exe` probe.

### Secondary predicates can share diagnostic quotations

An explicitly opted-in predicate may now declare
`"quote_from": ["match.json"]`. This fixes the 4036 shape where one predicate
measures the old diagnostic and a second measures the later internal failure.
Unlinked sibling predicates remain isolated.

> [!WARNING]
> **This changes scoring for the opted-in 4036 predicate.** Its v1.6.2104,
> v1.6.2106 and v1.6.2112 `match-crash.json` captures are valid
> `no-repro` measurements, not `invalid-probe`: those releases reached the
> feature and emitted the diagnostic quoted by the linked predicate. No other
> predicate inherits quotations implicitly.

### The canonical path gate is now inside the worker loop

`check_paths.py` gained `--issue` and `--path`, and `audit --issue` invokes the
same scoped implementation. Workers no longer need to grep a batch-global
failure stream or reimplement the matcher.

The old `if NUL: skip` shortcut was replaced with UTF-16 decoding plus a real
text/binary sniff. UTF-16 and mostly-text captures containing isolated NULs are
scanned; genuine generated binaries remain excluded by the existing policy.
The exact allowlist and its occurrence counts are unchanged.

Each repair has a positive regression test that fires and a negative control
that proves the rule did not simply broaden globally.

## What this batch taught us about the method

### Remove inert inherited flags; do not merely classify around them

4036 inherited `-HV 2021` from its title. Four releases rejected that flag,
creating a plausible but false version floor. A 21-build × 3-case × 2-spelling
matrix showed 51 byte-identical comparisons; the only 12 differences were the
four releases unable to parse the flag. Removing the inert flag recovered
v1.6.2104 and v1.6.2106, moving the measured start six months before filing.

`invalid-probe` prevents a false conclusion, but it still discards a datapoint.
When an inherited option is not load-bearing, removing it is strictly better.
Keep the as-filed command as provenance, then measure the option's effect.

### Verification tooling needs controls too

Three workers independently wrote false-negative self-checks while asking
whether path-gate failures belonged to their directory: one disabled regex
while supplying alternation, one copied the global failure stream into the
directory being checked, and one edited after the final gate run. All were
caught, but each had initially produced a reassuring empty result.

A clean result from an unproven query is worth nothing. Call the canonical
checker when one exists; otherwise first prove the query against fixtures that
must match and must not match. Run the gate after the final edit, not before it.

### Blind re-derivation is cheap and tests attribution rather than memory

Two separate agents were denied the workers' notes, verdicts and drafts and
received only each repro and measured release boundary:

- **3954:** within the 133-commit v1.8.2407→v1.8.2502 window, the agent screened
  16 plausible alternatives and independently selected
  [`0372fb792`](https://github.com/microsoft/DirectXShaderCompiler/commit/0372fb792).
  Its `LookupVectorMemberExprForHLSL` duplicate-swizzle condition predicts the
  measured `.r.xx` failure / `.r.x` success control.
- **4168:** within the 257-commit v1.7.2212.1→v1.7.2308 window, the agent
  independently selected
  [`bf015d2e1`](https://github.com/microsoft/DirectXShaderCompiler/commit/bf015d2e1).
  It found the annotation-copy hunks and the commit's own
  `lib_6_x`→`vs_6_5` reflection regression test, and independently counted the
  same seven production-touching commits in the window.

Both agree with the workers. They remain strong attributions rather than
commit-build bisections, but the independent search materially raises
confidence. The exercise was cheap enough that close-fixed attribution should
be re-derived, not merely reread.

### Crash predicates must describe the defect, not one release's wording

3954 is the sharpest measured example so far. One defect appears as an access
violation with empty stderr, LLVM Unreachable, an HRESULT carrying the
reporter's message, and ordinary E_FAIL text. Exit-only or literal-message
predicates invent different start and fix dates; one reports the issue fixed
four and a half years early. `internal_failure` plus its text markers is
load-bearing evidence, not stylistic preference.

### Shipped artifacts outrank tag-source ancestry

4206's v1.4.1907 executable behaves differently even though the later tag tree
already contains the suspected code. The tag tip post-dates the shipped July
binary. Source ancestry can bound a hypothesis, but it cannot overrule a
measured release artifact.

### Cross-version modules have their own version floor

4256's first validator matrix failed before testing ViewID state because
main-generated modules declared validator 1.10 while every shipped validator
supported at most 1.9. A known-good unmodified module exposed the vacuous
matrix. Portable `.ll`/DXIL must be emitted at the lowest validator version in
the range and accompanied by a positive per-release control.

## Cross-issue decisions

### 3943 and 8527 — same defect

Both converge on raw requested-path spelling being mistaken for file identity:
`TryFindOrOpen` uses `wcscmp`, while the synthetic `UniqueID` derives from the
open handle rather than a stable filesystem identity. Separator, `..` and case
aliases therefore create distinct `FileEntry` objects for the same file.
8527 is the later, narrower case/canonicalisation report. Treat it as a
duplicate or companion of 3943 rather than maintaining two root-cause tracks.

### 4168 and 4206 — distinct

4168 loses cbuffer type annotations only when a library is linked into a
shader; direct compilation is a clean control, and the issue is fixed.
4206 reproduces without linking and comes from `GetCBOffset`/`MarkCBUse`
mis-accounting a dynamic negative index. They share reflection only as an
observation surface and should not be merged.

## Independent draft review

All ten drafts were independently reviewed on `gpt-5.6-sol`, a different model
from the `claude-opus-5` draft authors. Concision was the primary criterion;
technical evidence such as diagnostics, version ranges, symbols, paths and IR
snippets was protected from cuts.

Most edits were applied verbatim. Four were applied with judgement:

- 3943 retained “`, a different rule`” because it distinguishes the failed CE
  fold from the reported identity rule.
- 3954 retained the `On "seems to only happen with Ray Tracing shaders":`
  anchor because the following sentence otherwise has no referent.
- 4256 retained that the harness *reads the module*, which makes its
  `[selftest]` line evidence rather than assertion.
- 4273 restored “compiling the rewriter's own output” because the shorter
  wording described a different input.

Two factual corrections were verified and applied:

- 3906's 20-release sweep was local; Compiler Explorer exercised two DXC
  configurations. The table now says `Release (all 20 stable releases)`.
- 4168's 257-commit window has seven commits touching the production file set:
  `bf015d2e1` and six alternatives. The old “only commit” wording was false.

## Per-issue findings

### 3902 — unused `RayQuery` leaves stale module flags

Any unused `RayQuery`, including `RayQuery<RAY_FLAG_NONE>`, is sufficient.
`CollectShaderFlagsForModule()` runs before `RemoveUnusedRayQuery()`, leaving
the tier-1.1 bit beside final IR that no longer uses RayQuery; the validator
recomputes zero and rejects the mismatch. `-Od` does not change the ordering.
Validator version 1.7 activates a compatibility shim and is a measured
workaround, not a fix.

### 3906 — SROA makes no progress

Every shipped Release build spins; Debug `main` stops quickly on an assertion.
Stepping through shows the bail-out leaves the bitcast use intact inside
`while (!V->use_empty())`, so the Release loop cannot advance. The reduced
trigger needs a struct data member plus an array-returning member function; the
reported wrapper-struct workaround remains effective.

### 3943 — `#pragma once` keys on spelling, not identity

Plain `-I` versus source-relative inclusion is enough to produce slash aliases
on Windows. `..` and case aliases fail too, even on case-insensitive NTFS.
Include guards suppress the duplicate body but still open the file twice. The
mechanism and all-release history support keeping the older issue open and
consolidating 8527 with it.

### 3954 — duplicate-element swizzle crash fixed

The bug exists from the oldest available release through v1.8.2407 and is gone
in v1.8.2502. Broken lowering leaves `.r` as an lvalue and presents
`HLMatrixSubscriptUseReplacer` with an unsupported bitcast; the fix adds the
missing lvalue-to-rvalue conversion for duplicate-element swizzles. Fixed and
workaround shaders produce byte-identical DXIL after the transition.

### 4036 — diagnostic regressed into an ICE

All releases that support the feature fail, but the failure changes at
v1.7.2207. `LowerGetResourceFromHeap` assumes a user shape and unconditionally
casts; a member call directly on the heap cast violates that assumption. The
local-variable and sampler-argument controls compile. The language acceptance
question can remain open, but an internal compiler error is not an acceptable
answer.

### 4096 — live language request with a new earlier diagnostic

The contextual conversion still does not invoke `operator bool()`. Since
v1.9.2607 DXC also diagnoses the operator declaration as unsupported, while
Clang's HLSL front end invokes it for `if (A)`. The source explains the older
behaviour; whether DXC continues tracking this now that the successor front end
has chosen a design is a product/language decision.

### 4168 — linker annotation loss fixed

Broken releases preserve cbuffer size and binding but report zero variables
after linking; the library alone and a direct shader compile both reflect two.
`bf015d2e1` copies the missing type annotation and adjusts metadata emission,
matching both reported problems. The independent source-window derivation
confirmed the attribution and the seven-commit production-touch count.

### 4206 — one offset fold, two opposite wrong flags

Folding `ProbeIndex - 1` through an unsigned offset produces an out-of-range
value. `upper_bound` then falls back to the final field, marking unused
`SkyLightColor` used while failing to mark genuinely read
`WorldPosToProbeCoord`. The false negative spans all releases; the reported
false positive begins in v1.5.2010. No commit is attributed.

### 4256 — validator trusts producer-owned ViewID state

Deleted, zeroed and deliberately false `dx.viewIdState` all validate. The
validator reads the ViewID operation and rejects unrelated malformed controls,
but never recomputes dependencies. Later PSV checking compares two
producer-derived copies and therefore does not close the gap. This is a
missing validation capability, appropriately classified as an enhancement.

### 4273 — rewriter deliberately retains explicit cbuffers

The rewriter removes unused functions and loose globals but never places
`HLSLBufferDecl` contents in its removal set. Existing regression tests
explicitly preserve both unused blocks and unused members. The behaviour is
constant from the first release with the option; changing it is an accepted
rewriter feature request, not a compiler regression.

## Timeline integrity

Read-only timeline checks found no new cross-reference events on any batch
issue. The only events were pre-existing: one on 3906 (2021), one on 3943
(2024), and three on 4096 (2023). All ten issues remained open, and none had
been updated during this triage.

## Verification

- No `reindex` or bare `audit` was run while batch 015 workers were live.
- Nine scoped evidence audits were clean. 4206 reported only the known
  `variant-valver14` expectation mismatch that awaits hypothesis re-capture.
- All ten audits still report `reviewed_by` persistence as pending because the
  final report-only instruction prohibited issue-artifact edits; the
  independent review itself was completed and applied.
- Predicate/tool regression suite: **197 checks passed**, including positive
  and negative controls for each tooling repair.
- The report path gate was run after the final render.
- Drafts were generated from each `comment.md` with
  `python scripts/render_comments.py 014`, not copied by hand.
- GitHub access remained read-only throughout.

## Proposed issue comments

These are **drafts for review, not posted**. No comment, label or state change
has been made on any issue. Each is written to be postable as-is by a maintainer, and every
claim in them is backed by captured evidence in `issues/<nnnn>/`.

They deliberately avoid promising fixes or timelines, and where the next step is a product or
language decision they say so rather than pre-empting it. Quoted compiler output was
re-verified before being written down.

Each draft ends with a trailer disclosing that it came from an assisted triage pass.

Source of each is `issues/<nnnn>/comment.md` — edit there, then re-run
`scripts/render_comments.py <batch>` to refresh this section.


### Draft — [#3902](https://github.com/microsoft/DirectXShaderCompiler/issues/3902) error: Flags must match usage.

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3902](https://github.com/microsoft/DirectXShaderCompiler/issues/3902).

Still reproduces on `main` (1.9.0.5433, 13730886e). An unused `RayQuery` local is enough on its
own — no acceleration structure, no `TraceRayInline`:

```
$ dxc -T cs_6_5 -E computeRTAO repro.hlsl
error: validation errors
error: Flags must match usage.
note: Flags declared=33554432, actual=0
Validation failed.
```

Same result with the `/O3 /Ges /WX /all_resources_bound` command line as filed at `cs_6_6`, and
with both `ps_6_6` shaders from the later comments.

https://godbolt.org/z/1bWP3sov6 — 1.6.2112 and trunk both fail; the third pane is the same source
with the `RayQuery` uses restored, and compiles.

Every stable release that has `RayQuery` at all behaves this way: v1.5.2010 through v1.9.2607, 19
releases, no exceptions. v1.4.1907 predates both `RayQuery` and SM 6.5, so there is no release
without this.

Three additional findings:

- **The template ray flags are irrelevant.** An unused `RayQuery<RAY_FLAG_NONE>` fails identically.
  `33554432` is the raw shader-flag bit for raytracing tier 1.1, not an encoding of the ray flags.
- **`-Od` does not help**, so "the optimizer removes it" is not the whole story.
  `DxilFinalizeModule` calls `CollectShaderFlagsForModule()`
  ([DxilPreparePasses.cpp:1001](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/lib/HLSL/DxilPreparePasses.cpp#L1001))
  *before* `RemoveUnusedRayQuery()` (line 1012), at every optimization level; the validator then
  recomputes from the final IR
  ([DxilValidation.cpp:4881](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/lib/DxilValidation/DxilValidation.cpp#L4881))
  and gets 0. With `-Vd` the module shows both halves at once — `define void @computeRTAO() { ret
  void }` next to `!5 = !{i32 0, i64 33554432, ...}`.
- **`-validator-version 1.7` compiles cleanly.** `ValidateShaderFlags` carries a compatibility
  shim for validator versions ≥1.5 and <1.8 that suppresses exactly this mismatch. It is a
  workaround for anyone blocked today, at the cost of pinning to an older validator.

Suggested label: `validation`, since DXC emits a module whose declared feature flags its own
validator rejects.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
````

### Draft — [#3906](https://github.com/microsoft/DirectXShaderCompiler/issues/3906) Compiler infinite loop issue

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3906](https://github.com/microsoft/DirectXShaderCompiler/issues/3906).

Still reproduces. The shader in the report fails to compile on `main` (1.9.0.5433, `13730886e`)
and on **all 20 stable releases from v1.4.1907 to v1.9.2607** — it has never worked.

Live repro: **https://godbolt.org/z/M7Ex1s9b3** (the `shader-playground` link in the report no
longer resolves). Both DXC panes answer `Killed - processing time exceeded`. Locally, v1.9.2607
was still running after 600 s, at 100% CPU throughout — a spin, not a wait.

### One defect, two signatures

| build | `dxc -T cs_6_0 -E main` |
|---|---|
| Release (all 20 stable releases) | never terminates |
| Debug (`main`) | `0xE0000001`, `Internal compiler error: LLVM Assert`, ~1 s |

Under a debugger the Debug build stops in `SROA_Helper::RewriteBitCast`, and continuing past
that assert — which is what a Release build does, since the assert is not compiled in — reaches
a second one whose message names the reported symptom:

```
assert(0 && "Type mismatch.")           lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp(2662)
!(&TheUse != PrevUse)                   lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp(2996)
    Infinite loop while SROA'ing value, use isn't getting eliminated.
```

The bail-out at 2661-2663 returns without erasing the bitcast or nulling the use, breaking the
contract stated at 2999-3000 (*"Each of these must either call `->eraseFromParent()` or null out
the use of V so that we make progress"*), so `while (!V->use_empty())` at 2991 never advances.
Both guards are `NDEBUG`-only, so Release just spins. That bail-out dates to `6ee4074a4`, the
first commit in the repository, which matches the release scan.

### Reduced repro

No `ByteAddressBuffer`, no `register`, no `readIndex()`:

```hlsl
struct RenderResourceHandle { uint handle; };

struct Test {
    RenderResourceHandle h;
    float3 infLoop()[2] {
        uint i = this.h.handle;
        float3 v[2] = { 0.xxx, 0.xxx };
        return v;
    }
};

[numthreads(8, 8, 1)] void main() {
    Test t;
    t.h.handle = 0;
    float3 w[2] = t.infLoop();
}
```

Two variants measured on v1.6.2106, v1.9.2607, and `main`:

- Removing the struct member entirely (member function returning an array, but no data member)
  compiles cleanly — as does lifting the function out of the struct.
- Replacing `RenderResourceHandle h;` with `uint h;` gives a **different** failure, not a hang:
  `llvm::cast<X>() argument of incompatible type!`, from the neighbouring exit at
  `ScalarReplAggregatesHLSL.cpp(2630)`. Worth covering in the same fix's tests.

The workaround in the report (wrap the values in a struct and return the struct) still works —
`repro.hlsl` with only that change compiles on `main`, v1.6.2106 and v1.9.2607. The new
Clang-based HLSL front end (`hlsl_clang_trunk` on the link above) compiles all of these without
incident.

**Labels:** no change suggested — `bug` and `crash` already fit, and `crash` covers "hitting an
assert".

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3943](https://github.com/microsoft/DirectXShaderCompiler/issues/3943) #pragma once cannot support path aliases

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3943](https://github.com/microsoft/DirectXShaderCompiler/issues/3943).

Still reproduces on `main` (1.9.0.5433, `13730886e`), and on **all 20 stable releases** from
v1.4.1907 through v1.9.2607 — every release run individually, not just the endpoints. The
v1.4.1907 diagnostic is byte-identical to today's.

`inc/common.h` is `#pragma once` plus `float CommonValue() { return 1.0f; }`:

```hlsl
// repro.hlsl
#include "inc/common.h"   // relative to this file
#include "common.h"       // same file, via -I inc

float4 main() : SV_Target { return CommonValue(); }
```

```
> dxc -T ps_6_0 -E main -I inc repro.hlsl
In file included from repro.hlsl:10:
./inc\common.h:5:7: error: redefinition of 'CommonValue'
./inc/common.h:5:7: note: previous definition is here
```

The two paths differ only in the separator. On Windows that is DXC's own doing:
`DirectoryLookup::LookupFile` builds an `-I` candidate with `llvm::sys::path::append`
(`HeaderSearch.cpp:293-297`), which emits `\`, while a source-relative include keeps the
separator from the `#include` text. So no unusual spelling is needed to hit this — plain
`-I` versus local is enough.

**The comparison is on path strings, not file identity.** Three checks:

* Spelling the first include `"inc\common.h"` — a one-character change — compiles clean. Once
  both spellings normalise to the same string, `#pragma once` works.
* `"inc/../inc/common.h"` reproduces (the body's `Root/../MyFile.h` shape).
* `"inc/COMMON.h"` reproduces **on NTFS**, which is case-insensitive — both `#include`s read
  the same bytes and the compiler still calls them two files. That confirms the 2024-02-20
  comment about case sensitivity, and it is the clearest evidence the check never reaches the
  filesystem.

`#ifndef` guards are unaffected, as the RTX PT SDK workaround linked above assumes — but they
suppress the second inclusion's *contents*, not the second open. `-H` on a guarded twin of the
repro:

```
; Opening file [./inc/guarded.h], stack top [0]
; Opening file [./inc\guarded.h], stack top [1]
```

Mechanism: `#pragma once` is keyed on `FileEntry`
(`Pragma.cpp:356-364`), and `FileManager` uniques `FileEntry` by `UniqueID`
(`FileManager.cpp:275`) — upstream clang's inode-based uniquing, which is why this works for
C++. But `DxcArgsFileSystemImpl::GetFileInformationByHandle`
(`dxcfilesystem.cpp:468-474`) zeroes the info struct and sets
`nFileIndexLow = (DWORD)(uintptr_t)hFile`, so the "unique ID" is the handle; a handle is
reused only when `TryFindOrOpen` matches the requested path with `wcscmp`
(`dxcfilesystem.cpp:256-260`). `NormalizePathW` (`Support/Path.h:101-127`) swaps slash
direction but does not collapse `..` or case-fold. Every distinct spelling therefore gets its
own `FileEntry`.

Worth flagging for the include-handler design mentioned in the 2024-10-02 comment: matching
clang here means a notion of file identity independent of the requested path, which a custom
`IDxcIncludeHandler` serving virtual sources may not be able to supply. That is the part that
needs deciding.

Not reproducible on Compiler Explorer: it is single-file; its path is masked as `<source>`,
`#include "<source>"` cannot be resolved, and DXC warns `#pragma once in main file`, a
different rule.

Label suggestion: keep `bug`, add `usability` — the failure mode is a confusing redefinition
error rather than bad codegen, and the workaround has already propagated into shipping SDKs.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3954](https://github.com/microsoft/DirectXShaderCompiler/issues/3954) AnyHit Shader hits `llvm_unreachable("Unexpected matrix subscript use.")` 

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3954](https://github.com/microsoft/DirectXShaderCompiler/issues/3954).

This no longer reproduces. The shader from the report compiles cleanly on `main`
(1.9.0.5433, [`13730886e`](https://github.com/microsoft/DirectXShaderCompiler/commit/13730886e)),
using the oldest profile that can express `[shader("anyhit")]`:

```
dxc -T lib_6_3 repro.hlsl
```

I checked every stable release that ships a `dxc` binary — 20 of them. It failed on every one
from v1.4.1907 (2019) through v1.8.2407, and passes from **v1.8.2502** onward — a single clean
transition:

| | |
| --- | --- |
| v1.8.2407 | `error: Unexpected matrix subscript use.`<br>`UNREACHABLE executed at C:\__w\1\s\DXC\lib\HLSL\HLMatrixSubscriptUseReplacer.cpp:93!` |
| v1.8.2502 | compiles, exit 0 |

Your quoted output matches v1.6.2106 and v1.6.2112 exactly, line 91 included, which fits the
September 2021 filing date.

The same defect reports itself four ways depending on release. v1.4.1907 and v1.5.2010 die
with an access violation and **completely empty stderr**; v1.6.2104 says only `Internal
compiler error: LLVM Unreachable`; v1.6.2106/v1.6.2112 print the message you quoted; v1.7.2207
through v1.8.2407 print it as an `error:` and exit with E_FAIL. Searching for the message text
alone would place the start of this bug in 2021 rather than at or before 2019.

**Cause and fix.** `HLMatrixSubscriptUseReplacer::replaceUses` handles only loads and stores of
a matrix-subscript pointer. Before the fix, `Param.Matrix[2].r.xxx` left `.r` as an lvalue, so
codegen emitted `bitcast float* %5 to <1 x float>*` on that pointer — neither a load nor a
store, so the pass hit the `llvm_unreachable`. Afterwards the front end loads the whole
`<3 x float>` and `extractelement`s from it, and the pass never sees the shape.

That points at [`0372fb792`](https://github.com/microsoft/DirectXShaderCompiler/commit/0372fb792)
("Fix assertion on splat of groupshared scalar", #6930), which adds the missing
`CK_LValueToRValue` in `LookupVectorMemberExprForHLSL` when a swizzle has duplicate elements. It
is in v1.8.2502 and not in v1.8.2407, and the duplicate-element condition matches the observed
behaviour on the last broken release: `Param.Matrix[2].r.x` compiles there, `Param.Matrix[2].r.xx`
crashes. I did not build at that commit, though, and there are 133 commits between the two tags,
so treat this as a strong attribution rather than a bisected result.

**The generated code is correct, not just non-crashing.** On both v1.8.2502 and `main`, the
original shader and your `Param.Matrix[2].xxx` workaround produce byte-identical DXIL — one
`cbufferLoadLegacy`, `extractvalue ..., 2` for the column-major `M[2][0]`, three `fmul`s. The
workaround is no longer needed.

On "seems to only happen with Ray Tracing shaders": the identical subscript in a `cs_6_0`
shader failed the same way on v1.4.1907, v1.6.2106, and v1.8.2407, so the trigger appears to be
the swizzle rather than the shader stage, consistent with the fix landing in Sema.

Side-by-side on Compiler Explorer (v1.6.2112 vs trunk): <https://godbolt.org/z/PT7Yqj1r6>. Note
that CE's Linux builds report the old-compiler failure as a bare `SIGSEGV` with no message; the
text above is from the Windows release binaries.

Suggest closing as fixed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4036](https://github.com/microsoft/DirectXShaderCompiler/issues/4036) Odd compiliation error with ResourceDescriptorHeap and type deduction

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4036](https://github.com/microsoft/DirectXShaderCompiler/issues/4036).

Still broken on `main` (1.9.0.5433, 13730886e) — but not in the way it was
reported. The compile error in the original post is gone; since **v1.7.2207** this
input crashes the compiler instead.

```
$ dxc -T ps_6_6 -E PSMain repro.hlsl
Internal Compiler error: llvm::cast<X>() argument of incompatible type!
[exit] 0x80AA001D
```

No source diagnostic or file/line/column; compilation dies in code generation.

**Compiler Explorer, the two states side by side:** https://godbolt.org/z/f59x8P75v
(1.6.2112 gives the reported diagnostic; trunk gives the internal error.)

### Where it fails

```
dxcompiler!llvm::llvm_cast_assert_internal
dxcompiler!llvm::cast<llvm::LoadInst,llvm::User>
dxcompiler!`anonymous namespace'::LowerGetResourceFromHeap
dxcompiler!CGHLSLMSHelper::FinishIntrinsics
dxcompiler!`anonymous namespace'::CGMSHLSLRuntime::FinishCodeGen
```

`LowerGetResourceFromHeap` in `tools/clang/lib/CodeGen/CGHLSLMSFinishCodeGen.cpp`
walks the users of the heap-subscript result assuming each is a `BitCastInst`
whose users are `LoadInst`s, and casts unconditionally. A member call on the cast
expression produces a different user, and the `cast<>` throws. That function is
byte-identical between v1.6.2112 and v1.7.2207, so what changed in that window is
upstream of code generation: the construct started reaching a lowering that was
never written to handle it.

### Scope

Only the member call directly on the cast is affected. Both of these compile
cleanly on `main`:

```hlsl
StructuredBuffer<float> buf = (StructuredBuffer<float>)ResourceDescriptorHeap[i];
return buf.Load(0);                                     // cast, then call
```
```hlsl
tex.Sample((SamplerState)SamplerDescriptorHeap[0], uv); // cast as an argument
```

So does the workaround suggested in the 2021-11-08 comment (assign the subscript to
a local and drop the cast). The construct itself appears in three tests, but all
three are `-ast-dump` or `-verify` and stop before code generation, which is why
nothing caught this.

The `[hlsl 2021]` in the original title looks incidental: output is byte-identical
with and without `-HV 2021` on every release that accepts the flag, and the
diagnostic reproduces on v1.6.2104 (2021-04), six months before the report.

### History

| | |
|---|---|
| v1.6.2104 – v1.6.2112 | reported diagnostic, `0x80004005` |
| v1.7.2207 – v1.9.2607, `main` | internal compiler error, `0x80AA001D` |

18 stable releases, every one that supports Shader Model 6.6 — for as long as it is
possible to check. v1.4.1907 and v1.5.2010 predate the feature and reject
`ps_6_6` outright, so they cannot answer. (Prereleases were not probed.)

### Suggested labels

`bug`, `crash` — currently unlabelled, and an unhandled internal cast failure is a
crash however the language question is eventually settled. Whether this spelling
should compile is a language decision this triage does not make; either way, an
internal compiler error is not an acceptable answer to it.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4096](https://github.com/microsoft/DirectXShaderCompiler/issues/4096) `bool` cast operator doesn't implicitly trigger

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4096](https://github.com/microsoft/DirectXShaderCompiler/issues/4096).

Still reproduces on `main` (`13730886e`, `dxc 1.9.0.5433`), and the diagnosis in the thread is
still accurate — but the failure has changed shape, and Clang has since answered the question.

**Current DXC.** `dxc -T cs_6_0 -E main -HV 2021` on the shader from the description:

```
repro.hlsl:3:3: error: conversion operator overloading is not allowed
  operator bool() {
  ^
repro.hlsl:11:7: error: value of type 'Foo' is not contextually convertible to 'bool'
  if (A)
      ^
```

The second error is the reported symptom. The first is new: PR #8206 (`b13e386be`, 2026-04-14)
added `err_hlsl_unsupported_conversion_operator`, so the declaration itself is now rejected.
That is the only commit touching `SemaDeclCXX.cpp` between v1.9.2602.24 and v1.9.2607. The
construct now fails earlier; it does not work.

**History.** Linear sweep of 20 stable releases: the symptom is present in all 16 that can
compile the input, v1.6.2112 (2021-12-08) through v1.9.2607. The four older ones answer
`Unknown HLSL version: 2021` and never ran it — confirmed with a minimal `-HV 2021` shader
that they also reject. v1.6.2112 shipped 16 days after this report, so no stable release
covers the build it was filed against.

The operator body has never run. Making the two candidate conversions disagree — `operator
bool() { return x > 5; }` with `x == 1`, storing 222 if the operator runs and 111 if it does
not — all 15 releases from v1.6.2112 to v1.9.2602.24 emit `i32 111` for `(bool)A`: the
flat conversion, not the operator.

**The 2023-02-08 comment is still correct.** `SemaOverload.cpp` line 1136 at `13730886e` is
`if (SuppressUserConversions || S.getLangOpts().HLSL)` in `TryUserDefinedConversion`, so no
user-defined conversion is ever considered, which is why the diagnostic is the generic "not
contextually convertible".

**Clang already does this.** [Compiler Explorer](https://godbolt.org/z/6Y38q1bn9): both DXC
panes fail, `hlsl_clang_trunk` compiles the shader. With an observable attached to the same
`if (A)`, Clang emits `bufferStore(..., i32 222, ...)` — it invokes `operator bool()` in the
condition. Controls compiling the same shader without the operator, and the buffer store on
its own, both succeed, so the acceptance is about the conversion rather than the stage or the
resource. (For an explicit `(bool)A` cast Clang currently does the same flat conversion the
older DXC releases do; that is a different expression from the one reported here.)

**Suggested labels:** add `type-system` and `enhancement`, keep `hlsl-next`. It has never
worked in any release that can express it, and the enabling change is a language-version
feature rather than a regression.

**The design position may already be on record.** This is milestoned HLSL 202x. In
[`microsoft/hlsl-specs` PR #37](https://github.com/microsoft/hlsl-specs/pull/37#discussion_r1158553249),
llvm-beanz said operator additions may depend on planned 202x overload-resolution work. That
comment concerned built-in operators rather than this conversion specifically, so it may or may
not apply here.

Whether DXC keeps tracking this — now that the declaration is a hard error and the successor
front end implements the behaviour — is a product and language decision, not something this
triage should pre-empt.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4168](https://github.com/microsoft/DirectXShaderCompiler/issues/4168) Can't get cbuffer's variables from a linked shader

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4168](https://github.com/microsoft/DirectXShaderCompiler/issues/4168).

This no longer reproduces on `main` (1.9.0.5433, `13730886e`), and it was fixed in
**v1.7.2308**.

Using the configuration from your 2022-01-23 comment — a library compiled `-T lib_6_x`, linked
to `ps_6_0`, then reflected:

```
dxc -T lib_6_x -Fo lib.dxo repro.hlsl
dxl -T ps_6_0 -E main -Fo linked.dxo lib.dxo
dxa -dumpreflection linked.dxo
```

On `main` the linked shader's cbuffer reflects both of its members:

```
  D3D12_SHADER_BUFFER_DESC: Name: CB0
        Type: D3D_CT_CBUFFER
        Size: 80
        uFlags: 0
        Num Variables: 2
```

On v1.6.2112 — the release current when you filed — the same three commands give
`Num Variables: 0`, with the cbuffer still bound and still sized `80`. So the report was
accurate.

Running the same chain across every stable release, with each release producing the container
and a fixed `dxa` reading it:

| | |
| --- | --- |
| v1.6.2106 – v1.7.2212.1 | `Num Variables: 0` |
| v1.7.2308 – v1.9.2607 | `Num Variables: 2` |

(v1.4.1907, v1.5.2010 and v1.6.2104 predate `-link` in `dxc.exe`, so they cannot run the
configuration at all. On every release, the same source compiled straight to `ps_6_0` with no
library and no link reflects both variables — that control is what makes the rows above a
statement about linking rather than about the reader.)

At v1.6.2112, the `lib_6_x` container alone reflects both variables correctly; only the linked
output loses them, localizing the loss to linking.

The fix looks like `bf015d2e1` ("Fix loss of buffer type info with libraries and linker",
#5197, 2023-05-10), which lands inside the v1.7.2212.1 → v1.7.2308 window. It adds the
`CopyTypeAnnotation(res->GetHLSLType(), …)` in `DxilLinkJob::AddGlobals` that your Problem 1
proposed, changes the SM 6.6 gating in `DxilMDHelper::EmitDxilResourceBase` for Problem 2, and
adds `preserve_cb_types.hlsl` / `preserve_sb_types.hlsl` covering this shape. That window holds
257 commits, so this is attribution by release boundary plus source content, not a build
bisect; six other commits touch the same file set, but none introduces the annotation copy.

Worth noting for coverage: `preserve_cb_types.hlsl` tests `vs_6_5`/`vs_6_6`/`vs_6_7`, not your
`ps_6_0`. `ps_6_0` measures clean on every release from v1.7.2308 onward, so it works; it just
has no regression test of its own.

Suggested action: close as fixed in v1.7.2308. Existing labels (`bug`, `reflection`,
`shader-linking`) are all correct; no change proposed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4206](https://github.com/microsoft/DirectXShaderCompiler/issues/4206) Incorrect 'D3D_SVF_USED' flag with fields in $Globals_cbuffer

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#4206](https://github.com/microsoft/DirectXShaderCompiler/issues/4206).

Still reproduces on `main` (1.9.0.5433, `13730886e`), and the reflection dump is wrong in
**two** ways for this shader, not one.

Compiling the shader from the report as `-T cs_6_0 -E ResampleCS` and reading the container's
reflection back with `dxa -dumpreflection`:

| `$Globals` variable | offset | read by the shader? | reported `uFlags` | |
| --- | --- | --- | --- | --- |
| `WorldPosToProbeCoord[6]` | 0 | **yes** | `0` | wrong — reported unused |
| `ProbeCoordToWorldPos[6]` | 96 | yes | `(D3D_SVF_USED)` | correct |
| `SkyLightColor` | 192 | **no** | `(D3D_SVF_USED)` | wrong — the reported symptom |

`WorldPosToProbeCoord` is also an unreported false negative: a caller could skip uploading a
constant the shader reads.

Changing exactly one character sequence in the shader, `ProbeIndex - 1` → `ProbeIndex` in

```hlsl
uint3 SourceProbeCoord = WorldPosToProbeCoordIndex(ProbePos + 0.5f, ProbeIndex - 1);
```

makes all three flags correct (`USED`, `USED`, `0`), with the `$Globals` layout unchanged. The
negative index is the trigger, exactly as reported.

**Root cause** — the analysis in the report holds up. `GetCBOffset`
(`lib/HLSL/DxilCondenseResources.cpp`) returns `unsigned` and folds `add i32 %ProbeIndex, -1`
to `0 + 0xFFFFFFFF`, which the caller shifts to `0xFFFFFFF0`. `MarkCBUse` then does
`upper_bound(offset)`, which returns `end()` for an offset past every field, and `it--`, so it
lands unconditionally on the last field. The same fold is why the intended field at offset 0
is never marked: one mis-folded offset, two wrong answers in opposite directions. A fix that
only stops marking the last field would still leave a genuinely-read field reported unused.

**History** — measured across all 20 stable releases, v1.4.1907 through v1.9.2607, holding the
reflection reader fixed and also re-checking with each release's own `dxcompiler.dll` (both
agree on every release):

- `WorldPosToProbeCoord` reported unused: **every release**, including v1.4.1907.
- `SkyLightColor` reported used: absent on v1.4.1907, present on v1.5.2010 and on all 18
  releases since. Below validator version 1.5 reflection recomputes usage with a range test
  instead of reading the metadata bit, and a range test cannot mis-attribute an out-of-range
  offset. No specific commit is named — compiling with `-validator-version 1.4` on `main`
  today does *not* restore the old behaviour, so the difference is not just that gate.

Not reproducible on Compiler Explorer: the flag lives in the container's reflection (`STAT`),
and the `-Fc` disassembly CE shows does not carry it.

Suggest keeping this open. Four years on it is unfixed, still reproduces, and the second face
above means the impact is wider than the title suggests.

**Labels:** keep `reflection`; suggest adding `bug` and `correctness`.

<sub>Compiler was built from `main` at `13730886e`.</sub>

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4256](https://github.com/microsoft/DirectXShaderCompiler/issues/4256) DXIL validation should run ComputeViewIdState pass

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4256](https://github.com/microsoft/DirectXShaderCompiler/issues/4256).

Still accurate. The validator does not recompute the ViewID state, on `main`
(1.9.0.5433, 13730886e) or on any shipped `dxv.exe` back to v1.8.2505.

`createComputeViewIdStatePass()` has three call sites — `PassManagerBuilder.cpp:391`
and `:709` (the compile pipeline) and `DxilLinker.cpp:1293`. None is in
`lib/DxilValidation/`, so validation has nothing to compare the serialized state
against.

Measured with `dxv.exe` over hand-edited modules built from one `vs_6_1` shader that
reads `SV_ViewID`. DXC computes `[8, 8, 15, 1, 2, 4, 8, 16, 32, 64, 128]` for it —
outputs 0-3 depend on ViewID, input *i* feeds output *i*. Deleting `!dx.viewIdState`
entirely, zeroing the dependency words, and replacing them with a deliberately false
mapping all pass. False mapping (the `[selftest]` lines are printed by the harness
that reads the module, before `dxv` runs):

```
[module] wrongdeps.ll (5990 bytes)
[selftest] module-calls-viewid-op=yes
[selftest] module-viewid-state=[8, 8, 240, 128, 64, 32, 16, 8, 4, 2, 1]
[selftest] module-viewid-state-declares-dependencies=yes
$ dxv.exe wrongdeps.ll
--- stdout ---
Validation succeeded.
[exit] 0x00000000
```

The same modules with an out-of-range `storeOutput` signature id, or with the shader
model lowered to 6.0, are rejected on every one of those validators — including
`error: Opcode ViewID not valid in shader model vs_6_0` quoting the `dx.op.viewID`
call. The validator reads the op; it just never checks it against the state.

**What has changed since 2022**, and why it does not close this: #6859 added
`PSVContentVerifier::VerifyViewIDDependence`, which does compare ViewID state during
validation. But it compares the PSV0 part with `DM.GetSerializedViewIdState()`
(`DxilContainerValidation.cpp:222`) — two copies of the same unvalidated metadata,
both derived from what the producer wrote — and returns early when the module state
is empty and the PSV state is all zero (`:225-229`). A producer that omits the node
gets both sides empty/zero and passes. What *is* recomputed is the `UsesViewID`
shader flag (`:504`), not the dependency data.

Suggested labels: **enhancement** (the ask is for validation the validator has never
performed) and **validation**. Whether the validator should own this is a product
decision — the pass exists and is already run during compilation and linking, so the
question is cost and where in `ValidateDxilModule` it belongs, not feasibility.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4273](https://github.com/microsoft/DirectXShaderCompiler/issues/4273) How to remove unused cbuffer?

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4273](https://github.com/microsoft/DirectXShaderCompiler/issues/4273).

**Still current on `main`** (`1.9.0.5433`, `13730886e`): `-remove-unused-globals`
does not remove an explicit `cbuffer` block, so this remains an open feature
request exactly as @tex3d framed it in 2022 — not a bug, and nothing has drifted
since.

Reproducing needs `dxr.exe`, not `dxc.exe`: `dxc` rejects these options outright
(`Unknown argument: '-remove-unused-globals'`), even though `dxc --help` prints a
`Rewriter Options:` section listing them. `dxr` forwards its argv straight to
`IDxcRewriter2::RewriteWithOptions`, the API in the report.

```hlsl
cbuffer cbA
{
  float4 gA;
};

cbuffer cbB
{
  float4 gB;
};

float4 gLooseUnused;
float4 gLooseUsed;

float4 vsMain(float4 pos : POSITION) : SV_Position
{
  return pos * gA + gLooseUsed;
}

float4 psMain() : SV_Target
{
  return gB;
}
```

```
dxr -E vsMain -remove-unused-globals -remove-unused-functions -extract-entry-uniforms repro.hlsl
```

```
cbuffer cbA {
  const float4 gA;
}
;
cbuffer cbB {
  const float4 gB;
}
;
const float4 gLooseUsed;
float4 vsMain(float4 pos : POSITION) : SV_Position {
  return pos * gA + gLooseUsed;
}
```

`psMain` removed, loose `gLooseUnused` removed, `cbB` — reachable only from the
removed entry point — kept. An unused member *inside* an otherwise-used block is
also kept, so the carve-out is "explicit `cbuffer` contents are never removal
candidates", not just "whole blocks survive".

**History: constant.** Driving each release's own `dxcompiler.dll` through a fixed
`dxr.exe`, the behaviour is identical from v1.5.2010 through v1.9.2607 and `main`
(19 releases). v1.4.1907 can't express the repro at all — its option table has no
`RewriteOption`/`remove-unused-globals`, and `-unchanged` already fails there with
`0x80070057` while a bare rewrite succeeds. So there's no regression here, and
nothing to bisect. That matches the code: in `dxcrewriteunused.cpp`, top-level
`VarDecl`s go into `unusedGlobals` (the set removal consumes) while `HLSLBufferDecl`s
go into a separate `cbufferDecls` list that is only traversed *"to save types for
cbuffer constant"* — they're never removal candidates.

**Implementation note:**
`tools/clang/test/HLSLFileCheck/rewriter/remove-unused-globals.hlsl` has asserted
the current behaviour since 2020 (`a408139da`) —

```
// Unused cbuffers are not removed at this time
// CHECK: cbuffer UnusedCBuffer
```

— plus a `// CHECK: float UnusedFloat;` for the unused-member case. Both `CHECK`s
have to flip, so the test will fail *because* the fix works.

On the measured DXC/SM6 path, the retained block does not consume a slot: compiling the
rewriter's own output for `vs_6_0` binds only `$Globals` at `cb0` and `cbA` at `cb1`,
reflection reports `ConstantBuffers: 2`, and `cbB` is dropped. DX11/SM5.x uses FXC and was not
tested; the source-cleanliness request @tex3d accepted still stands.

Labels look right as-is (`enhancement` + `rewriter`); no change suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

---

## Caveats

- The 3954 and 4168 commits are strong, independently re-derived attributions,
  not commit-build bisections.
- 4206's validator-version hypothesis capture still needs to be re-recorded
  with the reflection harness under the new hypothesis metadata.
- The rendered 4206 draft omits its fork-local build identifier under the
  report's public-citation rule; no technical claim was changed.
- Stable release history excludes prereleases except where an issue explicitly
  named one and policy opted it in. 3902's named v1.5.2003 check is reported
  separately from the stable range.
- Compiler Explorer cannot represent the multi-file, linker, reflection,
  doctored-module or rewriter surfaces for 3943, 4168, 4206, 4256 and 4273.
