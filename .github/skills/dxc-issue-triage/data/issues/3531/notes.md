# 3531 — No debug info for locally-declared dynamic resources (SM 6.6)

**Verdict: reproduces, on every stable release that can express the feature.**

Ground truth: `main-debug`, self-reporting
`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`. That SHA is
a fork-local merge that resolves nowhere public; the compiler source is identical to upstream
`13730886e` (`git diff --name-only 13730886e HEAD` returns 0 files outside the triage skill
directory, against a control diff over an older SHA that does return compiler sources). Cite
`13730886e`.

## Repro

`repro.hlsl` is the issue body's snippet with one repair: as filed it writes through an
undeclared `floatRWUAV`, so it does not compile. The declaration added is
`RWBuffer<float> floatRWUAV : register(u0);`. Nothing else is changed — same entry point name,
same local names, same `256 + val &0xf` index expression.

```
-T cs_6_6 -E DynamicResources -Zi -Qembed_debug repro.hlsl
```

The profile and flags were chosen as the *oldest* set that still shows the symptom:
`ResourceDescriptorHeap` requires SM 6.6, and `-Zi` is what the claim is about.
`-Qembed_debug` only suppresses the "no output provided for debug" warning; `-Od` behaves
identically (`variant-od-main-debug.txt`), so the symptom is not an optimisation artefact.

The repair is measured, not assumed inert: `control-alldynamic.hlsl` removes the bound
resource entirely and writes back through the heap resource instead. It scores the same
(`variant-alldynamic-main-debug.txt`, `--expect match`).

## What ground truth does

Exit 0, valid DXIL, `Resource descriptor heap indexing` noted in the header. Debug metadata,
verbatim from `out-main-debug.txt`:

```llvm
%3 = call %dx.types.Handle @dx.op.createHandleFromHeap(i32 218, i32 %and, i1 false, i1 false), !dbg !48 ; line:15 col:59
!11 = !DIGlobalVariable(name: "DynamicBuffer", scope: !0, file: !1, line: 10, type: !12, isLocal: true, isDefinition: true)
!13 = !DIGlobalVariable(name: "floatRWUAV", linkageName: "\01?floatRWUAV@@3V?$RWBuffer@M@@A", scope: !0, file: !1, line: 8, type: !14, isLocal: false, isDefinition: true)
!42 = !DILocalVariable(tag: DW_TAG_auto_variable, name: "val", scope: !7, file: !1, line: 14, type: !43)
```

Three variable entries: the two file-scope declarations and the entry point's `uint val`.
Nothing for `DynamicallyIndexedDynamicBuffer`, exactly as reported. The handle built from it
*does* carry a `!dbg` location (`line:15 col:59`), so the source position survives; it is the
variable entry that does not.

## The predicate, and why it is shaped that way

The finding is an **absence**, which SKILL.md flags as satisfiable for free by a run that
failed for unrelated reasons — and, in the other direction, falsifiable for free by anything
that echoes the token. Both traps are live here, the second acutely: `-Zi` embeds the shader
source into `!dx.source.contents`, so the identifier `DynamicallyIndexedDynamicBuffer` appears
in **every** run. A `not_contains` on the bare name would have reported "never reproduced".

`match.json` is therefore `all_of` with four positive clauses and one absence clause:

| clause | purpose |
| --- | --- |
| `@dx\.op\.createHandleFromHeap` | the compile reached DXIL codegen and really used the heap; a rejected compile cannot emit it |
| the declaration text, read back out of `!dx.source.contents` | anti-vacuity: this run compiled a shader that actually declares the local dynamic resource |
| `!DILocalVariable(... name: "val")` | self-test: local-variable debug info **is** being emitted in this run |
| `!DIGlobalVariable(... name: "DynamicBuffer")` | self-test: debug info for a **dynamic** resource **is** emitted in this run when it is a global |
| `not_regex !DI(Local\|Global)Variable(... name: "DynamicallyIndexedDynamicBuffer")` | the symptom |

The two self-tests together pin the gap to exactly *local* × *resource*: in one and the same
run, a heap resource at file scope is named and an ordinary local is named, while the local
resource is not.

`match-localdbg.json` is the same detector with the two heap-specific clauses relaxed, so the
same instrument can be pointed at a locally-declared **bound** resource.

## Controls

| control | predicate | expect | result |
| --- | --- | --- | --- |
| `control-name-selftest.hlsl` — same name, same line, declared `uint` instead of a resource | `match.json` | `no-match` | **no-match**. `!48 = !DILocalVariable(tag: DW_TAG_auto_variable, name: "DynamicallyIndexedDynamicBuffer", scope: !7, file: !1, line: 15, type: !43)`. The absence clause can fail, and the emitter can name this identifier at this line |
| `control-heap.hlsl` — smallest SM 6.6 heap shader, no local resource | `match.json` | `no-match` | **no-match** (anti-vacuity clause fails, as designed). Used per release for feature presence |
| `control-alldynamic.hlsl` — the repair removed | `match.json` | `match` | **match** |
| `control-local-bound.hlsl` — local aliases a *bound* buffer | `match-localdbg.json` | `match` | **match** — see below |
| `repro.hlsl` at `-fcgl` | `match-localdbg.json` | `no-match` | **no-match** — see below |

## Two findings beyond "still reproduces"

