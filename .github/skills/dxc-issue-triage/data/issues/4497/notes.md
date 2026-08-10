# #4497 — "struct value on \"stack\"" — triage notes

**Verdict: reproduces**, on ground truth and on every stable release back to v1.4.1907. It is
a **code-quality** issue, not a correctness one, and a maintainer already diagnosed it in 2022
and asked for it to stay open as a tracking item.

Ground truth: `main-debug`, a clean Debug build of `main` at **`13730886e`**, reporting
`1.9.0.5433`. (The binary self-reports the fork-local SHA `ab5400907` in its version string;
`.cache/compilers/main-debug.json` records the public commit and the reason for the
difference. Captured output is left verbatim.)

Expected symptom was written down in [`expected.md`](expected.md) **before** the first compile.

---

## What the issue actually says

The title is unhelpful; the body is precise. Two spellings of the same shader
([`repro.hlsl`](repro.hlsl), quoted verbatim from the issue):

```hlsl
void fct1(SData data)   { [branch] if (data.type == 0) [branch] if (data.value.x < 0) discard; }
void test1()            { fct1(dataBuffer[0]); }          // struct passed BY VALUE

void fct2(int id)       { [branch] if (dataBuffer[id].type == 0)
                          [branch] if (dataBuffer[id].value.x < 0) discard; }
void test2()            { fct2(0); }                      // buffer indexed directly
```

`test1` loads `SData::value` unconditionally; `test2` loads it only when `type == 0`. Both
outputs are correct. The reporter's ask is the last sentence of the body: *"The second version
looks better since the memory fetch is done only when the fi[r]st condition is true."*

Command line: the body does not give one. llvm-beanz's 2024 Compiler Explorer link
(`https://godbolt.org/z/xr6nv5z89`, read back through `GET /api/shortlinkinfo/xr6nv5z89`)
stores the body's snippet in two `dxc_trunk` panes with `-T ps_6_6 -E test1` / `-E test2`.
That is a maintainer-supplied command line, not an agent guess, so **repro quality is
`complete`**. [`cmd-as-filed.txt`](cmd-as-filed.txt) records it and why `cmd.txt` lowers the
profile to `ps_6_0` (history: `ps_6_6` did not exist before 2021 and would make every
pre-2021 release an `invalid-probe`; the symptom was measured to be profile-independent
first — see below).

## Result on ground truth

`-T ps_6_0 -E test1` ([`out-main-debug.txt`](out-main-debug.txt), exit 0):

```llvm
define void @test1() {
  %1 = call %dx.types.Handle @dx.op.createHandle(i32 57, i8 0, i32 0, i32 0, i1 false)
  %2 = call %dx.types.ResRet.f32 @dx.op.bufferLoad.f32(i32 68, %dx.types.Handle %1, i32 0, i32 0)
  %3 = extractvalue %dx.types.ResRet.f32 %2, 0
  %4 = call %dx.types.ResRet.i32 @dx.op.bufferLoad.i32(i32 68, %dx.types.Handle %1, i32 0, i32 12)
  %5 = extractvalue %dx.types.ResRet.i32 %4, 0
  %6 = icmp eq i32 %5, 0
  %7 = fcmp fast olt float %3, 0.000000e+00
  %8 = and i1 %7, %6
  br i1 %8, label %9, label %10, !dx.controlflow.hints !10
```

`-E test2` on the same file ([`variant-test2-direct-main-debug.txt`](variant-test2-direct-main-debug.txt)):

```llvm
  %2 = call %dx.types.ResRet.i32 @dx.op.bufferLoad.i32(i32 68, %dx.types.Handle %1, i32 0, i32 12)
  ...
  br i1 %4, label %5, label %10, !dx.controlflow.hints !10
; <label>:5
  %6 = call %dx.types.ResRet.f32 @dx.op.bufferLoad.f32(i32 68, %dx.types.Handle %1, i32 0, i32 0)
```

