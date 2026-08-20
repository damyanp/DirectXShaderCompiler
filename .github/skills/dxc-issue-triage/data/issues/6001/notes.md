# #6001 — Pass-through control point case broken for hull shader

## Ground truth
`main-debug`, commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
(`dxc --version`: `dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465
(triage, 7665270b9)`), Debug build.

## Repro
`repro.hlsl` / `cmd.txt`: `-T hs_6_0 -E MyHSMainPassthrough repro.hlsl`.
Reconstructed from the issue's own snippet, which does not define
`HSPerPatchData` used by `MyPatchConstantFunc`'s `out` parameter; it is added
here with the conventional `tri`-domain fields
(`float edges[3] : SV_TessFactor; float inside : SV_InsideTessFactor`)
implied by `[domain("tri")]` and by the constant function body's own field
references (`edges[0..2]`, `inside`). Everything else — entry point body,
attributes, signature struct — is copied verbatim from the issue. Repro
quality: partial (one struct filled in mechanically from context, the rest
verbatim).

## What was measured

The issue's own `RUN`/`CHECK` lines describe the fix:

```
// CHECK-NOT: @dx.op.loadInput
// CHECK: !dx.entryPoints = !{![[entries:[0-9]+]]}
// CHECK: ![[entries]] = !{null, !"MyHSMainPassthrough",
```

i.e. pass-through recognized == no `dx.op.loadInput` calls in the
control-point body, and `!dx.entryPoints` names `null` rather than the real
function.

`match.json` is `all_of`:
1. `define void @MyHSMainPassthrough\(\)\s*\{` — anti-vacuity anchor: proves
   the entry actually reached codegen (guards against an invalid probe or a
   failed compile vacuously looking like "no loadInput").
2. `call float @dx\.op\.loadInput\.f32` — the reported symptom: manual
   per-component copies still present.

Compiling `repro.hlsl` on `main-debug` (`out-main-debug.txt`) emits four
`dx.op.loadInput.f32` calls in `@MyHSMainPassthrough`'s body (one per float
lane of `POSITION`) and
`!5 = !{void ()* @MyHSMainPassthrough, !"MyHSMainPassthrough", !6, null, !16}`
in `!dx.entryPoints` — a real function pointer, not `null`. Exactly the
behavior described under "Actual Behavior": the entry point still manually
loads and stores every value; the SM5 pass-through case is not recognized.

**Control** (`control-no-input-read.hlsl`, `variant-control-no-input-read-
main-debug.txt`, `--expect no-match`): a control-point function that ignores
`input` entirely (`o.pos = float4(0,0,0,0); return o;`) compiles to a body
with **zero** `dx.op.loadInput` calls, scoring `no-match` as declared. This
shows the predicate's primary clause is not vacuously true for every
control-point entry — it specifically detects the per-component copy that
the reported repro produces.

## History

```
python scripts/triage.py bisect --issue 6001
```

`always-repro'd across v1.4.1907..v1.9.2607` (oldest→newest stable release,
short-circuited after both endpoints agreed; 5 probeable prereleases and 1
release with no usable asset excluded by policy). Consistent with this being
a feature gap (the compiler never implements the SM5 pass-through
optimization), not a regression — there is no release where the behavior
differed.

## Compiler Explorer
https://godbolt.org/z/nM3en9K5b — `dxc_1_6_2112` (CE's oldest DXC) and
`dxc_trunk` both emit the identical four `dx.op.loadInput.f32` calls and a
non-null `!dx.entryPoints` entry (`manual-case-godbolt-verify.txt` lines
99-102/152 and 347-350/400). Both panes agree with `main-debug` and with the
20-release scan: this has always been the behavior on every measurable DXC.

## Multi-part issue — what is and isn't measured here

The issue body raises three distinct problems:

1. **The compiler does not recognize the source-level pass-through scenario**
   (no optimization performed) — this is the part `match.json` measures
   above, and it **repros**.
2. **A validator crash** if a null metadata entry is hand-crafted to denote
   the pass-through case (relies on a function-pointer map that has no entry
   for a null function).
3. **A validator false-positive** if a function *declaration* (no body) is
   used instead, because the validator's external-declaration check assumes
   only DXIL/LLVM intrinsics are legitimately-external.

(2) and (3) both require a hand-built `.ll`/`.bc` module containing a
null-entry or declaration-only representation that, by the reporter's own
account, DXC's front end never produces and that the reporter "cannot even
craft ... in DXIL that successfully validates" — i.e. no `dxc.exe`-driven
`cmd.txt` compiling HLSL can reach that code path today. Recorded as
**not-compiler-verifiable** for those two sub-claims; they are plausible
based on the described metadata/map representation but are not independently
re-derived here (doing so would mean hand-authoring a DXIL module to probe
the validator, which is a materially larger undertaking than this repro and
is better suited to whatever follow-up issue the maintainer comment below
proposes splitting this into).

A 2024-10-28 comment from `damyanp` (MEMBER) says: *"It seems there's
multiple issues here, at least one of them is a bug in the validator that
we'll want to address, so we'll likely need to split this issue up."* No
split-off issue number is given in the thread, and the cross-reference
timeline shows no DXC issue linking back to #6001 as a split. It also shows
an external cross-reference: `HansKristian-Work/dxil-spirv#263` (2025-11-05,
closed), which calls the DXC-side fix "a planned feature" and links back to
this issue — independent, dated confirmation from over a year after filing
that the feature was still unimplemented in DXC as of that date.

## Text staleness
None. "Actual Behavior" in the issue body still describes exactly what
`main-debug` does today.

## Labels
Current: `bug`, `crash`, `validation`. All three are supported by the issue
text (the crash/validation content is real, just gated behind hand-crafted
DXIL rather than reachable from this HLSL repro) — no removal proposed.
`performance` is a plausible add, since the missing optimization means the
generated control-point shader does unnecessary per-component load/store
work relative to what the pass-through case would produce, but this is a
judgment call for whoever splits the issue rather than a clear-cut labeling
gap.
