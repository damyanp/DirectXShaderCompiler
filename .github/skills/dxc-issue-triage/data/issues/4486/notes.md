# #4486 — [SPIR-V] Nested static `for` loops with `[unroll]` are still loops

**Verdict: reproduces on `main` (1.9.0.5433, `13730886e`), and on every stable release that
has a SPIR-V backend.**

- Issue: <https://github.com/microsoft/DirectXShaderCompiler/issues/4486>, filed 2022-05-28 by
  OrangeeZ against DXC 1.6.2104.52. Label `spirv`. Milestone `Dormant`.
- Ground truth: `main-debug`, Debug build, `dxc --version` reports
  `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`. The
  binary self-reports a fork-local merge SHA that resolves for nobody; its compiler source is
  identical to upstream `main` at **`13730886e`**, which is what is cited everywhere else.
- Compiler Explorer: <https://godbolt.org/z/dYWfKGE1o> (verified by shortlink read-back;
  full pane text in `manual-case-godbolt-verify.txt`).

## What was measured

`repro.hlsl` is maintainer pow2clk's 2022-06-29 self-contained shader with the nested
`[unroll]` loop restored from the reporter's 2022-06-14 comment (item 2), which is the shape
the title is about; pow2clk's own file uses the reporter's *workaround*. `float4 tmpColor`
becomes `float3` to match the `float3 colors[4]` the completed shader declares, and an unused
`float max = 0;` is dropped. `control-manual-unroll.hlsl` holds pow2clk's version unchanged,
so repro and control differ in exactly the thing under test.

```
dxc -T ps_6_0 -E PS_bright_pass -spirv repro.hlsl
```

No command line appears anywhere in the thread. `ps_6_0` is the oldest profile that can
express the shader, which is what keeps the old releases probeable.

### Ground truth (`out-main-debug.txt`, exit 0, empty stderr)

```
               OpLoopMerge %114 %112 Unroll
               OpBranchConditional %113 %115 %114
...
               OpLoopMerge %122 %119 Unroll
               OpBranchConditional %121 %123 %122
```

Both `[unroll]`-marked loops survive as structured SPIR-V loops with back-edges and `OpPhi`
counters — the `while(true)` / `Phi` / `break` shape the reporter pasted, seen in the
disassembly rather than in a decompiler. The `Unroll` loop control is emitted and then not
acted on. Exactly **one** `OpFOrdGreaterThan` remains, inside the loops; the fully unrolled
nest would contain six.

The sibling `[unroll] for (i < 4)` sampling loop in the same function **is** unrolled — four
`OpImageSampleExplicitLod`, no loop — so this is not "SPIR-V ignores `[unroll]`".

## Predicate and controls

`match.json` = `all_of[ OpEntryPoint Fragment %<id> "PS_bright_pass", ^\s*OpLoopMerge ]`.

Clause 1 is the instrument self-test: the symptom is a codegen *shape*, so the predicate reads
`dxc`'s bundled SPIR-V disassembler, and a build that emitted no module — no SPIR-V backend, a
failed parse, output going somewhere else — must be seen as unmeasurable rather than fixed.
Clause 2 is anchored at start-of-line so a diagnostic or an `OpSource`-embedded comment quoting
the opcode cannot satisfy it.

All controls are captured, and all behaved as declared **before** they were run:

| capture | shader | expect | result |
| --- | --- | --- | --- |
| `variant-manual-unroll-main-debug.txt` | reporter's workaround | `no-match` | no-match — 0 `OpLoopMerge` |
| `variant-trivial-main-debug.txt` | no loop at all | `no-match` | no-match |
| `variant-runtime-loop-main-debug.txt` | uniform trip count | `match` | match — 1 `OpLoopMerge` |
| `variant-minimal-nested-main-debug.txt` | minimal restatement of the repro | `match` | match — 2 |
| `variant-minimal-manual-main-debug.txt` | minimal restatement of the workaround | `no-match` | no-match — 0 |
| `variant-spirv-nonconst-main-debug.txt` | nested loops, uniform outer bound | `match` | match — 2 |

