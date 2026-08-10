# #3927 — [SPIR-V] Not all unnecessary bindings are eliminated using SPIR-V backend

**Verdict: still reproduces, on every DXC release that has ever shipped a SPIR-V backend.**

Filed 2021-09-02 by `stil-t` (login verified via `gh issue view 3927 --json author`).
Ground truth: `main-debug`, `1.9.0.5433`, upstream commit `13730886e`.

## What was run

`cmd.txt`: `-T ps_6_0 -spirv repro.hlsl`

The reporter filed `dxc -T ps_6_0 -spirv test.hlsl -Fo test.spv` followed by
`spirv-dis test.spv` (`cmd-as-filed.txt`). **No workaround flags to question** — this issue
carries no `-fcgl` and no `-Vd`, so legalisation, optimisation and validation all run, at the
default optimisation level. The only deviation is dropping `-Fo`, which makes dxc disassemble
to stdout instead of writing a binary the predicate cannot read.

That deviation was measured rather than assumed. `check-fo-equivalence.py` compiles both ways
and parses the `.spv` header, `OpName` table and `Binding`/`DescriptorSet` decorations out of
the binary: same bound (36), same four decorations
(`manual-case-fo-equivalence.txt`). Dropping `-Fo` changes only where the module is written.

## The repro is the reporter's own case, not an approximation

`check-report-fidelity.py` extracts the disassembly quoted in the issue body straight out of
`issue.json` and compares it against `out-v1.6.2106.txt` — this triage's capture of
`repro.hlsl` on v1.6.2106, which is the `dxc_2021_07_01` the reporter says they used.
**64 lines, identical line for line** (`manual-case-report-fidelity.txt`). So every later
release probe is a probe of the reporter's instance.

## Symptom on ground truth (`out-main-debug.txt`, exit 0)

```
OpDecorate %Tex0 DescriptorSet 0
OpDecorate %Tex0 Binding 0
OpDecorate %SS0 DescriptorSet 0
OpDecorate %SS0 Binding 1
```

`%Tex1` and `%SS1` appear nowhere in the module — they are used only on the unreachable
`return`, and dead-resource elimination removes them. `%Tex0`/`%SS0` survive because the value
sampled from them feeds the `if` condition, and the branch is not folded even though both of
its targets end in `OpKill`. The last two blocks of the function are two `OpKill`s: nothing
the sample produces can reach an output.

## Predicate and controls

`match.json` is `all_of` of three positive regexes: `OpEntryPoint Fragment %main` (anchor),
`OpDecorate %Tex0 Binding`, `OpDecorate %SS0 Binding`. The anchor is not decoration — a probe
that emits nothing must not be able to satisfy a claim about module content, in either
direction.

| capture | what it establishes | declared | result |
| --- | --- | --- | --- |
| `variant-control-unused-main-debug.txt` | same shader with the `Tex0` sample and branch removed: `Tex0`/`SS0` are then genuinely unreferenced and **are** eliminated, leaving only `%Tex1 Binding 2` / `%SS1 Binding 3` | `no-match` | no-repro ✓ |
| `variant-control-hello-main-debug.txt` | a trivial `-spirv` shader compiles and does not match | `no-match` | no-repro ✓ |
| `variant-control-hello-v1.4.1907.txt` | that same trivial shader **also** fails on v1.4.1907 | `invalid-probe` | invalid-probe ✓ |
| `variant-control-hello-v1.5.2003.txt` | ditto on v1.5.2003 | `invalid-probe` | invalid-probe ✓ |
| `variant-O0-main-debug.txt` | at `-O0` all four resources keep bindings (0,1,2,3) | `match` | repro ✓ |

The first row is the control the symptom needs: it proves the predicate is not satisfied by
"any successful `-spirv` compile of a shader that declares `Tex0`", because elimination
demonstrably does happen when the resource is truly dead. The `-O0` row shows that *all* of
the elimination here is spirv-opt's, not the emitter's — which is why the primary probe uses
the reporter's default optimisation level, the level at which the optimiser removes one pair
and stops.

## History — linear scan over all 20 bisectable releases

`always-repro'd across v1.5.2010..v1.9.2607`. In the stable-release population, 19 score
`repro` and v1.4.1907 scores `invalid-probe`; ground truth also reproduces.

The filing names `dxc_2021_07_01`, not v1.5.2003. A separately measured
`v1.5.2003` prerelease is therefore supplemental evidence and is also an
invalid probe for the same cause:

```
dxc failed : SPIR-V CodeGen not available. Please recompile with -DENABLE_SPIRV_CODEGEN=ON.
```

- **v1.4.1907** — trimmed by `bisect` and counted as unprobeable in its final result.
- **v1.5.2003** — supplemental only under the prerelease policy: `out-v1.5.2003.txt`.

This is the trap the SPIR-V floor exists for. The predicate is content-based, so a build with
no SPIR-V code generator emits no `OpDecorate` at all and would score a clean `no-repro` —
manufacturing a regression at v1.5.2010 and licensing the claim "no release ever eliminated
these bindings". The `control-hello` captures close it: the same two releases reject
`float4 main() : SV_Target0 { return 1.0f; }` with the identical message, so the rejection is
the absent backend. Exit status is **1** with that message on the x64 `dxc.exe` of both
releases, not `0x80070057`.