**1. It is not specific to dynamic resources.** `control-local-bound.hlsl` is the same shader
with the local aliasing an ordinary `RWByteAddressBuffer : register(u1)`. It too gets no
`!DILocalVariable` — only the three file-scope/`val` entries appear
(`variant-local-bound-main-debug--match-localdbg.txt`). Dynamic resources are where it hurts,
because a heap resource has no binding for a tool to fall back on, but the missing metadata
covers locally-declared resources generally.

**2. The front end emits it; the DXIL pipeline drops it.** At `-fcgl`, which stops after
codegen, both the variable and its declare are present
(`variant-fcgl-main-debug--match-localdbg.txt`):

```llvm
call void @llvm.dbg.declare(metadata %struct.RWByteAddressBuffer* %DynamicallyIndexedDynamicBuffer, metadata !55, metadata !47), !dbg !56 ; var:"DynamicallyIndexedDynamicBuffer"
!55 = !DILocalVariable(tag: DW_TAG_auto_variable, name: "DynamicallyIndexedDynamicBuffer", scope: !7, file: !1, line: 15, type: !12)
```

So this is a loss during DXIL lowering, not a gap in `CGDebugInfo`, and `-Od` does not restore
it (`variant-od-main-debug.txt` carries the same three entries and the same absence) — i.e. it
happens in lowering that runs regardless of optimisation level. `val`, whose
alloca is promoted the same way, survives as an `llvm.dbg.value`. Local resource allocas are
promoted by `DxilPromoteLocalResources` (`lib/HLSL/DxilPromoteResourcePasses.cpp:100`), which
calls `PromoteMemToReg` on them; this triage did not isolate the exact pass that drops the
declare, and the pass name is offered as a starting point, not as a root cause.

## The artifact PIX reads

Everything above scores dxc's own disassembly. PIX reads the PDB, so `pdb-crosscheck.py`
compiles once with `-Fo` and disassembles the resulting container:
both outputs name exactly `['DynamicBuffer', 'floatRWUAV', 'val']`
(`manual-case-pdb-crosscheck.txt`). The instrument is looking at the same artifact a debugger
consumes.

## History

`bisect --linear` over all 20 stable releases (`--linear` because the filing date, 2021-03-02,
falls inside the release range, and endpoint agreement alone cannot exclude a mid-history
window):

```
v1.4.1907      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.5.2010      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.6.2104 .. v1.9.2607   repro   (18 releases, every one)
result: always-repro'd across v1.6.2104..v1.9.2607
```

Five probeable prereleases were excluded by policy (`v1.5.2003`, `v1.8.2306-preview`,
`v1.8.2405-mesh-nodes-preview`, `v1.10.2605.2`, `v1.10.2605.24`); the issue names none of
them. `v1.2.0-alpha` ships no usable `dxc`.

The two `n/a` results are confirmed genuine rather than assumed:
`manual-case-release-controls.txt` runs the feature-presence control on **every** release, and
v1.4.1907 and v1.5.2010 answer `error: invalid profile cs_6_6` to the smallest possible
heap shader as well as to the repro. They predate SM 6.6; trimming them is correct.

That matrix also runs `control-name-selftest.hlsl` per release, which is the check that makes
the absence meaningful release by release: **19 of 21 compilers tested (18 releases plus
ground truth) emit `!DILocalVariable(name: "DynamicallyIndexedDynamicBuffer")` when the local
is a plain `uint`.** So on every release where the repro compiled, that compiler demonstrably
*could* have named this variable and did not. The two that could not are the two that reject
`cs_6_6` outright.

The issue was filed 2021-03-02, before the first release that can run its repro (v1.6.2104,
2021-04-20) — the reporter was working against an unreleased compiler. "Always reproduced" here
means "on every stable release in which the feature exists".

## Compiler Explorer

https://godbolt.org/z/b11P9EvaG — `dxc_1_6_2112` and `dxc_trunk`, both exit 0, both showing
the same three debug-variable entries and none for the local resource
(`manual-case-godbolt-verify.txt`).

Two limitations stated in the banner rather than left for the reader to discover:

- CE appends `-Zi -Qembed_debug -Fc -` to every DXC pane. For this issue that would normally
  be disqualifying — a pane can show debug output a plain local run would not — but here the
  local command asks for the same flags on purpose, so the configurations agree. The pane's own
  `!dx.source.args` records the duplication and is the proof:
  `!23 = !{!"-E", !"DynamicResources", !"-T", !"cs_6_6", !"-Zi", !"-Qembed_debug", !"-Zi", !"-Qembed_debug"}`.
- The banner is compiled into the source, so pane line numbers are offset from the local
  captures (the entry point's local is at source line 15 locally, 30 on CE). The banner names
  no identifier that the note claims is missing, so no search hit it invites can come from the
  banner itself.

No Clang pane: `ResourceDescriptorHeap` is an SM 6.6 DXIL feature and the question here is the
content of DXC's DXIL debug metadata, which a Clang pane cannot answer.

## Labels

`bug` is correct and stays. Add **`debug info`** ("Related to debug info generation") — it is
precisely what the issue is about, and it is what makes this findable next to the other
debug-metadata work.

`PIX` was considered and rejected: its description is "Issues related to PIX passes", and the
defect is in the main lowering pipeline, not in `lib/DxilPIXPasses`. The reporter works on PIX;
the code does not.

## Assessment

Still valid, keep open. The report is accurate as written — the one nuance is that a `!dbg`
source location *is* emitted for the handle creation, so "no metadata at all" is about the
variable entry rather than about every trace of the declaration. That is not a staleness
finding: the text describes what the compiler does today, five years on.