The first row is the one that matters: the predicate does **not** fire on the shape the
reporter calls "perfectly flat", and since that shader contains the same sampling loop as the
repro, its `no-match` also proves the surviving `OpLoopMerge`s in the repro belong to the
nested pair and not to the sampling loop.

## History — always reproduced, for as long as it is possible to check

`bisect --linear`, every stable release, not just the endpoints:

- **19 / 19 stable releases with a SPIR-V backend reproduce**, v1.5.2010 (2020-10) through
  v1.9.2607, with no clean release anywhere in the range.
- **v1.4.1907 cannot answer.** It exits 1 with `dxc failed : SPIR-V CodeGen not available.
  Please recompile with -DENABLE_SPIRV_CODEGEN=ON.`, correctly classified `invalid-probe`. The
  SPIR-V floor is therefore v1.5.2010, and "always reproduced" means *for as long as it is
  possible to check* — it does not extend back to the repository's first release.
- 5 prereleases (v1.5.2003, v1.8.2306-preview, v1.8.2405-mesh-nodes-preview, v1.10.2605.2,
  v1.10.2605.24) are outside the search by policy; the issue names none of them. 1 tag
  (v1.2.0-alpha) ships no usable `dxc`.

### The instrument was checked on every release, not only on `main`

Because the predicate reads a disassembler, a change in what that disassembler prints would
look exactly like a change in behaviour. `release-matrix.py` therefore replays the repro *and
all five controls* against each release binary and records the anchor clause separately from
the behavioural clause (`manual-case-release-matrix.txt`, generated, with every command echoed
via `subprocess.list2cmdline`). Result:

```
MATRIX-4486: PARSE-OK: every scored run was either SPIR-V disassembly or an explicit
             SPIR-V-unavailable diagnostic
MATRIX-4486: SELFTEST-PASS: every release agreed with the expectations declared above; the
             predicate discriminated the repro from the workaround on every build that has a
             SPIR-V backend
```

Every one of the 19 releases: anchor present, `OpLoopMerge` = 2 on the repro and 0 on the
workaround. v1.4.1907 fails the anchor on **all six** shaders, including the trivial one — the
`invalid-probe` is feature absence, not something peculiar to this repro.

v1.6.2104, the release the reporter used, is in the matrix and behaves identically to `main`.

## Why — corroborated from source, not inferred from output

s-perron's 2023-03-10 comment ("the loop unroller in spirv-tools ... cannot unroll a loop
unless it is an inner-most loop with a known upper bound") is confirmed in this tree:

- `external/SPIRV-Tools/source/opt/loop_unroller.cpp:1113`, inside `LoopUtils::CanPerformUnroll`:
  ```cpp
  // Can only unroll inner loops.
  if (!loop_->AreAllChildrenMarkedForRemoval()) {
    return false;
  }
  ```
  and, earlier in the same function, a bail-out when `FindNumberOfIterations` cannot evaluate
  the trip count.
- `external/SPIRV-Tools/source/opt/optimizer.cpp:203` shows `CreateLoopUnrollPass(true)` is in
  `RegisterPerformancePasses`, which `SpirvEmitter.cpp:16659` registers — so the pass does run
  on this module.

**Nesting alone is not the blocker, and this was measured rather than assumed.**
`control-nested-constbound.hlsl` is the same nest with the inner bound changed from
`4 - j - 1` to a constant `3`. It unrolls **completely**: zero `OpLoopMerge`, nine
`OpFOrdGreaterThan`, zero `OpBranchConditional`. So the unroller does handle a nest whose
inner loop it can remove first. What defeats this repro is the combination: the inner trip
count depends on the outer induction variable, so the inner loop's iteration count is not
computable, so it is never removed, so the outer loop never becomes inner-most either. Neither
level is ever eligible.

I predicted `match` for that control and was wrong — the declared expectation is corrected to
`no-match` in the capture, and the shader's header records the prediction, the measurement and
the correction rather than quietly agreeing with the result.

## The DXIL path, measured rather than repeated

