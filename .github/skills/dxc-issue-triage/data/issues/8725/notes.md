# #8725 — [SER] Passing a payload by value to `HitObject::Invoke` asserts in CodeGen

**Verdict: `repros`** — on current `main` and on every release that can compile the repro.
The report is accurate in every particular, and the scope is **wider than the title says**.

Ground truth: `build/Debug/bin/dxc.exe`,
`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`, commit
`ab5400907`, verified against the batch brief before anything was run and recorded again in the
header of each `manual-case-*.txt` (with the binary's sha256). Reporter built from
`7676b1f90`. Issue filed 2026-07-31, **zero comments** — nothing in the thread extends or
contradicts the body. `expected.md` was written before any compiler ran and predicted every
control outcome correctly.

## Where each claim's evidence lives

| claim below | backing file |
| --- | --- |
| the repro fails on `main` | `out-main-debug.txt` |
| assert text, source line, full stacks; the Release face | `manual-case-assert-stack.txt` (produced by `assert-stack.cmd`, re-runnable) |
| the invalid `bitcast` in the emitted IR, and the `inout` contrast | `manual-case-fcgl-invalid-bitcast.txt` (CASES 7-8, same script) |
| release history | `out-v*.txt` (20 probes, from `bisect --linear`) |
| feature absence is real, not an unrelated rejection | `variant-control-hello-*.txt` |
| the `inout` workaround compiles | `variant-control-inout-*.txt` |
| scope: `HitObject::TraceRay`, static global, no-PAQ | `variant-ho-traceray-byval-main-debug.txt`, `variant-static-global-main-debug.txt`, `variant-nopaq-main-debug.txt` |
| plain `TraceRay` is unaffected, and why | `variant-traceray-byval-main-debug.txt`, `manual-case-intrinsic-param-ref.txt` |
| the ordinary local-payload spelling is unaffected | `variant-local-direct-main-debug.txt` |
| the four CE panes | `manual-case-compiler-explorer.txt`, `godbolt.txt`, `godbolt-note.txt` |

`triage.py reindex` was **not** run: it rewrites shared tables and other workers were live in
this batch. `triage.py audit --issue 8725` is the completeness check used instead.

## What was tested

`cmd.txt` is the reporter's own command line: `-T lib_6_9 repro.hlsl`. `repro.hlsl` is the
issue's shader verbatim (a header comment was added; no code changed).

| file | what it is | predicate / expectation | result on `main-debug` |
| --- | --- | --- | --- |
| `repro.hlsl` | the issue as filed | `match.json` | **repro**, exit `0xE0000001` |
| `control-inout.hlsl` | the reporter's workaround | `--expect no-match` | ✅ clean, exit 0 |
| `control-hello.hlsl` | trivial `lib_6_9`, no SER | `--expect no-match` | ✅ clean, exit 0 |
| `variant-local-direct.hlsl` | local payload straight into `Invoke` | `--expect no-match` | ✅ clean, exit 0 |
| `variant-traceray-byval.hlsl` | by-value payload, plain `TraceRay` | `--expect no-match` | ✅ clean, exit 0 |
| `variant-nopaq.hlsl` | no `[raypayload]`, `-disable-payload-qualifiers` | `--expect match` | **repro** |
| `variant-hitobject-traceray-byval.hlsl` | by-value payload, `dx::HitObject::TraceRay` | `--expect match` | **repro** |
| `variant-static-global.hlsl` | mutable `static Payload g` straight into `Invoke` | `--expect match` | **repro** |

Every declared expectation matched; the runner raised no warnings.

### The predicate, and why it is a disjunction

`match.json` is `any_of[ internal_failure, all_of[ "Instructions must be of an allowed type",
"unreachable" ] ]`.

The defect wears two faces and the report says so: a trapped assert in an assert-enabled build,
an invalid `bitcast` surviving into DXIL in a Release build. Release binaries are `NDEBUG`, so a
predicate keyed to the assert text would have scored **every** shipping release clean and
manufactured a "fixed in v1.8.2505" verdict out of nothing. The second disjunct is the Release
face, quoted from the issue and then verified byte-for-byte (below).

Conversely, a well-formed diagnosed error is **not** this symptom: dxc exits `E_FAIL`
(`0x80004005`) for ordinary errors, which is the same exit code every release binary returns
here. `variant-control-inout` and `variant-control-hello` exit 0, and the 15 feature-absent
releases exit `0x80004005` with an `error:` line and score `invalid-probe` — so the predicate is
demonstrably not just reading the exit code.

## Root cause, corroborated from source

Asserts go to `OutputDebugString`, not stderr, so `assert-stack.cmd` drives `cdb.exe` to capture
them. First assert (CASE 1):

```
Error: assert(type->isReferenceType() == E->isGLValue() && "reference binding to unmaterialized r-value!")
File:  C:\prj\DirectXShaderCompiler\tools\clang\lib\CodeGen\CGCall.cpp(2962)
Func:  clang::CodeGen::CodeGenFunction::EmitCallArg
```

with `EmitCallArgs` → `EmitCall` → `EmitCallExpr` → `ScalarExprEmitter::VisitCallExpr` above it.
**The report calls this the "preceding" assert; it is in fact the primary one.** The
`"Invalid cast!"` assert the report leads with is downstream of it (CASE 2 continues past each
assert with `gh`, giving the full sequence: reference-binding → `Invalid cast!`
(`lib/IR/Instructions.cpp:2257`, `llvm::CastInst::Create`) → `Illegal BitCast`
(`llvm::BitCastInst::BitCastInst`) → `Illegal BitCast` again, the last one from `AlwaysInliner`
via `CloneAndPruneFunctionInto`).

The path, all in the tree at `ab5400907`:

1. `CGMSHLSLRuntime::EmitHLSLOutParamConversionInit` (`tools/clang/lib/CodeGen/CGHLSLMS.cpp:6185`)
   handles `out`/`inout` parameters. `dx::HitObject::Invoke`'s payload parameter is `inout`, so
   it wants a copy-in/copy-out temporary.
2. It skips the temporary only when the argument's address is provably non-aliasing — an
   `alloca`, a groupshared pointer passed to a groupshared parameter, a `noalias` `Argument`, or
   a const global (`CGHLSLMS.cpp:6340-6356`; the `Argument` case is line 6355,
   `SafeToSkip = A->hasNoAliasAttr() && 0 == ArgVals.count(Ptr)`).
3. When the temporary **is** created, the argument is replaced by a `DeclRefExpr` whose value
   kind is `VK_RValue` for aggregates and objects, carrying the **non-reference** `ParamTy`
   (`CGHLSLMS.cpp:6384-6392`): *"Aggregate type will be indirect param convert to pointer type.
   So don't update to ReferenceType, use RValue for it."*
4. `CodeGenFunction::EmitCallArg` then compares the callee prototype's `Payload &` against
   `E->isGLValue()` = false → the assert at `CGCall.cpp:2962`.
5. With asserts off, the by-value aggregate path runs: `V = Builder.CreateLoad(RV.getAggregateAddr())`
   (`CGCall.cpp:3411`) then `V = Builder.CreateBitCast(V, IRFuncTy->getParamType(FirstIRArg))`
   (`CGCall.cpp:3429`) — a struct **value** bitcast to a **pointer**.

That is exactly what lands in the module. `-fcgl` (CASE 7, and CE pane 4) emits, without
complaint and with exit 0:

```llvm
%12 = load %struct.Payload, %struct.Payload* %agg.tmp
%13 = bitcast %struct.Payload %12 to %struct.Payload*
call void @"dx.hl.op..void (i32, %dx.types.HitObject*, %struct.Payload*)"(
    i32 382, %dx.types.HitObject* %obj, %struct.Payload* %13)
```

**Why `inout` works** (CASE 8, the same command on `control-inout.hlsl`): the parameter lowers
to `%struct.Payload* noalias %p`, step 2's `Argument` case fires, no temporary is created and
the real pointer is passed:

```llvm
define internal void @"\01?Function@@YAXUPayload@@@Z"(%struct.Payload* noalias %p) #0 {
  …
  call void @"dx.hl.op..void (i32, %dx.types.HitObject*, %struct.Payload*)"(
      i32 382, %dx.types.HitObject* %obj, %struct.Payload* %p)
```

So the workaround is not a coincidence; it is the one spelling that takes the `SafeToSkip` path.
`variant-local-direct.hlsl` — an ordinary local payload passed straight to `Invoke` — takes it
too, via the alloca case (`CGHLSLMS.cpp:6347`): no memcpy, no temporary, `%p` handed to the HL
op directly. That is why SER is not broken for everyone.

### Why plain `TraceRay` is unaffected: a Sema asymmetry

The report's "the same shader using `TraceRay` instead compiles fine" is correct, and the reason
is *not* in the intrinsic table — `gen_intrin_main.txt` declares the payload `inout udt Payload`
for the free-function `TraceRay` (:311), for `dx::HitObject::Invoke` (:1141) and for
`dx::HitObject::TraceRay` (:1140) alike. It is in the two different functions that build
intrinsic declarations (`manual-case-intrinsic-param-ref.txt` has both excerpts in full):

- **Free functions** — `AddHLSLIntrinsicFunction` (`SemaHLSL.cpp:2102`) converts an `out`/`inout`
  parameter to an lvalue reference **only if it is not an array or record type**
  (`SemaHLSL.cpp:2123-2135`), guarded with the comment *"Aggregate type will be indirect param
  convert to pointer type. Don't need add reference for it."* So plain `TraceRay`'s payload
  parameter stays `Payload`.
- **Object/class methods** — `AddHLSLIntrinsicMethod` (`SemaHLSL.cpp:6296`, called from
  `:11434`) converts **every** `out`/`inout` parameter to an lvalue reference
  (`SemaHLSL.cpp:6334-6340`) with no such guard. `dx::HitObject::Invoke` is a static class
  method (`[[static,class_prefix]]`), so its payload parameter is `Payload &`.

That is exactly the term the assert tests. With the argument already rewritten to a `VK_RValue`
`DeclRefExpr`:

```
TraceRay   type = Payload     -> isReferenceType() false == isGLValue() false   holds
Invoke     type = Payload &   -> isReferenceType() true  != isGLValue() false   ASSERTS
```

The IR confirms it. `-fcgl` on `variant-traceray-byval.hlsl` shows the copy-in/copy-out
conversion happening there **too** — same one temporary, same memcpy pair — but the temp's
*address* is passed:

```llvm
call void @"dx.hl.op..void (i32, %dx.types.Handle, …, %struct.RayDesc*, %struct.Payload*)"(
    i32 69, …, %struct.RayDesc* %ray, %struct.Payload* %0)
```

whereas the `Invoke` case has a **second** temporary (`EmitAnyExprToTemp` materialising the
r-value, the reference-type branch of `EmitCallArg`) which is then loaded and bitcast. So the
copy-in/copy-out temporary is not by itself the defect: **it takes both the temporary and a
reference-typed parameter.** Each of the three clean `Invoke`/`TraceRay` spellings is missing
one of the two, and each of the three failing ones has both — laid out as a table in
`manual-case-intrinsic-param-ref.txt` §E.

This also means the two natural repairs are not interchangeable. Giving `AddHLSLIntrinsicMethod`
the same record-type guard would stop the assert, but it would make the by-value case compile
*silently*, writing the payload back into a caller-invisible copy — which is what the report
asks to have diagnosed. The Sema diagnostic and the reference-type asymmetry are separate
questions, and a product decision, so the draft states both and prescribes neither.

### The two faces are one defect, measured

Continuing past the asserts under `cdb` (CASE 2) makes the Debug build print, verbatim, what the
report attributes to a Release build:

```
error: validation errors
Function: ?RayGen@@YAXXZ: error: Instructions must be of an allowed type.
note: at 'unreachable' in block '#0' of function '?RayGen@@YAXXZ'.
Validation failed.
```

This is what the release binaries and all three non-`-fcgl` CE panes print. `NDEBUG` was
emulated by continuing rather than by building a second compiler, which is worth knowing when
reading that capture — see `method-notes.md` §2.

## The title understates the scope

Two variants fail identically — same assert, same line, same stack:

- **`dx::HitObject::TraceRay`** with the same by-value payload
  (`variant-ho-traceray-byval-main-debug.txt`). Not specific to `Invoke`. Both intrinsics take
  the payload as `inout`, and the defect is in the shared argument-conversion path.
- **A mutable `static Payload g` passed straight to `Invoke` from the entry point**
  (`variant-static-global-main-debug.txt`) — *no by-value parameter and no user function at
  all*. A mutable global is not an alloca, not groupshared, not a `noalias` argument and not
  const, so step 2 does not fire.

The accurate statement of the trigger is therefore **"an object-method intrinsic with an `inout`
record parameter, called with an argument whose address is not provably non-aliasing"** — of
which "passed by value" is one instance and a mutable global is another. Any fix scoped to
by-value parameters of `Invoke` would leave both of these standing. Recorded as `text_stale`.

The report's other two claims hold: plain `TraceRay` with a by-value payload compiles clean
(exit 0, `variant-traceray-byval-main-debug.txt`), for the Sema reason set out above, and
`-disable-payload-qualifiers` with no `[raypayload]` and no access annotations still asserts
(`variant-nopaq-main-debug.txt`), so payload access qualifiers are not involved.

## Is this valid input?

No — and the "Expected Behavior" in the report (a Sema diagnostic) is the right shape of fix.
An `in` parameter is a distinct local object; binding it to an `inout` payload parameter cannot
have the caller-visible write-back that `inout` promises. The existing guard is narrow: for
`out`/`inout`/`ref` intrinsic parameters, `HLSLExternalSource::MatchArguments`
(`tools/clang/lib/Sema/SemaHLSL.cpp:7088-7097`) rejects only `pType.isConstant(actx)` or an
`OK_BitField` argument, with the comment *"This is hacky. We should actually be handling this by
failing reference binding in sema init with `SK_BindReference*`."* A by-value parameter is
neither constant nor a bit-field, and neither is a mutable global — so nothing rejects them.

Note that a plain "reject it" fix must not accidentally reject the static-global case as a
*syntax* problem: that one is a perfectly ordinary lvalue and the real defect there is the
copy-in/copy-out lowering, not the argument's spelling. The two cases share an assert but may
not share a fix.## History — measurable, and it is "never worked"

`bisect --linear`, `match.json`, over the 20 bisectable releases:

```
v1.4.1907 … v1.8.2502   invalid-probe   error: invalid profile lib_6_9   (15 releases)
v1.8.2505 … v1.9.2607   repro           error: validation errors          (5 releases)
result: always-repro'd across v1.8.2505..v1.9.2607 (15 release(s) skipped as unprobeable)
```

The five that repro are v1.8.2505, v1.8.2505.1, v1.9.2602, v1.9.2602.24 and v1.9.2607.

**Contrary to what the batch brief anticipated, the release axis here is not unmeasurable.**
SM 6.9 shipped in v1.8.2505 (published 2025-05-30; v1.8.2502, 2025-02-21, rejects the profile),
so five shipping releases can express the repro, and all five show the Release-build face of the
defect. The remaining 15 are genuine feature absence, not clean
runs — `error: invalid profile lib_6_9`, and the profile is rejected before the source is even
parsed. That was checked rather than assumed: `control-hello.hlsl`, a trivial `lib_6_9`
raygeneration shader with no SER in it, is rejected by v1.4.1907 and v1.8.2502 the same way and
compiles cleanly on v1.8.2505 and v1.9.2607
(`variant-control-hello-{v1.4.1907,v1.8.2502,v1.8.2505,v1.9.2607}.txt`). That is the three-way
distinction the brief asks for, made by measurement.

`control-inout.hlsl` also compiles clean on v1.8.2505 and v1.9.2607, so the workaround is
available in shipping releases, not just on `main`.

There is no window to bisect: the defect is present in the first release that has the feature.
No commit-level attribution was attempted and none is needed. `-T lib_6_9` is already the oldest
profile that can express `dx::HitObject::Invoke`, so there is no lower target to retreat to.

Two catalogued prereleases, `v1.10.2605.2` and `v1.10.2605.24`, are **not** part of that history:
`bisect` probes only non-prerelease tags. They are carried by Compiler Explorer, so they could be
checked there if a maintainer wants them; see `method-notes.md` §4.

## Compiler Explorer

<https://godbolt.org/z/Eo8YbKs5n> — verified after publishing: `HEAD` returns HTTP 200 and
`/api/shortlinkinfo/` reports the four panes with the options claimed
(`manual-case-compiler-explorer.txt`). The source carries `godbolt-note.txt` as a banner.

| pane | shows |
| --- | --- |
| `dxc_1_8_2502 -T lib_6_9` | `error: invalid profile lib_6_9` — the feature-absence floor, in the link itself |
| `dxc_1_9_2607 -T lib_6_9` | the user-facing symptom on the newest shipping release |
| `dxc_trunk -T lib_6_9` | the same on trunk (`dxc(private) 1.9.0.10001 (main, 32dd9cfc)`) |
| `dxc_trunk -T lib_6_9 -fcgl` | **exit 0**, and the `bitcast %struct.Payload %14 to %struct.Payload*` |

The `-fcgl` pane is the useful one: CE runs Linux Release builds, so the assert cannot appear,
but the invalid IR is right there and matches the local capture. It also shows this is neither
Windows-specific nor Debug-specific.

Panes deliberately omitted, with reasons in `manual-case-compiler-explorer.txt`:
`dxc_1_10_2605_2` / `dxc_1_10_2605_24` (CE has them, but they are GitHub *prereleases* and so
are outside the local bisect set — a pane the recorded history does not cover), and
`hlsl_clang_trunk`, which was checked rather than assumed: it answers
`error: declaration of anonymous struct must be a definition` and
`error: use of undeclared identifier 'dx'`, i.e. no `[raypayload]`, no `RayDesc`, no
`dx::HitObject`. `check-in-clang` is therefore not proposed.

## Labels

Now `bug`, `needs-triage`. Proposed: **add** `crash`, `incorrect-code`, `diagnostic`, `sm6.9`;
**remove** `needs-triage`.

- `crash` — "DXC crashing or hitting an assert". Exit `0xE0000001`, a trapped LLVM assert;
  `bug` alone understates it.
- `incorrect-code` — "Issues relating to handling of incorrect code". The input is invalid and
  DXC's handling of it is the defect. This is the label that records the finding.
- `diagnostic` — the requested and correct outcome is a Sema error; there is none today.
- `sm6.9` — SER / `dx::HitObject` is SM 6.9, and the defect dates to the first SM 6.9 release.
- `needs-triage` removed: repro confirmed on `main`, root cause located, scope characterised,
  history established back to the feature's introduction. The issue has no comments, so there is
  no discussion suggesting it is still awaiting a first look; the draft notes I may be missing
  history behind the current labels.

Deliberately **not** proposed:

- `correctness` ("bugs that impact shader correctness") — the correct behaviour is rejection,
  not different codegen. `incorrect-code` says that; `correctness` would misstate it.
- `validation` — this label means DXIL validation specifically. The validation failure here is a
  *symptom* of a front-end defect, and the validator is doing its job by rejecting the module.
  Adding it would mis-route the issue.
- `check-in-clang` — checked and answered: the construct is out of reach of the new front end
  today (above).

## Limits of this triage

- The Release-build face was reproduced by continuing past the asserts in the Debug build and by
  five release binaries plus three CE panes, **not** by building a local Release DXC. The
  agreement across those eight independent observations makes that a low risk, but it is not a
  local `NDEBUG` build.
- History is release-granular by design. No commit-level bisect over `main` was attempted; with
  the defect present in the first release that has the feature there is no window to search.
- No runtime/GPU behaviour was examined. Nothing in the verdict depends on it — the failure is
  entirely compiler-visible.
- `dx::HitObject`'s other payload-taking entry points were not exhaustively enumerated; two were
  tested (`Invoke`, `TraceRay`) and both fail, which is enough to establish that the title
  understates the scope but not enough to claim a complete list.
