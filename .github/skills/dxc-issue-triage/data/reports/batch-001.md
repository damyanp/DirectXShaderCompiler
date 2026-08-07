# DXC open-issue triage — batch 001

**Scope:** the 5 oldest open issues in `microsoft/DirectXShaderCompiler`, oldest first.
**Ground truth:** clean `main` **Debug** build, commit `eff900d5` (`1.9.0.15422 (main, eff900d54)`).
**History:** official release binaries, 20 bisectable releases, v1.4.1907 (2019-07) → v1.9.2607 (2026-07).
**Runs:** 33 local compiler invocations across 3 builds, all captured on disk.
**Shareable repros:** five annotated Compiler Explorer links, each verified before publishing.

> Report only. No issues were edited, labelled, commented on or closed, and no DXC source was
> changed.

---

## Headline

**All five still reproduce. None are stale. Nothing here can be closed as fixed.**

That is a notable result in itself — these are the five oldest open issues in the repo, aged
7–9 years, and every one of them still describes live behaviour.

Two of the five, however, have **misleading issue text**: what the issue says happens is no
longer what happens, even though the underlying defect is still there. Anyone spot-checking
those against a release build would reasonably conclude "cannot reproduce" and be wrong. That
failure mode — not staleness — is the main risk this exercise found.

## Summary table