Exactly the reported asymmetry: the `.f32` load above the branch in `test1`, inside the
guarded block in `test2`, and `test1`'s two `[branch]` ifs folded into one `and i1`.

**Profile-independent.** Same shape at `ps_6_2` ([`variant-ps62-main-debug.txt`](variant-ps62-main-debug.txt))
and at the as-filed `ps_6_6` ([`variant-asfiled-ps66-main-debug.txt`](variant-asfiled-ps66-main-debug.txt),
[`variant-test2-direct-ps66-main-debug.txt`](variant-test2-direct-ps66-main-debug.txt)); only the DXIL
spelling changes (`bufferLoad` → `rawBufferLoad` at SM 6.2+). Lowering the profile for the
history sweep is therefore inert, and was measured rather than assumed.

## Predicate

[`match.json`](match.json) — `all_of`:

| clause | why |
| --- | --- |
| `@dx\.op\.discard\(i32 82` | anti-vacuity: the shader really was compiled |
| `@dx\.op\.(?:raw)?[bB]ufferLoad\.i32\(` | the `type` load exists |
| `^\s*br i1 ` | the function has a conditional branch at all |
| `define void @[\w.]+\(\)(?:(?!br i1)[\s\S])*?@dx\.op\.(?:raw)?[bB]ufferLoad\.f32\(` | **the symptom**: the float load appears before any `br i1` |

The last clause is positional, not textual — nothing appears or disappears between the two
spellings, only the order changes. Controls (all declared with `--expect` and all as
declared): `-E test2` same source → `no-match`; `ps_6_6` and `ps_6_2` identity → `match`.
The `(?:raw)?` was added because of a real defect caught by those positive controls; see
[`method-notes.md`](method-notes.md) §1.

[`match-position.json`](match-position.json) is the same detector without the `discard`
anchor, used to score the compute restating (§ Compiler Explorer).

## History — the asymmetry has always been there

`bisect --linear` scores `test1` **`always-repro'd`**: 20/20 stable releases from
**v1.4.1907** (2019) to **v1.9.2607**, plus ground truth. Zero invalid probes; 5 prereleases
skipped by policy; `v1.2.0-alpha` publishes no usable `dxc`.
([`out-v1.4.1907.txt`](out-v1.4.1907.txt) … [`out-v1.9.2607.txt`](out-v1.9.2607.txt).)

A single-sided bisect is not sufficient for a *comparative* issue: `test1` reproducing in 2019
is equally consistent with "the asymmetry is ancient" and with "both forms were bad and only
`test2` improved". [`measure-release-matrix.py`](measure-release-matrix.py) therefore runs
**both** entry points on all 21 builds:

```
builds probed: 21   unexpected scores: 0
SELF-TEST: pass
```

`test1 = repro`, `test2 = no-repro`, on **every** build
([`manual-case-test2-control-matrix.txt`](manual-case-test2-control-matrix.txt)). Nothing has
moved since the report; there is no window to bisect and nothing in the issue text is stale.

## Mechanism

### The front end emits the load unconditionally — before any optimization

`-fcgl` (HL IR, no passes run) on `test1`
([`variant-fcgl-test1-main-debug.txt`](variant-fcgl-test1-main-debug.txt)):

```llvm
define void @test1() #0 {
entry:
  %0 = alloca %struct.SData
  ...
  call void @llvm.memcpy.p0i8.p0i8.i64(i8* %5, i8* %6, i64 32, i32 1, i1 false)   ; line:19 col:2
  call void @"\01?fct1@@YAXUSData@@@Z"(%struct.SData* %0)
```

A 32-byte copy of the whole element into an `alloca`, in the entry block, above everything.
`test2`'s `-fcgl` entry is just `call void @"\01?fct2@@YAXH@Z"(i32 0)`
([`variant-fcgl-test2-main-debug.txt`](variant-fcgl-test2-main-debug.txt)), and its float load
sits inside `if.then` from the start.

