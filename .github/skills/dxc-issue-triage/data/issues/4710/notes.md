# #4710 — Index for resource array inside cbuffer must be a literal expression

**Verdict: reproduces on `main`, and it is a regression.** v1.4.1907 compiles the reporter's
shader and emits correct DXIL. v1.5.2010 is the first release that rejects it, and every
release since does. Whether the rejection is *wrong* is a design question this triage does
not settle — see "What this does not answer".

Ground truth: `<repo>/build/Debug/bin/dxc.exe`, repo commit `13730886e6a9019e4e0823746470f3ab75341d6b`
(the binary self-reports `1.9.0.5433 (triage, ab5400907)`; the mismatch is the known
build-stamp condition, not a different tree).

## What was measured

`repro.hlsl` is the issue body verbatim. `cmd.txt` is `-T ps_6_0 -E psMain`; the reporter
filed `-T ps_6_6`, kept as `cmd-as-filed.txt` and captured as
`variant-as-filed-ps66-main-debug.txt`. The retarget is deliberate: `ps_6_0` shows the
identical diagnostic and reaches back to v1.4.1907, whereas `ps_6_6` does not exist before
v1.6.2104 and would have silently truncated the history at exactly the point that matters.

**The predicate is the exact diagnostic text**, `match.json`:

```
error: Index for resource array inside cbuffer must be a literal expression
```

Not `nonzero_exit` — dxc returns `E_FAIL` (`0x80004005`) for *every* diagnosed error, so exit
status carries no information here. Not a bare `error:` either: the symptom of this issue is
a diagnostic, so a loose predicate would score any release that dislikes anything about the
shader as a reproduction, and would have reported "always reproduced" for a case that in fact
used to compile. The usual `invalid-probe` safety net is blind to this, because for a
diagnostic issue the demotion signal and the symptom are the same class of observation.

The substitute is a **positive control on the same binary**: `manual-case-release-history.txt`
runs six shaders against all 21 builds and asserts three controls per build.

| shader | role | expectation |
| --- | --- | --- |
| `repro.hlsl` | subject, form A `foo_bar.Texture[i]` | — |
| `case-cb-array-dynamic.hlsl` | subject, form B `FooBarTextures[i]` | — |
| `case-truly-dynamic.hlsl` | subject, index from an input semantic | — |
| `control-literal-index.hlsl` | control: same array, literal index | must not match |
| `control-global-array.hlsl` | control: form C, array outside the cbuffer | must not match |
| `control-hello.hlsl` | control: trivial pixel shader | must not match |

**63 control assertions, 0 failures.** No build was disqualified, and no build was scored on a
capture it could not produce.

## Result

| | v1.4.1907 | v1.5.2010 → v1.9.2607, main |
| --- | --- | --- |
| repro (form A) | compiles | diagnostic |
| form B | compiles | diagnostic |
| truly dynamic index | compiles | diagnostic |
| all three controls | compile | compile |

Twenty stable releases, scanned linearly (`bisect --linear`). Five prereleases and
`v1.2.0-alpha` are excluded: the issue names `main` and the July 2022 official release, not a
prerelease. `bisect` printed "non-monotonic history"; that wording is misleading here — there
is a single clean→repro transition at v1.5.2010 and nothing oscillates.

v1.5.2010 words the message differently (`Function: psMain: error: … Use /Zi for source
location.`) but the literal substring is intact, so one predicate is valid across the whole
range.

### The strongest evidence: `out-v1.4.1907.txt`

v1.4.1907 does not merely avoid the error — it produces the *right* shader:

```
; FooBars.Texture                   texture     f32          2d      T0             t0    16
%…_texture_2d40 = call %dx.types.Handle @dx.op.createHandle(i32 57, i8 0, i32 0, i32 0,  i1 false)
%…_texture_2d39 = call %dx.types.Handle @dx.op.createHandle(i32 57, i8 0, i32 0, i32 5,  i1 false)
%…_texture_2d38 = call %dx.types.Handle @dx.op.createHandle(i32 57, i8 0, i32 0, i32 10, i1 false)
%…_texture_2d   = call %dx.types.Handle @dx.op.createHandle(i32 57, i8 0, i32 0, i32 15, i1 false)
```

