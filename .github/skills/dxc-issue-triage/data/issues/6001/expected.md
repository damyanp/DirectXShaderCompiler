# Expected symptom (written before running anything)

Issue: hull shader "pass-through" control point case is not recognized by DXC.
SM5 allows a hull shader's control-point phase to be entirely elided when the
control-point function is just `return input[id];` for the ID given by
`SV_OutputControlPointID` — the runtime then knows to copy each control point
straight from input to output with no shader invocation at all ("null main
entry" / pass-through phase). The issue's own reduced repro's RUN line encodes
what "fixed" would look like:

```
// RUN: %dxc -T hs_6_0 -E MyHSMainPassthrough %s | FileCheck %s
// CHECK-NOT: @dx.op.loadInput
// CHECK: !dx.entryPoints = !{![[entries:[0-9]+]]}
// CHECK: ![[entries]] = !{null, !"MyHSMainPassthrough",
```

- **repros** (symptom present, matches the report): the compiled control-point
  shader still contains `dx.op.loadInput` / `dx.op.storeOutput` calls that
  manually copy each control point field, and `!dx.entryPoints` names a real
  function (a non-null entry), i.e. DXC still emits a normal control-point
  shader body rather than recognizing the pass-through case and emitting a
  null entry.
- **does-not-repro**: DXC emits no `dx.op.loadInput` for the control-point
  function and `!dx.entryPoints` carries `null` in the function-pointer slot
  for the HS control-point entry, matching the `CHECK`/`CHECK-NOT` lines
  above.

The issue body also describes two *other*, narrower problems that only occur
if a null-entry / declaration-only pass-through representation is crafted by
hand directly in DXIL (a validator crash from a dangling function-pointer
map lookup, and a validator false-positive on the function declaration being
treated as an unrecognized external declaration). Nothing in stock DXC's
front end ever emits that representation today (that is the whole complaint —
"the compiler does not recognize the scenario in the first place"), so those
two problems are not reachable by compiling HLSL through `dxc.exe` and cannot
be probed by a `cmd.txt`-driven compile. They would need a hand-crafted
`.ll`/`.bc` module with a null entry and no compiler-observable driver command
produces one from source. Recorded as **not-compiler-verifiable** for that
sub-question; the primary, source-reachable claim (no pass-through
optimization is performed) is the one scored by `match.json`.

The repro in the issue omits the `HSPerPatchData` struct used by
`MyPatchConstantFunc`'s `out` parameter; it is reconstructed below with the
conventional `tri`-domain fields (`float edges[3] : SV_TessFactor`,
`float inside : SV_InsideTessFactor`) implied by `[domain("tri")]` and the
constant function body (`edges[0..2]`, `inside`). Repro quality: **partial**
(source is filled in, but is a straightforward completion of the issue's own
snippet using its own field names).