So **no pass hoisted anything**. HLSL argument passing is by value, the copy-in reads the
entire struct, and the optimizer's later job is only to narrow it: `value2` is never read and
is DCE'd, leaving loads of `value.xyz` (mask 7, offset 0) and `type` (offset 12). This is
exactly tex3d's 2022 explanation, and it is also the title — the "struct value on the stack"
is that `alloca`.

**It is not about function parameters.** [`repro-localcopy.hlsl`](repro-localcopy.hlsl)
deletes the call and keeps `SData data = dataBuffer[0];` in the entry point; it reproduces
identically ([`variant-localcopy-main-debug.txt`](variant-localcopy-main-debug.txt)). Any
whole-struct copy out of the buffer does this.

### Why the `[branch]` hints do not stop the fold — source corroboration

Both `[branch]` hints are present in the HL IR for both entry points. In `test1` the pair is
flattened; in `test2` it is not. The DXIL names the merged value `%or.cond`
([`variant-zi-ps62-main-debug.txt`](variant-zi-ps62-main-debug.txt); also visible without
`-Zi` on v1.4.1907):

```llvm
%or.cond = and i1 %cmp2.i, %cmp.i, !dbg !78 ; line:12 col:14
```

`"or.cond"` is created in exactly one place in the tree —
`git grep 'or\.cond"' -- lib tools include` returns only three sites, all inside
`llvm::FoldBranchToCommonDest` (`lib/Transforms/Utils/SimplifyCFG.cpp:2095`), the merged-branch
one being **:2275** (`Builder.CreateBinOp(Opc, PBI->getCondition(), New, "or.cond")`, where
`Opc` may be `And`). That is direct evidence for tex3d's "eliminated by simplifycfg", and it
identifies *which* transform.

Two further source facts, both checked rather than assumed:

- **DXC does honour `[branch]` — but only in two of the three flattening paths.**
  `hlsl::DxilMDHelper::HasControlFlowHintToPreventFlatten` is called from
  `SpeculativelyExecuteBB` (**SimplifyCFG.cpp:1494**, function at :1490) and from
  `FoldTwoEntryPHINode` (**:1929**, function at :1817), each inside an
  `// HLSL Change Begins.` block that returns `false` early. `FoldBranchToCommonDest`
  (:2095–2392) has **no such guard**. So tex3d's improvement #1 is a specific, bounded gap
  rather than a vague wish.
- **Why `test2` survives the same pass.** `FoldBranchToCommonDest` requires every instruction
  in the block ahead of the condition to be a "bonus instruction" that
  `isSafeToSpeculativelyExecute` (**:2152**), returning `false` otherwise. In `test1` the load
  is already in the entry block, so only the `fcmp` needs cloning and the fold is legal. In
  `test2` the guarded block contains the *load*, which is not speculatable, so the fold is
  refused and the nested branches remain.

That is the whole issue in one sentence: **the by-value copy hoists the load, and the hoisted
load is what makes the branch fold legal.** The flattening is a consequence of the copy, not
an independent second defect.

## Compiler Explorer

<https://godbolt.org/z/acfEvEz6o> — four panes, one source: `dxc_trunk` and `hlsl_clang_trunk`,
each on `test1` and `test2`, all `-T cs_6_0`. Full output captured in
[`manual-case-godbolt-verify.txt`](manual-case-godbolt-verify.txt); banner in
[`godbolt-note.txt`](godbolt-note.txt).

The panes compile [`repro-cs.hlsl`](repro-cs.hlsl), an **agent-constructed** compute restating
(pixel → `[numthreads]`, `discard` → `RWBuffer` store), because clang-dxc answers
`error: use of undeclared identifier 'discard'` and a pane full of that says nothing about
this issue. The translation was re-checked locally before publication, scored by
`match-position.json` in both stages
([`variant-cs-test1-main-debug--match-position.txt`](variant-cs-test1-main-debug--match-position.txt),
[`variant-cs-test2-main-debug--match-position.txt`](variant-cs-test2-main-debug--match-position.txt),
and the two `variant-pixel-position-*` files). The asymmetry survives the translation.

