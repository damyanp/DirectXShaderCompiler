# Method observations from #2528

For collation to promote or discard. Nothing here was acted on; `SKILL.md` and `scripts/`
were not touched.

## 1. A wrong-code predicate may need a second `cmd.txt` line, not a changed one

SKILL.md's guidance on `cmd.txt` is written around one invocation, and its warning about
flags is entirely about *removing* an inherited workaround (#3768's `-fcgl -Vd`). This issue
needed the opposite move: the as-filed command fails DXIL validation and therefore prints no
DXIL at all, so a predicate that inspects generated code has nothing to read. Adding a second
line — the same source with `-Vd` — put both the diagnostic and the module into one capture,
so the as-filed behaviour is still measured and the code is visible.

That seems like the general answer for **any wrong-code issue whose wrongness is caught by the
validator**: do not swap the command, append the instrumented one. Worth a sentence in step 3
or step 4, because the obvious alternative (replace `cmd.txt` with the `-Vd` form) quietly
destroys the evidence that the compile fails at all, and the other obvious alternative (put
`-Vd` only in a labelled variant) leaves `bisect` — which drives `cmd.txt` — unable to measure
the wrong-code claim across releases at all.

Two rough edges it exposed, neither harmful here:

- `godbolt` prints `warning: multi-invocation cmd.txt; linking the first only` and silently
  uses line 1 for CE args. Correct behaviour, but it means the default CE panes show the
  diagnostic and not the code; `--compilers "id:<args>"` overrides are then mandatory rather
  than optional. Possibly worth saying so where the warning is emitted.
- `audit`'s `cmd.txt` source-extraction takes the first `.hlsl` token per line and `break`s,
  so multi-line files work — but it is load-bearing and undocumented.

## 2. `--expect no-match` on a variant that demonstrates a *wider* bug reads as "clean"

The struct/varying case (`case-struct-varying.hlsl`) is the strongest evidence on this issue,
and under the primary `match.json` it scores `no-repro` — because `match.json` looks at output
element 0, which in that shader is the correctly-passed-through `SV_Position`. A capture
headed `# verdict: no-repro` sitting next to the repro is exactly the wrong signal for the
file that carries the finding.

Solved here by giving it its own predicate (`match-varying.json`) and running it with
`--match`, which produces `variant-struct-varying-main-debug--match-varying.txt` with
`# verdict: repro` / `# expect: match`. That works well and needed no tooling change, but the
combination `run --shader X --label Y --match Z` is not mentioned anywhere in SKILL.md — step
4 introduces extra predicates only for "the reported symptom differs from current behaviour",
and step 5 shows `--match` only on the primary probe. **A second predicate is also the right
tool for a second *shape* of the same defect**, and it is what keeps the evidence legible.

## 3. The Clang control worked exactly as SKILL.md predicts, on a new stage

Step 7 lists Clang stage support as compute complete / pixel front-end-only / geometry
unsupported. Vertex is not listed. Measured on CE: `hlsl_clang_trunk` cannot lower vertex
signature I/O either — a trivially valid `float4 main(float4 p : POSITION) : SV_Position`
gives `Unsupported intrinsic llvm.dx.load.input.v4f32 for DXIL lowering`, and only
`-fsyntax-only` gets a clean pane.

Separately, Clang's front end rejects `inout float4 pos : SV_Position` with
`attribute 'SV_Position' only applies to a field or parameter of type 'float/.../float4'` —
and the same error fires on the known-good control. Without the control this is a very
convincing false diagnosis; it is #1702's trap in a different stage. Suggest adding **vertex:
front end parses, backend cannot lower signature I/O** to the stage list, since that is now
measured, and it is captured in `manual-case-ce-clang.txt`.

## 4. Verifying a CE link needs more than `godbolt`'s summary line

SKILL.md already warns that `godbolt` records only the first line of each pane. On this issue
that warning was live: the `dxc_1_6_2112` pane's first line is
`warning: DXIL.dll not found. Resulting DXIL will not be signed...`, which says nothing, while
the finding — `error: Not all elements of output SV_Position were written.` — is three lines
down. "Open the link" is the current advice, but a human opening a link leaves nothing on
disk, which is the #3038 failure mode.

`ce-verify.py` in this issue directory re-compiles the *annotated* source with the *saved*
per-pane arguments and dumps every pane in full to `manual-case-ce-panes.txt`. It is ~30 lines
and reuses `triage.ce_compile`, so it cannot drift from what `godbolt` publishes. If collation
thinks it is generally useful, the natural home is `triage.py godbolt --verbose` or a
`godbolt --verify` that writes `manual-case-ce-panes.txt` automatically — the point being that
link verification should leave evidence, like every other check.

## 5. Small thing: `labels --issue N` prints an empty proposal

`python scripts/triage.py labels --issue 2528` prints `#2528 proposed + -` with nothing after
the `+` or `-`. It reads like a tool that failed. Presumably it just reflects that no proposal
has been recorded yet, but a line saying so would be clearer.

## 6. Possibly related issues — deliberately not claimed in the draft

Recorded here rather than in `comment.md`, per the brief; collation can check them.

- The silent half of this defect (a valid-DXIL shader with never-written output components)
  is the same *class* of observation as "undefined values reach the consumer with no
  diagnostic". If another issue in the backlog covers unwritten/undefined signature
  components generally, these may want cross-referencing. I have not looked, and this is a
  guess about the backlog, not a finding.
- `tools/clang/test/HLSLFileCheck/hlsl/functions/arguments/inout5.hlsl` and
  `tools/clang/test/CodeGenSPIRV/fn.param.inout.stage.hlsl` both use `inout` stage parameters
  but neither covers the partial-write case, so the issue's own `RUN:`/`CHECK:` block is
  still an unwritten regression test. That is a concrete, small piece of work if anyone wants
  it, but proposing work is not this skill's job so it is not in the draft.