Everything from v1.5.2010 (2020-10, the first release with a SPIR-V backend) onward
reproduces, including the v1.6.2106 the reporter used and today's `main`.

## What did change since 2021 — and it is not the symptom

Countable from the captures (`# verdict`, `; Bound:`, presence of `%gl_FragCoord` /
`OpLogicalAnd`):

| releases | module |
| --- | --- |
| v1.5.2010, v1.6.2104, v1.6.2106 | bound 35, unused `%gl_FragCoord` in `OpEntryPoint`, eager `OpLogicalAnd` |
| v1.6.2112 … v1.7.2212.1 | bound 33, `%gl_FragCoord` now eliminated |
| v1.7.2308 … v1.9.2607, `main` | bound 36, `&&` now short-circuited (extra `OpSelectionMerge` + `OpPhi`) |

So the module got *smaller* once (the unused `SV_Position` interface variable went away) and
then grew more control flow when `&&` became short-circuiting. The four lines this issue is
about are unchanged throughout.

## Source corroboration

DXC contributes no elimination logic of its own here — it hands the module to SPIRV-Tools:

- `SpirvEmitter::spirvToolsOptimize` (`tools/clang/lib/SPIRV/SpirvEmitter.cpp:16639`): with no
  `-Oconfig` it registers `RegisterPerformancePasses(...)`, then volatile-semantics and
  compact-ids.
- `SpirvEmitter::spirvToolsLegalize` (same file, `:16679`): `RegisterLegalizationPasses(...)`
  plus `CreateAggressiveDCEPass(...)` around the resource-flattening passes.
- The call site (`:985`) gates the optimiser on
  `theCompilerInstance.getCodeGenOpts().OptimizationLevel > 0`, which is exactly why the `-O0`
  variant keeps all four resources: at `-O0` `spirvToolsOptimize` is not called at all. So the
  emitter alone emits four bound resources, and everything eliminated at the default level was
  eliminated by SPIRV-Tools.

That is exactly consistent with `s-perron`'s 2024-08-22 comment placing the fix in spirv-opt:
a pass that recognises two branch targets as semantically identical and folds the branch.
Nothing in DXC's SPIR-V emitter would need to change.

The only related user-facing knob points the other way: `-fspv-preserve-bindings`
(`include/dxc/Support/HLSLOptions.td:445`) — "Preserves all bindings declared within the
module, even when those bindings are unused". Of the 28 `-fspv-*` / `-fvk-*` flags in the
SPIR-V option group, none asks for more aggressive elimination (`-fspv-preserve-interface` is
the other preserve; the `-fvk-*-shift` / `-fvk-bind-*` family assigns binding numbers).
Also noted from `variant-control-unused`: eliminated resources leave holes, they do not
renumber — `Tex1`/`SS1` keep bindings 2 and 3 after `Tex0`/`SS0` are removed.

## Assessment

The emitted module is **correct, just not minimal**. Nothing miscompiles; the cost is a
descriptor binding the application must still provide, plus an image sample and a branch that
execute for nothing. That makes this an optimisation-quality request rather than a
correctness bug, which matches how the maintainer answered it in 2024: not planned, but a
contributed fix would be accepted.

Nothing has moved since that answer. There is no decision waiting on anyone — the issue is
accurately reported, still true, and needs an implementer.

**Not marked `text-stale.`** The title and body still describe exactly what the compiler
does. The disassembly quoted in the body is from v1.6.2106 and differs from today's in two
incidental ways (see the table above), but it is presented as a 2021 observation and its
claim — `Tex1`/`SS1` eliminated, `Tex0`/`SS0` not — is still exactly right. "Old quoted
output" is not staleness.

## Labels

Now: `spirv`. Proposed additions:

- **`enhancement`** ("Feature suggestion") — the output is correct; this asks for a better
  optimisation. Nothing here is labelled `bug`, so this is a classification the issue is
  currently missing rather than a downgrade.
- **`up-for-grabs`** ("Contributors welcome") — this is the literal content of the maintainer
  comment: *"not currently in our plans, but we would accept a fix if someone else were to
  implement it."* Recording it as a label is what makes that discoverable to someone looking
  for work.

Considered and left off: `performance` ("Optimizations for shader runtime speed or compile
time") is defensible — the surviving sample and branch do execute — but the label reads as
being about the compiler's own speed, and a maintainer may prefer to scope it that way.
`external` was rejected: the fix does live in SPIRV-Tools, but the maintainers kept the issue
on DXC's tracker and offered to take a patch, so labelling it out of scope would misrepresent
their own answer. No removals — `spirv` is right.

## Limits of this triage

- CE runs Release Linux builds; both panes agree with the local Debug build, and this is a
  codegen-content issue rather than an assert, so the build flavour is not load-bearing.
- The scan probes released binaries only. It cannot say whether some unreleased window in
  between behaved differently, and no release is fine-grained enough to date a spirv-opt
  pipeline change to a commit.
- Only `ps_6_0` at the default optimisation level (plus one `-O0` variant) was tested. No
  claim is made about other stages, `-Oconfig` recipes, or `-fvk-*` binding overrides.
