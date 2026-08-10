# #3066 — Suggestion: Improved human-readable values in disassembly

**Verdict: `repros`** — the readability gaps the issue lists are still present, with two
documented exceptions and one documented change of behaviour going the other way.

Reported by @jeffnn, 2020-08-05, no comments in five years. Labels `enhancement`, `dxil`.

Tested against a Debug build self-reporting `1.9.0.5433`, upstream `13730886e`, and against
all 20 stable releases from `v1.4.1907` to `v1.9.2607`.

---

## 1. What the issue asks for

The body is a list of five separate requests. `expected.md` records them verbatim and was
written before the compiler was run. Abridged:

| # | ask |
| --- | --- |
| A | a DXIL comment pointing to the original file/line/HLSL snippet, rather than crawling metadata |
| B | show the real float value (`0.0001`) in the comment, not just `float 0x3F1A36E2E0000000` |
| C | generally more hard-coded value decoding in the comment, "like is already done for the unary & binary operators"; the named example is the opcode value for `dx.op.storeOutput.f32` |
| D | for loads/stores through buffers/inputs/outputs, put the friendly resource name in the comment |
| E | the same for the Resource Bindings and Output Dependencies sections |

Two things about the framing matter for the verdict.

* The reporter states his own baseline inside ask C: unary and binary operators **already**
  carried a decoded comment in 2020. So "still reproduces" here means the decoding is *still
  just as partial*, not that it is absent.
* The quoted line comes from a PIX-instrumented module (`!pix-dxil-inst-num`,
  `!pix-dxil-reg`). Every ask is nonetheless about the shared printer, not about PIX.

## 2. Result per ask

Measured on the ground-truth build. Line numbers refer to `out-main-debug.txt` (the default
`dxc <src>` listing) and `variant-zi-main-debug.txt` (the same with `-Zi -Qembed_debug`).

| # | status | evidence |
| --- | --- | --- |
| **A** | **partially met, and was already partially met in 2020** | With `-Zi -Qembed_debug` each instruction gets `; line:N col:M` and `!dbg`, and `llvm.dbg.*` calls get `var:"…" func:"…"`. There is still no file name and no source snippet, and nothing at all without `-Zi`. |
| **B** | **unmet in all 20 releases** | Line 134 is the reporter's example almost verbatim: `%16 = call float @dx.op.binary.f32(i32 35, float %15, float 0x3F1A36E2E0000000)  ; FMax(a,b)`. The comment decodes the opcode and names the operands, then stops. |
| **C** | **the named example was already decoded when the issue was filed; the general ask is unmet** | Line 139: `call void @dx.op.storeOutput.f32(i32 5, …)  ; StoreOutput(outputSigId,rowIndex,colIndex,value)`. What is still missing is decoding of operand *values* — `outputSigId` 0 is not resolved to `SV_Target`, `i8 0` is not resolved to `.x`. |
| **D** | **unmet; there is an open `TODO` for it in the source** | Line 135: `call void @dx.op.bufferStore.f32(i32 69, %dx.types.Handle %1, …)  ; BufferStore(uav,coord0,…)`. The comment never says which of the four rows of the Resource Bindings table is being written. |
| **E** | **split: the bindings half is met and always was; the dependency half is unmet** | Lines 92–93 print `g_diffuseTexture … T0 … t0` and `g_luminanceOut … U0 … u0`. Lines 101–104 print `;   output 0 depends on inputs: { 4, 5 }` — bare scalar element indices on both sides. |

### The two things that did change since 2020

* **SM 6.6 `annotateHandle` decoding.** On `-T ps_6_6` the listing prints
  `; AnnotateHandle(res,props)  resource: Texture2D<4xF32>` and
  `resource: RWStructuredBuffer<stride=4>`. This is a real improvement in the direction ask
  C asks for. The code that prints it was already in the file in August 2020 but was
  unreachable until SM 6.6 shipped in `v1.6.2104`, so it is a change in what a user sees,
  not a change made in response to this issue.
* **A change going the *other* way, in the window `v1.4.1907` → `v1.5.2010`.** See §4.

## 3. Source corroboration

The printer is `DxcAssemblyAnnotationWriter::printInfoComment` in
`tools/clang/tools/dxcompiler/dxcdisassembler.cpp` (from line 1269).

* **Ask D has a literal open `TODO` in that function**, at line 1319:
  `// TODO: if an argument references a resource, look it up and write the name/binding`.
  That comment is present in today's source *and* in the source as of `55b847a22`, the
  commit closest to the filing date. Nobody has acted on it in five years.
* **The 2020 and current versions of `printInfoComment` are structurally the same.** The
  diff over that range is confined to the addition of `func:"…"` on debug-value comments and
  a refactor of the opcode-signature table lookup. The `; line:N col:M` output, the
  `var:"…"` output, the per-op `; <OpName>(<operands>)` comment and the `AnnotateHandle`
  resource decode were all present already.
* **The op-name comment has never been selective**, contrary to the premise of ask C.
  `OpCodeSignatures` is generated from hctdb for every op in every table
  (`utils/hct/hctdb_instrhelp.py:1464-1493`), so `storeOutput` had a decoded comment when
  the issue was filed. The reporter's impression that only unary/binary ops were decoded is
  most likely because those are the ops whose comment *also* names a specific operation
  (`FMax`) rather than repeating the intrinsic's own name.
