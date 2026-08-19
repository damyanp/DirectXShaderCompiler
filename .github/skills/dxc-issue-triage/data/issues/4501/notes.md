# #4501 — [SPIR-V] Debug info should use DebugBuildIdentifier and DebugStoragePath with -Fd flag

* Issue: <https://github.com/microsoft/DirectXShaderCompiler/issues/4501>, filed 2022-06-03 by
  `baldurk`. Open. Label `spirv`. Milestone `Dormant`.
* Ground truth: `main-debug`, clean Debug build, upstream commit `13730886e`.
  `dxc --version` reports `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433
  (triage, ab5400907)`. The binary self-reports the fork-local merge `ab5400907`, which
  resolves nowhere public; the source it was built from is identical to `13730886e`, verified
  with a controlled diff:
  `git diff --name-only 13730886e HEAD` → 0 files outside
  `.github/skills/dxc-issue-triage/`, and the control `git diff --name-only 13730886e HEAD~40`
  → 85 files outside it, so the query can detect differences.
* Verdict: **repros** (the requested capability is still absent), history
  **never-implemented**, action **enhancement-not-bug**.

## What was asked for

Three separable asks, scored separately (`expected.md`):

| ask | status on `13730886e` |
| --- | --- |
| A — emit `DebugBuildIdentifier` (NonSemantic.Shader.DebugInfo.100 opcode 105) | not emitted |
| B — emit `DebugStoragePath` (opcode 106) | not emitted |
| P — `-Fd` usable with `-spirv` at all (the premise of A and B) | rejected outright |

## How it was measured

`cmd.txt`: `-T ps_6_0 -E main -spirv -fspv-debug=vulkan-with-source repro.hlsl`.
`-fspv-debug=vulkan-with-source` is the only DXC mode that emits the
`NonSemantic.Shader.DebugInfo.100` instruction set (`lib/DxcSupport/HLSLOptions.cpp`,
`debugInfoVulkan`; documented at `docs/SPIR-V.rst:629`), so it is the strongest form of the
question: if these instructions are emitted anywhere, they are emitted here.

`-Fd` is deliberately **not** in `cmd.txt`, because it produces no SPIR-V at all — see P below.

`match.json` is `all_of` of four clauses, and the first two are load-bearing rather than
decorative:

1. `contains OpExtInstImport "NonSemantic.Shader.DebugInfo.100"` — a module was produced and
   imports the instruction set the issue is about;