Handle indices 0/5/10/15 and cbuffer `regIndex` 0/9/18/27 are arithmetically correct for
`FooBars[i].Texture[i]` over a 4-element struct array whose element holds one scalar and four
textures. FXC `ps_5_0` on Compiler Explorer independently produces the *same* binding layout —
`FooBars[0].Texture[0]` at `t0`, `[1].[1]` at `t5`, `[2].[2]` at `t10`, `[3].[3]` at `t15`.
Two independent compilers agreeing on the answer is much stronger than either alone.

## Why it changed: `94460c988`

`git log -S` on the diagnostic string returns exactly one commit:
**`94460c988` "Support register binding on resource in cbuffer. (#2582)"**, Xiang Li,
2019-11-11. `git merge-base --is-ancestor` places it after v1.4.1907 and before v1.5.2010 —
the measured boundary. The window is 434 commits, 8 of which touch `lib/HLSL/HLModule.cpp`,
so the attribution is strong rather than proven.

The commit removed the `Ty = ArrayType::get(Ty, arraySize)` collapse ("Not support resource
array in cbuffer") so each cbuffer resource element becomes its own global with its own
register binding — `Tex1.0`, `Tex1.1`, … — which is what makes `register()` on a resource in a
cbuffer work. Per-element binding is also precisely what makes a non-constant index
unlowerable at that point. The same commit **rewrote
`tools/clang/test/HLSLFileCheck/hlsl/objects/CbufferLegacy/resource-in-cb4.hlsl` from a
successful binding table to a CHECK for this error**, i.e. it deliberately converted a
previously-compiling case into a diagnosed one. Both tests that assert this diagnostic
(`res_in_cb3.hlsl`, `resource-in-cb4.hlsl`) use a *genuinely* dynamic index; neither covers
the reporter's `[unroll]` case.

## Why the shader is rejected: pass ordering (`manual-case-pass-order.txt`)

The guard is `lib/HLSL/HLModule.cpp:816`:

```cpp
unsigned HLModule::GetBindingForResourceInCB(GetElementPtrInst *CbPtr, …) {
  if (!CbPtr->hasAllConstantIndices()) {
    // Not support dynmaic indexing resource array inside cb.
    string ErrorMsg("Index for resource array inside cbuffer must be a literal expression");
    dxilutil::EmitErrorOnInstruction(CbPtr, ErrorMsg);
```

It lives in a **DXIL-lowering pass, not in Sema** — despite the `file:line:col` + caret shape
of the message. Two measurements pin this down:

* `-fcgl` accepts the shader (exit 0), so the front end has no objection.
* replaying dxc's own pass list under `cdb` captures the stack:
  `DxilGenerationPass::runOnModule → GenerateDxilOperations → TranslateBuiltinOperations →
  TranslateHLBuiltinOperation → TranslateSubscriptOperation → TranslateHLSubscript →
  TranslateCBOperationsLegacy → TranslateCBAddressUserLegacy → TranslateCBGepLegacy →
  TranslateResourceInCB → GetOrCreateResourceForCbPtr → CreateResourceForCbPtr →
  HLModule::GetBindingForResourceInCB → EmitErrorOnInstruction`.

And `dxc -Odump` shows the ordering that explains the reporter's confusion:

```
[ 36] -dxilgen                       <-- contains the guard
[ 41] -dxil-loop-unroll,…            <-- implements [unroll]
```

`[unroll]` runs **five passes after** the check that demands a literal index. The induction
variable is still a non-constant SSA value when the guard tests it, so writing `[unroll]` can
never satisfy the guard. `lib/Transforms/IPO/PassManagerBuilder.cpp` `addHLSLPasses()` adds
`createDxilGenerationPass` before `createDxilLoopUnrollPass` — under a comment reading
"Passes to handle [unroll] … Needs to happen before resources are lowered and before HL module
is gone", which is in visible tension with where the pass actually sits.

**Deliberately not claimed:** hoisting `-dxil-loop-unroll` above `-dxilgen` under `dxopt` does
silence the diagnostic, but the self-check in `manual-case-pass-order.txt` counts **one**
`textureLoad` where a faithful 4-iteration unroll owes four. That arm is recorded as a
negative result. It is not evidence that reordering is a fix, and it should not be read as
one.

## Cross-compiler (`manual-case-godbolt-verify.txt`, <https://godbolt.org/z/EKh5E8Y4M>)

* `dxc_1_6_2112` and `dxc_trunk`: both emit the diagnostic. CE's oldest DXC already postdates
  the regression, so no CE pane can show the era in which this compiled.
* `fxc_10_0_19041 /T ps_5_0`: compiles, with the binding table quoted above. This is the first
  direct measurement of the `fxc-disagrees` label on this issue — previously only asserted.
* `fxc_10_0_26100 /T ps_5_1`: dies with `0xC0000005` and emits nothing. The reporter's own
  follow-up says exactly this ("returns without reporting an error but also fails to emit a
  file"). Note the two FXC panes differ in build as well as profile, so this corroborates the
  report rather than isolating the variable.
* `hlsl_clang_trunk`: **crashes** in `CGHLSLRuntime::emitBufferCopy`.
  `manual-case-clang-control.txt` controls it — the identical shader shape with the resource
  member removed compiles cleanly, as does a trivial shader — so the crash tracks the resource
  member specifically and is not generic Clang HLSL immaturity. That is a distinct Clang-side
  defect, and it is directly relevant to the open question in this thread.

## What this does not answer

**Whether the diagnostic is wrong.** The restriction is deliberate: `94460c988` chose
per-element register binding for cbuffer resources, and that choice is what a non-literal
index cannot express. A maintainer could reasonably conclude either that

* the guard is too strict — the index *is* statically determined once `[unroll]` runs, the
  shader has a correct lowering (v1.4.1907 and FXC `ps_5_0` both produced it), and the fix is
  to run the guard after unrolling or to constant-fold before it; or that
* the guard is correct and the diagnostic is merely unhelpful, in which case the bug is that
  it does not say *why* `[unroll]` cannot help, and the documentation gap is the deliverable.

Nothing measurable distinguishes those. damyanp's 2024-04-29 comment asks bogner "can you
check what the right thing to do here is please (especially in the clang context)"; that
question is still open, and the Clang crash above is new input to it. Hence
`needs-human-judgement`.

**Also unmeasured:** whether v1.4.1907's acceptance of the *truly* dynamic case
(`case-truly-dynamic.hlsl`) was a correct compile or a silent miscompile. Its old binding
model gave the array a single 16-element range, which a dynamic index can express, so it was
probably legitimate — but this triage did not verify the emitted code executes correctly, and
that case is *not* what the reporter asked for.

## Files

| file | what it is |
| --- | --- |
| `expected.md` | written before any compiler ran: the symptom, the inverted polarity, the planned predicate and controls |
| `match.json` | the exact-literal predicate and why it is exact |
| `manual-case-release-history.txt` | 21 builds × 6 shaders, controls asserted per build (`measure-history.py`) |
| `out-v1.4.1907.txt` | the release that compiles it, with correct DXIL |
| `manual-case-pass-order.txt` | `-Odump` ordering, `-fcgl`, the `cdb` stack, and the negative hoist result (`probe-pass-order.py`) |
| `manual-case-godbolt-verify.txt` | full text of all five CE panes |
| `manual-case-clang-control.txt` | control establishing the Clang crash tracks the resource member (`probe-clang-control.py`) |
| `method-notes.md` | traps hit while doing this |