* **Ask E splits cleanly in the source.** `PrintResourceBindings` (line ~483) already calls
  `res.GetGlobalName()`, which is why the bindings table carries names.
  `PrintOutputsDependentOnViewId` / `PrintInputsContributingToOutputs` (lines ~510-560)
  print raw scalar indices and have no access to signature element names at that point.

## 4. Release history, and a behaviour change nobody asked for

`triage.py bisect --linear` over 20 stable releases, on the primary predicate:

* `v1.4.1907` → **no-repro**
* `v1.5.2010` through `v1.9.2607` (19 releases) → **repro**

The `v1.4.1907` result is not the enhancement having once been implemented. Only clause
`root[4]` (ask D) differs; every other clause matches in `v1.4.1907` exactly as it does
today. See `manual-case-clause-matrix.txt`.

What actually changed: **in `v1.4.1907` the disassembly printed resource-derived value names
without any debug flag**, e.g.

```
call void @dx.op.bufferStore.f32(i32 69, %dx.types.Handle %g_luminanceOut_UAV_structbuf, i32 0, i32 0, float %FMax, …)
```

From `v1.5.2010` onward the same command prints `%dx.types.Handle %1` and `float %16`, and
the names only reappear if `-Zi -Qembed_debug` is passed. Confirmed by a direct `-Zi` probe
against `v1.5.2010` itself (`variant-zi-v15-v1.5.2010.txt`). A second predicate isolating
just this clause (`match-resname.json`) was bisected separately over the same 20 releases and
shows the identical transition.

So a shader author reading default disassembly today gets *less* of ask D than in 2019.

**The mechanism was not identified.** The handle name is constructed and applied
unconditionally in `lib/HLSL/DxilCondenseResources.cpp:2136-2141` and at the
`Builder.CreateCall(createHandle, Args, handleName)` sites on lines 2204/2239/2253. Searches
for `setDiscardValueNames`, value-symbol-table stripping and `StripDebugInfo` in the DXC
layers turned up nothing that would gate it. The observation is solidly measured across two
predicates and a targeted probe; the cause and the exact commit are not known, and the
window (2019-07 → 2020-10) is wide. This is stated as an observation, not a diagnosis.

Releases skipped: `v1.2.0-alpha` (no dxc asset) and five prereleases by policy
(`v1.5.2003`, `v1.8.2306-preview`, `v1.8.2405-mesh-nodes-preview`, `v1.10.2605.2`,
`v1.10.2605.24`).

## 5. Which views were tested

* `dxc -T ps_6_0 -E main repro.hlsl` — the default stdout listing. This is the primary
  capture.
* `dxc -dumpbin` over the compiled container — **byte-identical annotation** to the above;
  both go through `dxcutil::Disassemble`. Captured in `manual-case-other-views.txt`.
* `dxa -dumpreflection` — a genuinely different view, and worth noting because it *already*
  does what the issue asks for: it prints `SystemValueType: D3D_NAME_POSITION`,
  `Type: D3D_SIT_CBUFFER`, `ComponentType: D3D_SVT_FLOAT`, `Name: g_luminanceOut`. Enum
  decoding is routine in the reflection printer and absent in the disassembly printer.

No Clang pane and no `-fcgl` variant: the pixel stage has no equivalent comment-annotated
listing to compare against, so neither would say anything about the asks.

## 6. Predicate and controls

`match.json` is an `all_of` of six line-anchored regexes: two positive self-tests followed by
one clause each for asks B, C, D and E. Every symptom clause is anchored with `(?m)…$` so
that a decoded form *appended* to the comment falsifies it rather than being ignored.

Three controls, all behaving as intended (`manual-case-clause-matrix.txt`):

| control | result | what it rules out |
| --- | --- | --- |
| `variant-zi-main-debug.txt` (`-Zi -Qembed_debug`) | **no-repro**, self-tests still match | the predicate is not satisfied merely by output existing — when names and locations *are* printed, the symptom clauses flip while the self-tests hold |
| `control-plain.hlsl` (trivial valid shader) | **no-repro** | the constructs must actually be present |
| `control-broken.hlsl` (syntax error) | **no-repro** | a failed compile emitting no disassembly cannot satisfy any clause |

The `-Zi` control is the important one. It is the only control that distinguishes "the
symptom is absent because the value is now printed by name" from "the symptom is absent
because nothing was printed at all", which is exactly the vacuity trap for a
readability issue.

## 7. Compiler Explorer

https://godbolt.org/z/e69hs8h97 — two panes, `dxc_1_6_2112` and `dxc_trunk`, identical text
in all three places the banner points at.

**Caveat recorded in the banner:** Compiler Explorer appends `-Zi -Qembed_debug` to every DXC
pane regardless of the arguments given, verifiable in the `!dx.source.args` node of either
pane. CE therefore *cannot* show DXC's default listing, and shows the compiler at its most
readable. Adding `-Qstrip_debug` does not counter it (tested locally: it strips the
container's debug part, not the module's). A reader who only follows the link would see
named handles and `; line:N col:M` and would over-estimate the current state of asks A and D
— hence the caveat, and hence the local captures carry the primary claim.

An FXC contrast pane was tried and dropped: FXC rejects the shader with `error X4509` because
SM 5.0 requires pixel-shader UAVs at `u1` or above, and a failed pane says nothing.