2. `regex OpExtInst\s+%\w+\s+%\w+\s+DebugCompilationUnit` — **instrument self-test**: this
   build emits, and this disassembler *names*, instructions from that set. Without it, the
   absence of a name in clauses 3–4 would be uninterpretable (the #3535/#3872 trap);
3. `not_regex DebugBuildIdentifier`;
4. `not_regex DebugStoragePath`.

`repro.hlsl` never spells either instruction name, because `vulkan-with-source` embeds the
shader text in the module and a mention would manufacture a hit in every run.

### Controls (all captured, all as declared)

| capture | command difference | expect | result |
| --- | --- | --- | --- |
| `variant-tokens-in-source-main-debug.txt` | source names both instructions in comments | `no-match` | `no-repro` ✔ |
| `variant-no-debug-flags-main-debug.txt` | `-spirv` with no debug flag | `no-match` | `no-repro` ✔ |
| `variant-fd-with-spirv-main-debug.txt` | adds `-Fd spirv-pdb\ -Fo out.spv` | `no-match` | `no-repro` ✔ |

The first proves the absence clauses can be falsified — they are not dead regexes. The second
and third prove the positive anchors are doing work. The third is the specific trap this issue
carries: `-spirv -Fd` exits 1 with **no SPIR-V whatsoever**, so a bare
`not_regex DebugBuildIdentifier` predicate would have scored it as a perfect reproduction
while measuring nothing. Its capture is 561 bytes and contains one line of stderr; anyone can
re-check that directly.

## Result on ground truth

Exit 0. The module imports `NonSemantic.Shader.DebugInfo.100` and carries **16 distinct
kinds** of debug instruction from it (`out-main-debug.txt`):

```
DebugCompilationUnit DebugEntryPoint DebugExpression DebugFunction
DebugFunctionDefinition DebugInlinedAt DebugLexicalBlock DebugLine
DebugLocalVariable DebugNoScope DebugScope DebugSource DebugTypeBasic
DebugTypeFunction DebugTypeVector DebugValue
```

Neither requested instruction is among them. Note `DebugEntryPoint` — opcode **107**, the
immediate neighbour of the two that are missing, added to the instruction set at the same
time. So this is a gap in what DXC emits, not a gap in the instruction set, in SPIRV-Headers,
or in the disassembler.

### P — `-Fd` with `-spirv`

```
$ dxc -T ps_6_0 -E main -spirv -fspv-debug=vulkan-with-source -Fd spirv-pdb\ -Fo out.spv repro.hlsl
[exit] 1
dxc failed : -Fd is not supported with -spirv
```

`OPT_Fd` is on the explicit reject list in `hasUnsupportedSpirvOption()`
(`lib/DxcSupport/HLSLOptions.cpp:360-378`), with a lit test at
`tools/clang/test/CodeGenSPIRV/spirv.opt.fd.hlsl`. That rejection was added by
`e80724a7a` ("[spirv] Fail when unsupported options are used (#4518)", 2022-06-20) —
**17 days after this issue was filed**, and it first shipped in v1.7.2207.

The release matrix dates the other side of that: on **v1.6.2112**, the release current when
the issue was filed, `-spirv -Fd` was accepted and then failed with
`Unable to find required part in blob` — dxc looking for a DXIL debug part in a SPIR-V blob.
So `-Fd` never worked for SPIR-V; it went from a confusing failure to an explicit diagnostic.

## Source corroboration

* `git grep DebugBuildIdentifier` and `git grep DebugStoragePath` over the whole DXC tree
  return **nothing** — no emitter, no enumerator, no test, no doc.
* The instruction kinds DXC can represent are the `IK_Debug*` values in
  `tools/clang/include/clang/SPIRV/SpirvInstruction.h`: 23 kinds, none of them these two.
* The emitter writes the extended-set opcodes it supports as numeric literals in
  `tools/clang/lib/SPIRV/EmitVisitor.cpp` — `102u` (`DebugSourceContinued`, line 1577),
  `103u` (`DebugLine`, line 408), `104u` (`DebugNoLine`, line 323). There is no `105u` or
  `106u` anywhere in `tools/clang/lib/SPIRV/`.
* The two instructions exist in the spec DXC vendors: `DebugBuildIdentifier` = 105 (operands
  `Identifier`, `Flags`) and `DebugStoragePath` = 106 (operand `Path`) in
  `external/SPIRV-Headers/include/spirv/unified1/extinst.nonsemantic.shader.debuginfo.100.grammar.json`
  (version 100, revision 6). They entered SPIRV-Headers on **2021-03-24** (`820d0ae`, "Add
  NonSemantic.Vulkan.DebugInfo.100 JSON/header"), i.e. over a year *before* this issue was
  filed. The specification is not the blocker.
* The consumer side exists too: SPIRV-Tools validates both
  (`source/val/validate_extensions.cpp:3725,3730`) and its aggressive-DCE pass has explicit
  `DebugBuildIdentifier` handling (`source/opt/aggressive_dead_code_elim_pass.cpp:772,1022`).
* `docs/SPIR-V.rst` documents `-fspv-debug=vulkan-with-source` (line 629) but says nothing
  about split/stripped debug info for SPIR-V, in either direction.
* Scoped observation, `tools/clang/lib/SPIRV/` only: the SPIR-V backend computes no hash of
  the module or its source. The only hash it emits is DXC's own git commit hash, via
  `OpModuleProcessed` (`SpirvEmitter.cpp:684-686`). The `Identifier` operand ask A needs has
  no existing producer in that backend. (This is an observation about what exists, not an
  estimate of what implementing it would cost.)

## History

`bisect --linear` over the full stable sequence, with **both** predicates:

| releases | primary `match.json` | instrument `match-instrument.json` |
| --- | --- | --- |
| v1.4.1907 | `invalid-probe` (`SPIR-V CodeGen not available`) | `invalid-probe` |
| v1.5.2010, v1.6.2104, v1.6.2106 | `invalid-probe` (`unknown SPIR-V debug info control parameter`) | `invalid-probe` |
| v1.6.2112 … v1.9.2607 (16 releases) | `repro` | `repro` |

The two scans are **identical**, and that is the finding: the apparent transition at v1.6.2112
is the *instrument* turning on, not the behaviour changing. Where the self-test flips and the
behavioural clauses do not, the release is unmeasurable, not clean.

`manual-case-release-matrix.txt` (generated by `measure-releases.py`, which echoes every
command via `subprocess.list2cmdline`) settles why, across **21 cached release binaries**
(20 stable + the v1.5.2003 prerelease), each run in six debug modes plus a `-Fd` probe and a
`--version` check — 168 invocations, 147 of them compiles:

* v1.4.1907 and v1.5.2003 produce no SPIR-V in any mode: `SPIR-V CodeGen not available`.
* v1.5.2010, v1.6.2104, v1.6.2106 accept `rich`/`rich-with-source`/`line`/`-Zi` and emit
  **`OpenCL.DebugInfo.100`**, not the NonSemantic set. They reject `-fspv-debug=vulkan*` with
  `unknown SPIR-V debug info control parameter: vulkan-with-source`. `OpenCL.DebugInfo.100`
  tops out at opcode **36** (`extinst.opencl.debuginfo.100.grammar.json`), so 105 and 106 do
  not exist in the only set those releases can emit — their silence is genuine feature
  absence, not an artifact of my repro.
* v1.6.2112 (2021-12-08) is the first stable release emitting `NonSemantic.Shader.DebugInfo.100`
  — 13 instruction kinds there, 16 today.
* Every one of the 21 binaries rejects `-Fd` with `-spirv`, with the wording splitting at
  v1.7.2207 as described above.
* `RESULT-4501: requested instructions seen anywhere: NO`, over all 147 compiles.

So: **never implemented**, across every stable release that can express the question — 16 of
them, v1.6.2112 (2021-12) through v1.9.2607 (2026-07) — and unmeasurable, not clean, in the
four older ones. Prereleases are outside the search by policy; v1.5.2003 was measured only by
the matrix and produces no SPIR-V either.

## Compiler Explorer

<https://godbolt.org/z/cj44aEcbj> — `dxc_1_6_2112` and `dxc_trunk`, both exit 0, both emit
NonSemantic debug info, neither emits either instruction (`manual-case-godbolt-verify.txt`:
0 occurrences of each token, 2 NonSemantic imports). The link was verified by reading back
`GET /api/shortlinkinfo/cj44aEcbj`: two panes, correct ids, correct arguments.

The banner in `godbolt-note.txt` deliberately refers to the instructions by **opcode number**,
never by name: the banner is prepended to the compiled source, and `vulkan-with-source` writes
the source into the module, so naming them would manufacture a hit in both panes.

CE limits that matter here: it cannot show P at all (it cannot pass `-Fd` usefully to a
rejected combination), and its oldest DXC is 1.6.2112, so it cannot date anything. The local
matrix covers both.

## Assessment

This is a **feature request that has never been implemented**, not a defect and not a
regression. The status field says `repros` only in the narrow sense that the requested
capability is still absent; nothing here is broken.

What has changed since 2022-06-03 is worth telling the reporter, because it changes the shape
of the ask rather than answering it: `-Fd` was accepted-then-failed at filing time and is now
a hard error with `-spirv`. So the request is not "add two instructions to the existing `-Fd`
path" — there is no `-Fd` path for SPIR-V to extend. It is "add split debug info to the SPIR-V
backend", with `DebugBuildIdentifier`/`DebugStoragePath` as the module-side half of that.

Nothing in the thread is stale: the body describes DXIL behaviour accurately, makes no claim
about what SPIR-V currently emits, and is 1 comment long. `text_stale` is not warranted.

## Labels

Current: `spirv`. Proposed additions:

* `enhancement` ("Feature suggestion") — nothing here is broken; the milestone `Dormant` is
  described as being for *defects*, which this is not.
* `debug info` ("Related to debug info generation") — makes it findable alongside the other
  debug-info work.

No removals: `spirv` is correct. I may be missing history from outside the thread — the issue
was routed to @greg-lunarg in 2022 and has been through three project/milestone moves since.
