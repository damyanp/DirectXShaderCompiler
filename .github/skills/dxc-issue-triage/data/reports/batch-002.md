# DXC open-issue triage — batch 002

Triaged against a clean `main` **Debug** build, `1.9.0.15422`, commit `eff900d5`, with
SPIR-V codegen enabled. History checked against all 20 bisectable release binaries,
v1.4.1907 → v1.9.2607.

**No issue was edited, commented on, labelled or closed. No DXC source was changed.**

## Headline

**One issue is closable.** #3768 is fixed, and the release history pins the failure to
exactly the two releases around the original report — the first genuinely resolved issue
found across both batches. Confidence is **high**, raised from medium after measuring the
crash's per-run failure rate.

The other four all still reproduce, and none is a regression: every one fails in all 20
releases. Two findings are worth a maintainer's attention beyond the individual issues:

- **#3444's title is wrong.** It says `float2`, `float3` and `float4` work. They do not —
  all four widths fail identically. Anyone who has used the title to scope the bug has been
  working from a false premise since 2021.
- **#3444 has never worked in any shipped release**, despite a fix (#3043) and a revert. The
  fix changed the *severity* — a silent access violation became a caught error — but no
  release has ever produced a proper diagnostic.

Batch 002 was chosen to exercise paths batch 001 never touched: SPIR-V, a hang, and an issue
with a documented fix-then-revert history. All three exposed defects in the triage method
itself, described under [What batch 002 taught us](#what-batch-002-taught-us). Four of those
were bugs that produce *wrong verdicts*, which is the main risk in this exercise.

The fourth was found late, by a maintainer question rather than by the method: asking whether
#3768's `-fcgl -Vd` workaround was still needed exposed that **the crash is intermittent**
(~70% of runs) and that every probe in the history search had been a single run. That is worth
recording as a result in itself — the review gate caught something five issues of automated
triage did not.

## Summary table

| Issue | Filed | Repro | Status vs `main` | History | Suggested action |
| --- | --- | --- | --- | --- | --- |
| [#3009](https://github.com/microsoft/DirectXShaderCompiler/issues/3009) uninitialized value passed as `undef` | 2020-09 | complete | **repros** | always | keep open |
| [#3048](https://github.com/microsoft/DirectXShaderCompiler/issues/3048) derived-to-base conversion crashes | 2020-10 | complete | **repros** | always | keep open |
| [#3444](https://github.com/microsoft/DirectXShaderCompiler/issues/3444) `float` `SV_DispatchThreadID` crashes | 2021-02 | complete | **repros** | always | keep open + **fix title** |
| [#3768](https://github.com/microsoft/DirectXShaderCompiler/issues/3768) SPIR-V `printf` crash | 2021-05 | complete | **does not repro** | regressed v1.6.2104, fixed v1.6.2112 | **close-fixed** (high) |
| [#3873](https://github.com/microsoft/DirectXShaderCompiler/issues/3873) empty-struct inheritance hang | 2021-07 | complete | **repros** | always | keep open |

Repro quality was `complete` for all five — a marked contrast with batch 001, where the oldest
issues were mostly prose. Newer issues carry runnable repros.

## Per-issue findings

### #3009 — uninitialized value silently passed as `undef` (2020-09)

DXC exits 0, emits no diagnostic, and puts `i32 undef` straight into an `IMad`. FXC rejects the
same source outright with `error X4000`. Clang trunk emits the identical `undef` and is equally
silent, so the gap carries forward rather than being closed by the successor.

The `validation` label is **correctly** applied here — @damyanp noted in 2024 that the validator
should catch this, and `validation` means DXIL validation specifically. Worth recording because
batch 001 found the same label misapplied on #1306; it is not reliably wrong or reliably right.

> **A false positive in our own predicate.** The first predicate for this issue matched any
> `undef` operand of any `dx.op`. A control — the same shader with the missing assignment
> restored — *also matched*, because `loadInput`'s trailing `gsVertexAxis` operand is `undef`
> in every non-GS shader, and `bufferStore`'s unused coordinates are too. Left alone it would
> have reported clean shaders as reproducing the bug. The predicate now matches `undef` only as
> an operand of an *arithmetic* op, and the control is recorded next to it.

### #3048 — derived-to-base conversion crashes codegen (2020-10)

Asserts in a Debug build, `SIGSEGV` on Linux release builds, in all 20 releases. **Clang trunk
compiles it cleanly**, which both answers the issue's `check-in-clang` label and suggests where
to look for the fix. Changing the parameter type from the base to the derived class compiles,
isolating the conversion rather than the inheritance.

### #3444 — `float` `SV_DispatchThreadID` (2021-02) ⚠️ title is wrong

Two independent findings.

**The title is refuted.** It claims `float2`, `float3` and `float4` work. Tested individually,
all four widths fail identically, in both Debug and Release, on current `main` and on
v1.9.2607. A `uint3` control compiles cleanly. This confirms @damyanp's 2024 comment and
contradicts the title the issue has carried since 2021.

**It has never worked.** This was the batch's designated test of the history search, because
#3043 fixed it in 2021 and the fix was later reverted. The linear scan shows the defect present
in every release; what changed was severity:

| Releases | Behaviour |
| --- | --- |
| v1.4.1907 – v1.6.2104 | silent access violation (`0xC0000005`), no message |
| v1.6.2106 – v1.6.2112 | `Internal Compiler error: llvm::cast<X>() argument of incompatible type!` |
| v1.7.2207 – v1.9.2607 | `error: llvm::cast<X>() argument of incompatible type!` |

Both FXC and Clang emit a proper diagnostic naming the semantic and the required type. DXC
leaks an internal LLVM assertion instead. That makes this a well-specified gap rather than an
open design question.

### #3768 — SPIR-V `printf` crash (2021-05) ✅ fixed

The only closable issue found so far. The failure is confined to two releases:

| Release | Result |
| --- | --- |
| v1.4.1907 | *unprobeable* — that build has no SPIR-V support at all |
| v1.5.2010 | clean |
| v1.6.2104 | **`STATUS_HEAP_CORRUPTION` (`0xC0000374`)** |
| v1.6.2106 | **`STATUS_HEAP_CORRUPTION`** |
| v1.6.2112 → v1.9.2607 | clean |

`0xC0000374` is consistent with the heap corruption the reporter saw under Application
Verifier, and the window brackets the May 2021 report date.

**The crash is intermittent — 27/40 runs at v1.6.2104, 33/40 at v1.6.2106.** That was not known
when this issue was first written up, and it changes the verdict twice over. It means a
single-run probe calls a *reproducing* release clean about a quarter of the time, which during
a linear scan invents release boundaries that are not there. It also means the clean results
are quantifiable rather than merely reassuring: current builds are clean over 110 runs, 55 on
the v1.9.2607 release binary and 55 on `main` Debug, covering both `ps_6_0` as originally
reported and `cs_6_0`. Against a ~70% per-run failure rate, 55 consecutive clean runs on the
configuration that actually failed is a real result.

**Confidence raised from medium to high** on that basis. The earlier "clean runs are weak
evidence" reasoning was sound only while the per-run rate was unknown; measuring it was what
converted an absence of crashes into evidence. The residual risk is latent corruption that the
retail heap tolerates — Application Verifier detected it earlier than the retail heap did — so
a page-heap run remains the one unrun check. It needs an elevated shell, which was not
available.

**This was never a SPIR-V lowering bug, and the repro had been testing the wrong thing.** The
reporter filed it with `-fcgl -Vd` to dodge an unrelated SPIRV-Tools crash, and that workaround
was copied into our repro — silently disabling legalization and validation for the whole
history search. Two things fall out of removing it. First, the workaround is obsolete:
KhronosGroup/SPIRV-Tools#4219 was fixed by #4280, merged the day after this issue was filed.
Second, it was never suppressing this defect anyway — the reported stack is `BumpPtrAllocator`
slab teardown under `Sema::BuildOverloadedCallExpr`, in the front end, reached long before
legalization runs, and all four flag combinations crash at similar rates in the affected
releases. The repro now runs without the flags; `cmd-as-filed.txt` preserves the original.

The reporter also used `ps_6_0`, while our repro had been built from the test file's `RUN:`
line, which says `cs_6_0`. Both behave identically here, but that was luck, not method.

### #3873 — empty-struct inheritance hang (2021-07)

One defect with two faces: **Release builds hang unboundedly** (still running after 5 minutes),
while a **Debug build asserts in about 2 seconds** on the same input. Reproduces in all 20
releases. Clang trunk compiles it cleanly. Giving the empty struct a member makes the hang go
away, confirming the trigger.

## Shareable repros

All five links verified HTTP 200 with the expected panes and a "what to look for" banner.

| Issue | Link | Panes |
| --- | --- | --- |
| #3009 | https://godbolt.org/z/5bdo83bTY | FXC, DXC 1.6.2112, DXC trunk, Clang trunk |
| #3048 | https://godbolt.org/z/1o5Exs9YP | DXC 1.6.2112, DXC trunk, Clang trunk |
| #3444 | https://godbolt.org/z/d6jG8Yjrr | FXC, DXC 1.6.2112, DXC trunk, Clang trunk |
| #3768 | https://godbolt.org/z/e5KT1E6W9 | DXC 1.6.2112, DXC trunk |
| #3873 | https://godbolt.org/z/6z6j7Ma36 | DXC 1.6.2112, DXC trunk, Clang trunk |

Three repros (#3009, #3048, #3873) are published as compute-shader restatements of pixel or
vertex originals, so Clang — which cannot lower `SV_Target` — can run the same source. Each was
verified to reproduce the original symptom before being published, and each link says it is a
restatement. The local evidence keeps the stage-accurate original.

#3768's link can only confirm the fix: Compiler Explorer's oldest DXC is 1.6.2112, which is
already the release that fixed it. Said plainly on the link rather than left to mislead. It was
also regenerated late in the batch to drop the `-fcgl -Vd` the issue was filed with, so the
published link now exercises legalization and validation rather than stopping short of them.

Clang comparisons turned out to carry real signal in this batch, not just colour:

| Issue | Clang trunk |
| --- | --- |
| #3009 | same gap — identical `undef`, no diagnostic |
| #3048 | compiles cleanly — DXC-only bug |
| #3444 | correct diagnostic — DXC-only bug |
| #3873 | compiles cleanly — DXC-only bug |

## What batch 002 taught us

Batch 002 was picked to stress paths batch 001 never reached. It found four tooling defects
that produce **wrong verdicts**, and all four are now fixed and covered by the skill.

### 1. A "does not reproduce" is worthless unless the compiler actually ran the repro

#3873 targets `ps_6_7`. Every release up to v1.6.2112 "fixed" it — because SM 6.7 did not exist
yet and those compilers reject the *profile*, never reaching the code under test. Retested at
`ps_6_0`, the oldest release hangs, so it had in fact always reproduced. Left alone this would
have reported a regression that never happened.

The same trap caught #3768 differently: v1.4.1907 has no SPIR-V support at all and answers
`SPIR-V CodeGen not available`.

The runner now classifies these as `invalid-probe` rather than `no-repro`. A history search
trims unprobeable releases off the ends of its range and reports how many it skipped, instead
of silently folding them into the result.

### 2. Binary search assumes something these issues do not guarantee

Bisection assumes the symptom is monotonic. #3768 is not: clean, then broken for two releases,
then clean again. A binary search compares the endpoints, finds both clean, and concludes the
bug **never happened** — missing a real, findable window. Only a linear scan finds it.

`bisect --linear` now exists and reports transitions rather than a single boundary. It is the
right default whenever an issue has a fix-then-revert history, which is exactly what #3444 was
chosen to test.

### 3. One defect can have two signatures, and each hides the other

#3873 hangs in Release and asserts in Debug. A `timeout` predicate scores the Debug ground
truth as `no-repro`; an `internal_failure` predicate scores the Release binaries as `no-repro`.
Either alone reports this open, reproducing bug as fixed. Predicates can now be composed with
`any_of` / `all_of`.

### 4. Controls apply to predicates, not just to compilers

Batch 001 established that an error from a compiler that cannot compile the repro is not
evidence. #3009 extends it: a *predicate* needs a control too. Its first version matched
correct shaders, and only running it against a known-good input revealed that. Every text-based
predicate now records the control alongside it.

### 5. A nondeterministic bug makes single-run probes worthless

Found only because you asked us to retest #3768's `-fcgl -Vd` workaround: re-running that repro
revealed the crash is **intermittent**, firing on 27/40 runs at v1.6.2104 and 33/40 at
v1.6.2106. Every probe in the original history search was a single run.

That is a wrong-verdict bug, not a nuisance. At a ~70% hit rate, one probe calls a *reproducing*
release clean about a quarter of the time, and in a linear scan an unlucky probe is
indistinguishable from a fix — it invents release boundaries that do not exist. A live
demonstration after the fix: `--repeat 10` against v1.6.2106 needed **four attempts** before the
crash appeared.

`run --repeat N` and `bisect --repeat N` now exist, short-circuiting on the first sighting so a
reproducing release stays cheap. Repeats also work in the other direction: absence of a crash
means nothing until the per-run rate is known, and measuring it is exactly what raised #3768
from medium to high confidence.

### 6. Inherited reporter workarounds silently shrink what you test

#3768 was filed with `-fcgl -Vd` "to disable legalization, since there's a current spirv-tools
issue that would crash and confuse issues". That was reasonable in 2021 and wrong to keep: it
was copied into the repro, so legalization and validation never ran in any of the 20 release
probes.

Both halves of the workaround turned out to be stale. The upstream bug
(KhronosGroup/SPIRV-Tools#4219) was fixed by #4280, merged the *day after* the issue was filed.
And it had never been suppressing this defect anyway — the reported stack is in
`Sema::BuildOverloadedCallExpr`, in the front end, reached long before legalization; all four
flag combinations crash at similar rates.

A related miss in the same issue: the reporter used `ps_6_0`, but the repro was built from the
test file's `RUN:` line, which says `cs_6_0`. Both behave identically here, but that was luck.
The skill now says to reproduce the reporter's exact configuration first, then re-test their
workarounds separately, keeping the original as `cmd-as-filed.txt`.

### 7. Independent review keeps earning its place

The reviewing model caught real errors again, not just verbosity: "no shipped release has ever
compiled this correctly" (the input is invalid — it *should* be rejected), "only DXC fails to
say so" (DXC does emit an error, just a bad one), and a claim that FXC and Clang share "the
exact diagnostic text" when their wordings differ. All three were fixed.

On the rewritten #3768 comment it did it again across two rounds, cutting "every release"
(v1.4.1907 was unprobeable), "matches" the Application Verifier stop (different failure status,
no stack captured), a run count that was both wrong and implied an untested Release build, and
"would settle it" of the page-heap check (it would strengthen confidence, not prove absence).
It also caught that an inference had been passed off as fact — that SPIRV-Tools#4219 "has since
been resolved" was deduced from current dxc working, not checked. It named the fixing PR; that
was then verified independently before being cited.

Its judgement on what to *cut* still needed filtering — it proposed removing the `undef`
false-positive warning and the page-heap recommendation, both of which are load-bearing. It also
flagged the `0xE0000001` exit codes as noise; those stayed in evidence but came out of prose.

## Proposed label changes

Validated against the live label set (58 labels, re-fetched this run). Nothing applied.

| Issue | Now | Add | Remove |
| --- | --- | --- | --- |
| #3009 | `bug`, `validation` | `diagnostic`, `fxc-disagrees` | — |
| #3048 | `bug`, `crash`, `check-in-clang` | `type-system` | `check-in-clang` (answered: Clang is clean) |
| #3444 | `bug`, `tech-debt`, `diagnostic` | `fxc-disagrees` | — |
| #3768 | `spirv` | — | — |
| #3873 | `bug`, `crash` | `type-system` | — |

Two judgement calls left open rather than decided:

- **#3048 `check-in-clang`** — Clang compiles this cleanly, so if the label means "check whether
  Clang has this too", it is answered. If it tracks parity work, keep it.
- **#3873 `crash`** — it hangs rather than crashing in shipping builds. `crash` is the closest
  existing label; there is no hang-specific one.

`validation` on #3009 is correctly applied and should stay — noted only because the same label
was wrong on #1306 in batch 001.

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


### Draft — [#3009](https://github.com/microsoft/DirectXShaderCompiler/issues/3009) dxc silently passes uninitialized value as undef

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#3009](https://github.com/microsoft/DirectXShaderCompiler/issues/3009).

Still reproduces on `main` (1.9.0.15422, `eff900d5`), and in every release from v1.4.1907
through v1.9.2607.

Repro: https://godbolt.org/z/5bdo83bTY

```hlsl
int2x2 m;
RWStructuredBuffer<int2> output;

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
	int2 b;
	b.x = tid.x;      // b.y is never assigned
	output[0] = mul(b, m);
}
```

The uninitialized half reaches arithmetic:

```llvm
%11 = call i32 @dx.op.tertiary.i32(i32 48, i32 undef, i32 %6, i32 %10)  ; IMad(a,b,c)
```

Same source, three compilers:

| Compiler | Result |
| --- | --- |
| FXC | `error X4000: variable 'b' used without having been completely initialized` |
| DXC | exits 0, no diagnostic, `i32 undef` into `IMad` |
| Clang (trunk) | identical `undef`, also no diagnostic |

One trap worth knowing if anyone tests for this: `undef` alone is not a usable signal. Some
DXIL ops carry structurally-undef operands in correct code — `loadInput`'s trailing
`gsVertexAxis` and `bufferStore`'s unused coordinates both appear as `undef` in the output
above.

The link restates the original `vs_6_2` repro as a compute shader so all three compilers can
run the same source; the original behaves the same way, as does @pow2clk's `SV_Position`
variant.

**Labels:** `validation` looks correctly applied, given the note above that the validator
should be able to detect this. Suggest adding `diagnostic` and `fxc-disagrees`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3048](https://github.com/microsoft/DirectXShaderCompiler/issues/3048) Casting subclass to parent of three class heirarchy causes crashes

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#3048](https://github.com/microsoft/DirectXShaderCompiler/issues/3048).

Still reproduces on `main` (1.9.0.15422, `eff900d5`), and in every release from v1.4.1907
through v1.9.2607.

Repro: https://godbolt.org/z/1o5Exs9YP

```hlsl
struct A { float4 stuff; };
struct B : A { float4 gimme() { return stuff; } };
struct C : B { void dostuff() { stuff = 0; } };

float4 f(B thing1) { return thing1.gimme(); }   // passing a C here is the trigger

RWStructuredBuffer<float4> output;

[numthreads(1, 1, 1)]
void main()
{
	C thing2;
	thing2.stuff = float4(1, 2, 3, 4);
	output[0] = f(thing2);
}
```

| Compiler | Result |
| --- | --- |
| DXC `main` Debug | LLVM assert in codegen |
| DXC v1.6.2112 and trunk (Linux builds) | `SIGSEGV` |
| Clang (trunk) | compiles cleanly |

Changing `f`'s parameter from `B` to `C` compiles, which isolates the derived-to-base
conversion rather than the inheritance itself.

The link restates the original `ps_6_0` as a compute shader so Clang can run the same source;
the original crashes identically.

**Labels:** Clang compiles this cleanly, so `check-in-clang` may have been answered — removing
it is a maintainer call. Suggest adding `type-system`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3444](https://github.com/microsoft/DirectXShaderCompiler/issues/3444) [DXIL] Decorating CS float argument with SV_DispatchThreadID semantic crashes the compiler (float2, float3 and float4 works)

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#3444](https://github.com/microsoft/DirectXShaderCompiler/issues/3444).

Still reproduces on `main` (1.9.0.15422, `eff900d5`). Checked against all 20 releases from
v1.4.1907 to v1.9.2607: every one fails on this input, so despite #3043 and the later revert,
no shipped release has ever produced a proper diagnostic for it.

Repro: https://godbolt.org/z/d6jG8Yjrr

```hlsl
RWStructuredBuffer<float4> rwTexture;

[numthreads(1, 1, 1)]
void CSMain(float id : SV_DispatchThreadID)   // float, not uint
{
	rwTexture[3] = id.xxxx;
}
```

`float2`, `float3` and `float4` fail identically to `float`, so the vector forms noted in the
title are affected too. `uint3` compiles cleanly, isolating the non-integral type.

| Compiler | Result |
| --- | --- |
| FXC | `error X4555: invalid type used for 'SV_DispatchThreadID' input semantics, must be integral` |
| Clang (trunk) | `error: attribute 'SV_DispatchThreadID' only applies to a field or parameter of type 'uint/uint2/uint3'` |
| DXC | `error: cast<X>() argument of incompatible type!` |

DXC does reject the shader, but the message is a leaked internal LLVM assertion rather than an
HLSL diagnostic. FXC and Clang both name the semantic and the expected type.

The severity has softened over the years without the defect being fixed, which is worth knowing
when reading older reports: v1.4.1907–v1.6.2104 access-violated silently (`0xC0000005`), and
from v1.6.2106 onward it is caught and reported as the `cast<X>()` message above.

**Labels:** `diagnostic` and `tech-debt` both look right. Suggest adding `fxc-disagrees`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3768](https://github.com/microsoft/DirectXShaderCompiler/issues/3768) [SPIR-V] crash compiling shader using printf

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#3768](https://github.com/microsoft/DirectXShaderCompiler/issues/3768).

**This appears to be fixed.** It no longer reproduces on `main` (1.9.0.15422, `eff900d5`) or in
any release from v1.6.2112 through v1.9.2607.

Running `tools/clang/test/CodeGenSPIRV/intrinsics.printf.hlsl` against every SPIR-V-capable
release puts the failure in a narrow window:

| Release | Result |
| --- | --- |
| v1.5.2010 | compiles cleanly |
| v1.6.2104 | **crashes — `STATUS_HEAP_CORRUPTION` (`0xC0000374`)** |
| v1.6.2106 | **crashes — same** |
| v1.6.2112 → v1.9.2607 | compiles cleanly |

(v1.4.1907 can't be probed — that build has no SPIR-V codegen.) `0xC0000374` is consistent with
the corruption Application Verifier reported.

**The crash is intermittent, as you suspected.** In the affected releases it fires on 27/40 runs
at v1.6.2104 and 33/40 at v1.6.2106, so a single clean run there would not rule it out. The
v1.9.2607 release binary was clean in 55/55 runs (`ps_6_0` as originally reported, and
`cs_6_0`). A `main` Debug build was also clean in 55/55, though your local Debug build worked
too, so that configuration proves less. Output was inspected on current `main`: the DebugPrintf
import, six `OpString`s and six matching `OpExtInst` calls, as expected.

**The `-fcgl -Vd` flags are no longer needed for this test case**, and the 110 current-build runs
above omit them, so legalization and validation actually run. The SPIRV-Tools crash they were
avoiding (KhronosGroup/SPIRV-Tools#4219) was fixed by KhronosGroup/SPIRV-Tools#4280, merged the
day after you filed this. They also do not appear to have been masking anything here: at
v1.6.2104 and v1.6.2106, all four combinations (`-fcgl -Vd`, each alone, and neither) crash at
similar rates.

Current test case: https://godbolt.org/z/e5KT1E6W9 — Compiler Explorer's oldest DXC is 1.6.2112,
already past the affected window, so it can only show current behaviour.

Worth noting before closing: the Application Verifier / page-heap check was not re-run, and it
detected the corruption earlier than the retail heap did.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3873](https://github.com/microsoft/DirectXShaderCompiler/issues/3873) Infinite loop related to struct inheritance and empty struct

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#3873](https://github.com/microsoft/DirectXShaderCompiler/issues/3873).

Still reproduces on `main` (1.9.0.15422, `eff900d5`), and in every release from v1.4.1907
through v1.9.2607.

Repro: https://godbolt.org/z/6z6j7Ma36

```hlsl
struct Helper { float getColor() { return 0; } };   // empty
struct Parent { Helper helper; };
struct Child : Parent
{
	float memberVar;
	float color() { return helper.getColor(); }
};

RWStructuredBuffer<float> output;

[numthreads(1, 1, 1)]
void main()
{
	Child instance;
	output[0] = instance.color();
}
```

| Build | Result |
| --- | --- |
| Release (v1.9.2607) | no output; still running after 5 minutes |
| `main` Debug | LLVM assert in ~2 seconds, same input |
| Clang (trunk) | compiles cleanly |

Giving `Helper` a member makes it compile, which confirms the empty struct is the trigger.

The Debug assert and the Release hang may or may not share a cause; flagging only because a
Debug build fails fast here and a Release build does not fail at all, so the two configurations
look like different bugs.

The link restates the original `ps_6_0` as a compute shader so Clang can run the same source;
the original hangs identically.

**Labels:** suggest adding `type-system`. `crash` is the closest existing fit, though in a
shipping Release build this hangs rather than crashing.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

---

## Caveats

- **Debug ground truth cuts both ways.** It makes asserts fire, which is what catches #3048 and
  #3873 — but it also *hides* the #3873 hang, and it is the configuration #3768's reporter said
  does not fail. Release binaries were used wherever the reported symptom was configuration
  dependent.
- **`always-repro'd` has a floor of v1.4.1907**, and for SPIR-V issues a higher one, since that
  build has no SPIR-V. It means "present in every release we can test", not "present since the
  beginning of time".
- **#3768's clean result now rests on measurement, not just history.** The per-run failure rate
  in the affected releases (~70%) is what makes 55 consecutive clean runs meaningful. The
  page-heap test remains undone and is the only outstanding check.
- **Compiler Explorer's `dxc_trunk` is rolling and was non-deterministic in batch 001.** Nothing
  published pins an exact trunk symptom.
- **Five issues is still a small sample**, and it was deliberately biased toward crashes and
  hangs. The one-in-five closable rate should not be extrapolated.

## Suggested next step

Batch 002 stressed the method harder than batch 001 and broke it in four places, all now
fixed. Before a wider automated pass, the useful next batch would sample what these two have
avoided: issues with **no repro at all** and issues that are **not compiler-verifiable**
(runtime, driver, or GPU-execution behaviour). Those are the categories where an automated pass
is most likely to produce confident nonsense, and neither has been exercised yet.

Two items need a maintainer decision rather than more triage:

1. **#3768** — close as fixed. The page-heap run is a cheap extra check if you want it, but it
   is no longer what the verdict hangs on.
2. **#3444** — the title is actively misleading and worth correcting regardless of when the bug
   gets fixed.