pow2clk wrote "DXIL properly unrolls this loop". Measured with `match-dxil-unrolled.json`
(`all_of[ define void @PS_bright_pass\(\), NOT "Could not unroll loop" ]`):

- `variant-dxil-main-debug--match-dxil-unrolled.txt`: match. DXIL is emitted, no diagnostic,
  four `dx.op.sampleLevel` calls and five flatten-hinted branches with no back-edge.
- `variant-dxil-nonconst-main-debug--match-dxil-unrolled.txt`: no-match. The same nest with a
  uniform outer bound is a **hard error** on the DXIL path, once per loop —
  `control-nonconst-nested.hlsl:24:27: error: Could not unroll loop. Loop bound could not be
  deduced at compile time. Use [unroll(n)] to give an explicit count. Use '-HV 2016' to treat
  this as warning.` — exit `0x80004005`.
- `variant-dxil-nonconst-hv2016-main-debug--match-dxil-unrolled.txt`: no-match, and this is the
  control that isolates the absence clause — with `-HV 2016` the same message is a *warning*,
  so DXIL is emitted (clause 1 passes) while the token is present (clause 2 fails).

That third capture also settles the interpretation of clause 2: DXC's DXIL path never silently
drops an `[unroll]`, so "DXIL emitted and no such diagnostic" really does mean every `[unroll]`
was honoured.

**The contrast worth reporting:** `variant-spirv-nonconst-main-debug.txt` is the *same* shader
the DXIL path rejects outright, compiled with `-spirv`. It exits **0** with empty stderr and
two surviving loops. An `[unroll]` that cannot possibly be honoured is a hard error on one
back end and silent on the other.

## Assessment

Real, still-live, root cause understood and already stated in the thread by a maintainer. The
fix belongs in SPIRV-Tools' loop unroller (outer-loop unrolling, or iterating the pass to a
fixed point after inner loops are removed), not in DXC's SPIR-V emitter, which is doing the
right thing by emitting the `Unroll` loop control. s-perron closed the disposition question in
2024-08-23: "The maintainers will not be fixing this. If someone wants to make the change to
spirv-opt, we can help review the changes."

So there is nothing for triage to decide here. What this pass adds is: the issue is confirmed
current on `main` and on all 19 SPIR-V-capable stable releases; the failing condition is
narrower than "nested loops" (it is a dependent inner bound); and the silent acceptance of an
unsatisfiable `[unroll]` in the SPIR-V path is a separate, smaller, self-contained gap that
does not need outer-loop unrolling to fix.

Nothing here speaks to the reporter's hardware measurements (Mali/Adreno divergence, malioc
cycle counts, the 8x figure). Those need a GPU; no attempt was made to confirm or deny them.

## Labels

Now: `spirv`. Proposed additions, no removals:

- **`performance`** ("Optimizations for shader runtime speed or compile time") — the entire
  report is about generated-code quality and shader runtime cost.
- **`up-for-grabs`** ("Contributors welcome") — records the maintainer's own 2024-08-23
  invitation, and makes it findable by someone looking for work.

Whether `wont-fix` or `external` should also apply is a disposition question for a maintainer:
the change would have to land in SPIRV-Tools, but s-perron offered review. Not proposed here.

## Files

| file | what it is |
| --- | --- |
| `expected.md` | symptom, repro quality, predicate and every control's expectation, written before the compiler ran |
| `repro.hlsl`, `cmd.txt`, `match.json` | the repro, its exact command, the predicate |
| `out-main-debug.txt`, `out-v1.*.txt` | 20 primary probes: ground truth and 19 stable releases + v1.4.1907 |
| `control-*.hlsl`, `minimal-*.hlsl`, `variant-*.txt` | 8 controls and their captures |
| `match-dxil-unrolled.json` | the DXIL-arm predicate and its rationale |
| `release-matrix.py`, `manual-case-release-matrix.txt` | per-release instrument self-test and control replay |
| `manual-case-godbolt-verify.txt` | full text of all three Compiler Explorer panes |
| `method-notes.md` | observations about the method, for collation |