| # | Title | Repro | Status vs `main` | History | Suggested action | Godbolt |
| --- | --- | --- | --- | --- | --- | --- |
| [708](https://github.com/microsoft/DirectXShaderCompiler/issues/708) | RegisterOffset is being ignored | agent-constructed | **repros** | always-repro'd | still-valid-keep-open | [link](https://godbolt.org/z/MsfE6b1v8) |
| [1306](https://github.com/microsoft/DirectXShaderCompiler/issues/1306) | Validation for sync in varying flow control | complete | **repros** (never implemented) | always-repro'd | enhancement-not-bug | [link](https://godbolt.org/z/c3ojha8KW) |
| [1627](https://github.com/microsoft/DirectXShaderCompiler/issues/1627) | force include file | agent-constructed | **repros** (never implemented) | always-repro'd | enhancement-not-bug | [link](https://godbolt.org/z/E1xv7nvPa) |
| [1702](https://github.com/microsoft/DirectXShaderCompiler/issues/1702) | Array as parameter of function | complete | **repros** (symptom shifted) | always-repro'd | still-valid-keep-open | [link](https://godbolt.org/z/Tfe5d4fGW) |
| [1768](https://github.com/microsoft/DirectXShaderCompiler/issues/1768) | Arrays of structs in GS OutputStreams | complete | **repros** (crash-class) | always-repro'd | still-valid-keep-open | [link](https://godbolt.org/z/b66vK5EPx) |

All five are now reproducible in one click on Compiler Explorer, each annotated with what to
look for, and four set **Clang** beside DXC — see [Shareable repros](#shareable-repros) for why
#1768 has no Clang pane and for the caveats that come with the rest.

Evidence for each is in `issues/<nnnn>/`: `expected.md` (symptom pinned down *before*
running), `repro.hlsl`, `cmd.txt`, `match.json` (the symptom predicate), `notes.md`, and the
captured `out-*.txt` for every compiler tested.

---

## Per-issue findings

### #708 — RegisterOffset is being ignored (2017-10-13, oldest open issue)

The issue was prose-only, so the repro is agent-constructed:
`Texture2D tex : register(t1[27]);`

DXC compiles it cleanly with no warning and binds the resource at `t1` — the `[27]` is
discarded in silence. Unchanged across all releases.

This one is backed by **source evidence, not just observed output**: `RegisterOffset` is
parsed (`ParseDecl.cpp:502`), stored (`HlslTypes.h:269`), echoed when dumping the AST
(`DeclPrinter.cpp:1487`, `ASTDumper.cpp:1070`), and compared for duplicate detection
(`SemaHLSL.cpp:13166`) — but **never read by binding assignment or codegen**. Parsed and
dropped.

The defect (accepting syntax DXC does not implement, without diagnosing it) is unambiguous.
What DXC *should* do is a genuine open question, and @damyanp's 2024 comment points that
decision at the HLSL 202x spec.

### #1306 — Validation for sync in varying flow control (2018-05-24)

Complete repro. DXC compiles it with no diagnostic at all; the emitted DXIL confirms
`dx.op.barrier` sits inside a divergent branch. FXC rejects the same shader with X3663.

This is a feature that was never built, not a regression. The issue already contains most of
a decision: SPIR-V maintainers argued in 2018 it belongs in SPIRV-Tools validation and can
only ever be a warning; @damyanp noted in 2024 that it needs uniformity analysis and would
likely be solved in Clang (`microsoft/hlsl-specs#246`).

**Candidate for redirecting to the specs/Clang work** rather than remaining an open DXC bug.

### #1627 — force include file (2018-10-24)

`dxc -include forced.h` → `Unknown argument: '-include'`, on every release.

I checked the full option list for an alternative spelling: DXC has `-I` (search path), `-Vi`
and `-H`, but **no forced-include of any form**. There is no workaround short of editing the
shader source.

Two things make this stand out from the other enhancements: it is labelled
`low-hanging-fruit`, and demand is demonstrably current — it was independently re-raised on
2025-07-18 by a second user with the same motivation (injecting a prelude into third-party
shader sources that cannot be edited).

The Clang comparison sharpened the ask considerably. Clang has the capability already, just not
in the dxc-compatible driver — bare `-include` is rejected there too, but
`-Xclang -include -Xclang forced.h` works. So this is **exposing an existing behaviour at the
driver level**, not implementing a feature.

**Best `up-for-grabs` candidate in this batch**, and smaller than it looked.

### #1702 — Array as parameter of function (2018-11-13) ⚠️ issue text is stale

Still a real bug, but **not the bug the issue describes**.

- The issue's comments report an assert in `SROA_Helper::RewriteBitCast`. Bisecting an
  internal-failure predicate across all 20 releases found **no crash in any of them**,
  including v1.4.1907 (2019-07) — the oldest shipping a usable `dxc.exe`, so when the assert
  stopped cannot be determined.
- What actually happens, and has happened since at least 2019: DXC drops the call to
  `Func` and emits `define void @main() { ret void }`, writing nothing to `SV_Target0`. FXC
  rejects the same code with X3072.
- The only change in seven years is that DXC now *warns* ("Declared output SV_Target0 not
  fully written"). v1.4.1907 emitted no warning and additionally mislabelled the signature as
  fully written.

Wrong code is arguably worse than a crash, so this should stay open. Maintainer position
(@llvm-beanz, 2024) is that it needs larger parameter-passing work and will likely land in
Clang; DXC draft PR #5249 was not expected to merge. **The Clang comparison qualifies that
position:** restating the same construct as a compute shader (which Clang supports fully) shows
Clang already compiles it *correctly*, storing the real values, while DXC emits `undef` stores
that its own validator rejects. So this is not a gap waiting on the Clang rewrite — it is one
Clang has already closed.

**If it stays open, the description should be refreshed** so the next person does not chase a
crash that stopped happening before 2019.

### #1768 — Arrays of structs in GS OutputStreams (2018-12-12) ⚠️ mis-labelled severity

Fails internally in **every** build tested, and in three different ways:

| Compiler | Exit | Behaviour |
| --- | --- | --- |
| `main` Debug | `0x80000003` | `STATUS_LLVM_ASSERT` — the `DXASSERT` the reporter named |
| v1.4.1907 | `0xC0000005` | **access violation**, no output |
| v1.9.2607 | `0x80004005` | `error: llvm::cast<X>() argument of incompatible type!` |

Two separable defects: the feature gap (arrays of structs in GS streams were never
implemented — awkward because DXIL has arrays but not structs), and the failure mode (an
unimplemented feature crashing instead of diagnosing). Even if the feature is never built,
rejecting the construct with a clear message is cheap and worthwhile.

It is labelled only `bug`. Given it access-violates in shipping builds, **`crash` is
warranted.**

---

## Shareable repros

All five now have a one-click Compiler Explorer link (see the table above), each carrying a
`// What to look for` banner naming the exact thing a reader should check — the `HLSL Bind`
column, the empty `main()`, the abnormal exit. Without that, a link to a shader that compiles
"fine" is an invitation to conclude the bug is gone.

**Four of them now put Clang beside DXC**, which turned out to be worth more than a second
opinion. CE carries `hlsl_clang_trunk` and `hlsl_clang_assertions_trunk` (the two agreed on
every repro here, so one pane suffices). Since HLSL support is being rebuilt in Clang, "does
this still reproduce?" and "is this already answered in the successor compiler?" are different
questions, and the second is often the more useful one:

- **#708** — Clang **rejects** `register(t1[27])` outright (`error: expected ')'`). The silent
  acceptance is DXC's alone, and Clang has effectively already picked one of the two options
  the issue leaves open.
- **#1306** — Clang compiles the divergent barrier **silently too**. The 2024 comment suggests
  this analysis would live in Clang; the link shows the gap is still open there.
- **#1627** — the strongest of the four, and it **reversed a decision**. This was recorded as
  "no link needed, it is just an unknown-argument error". But Clang *does* have the capability,
  reachable today as `-Xclang -include -Xclang forced.h`; its pane fails with
  `fatal error: 'forced.h' file not found` (CE is single-file), and *reaching a file lookup* is
  what proves the flag was honoured. DXC fails earlier, while parsing arguments. That reframes
  the request from "add a feature" to "expose an existing one at the driver level" — which is a
  materially different, and much smaller, ask.
- **#1702** — the strongest of the four, once the repro was translated. Clang does not merely
  accept `float4 a[]`, it **compiles it correctly**; DXC emits `undef` stores that its own
  validator rejects. See below — this pane needed both a translation and a control.

**#1768 deliberately has no Clang pane, and the alternative was tested.** Clang has no
geometry-shader support (`unknown type name 'point'`), so it fails at parse for reasons
unrelated to the bug. The standard remedy is to restate the repro as a compute shader — that
was tried and rejected: the construct in isolation (an array of structs carrying semantics,
written through a function) compiles **cleanly** in both DXC trunk and Clang trunk as `cs_6_0`.
The crash lives in the GS output-stream path, not the data structure, so a translation would
exercise a different code path and quietly imply the bug is elsewhere.

Two links do more than restate the finding:

- **#1306** and **#1702** put **FXC beside DXC and Clang**. FXC fails with `error X3663` and
  `error X3072` respectively; DXC compiles both silently. The feature request *is* the diff
  between the panes.
- **#1768** shows that the *same* bug surfaces differently across builds — and on trunk,
  between runs of the same input, alternating between `SIGSEGV` and
  `error: cast<X>() argument of incompatible type!`. The link is evidence that the failure is
  crash-class, not that it has a particular message.

### Clang panes need controls

Two of the four Clang comparisons were nearly published as false findings, and both were caught
the same way — by running a **control**.

Clang trunk rejected #1702 with `error: Unsupported intrinsic llvm.dx.store.output.v4f32 for
DXIL lowering`, which reads like a verdict on the issue. It is not: a one-line
`float4 main() : SV_Target { return 0; }` fails **identically**. Clang's DXIL backend cannot
yet lower *any* pixel shader writing `SV_Target`. Published as-is, that pane would have been
pure noise dressed as evidence.

Separately, `dxc_trunk` appeared to accept `/FI forced.h` silently with exit 0 — a tempting
"DXC silently ignores the MSVC spelling" claim. The control killed it: `/ZZZNONSENSE` is
accepted just as silently, and Clang reports `/FI` as `no such file or directory`. On CE's
Linux builds a `/`-prefixed argument looks like an absolute path, so MSVC-style flags simply
are not testable there. Nothing about DXC was learned.

### Translating a repro beats dropping the comparison

The first fix for #1702's unusable Clang pane was `-fsyntax-only` — ask the front end the one
question it can still answer. That worked, and produced a true but thin finding: "Clang accepts
`float4 a[]` with no diagnostic either, so the gap is shared."

Restating the same construct as a **compute shader** — which Clang supports fully — replaced
that with something much stronger. Same construct, three different answers:

| Compiler | Result |
| --- | --- |
| FXC `cs_5_0` | rejects: `error X3072: array dimensions of function parameters must be explicit` |
| DXC 1.6.2112 / trunk | accepts, emits `float undef` stores, **its own validator rejects the module** |
| Clang trunk | compiles correctly, stores `float 1.000000e+00` |

That inverts the conclusion. Clang has not inherited the gap — it has already handled the case.
DXC is the only one of the three wrong *either way*: whichever answer is right for the language,
emitting `undef` is not it. The `check-in-clang` label proposed for #1702 was dropped as a
direct result.

The rule now in the skill: when Clang cannot compile the repro's stage, **first try translating
it to compute**; only omit the pane if the translation would exercise a different code path
(as with #1768, verified). The stage-accurate original stays as the local evidence, and the
translation is verified locally before publishing.

The rule this produces: **an error from a compiler that cannot compile the repro at all is not
evidence.** Before believing any cross-compiler difference, compile something trivial with the
same flags and confirm the difference does not survive.

Three further caveats on how much weight these links can carry:

1. **Compiler Explorer runs Release builds**, so asserts are compiled out exactly as in
   shipping releases. A Debug-only assert looks clean there. CE corroborates the local Debug
   build; it never overrules it. (`hlsl_clang_assertions_trunk` is the one exception, and it is
   Clang-only — there is no assertions DXC on CE.)
2. **CE's oldest DXC is 1.6.2112**, newer than the local bisect floor of v1.4.1907. Dating a
   fix still requires the local release cache.
3. **CE is single-file.** #1627's `forced.h` cannot exist there. In that case the absence is
   itself the evidence, but multi-file repros in general cannot be fully represented.

Generating these links also **caught a live defect in the triage tooling**. CE's Linux trunk
reports `cast<X>() argument of incompatible type!` where the Windows build says
`llvm::cast<X>()`. The crash predicate anchored on the `llvm::` spelling, so it scored a real
crash as clean — the exact false-"fixed" failure mode described below, resurfacing in a new
guise. The marker is now build-agnostic, and all five verdicts were re-verified afterwards.
A predicate that has only ever been tested against one build is not yet a tested predicate.

---

## What the pilot taught us about the method

Three findings that change how the wider pass should be run:

**1. Text-matching on crash symptoms produces false "fixed" verdicts.**
My first predicate for #1768 matched the assert message. It reported both release binaries as
clean — wrong. Shipping releases are Release builds with asserts compiled out, so the same
bug surfaces as an access violation or a stray `llvm::cast` failure instead. The fix was an
exit-code-based `internal_failure` predicate. **Every one of the ~50 `crash`-labelled open
issues is exposed to this**, so the predicate is now a first-class primitive rather than a
per-issue regex.

**But the first version of that fix was itself wrong, in the more dangerous direction.** It
classified "any exit code other than 0 or 1" as an internal failure. Measuring dxc's actual
exit codes shows that is badly wrong on Windows:

| Outcome | Exit code |
| --- | --- |
| success | 0 |
| input file not found | 1 |
| **plain syntax error** | **0x80004005** (E_FAIL) |
| **invalid target profile** | **0x80004005** |
| **DXIL validation failure** | **0x80004005** |
| assert fires (Debug) | 0x80000003 |
| access violation | 0xC0000005 |
| `llvm_unreachable` / `report_fatal_error` | 0xE0000002 / 0xE0000003 |

dxc returns `E_FAIL` for **ordinary diagnosed errors**. The original rule therefore reported
essentially every failing compile as a crash — it would have *invented* crash bugs across the
backlog, which is worse than missing them, because a false "still crashes" is much likelier to
be believed and acted on than a false "fixed". It surfaced only because #1702's compute repro
produced a legitimate validation failure that the predicate flagged as a crash.

The predicate now tests the specific status codes dxc's own exception filter recognises
(`tools/clang/tools/dxclib/dxc.cpp`), plus POSIX signal exits for Compiler Explorer's Linux
builds. It is covered by a 15-case unit test, and all five pilot verdicts were re-run
afterwards and are unchanged. The lesson generalises: **the predicate is the experiment**, and
it deserves the same scepticism as any other result — derive it from the compiler's own source,
and measure the codes rather than assuming them.

(Related, and the same shape of error: dxc **silently ignores** unrecognised `/`-style flags —
`/ZZZNONSENSE` exits 0. A clean exit never proves a flag was honoured.)

**2. "Repros" and "repros as described" are different questions.**
#1702 needed two predicates to tell an honest story: the reported crash is gone, the actual
defect is not. Recording the symptom in `expected.md` *before* running, and allowing more than
one predicate per issue, is what made that visible instead of collapsing it into a single
misleading verdict.

**3. Bisection is much cheaper than budgeted.**
Every issue in this batch was `always-repro'd`, so the two-endpoint check short-circuited and
no binary search was ever needed — 33 local runs across just 3 builds, and only 2 release
downloads for the whole batch. The cost model should be "cheap unless there is a transition to
find".

**4. Two things must be re-derived every run, not remembered.**
The label taxonomy is repo state — labels get added, renamed and retired — so it is now
re-fetched each batch and every proposal is validated against the live set, with unknown names
rejected rather than silently stored. And the drafts are now reviewed by a separate agent on a
different model before a human sees them; the author of a draft cannot judge its length,
because they know why every sentence is there. Both are steps in the skill, not conventions.

**5. Comparing against Clang answers a different question, and is often the better one.**
For issues this old, "does it still reproduce in DXC?" matters less than "has the successor
compiler already settled this?". Four of the five links now carry a Clang pane, and it changed
conclusions three times: Clang *rejects* #708's syntax outright (answering a design question the
issue leaves open), it already implements #1627's feature behind `-Xclang` (shrinking that
request from "add a feature" to "expose one"), and it compiles #1702 *correctly* where DXC
emits `undef` (removing the case for `check-in-clang` there).

But Clang's DXIL backend is incomplete, so it errors on repros for reasons unrelated to the
issue. **An error from a compiler that cannot compile the repro at all is not evidence** —
compile something trivial with the same flags before believing any difference. And where Clang
cannot handle the repro's shader stage, **translating the repro to compute beats dropping the
comparison**: #1702's compute restating turned a thin "Clang accepts it too" into a three-way
disagreement that reframed the issue. Where translation would exercise a different code path,
omit the pane instead — verified for #1768, whose construct compiles cleanly as a compute
shader, confirming the crash is specific to the GS output-stream path.

Also worth recording, because it cost real time: the local `build/Debug` binary reported a
**stale version string** from a previously-built feature branch (`damyanp/fix-resource-struct-zero-init,
dc2088b20-dirty`) even after rebuilding clean `main`. The generated `build/utils/version/version.inc`
and `dxcversion.inc` are not regenerated on branch change. They must be deleted to force it.
Triage provenance is worthless if the binary misreports what it is.

## Proposed label changes

Recorded, **not applied**. Every name below was validated against the repo's live label set
(58 labels, fetched during this batch) — the tooling rejects a label that does not exist and
suggests the nearest real one, so these are all applicable as written.

| Issue | Currently | Add | Remove |
| --- | --- | --- | --- |
| [#708](https://github.com/microsoft/DirectXShaderCompiler/issues/708) | `bug` | `diagnostic`, `hlsl-next` | — |
| [#1306](https://github.com/microsoft/DirectXShaderCompiler/issues/1306) | `enhancement`, `validation` | `fxc-disagrees`, `diagnostic` | **`validation`** |
| [#1627](https://github.com/microsoft/DirectXShaderCompiler/issues/1627) | `enhancement`, `low-hanging-fruit` | `up-for-grabs`, `usability` | — |
| [#1702](https://github.com/microsoft/DirectXShaderCompiler/issues/1702) | `bug`, `shader-linking` | `fxc-disagrees`, `incorrect-code`, `correctness` | **`shader-linking`** |
| [#1768](https://github.com/microsoft/DirectXShaderCompiler/issues/1768) | `bug` | `crash`, `diagnostic` | — |

Three patterns worth noting, because they will recur:

**Severity is understated on old crash reports.** #1768 access-violates in a shipping release
build and is labelled only `bug`. If `crash` is used to size the backlog, that number is low.

**Two removals, of different confidence.** #1306 carries `validation` — a label whose *name*
reads generically but which means **DXIL validation** specifically. The request there is for a
front-end compile-time diagnostic, and the only validator discussed in the thread is SPIR-V's,
so it is safe to drop. #1702 carries `shader-linking`, but the repro is a plain `ps_6_0` shader
and neither the body nor any comment mentions linking, libraries or `lib_6_x`. It looks
misapplied — but a label added in 2018 may encode context that was never written down, so the
draft raises it as a question rather than asserting it. Read the label descriptions, not the
list of names.

**The most valuable labels are the ones that record the finding.** `fxc-disagrees` on #1306 and
#1702 are the difference between this work being re-done in two years and being findable.
`hlsl-next` on #708 likewise moves a language-design question out of the undifferentiated `bug`
pile. `check-in-clang` was proposed for #1702 and then **withdrawn**, because the Clang pane
showed Clang already compiles that case correctly — a label proposal is a finding too, and it
has to survive the evidence.

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


### Draft — [#708](https://github.com/microsoft/DirectXShaderCompiler/issues/708) RegisterOffset is being ignored from RegisterAssignment

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#708](https://github.com/microsoft/DirectXShaderCompiler/issues/708).

On `main` (1.9.0.15422, `eff900d5`), `register(t1[27])` still binds at `t1` with no
diagnostic, silently discarding the `[27]`. Unchanged from v1.4.1907 (2019-07) through
v1.9.2607.

Repro: https://godbolt.org/z/MsfE6b1v8

```hlsl
Texture2D tex : register(t1[27]);
float4 main() : SV_Target { return tex.Load(int3(0, 0, 0)); }
```

```
; Name                                 Type  Format         Dim      ID      HLSL Bind  Count
; tex                               texture     f32          2d      T0             t1     1
```

`RegisterAssignment::RegisterOffset` is parsed (`ParseDecl.cpp`), stored (`HlslTypes.h`),
dumped (`DeclPrinter.cpp`, `ASTDumper.cpp`) and checked for conflicts (`SemaHLSL.cpp`), but
never read by binding assignment or codegen.

Clang trunk does not accept the syntax at all (`error: expected ')'`), so the silent-accept
behaviour is DXC's alone.

The clear defect is that DXC accepts syntax it does not implement without diagnosing it. What
it *should* do is a separate question: `register(t<n>[<offset>])` is undocumented for SRVs, so
whether the offset shifts the binding or the form should be rejected outright likely belongs
with HLSL 202x — though Clang has effectively already answered "reject".

Suggest keeping this open; a diagnostic is warranted regardless of how the semantics land.

**Labels:** suggest adding `diagnostic` and `hlsl-next`; keep `bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#1306](https://github.com/microsoft/DirectXShaderCompiler/issues/1306) Validation for sync in varying flow control

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#1306](https://github.com/microsoft/DirectXShaderCompiler/issues/1306).

On `main` (1.9.0.15422, `eff900d5`), DXC still accepts a barrier in divergent control flow
with no diagnostic. Unchanged from v1.4.1907 through v1.9.2607.

Repro: https://godbolt.org/z/c3ojha8KW

FXC rejects the original shader:

```
error X3663: thread sync operation found in varying flow control, consider reformulating your
algorithm so all threads will hit the sync simultaneously
```

DXC 1.6.2112 and trunk place the barrier inside the divergent branch (debug metadata elided):

```llvm
  %5 = icmp eq i32 %4, 0                     ; line:8 col:21
  br i1 %5, label %6, label %13              ; line:8 col:8

; <label>:6
  call void @dx.op.barrier(i32 80, i32 9)    ; line:10 col:9  Barrier(barrierMode)
```

The thread's conclusion still holds: without uniformity analysis the best achievable result is
a warning with false positives rather than an error, and the likely home for that analysis is
Clang (microsoft/hlsl-specs#246). Worth noting the link's fourth pane: Clang trunk compiles
this silently too, so the gap is not yet closed there either. Consider tracking it as a Clang /
HLSL specs item rather than an open DXC issue — but the repro is good and the gap is real, so
not as "cannot reproduce".

**Labels:** suggest adding `fxc-disagrees` and `diagnostic`, and removing `validation` — that
label means DXIL validation, whereas this is a front-end compile-time analysis. The only
validator discussed in the thread is SPIR-V's, which is a different component.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#1627](https://github.com/microsoft/DirectXShaderCompiler/issues/1627) force include file

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#1627](https://github.com/microsoft/DirectXShaderCompiler/issues/1627).

`-include` is still unsupported on `main` (1.9.0.15422, `eff900d5`), and on every release from
v1.4.1907 through v1.9.2607.

```
$ dxc -T ps_6_0 -E main -include forced.h repro.hlsl
dxc failed : Unknown argument: '-include'
```

There is no equivalent spelling: DXC has `-I` (include search path), `-Vi` (trace include
processing) and `-H` (show include nesting), but no forced-include option.

The demand is not historical — a second, unrelated user re-raised this in July 2025 with the
same motivation: injecting a prelude header into third-party shader sources that cannot be
modified. `-I` does not serve that.

Side-by-side with Clang: https://godbolt.org/z/E1xv7nvPa

Clang already has the capability; it is just not exposed by the dxc-compatible driver, so it
currently needs `-Xclang -include -Xclang forced.h`. In that pane the error is
`fatal error: 'forced.h' file not found` — Compiler Explorer is single-file, so the header does
not exist, but reaching a *file lookup* shows the flag was accepted and acted on. DXC fails
earlier, while parsing arguments. So the ask is a driver-level spelling of behaviour that
already exists upstream.

**Labels:** suggest adding `up-for-grabs` and `usability`; keep `low-hanging-fruit`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#1702](https://github.com/microsoft/DirectXShaderCompiler/issues/1702) Array as parameter of function

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#1702](https://github.com/microsoft/DirectXShaderCompiler/issues/1702).

The reported assert no longer reproduces on `main` (1.9.0.15422, `eff900d5`), but the codegen
bug behind it does.

Repro: https://godbolt.org/z/Tfe5d4fGW

**The assert is absent from every release I can test.** `SROA_Helper::RewriteBitCast` does not
fire in any of the 20 releases from v1.4.1907 (2019-07) onward. That is the oldest release
shipping a usable `dxc.exe`, so this cannot establish when it stopped — only that it is gone
from everything checkable. Worth knowing before anyone re-tests this issue by looking for the
crash and concludes it is fixed.

**The bug it came from is still there.** DXC accepts the unsized parameter
`float4 Func(float4 a[])`, which FXC rejects with `error X3072: 'a': array dimensions of
function parameters must be explicit`. The argument then never reaches `Func`. In the linked
compute repro DXC emits undefined stores, and its own validator rejects the result:

```
error: Assignment of undefined values to UAV.
Validation failed.
```

The pixel shader from the issue has the same trigger but fails more quietly: the call is
dropped, `main` is empty, and the only hint is `warning: Declared output SV_Target0 not fully
written in shader`. v1.4.1907 produced that same empty `main`, without the warning. Giving the
parameter an explicit size (`float4 a[2]`) compiles cleanly and stores real values, which
isolates the unsized parameter as the trigger.

A 2024 comment above says this needs broader parameter-passing work that would likely be
addressed in Clang. Clang trunk already compiles the linked repro correctly, storing the real
values. So whichever answer is right for the language — reject it like FXC, or accept it like
Clang — DXC currently matches neither.

If the issue remains open, the title and description could focus on the codegen rather than the
reported assert.

**Labels:** suggest adding `fxc-disagrees`, `incorrect-code` and `correctness`, and removing
`shader-linking` — the repro is self-contained and I don't see a linking component in the
thread, though I may be missing why it was applied.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#1768](https://github.com/microsoft/DirectXShaderCompiler/issues/1768) Arrays of structs in GS OutputStreams are not supported

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#1768](https://github.com/microsoft/DirectXShaderCompiler/issues/1768).

Still reproduces on `main` (1.9.0.15422, `eff900d5`), and in every release from v1.4.1907
through v1.9.2607. It crashes rather than erroring.

Repro: https://godbolt.org/z/b66vK5EPx

```hlsl
struct GSInOutNested { float value : TEXCOORD0; };
struct GSInOut { GSInOutNested nested[1]; };

[maxvertexcount(1)]
void main(point GSInOut input[1], inout PointStream<GSInOut> output)
{
    output.Append(input[0]);
}
```

The failure looks different depending on the build, and on trunk between runs of the same
input — worth recording, because it makes this easy to mis-triage:

| Build | Result |
| --- | --- |
| `main` Debug | assert / internal compiler error (`0x80000003`) |
| v1.4.1907 | access violation (`0xC0000005`) |
| v1.6.2112 (Linux) | `SIGSEGV` |
| trunk (Linux) | `SIGSEGV` on some runs, `error: cast<X>() argument of incompatible type!` on others |

Two separable issues:

1. **Feature gap** — arrays of structs in GS streams are unimplemented. The 2018 comment above
   explains why it is awkward: DXIL has arrays but not structs, so `struct { int; float; }[42]`
   must lower to `int[42]; float[42]`, perturbing layout and semantic ordering.
2. **Failure mode** — that unimplemented case crashes instead of diagnosing.

Even if (1) is never implemented, (2) is worth fixing on its own: reject the construct with a
clear message.

**Labels:** suggest adding `crash` (currently labelled only `bug`, though it access-violates in
shipping builds) and `diagnostic`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

---

## Caveats

- **Biased sample.** The five oldest issues are unusually thin and unusually likely to be
  design questions rather than crisp bugs. A 5/5 "still reproduces" rate will almost certainly
  not hold across the backlog.
- **Bisection floor is v1.4.1907 (2019-07).** It is the oldest release shipping a usable
  `dxc.exe` (`v1.2.0-alpha` ships only `dxil.zip`). For #708 and #1306, which predate it,
  "always-repro'd" means "for as long as it is possible to check" — not "since the issue was
  filed".
- **Two repros are agent-constructed** (#708, #1627) from prose descriptions. They are
  faithful to the reports, but a human should confirm they capture what the reporter meant
  before any action is taken on those issues.
- **No SPIR-V issue appeared in this batch.** The `-spirv` path is in scope but is not yet
  exercised; the first batch containing one should be reviewed with extra care.
- **The label proposals are one reader's judgement.** They were validated for *existence*
  against the live taxonomy, which says nothing about whether they are the right call. The two
  removals in particular are the kind of change that a maintainer with history may reject.

## Suggested next step

None of these five can be closed, so the actionable output is small: #1627 looks like a good
`up-for-grabs` pick, #1768 warrants a `crash` label, and #1702's description is misleading
enough to be worth refreshing.

The more valuable next step is a **second batch drawn from a different slice** — ideally
2020–2022 bugs, including at least one SPIR-V and one `crash`-labelled issue — to test the
workflow where "no longer reproduces" is actually plausible. This batch could not exercise the
bisection search at all.