**New datapoint: clang-dxc behaves the same way.** `hlsl_clang_trunk`, `test1`:

```llvm
  %3 = call %dx.types.ResRet.i32 @dx.op.bufferLoad.i32(i32 68, %dx.types.Handle %1, i32 0, i32 12)
  %5 = icmp eq i32 %4, 0
  %6 = call %dx.types.ResRet.f32 @dx.op.bufferLoad.f32(i32 68, %dx.types.Handle %1, i32 0, i32 0)
  %8 = fcmp ... olt float %7, 0.000000e+00
  %9 = select i1 %5, i1 %8, i1 false
  br i1 %9, ...
```

versus `test2`, where the `.f32` load is inside the block guarded by `br i1 %5`. Same
asymmetry, expressed as a `select` rather than an `and`. Whatever is done here will have to be
done again in the Clang-based compiler; it is not something the rewrite fixes for free.

## Reporter-instance fidelity

The reporter's quoted IR cannot be byte-compared: it uses `rawBufferLoad`, `llvm.dbg.value`,
`%or.cond`, `createHandle(i32 57, …)` and a mangled `…@Z.exit` label, i.e. `-Zi` at SM 6.2–6.5
inside a larger private shader (their paste also shows `storeOutput`, which the public snippet
cannot produce). Compiling the public snippet with `-Zi -Qembed_debug -T ps_6_2` reproduces
that shape essentially exactly, with identical operands
([`variant-zi-ps62-main-debug.txt`](variant-zi-ps62-main-debug.txt)):

```llvm
%RawBufferLoad1 = call %dx.types.ResRet.f32 @dx.op.rawBufferLoad.f32(i32 139, %dx.types.Handle %dataBuffer_texture_structbuf, i32 0, i32 0, i8 7, i32 4), !dbg !68 ; line:19 col:2  ; RawBufferLoad(srv,index,elementOffset,mask,alignment)
%RawBufferLoad = call %dx.types.ResRet.i32 @dx.op.rawBufferLoad.i32(i32 139, %dx.types.Handle %dataBuffer_texture_structbuf, i32 0, i32 12, i8 1, i32 4), !dbg !68 ; line:19 col:2  ; RawBufferLoad(srv,index,elementOffset,mask,alignment)
```

So the structural claim in the body is faithful to what a real build does; only the register
names and the surrounding shader differ.

## Assessment

- **Status `repros`**, confidence **high**: measured on 21 builds with a positive and a
  negative control on each, and corroborated in the source.
- **Not a correctness defect.** Every probe exits 0 and both outputs are valid DXIL. Any
  predicate keyed on diagnostics or exit status would be meaningless here.
- **Nothing is stale.** Body, comments and current behaviour agree; no `--text-stale`.
- **Suggested action `still-valid-keep-open`.** tex3d asked in 2022 for it to stay open to
  track two optimizer improvements; both are still unimplemented, and the source now names the
  precise gap for the first (`FoldBranchToCommonDest` lacks the hint guard its two siblings
  have). The issue is in the **Dormant** milestone, which fits: real but low priority, with a
  one-line workaround (index the buffer directly) already demonstrated by `test2`.
- **Labels: `performance` (keep) + add `enhancement`** ("Feature suggestion") — the ask is
  better codegen for valid input, not a defect fix, and the tracked work is two optimizer
  features. Not proposing `check-in-clang`: that label's description is a to-do ("See if this
  repros in clang as well") and the comparison has now been run and is recorded above. No
  removals; the existing label is right and we may be missing history behind it.

Draft comment: [`comment.md`](comment.md). Method observations: [`method-notes.md`](method-notes.md).
