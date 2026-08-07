# #2633 — [SPIRV][Question] Link libraries

Filed 2020-01-07 by tomaszmi. Labels `enhancement`, `spirv`. 14 comments, last 2025-04-23.
Triaged against `main` at `ab5400907` (`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433)`).

## Question asked

Can HLSL be compiled into SPIR-V "libraries" that are linked later, the way `lib_6_x` +
`IDxcLinker` works for DXIL? Nobody in the thread ever answers it as two separable
halves, which is what it turns out to be.

## Verdict

**The export half exists and has since v1.6.2104. The import half does not exist on any
probeable release or on `main`.** Not a defect — a partially-implemented capability
request whose remaining half is blocked on a design decision, not on a bug.

| half | question | measured |
|---|---|---|
| export | can dxc *produce* a relocatable module? | **yes**, since v1.6.2104 |
| import | can dxc *consume* an unresolved symbol? | **no**, v1.5.2010 → v1.9.2607 → main |

### Export half — works

`export float4 foo(...)` with `-T lib_6_3 -spirv -fspv-target-env=universal1.5` emits

```
OpCapability Linkage
OpDecorate %foo LinkageAttributes "foo" Export
```

`universal1.5` is not optional: Vulkan target envs reject `Capability Linkage`, so the
module has to be linked before a driver will take it. That is the intended shape, not a
limitation.

Bisected with `match-export.json` (**inverted polarity**, see below): single clean
transition, absent at v1.5.2010 → present at v1.6.2104.

Attribution: commit `5ae95866e` / PR #3234 "[SPIRV] Add support hlsl export function
attribute" (2020-11-26). `git merge-base --is-ancestor` puts it inside v1.6.2104 and
outside v1.5.2010. The window is 268 commits, of which **exactly one** touches
`HLSLExportAttr` under `lib/SPIRV/` or `Capability::Linkage`. Strong, not proven — the
commit was not built. `--fixed-in` is deliberately left unset; this is not a fix.

Source anchors on `main`:
- `tools/clang/lib/SPIRV/DeclResultIdMapper.cpp:1824` — `decorateLinkage(..., LinkageType::Export)` for `HLSLExportAttr`
- `tools/clang/lib/SPIRV/CapabilityVisitor.cpp:411` — adds `Capability::Linkage`
- lit tests already assert it: `CodeGenSPIRV/fn.export.hlsl`, `fn.export.with.entrypoint.hlsl`, `lib.fn.export.with.entrypoint.hlsl`

### Import half — absent

```
repro.hlsl:27:21: error: found undefined function
```

`SpirvEmitter.cpp:3227`. Exit `0x80004005` — E_FAIL, an ordinary diagnosed error, **not
a crash**. There is **no `LinkageType::Import` call site anywhere in
`tools/clang/lib/SPIRV`**, so this is a genuinely unimplemented direction rather than a
path that misfires.

Diagnostic text unchanged since `04a526945` (2017-11-24, PR #847), so it is a stable
thing to grep for across the whole scan.

Invariant across 6 flag combinations (`manual-case-flag-matrix.txt`): default env;
`-fspv-target-env=universal1.5`; `+-fcgl`; `+-Vd`; `-T lib_6_6` (s-perron's own
profile); `-T lib_6_9`.

## History

`bisect --linear`, 21 release tags:

- **v1.4.1907** and **v1.5.2003** → `dxc failed : SPIR-V CodeGen not available.` →
  `invalid-probe`, not clean runs. The effective SPIR-V floor is **v1.5.2010**
  (2020-10-22).
- v1.5.2003 is the prerelease hole SKILL warns about for 2020-era issues; probed by
  hand, same answer.
- v1.5.2010 → v1.9.2607, 19 releases: import half repros on all of them.

**The floor postdates the report by nine months.** No shipped release binary from
January 2020 has SPIR-V codegen at all, so "did this ever work?" is unanswerable from
releases and was never in question anyway — the reporter was asking for something new.

## Has anything changed? (the actual point of this triage)

Checked, all captured in `manual-case-driver-cases.txt`:

| candidate | result |
|---|---|
| `-default-linkage external` | DXIL-only knob; SPIR-V module gets no linkage, fails `No OpEntryPoint instruction was found` |
| `dxc -link` on a `.spv` | `dxc failed : Invalid DXIL container.` |
| inline SPIR-V escape hatch | cannot express `LinkageAttributes`: `[[vk::ext_decorate]]` is `VariadicUnsignedArgument`, `[[vk::ext_decorate_string]]` is `VariadicStringArgument` (`Attr.td:1453,1470`); the decoration needs string **and** int. Empirically still `found undefined function` |
| `export` decl with no body | emits nothing — unused declarations are never registered → `No OpEntryPoint instruction was found` |
| SPIRV-Tools `spirv-link` | still documented "under development", but is target-env aware |

**And the one that matters: clang.** `hlsl_clang_trunk` compiles *both* halves at exit 0
with plain `-T lib_6_3 -spirv`:

```
OpDecorate %10 LinkageAttributes "_Z3fooDv4_f" Export     # definition
OpDecorate %13 LinkageAttributes "_Z3fooDv4_f" Import     # undefined declaration
```

That is the shape s-perron proposed in 2024, already emitted by the successor front end.
Two caveats stated in the comment: clang needs no `universal1.5`, and it uses Itanium
mangling where DXC uses the plain source name, so DXC and clang modules would not
resolve each other's symbols today. Controlled — the two clang panes differ only in
`-DIMPORT_HALF=1`, and the export half succeeds on *both* compilers, so the divergence
is isolated to the import half.

Not claimed: that clang "supports linking". What was measured is that it emits the
decorations. Whether a link then succeeds was not tested and CE cannot test it.

## Maintainer positions already in the thread

- **jaebaek, 2020-01-10** — "no relocatable code".
- **ehsannas, 2020-04-22** — three-step design; "spirv-link only works for OpenCL".
- **s-perron, 2024-07-26** — the current design position and the most useful thing in
  the thread: add `Import` to undefined functions, run `spirv-link` before the driver
  sees the module, Vulkan rejects the Linkage capability, plus unsolved problems around
  global variables and `lib_6_x` backwards compatibility; aligns with HLSL spec §8.8.

The 2020 answers are now partly out of date — "no relocatable code" is no longer true of
the export direction — which is why `--text-stale` is set. It is set narrowly: the 2020
comments, not s-perron's 2024 one, which still describes the situation accurately.

## Predicate polarity — read before comparing histories

- `match.json` — `contains "error: found undefined function"`. Positively anchored on a
  diagnostic, so an early/unrelated failure cannot satisfy it for free. `repro` = the
  capability is **absent**. Normal polarity.
- `match-export.json` — `contains "OpCapability Linkage"`, **deliberately inverted**.
  `repro` = the capability is **PRESENT**. `bisect` therefore prints
  `transitions at v1.6.2104 -> repro`, which reads like a regression and is the
  opposite: it is the feature *appearing*.

The natural spelling of the export predicate would have been
`not_contains "OpCapability Linkage"` — an absence predicate that every pre-v1.6 release
satisfies for free, and every *failed compile* satisfies for free too. Inverting it
removes both failure modes at once.

The export predicate also had to survive the #3092 echo trap: `OpCapability Linkage`
appears in two very different outputs — a successful disassembly, and dxc's own
validator echoing the instruction it just rejected under a Vulkan env
(`fatal error: generated SPIR-V is invalid: Capability Linkage is not allowed ...`
followed by `  OpCapability Linkage`). Controlled with
`variant-export-universal15 --expect match` for the clean shape.

## Controls

| control | purpose | result |
|---|---|---|
| `control-defined.hlsl` × 21 releases | is `found undefined function` a real measurement or a byproduct of a broken probe? | clean `no-repro` exit 0 on all 19 probeable releases; `invalid-probe` only at the two SPIR-V-less tags |
| `variant-export-universal15 --expect match` | export predicate reads a real module, not an error echo | match |
| `variant-inline-spirv-import --expect match` | no user-level workaround | match (still fails) |
| CE fold, both directions | `-DIMPORT_HALF` actually selects halves | export half: match under `match-export.json`, no-match under `match.json`; import half: match under `match.json` |
| clang export vs clang import panes | isolate the divergence | export succeeds on both compilers; only import diverges |

The `control-defined` expectation at v1.4.1907/v1.5.2003 was revised to `invalid-probe`
via `triage.py expect`, which is the sanctioned mechanism — not by editing results.

## Labels

Now: `enhancement`, `spirv`. Proposed add: **`question`**.

- `question` ("Question or inquiry") — the title literally says `[Question]` and the body
  asks whether a capability exists. 7 issues already carry `question`+`spirv`
  (#5076, #2108, #2056, #1393, #1379, #630, #459), so this is the house pattern.
- `enhancement` ("Feature suggestion") is the routing label for feature requests and is
  **already applied** — nothing to add there.
- **`shader-linking` deliberately rejected.** Its name is a perfect match and its usage
  is not: all 12 issues carrying it are DXIL linker bugs (#7635, #7486, #6889, #5739,
  #5737, #5736, #5721, #5704, …) and it has **never** been paired with `spirv`. Adding it
  would route a SPIR-V codegen request into the DXIL linker bucket. Textbook case of
  reading the description and the usage rather than the name.
- `check-in-clang` ("See if this repros in clang as well") — not proposed. It is an
  action item, and the action was performed; the result is in the comment.
- `hlsl-next` — not proposed. HLSL already specifies this (spec §8.8, per s-perron); the
  gap is in DXC's SPIR-V backend, not in the language version.

Recorded only. Not applied.

## Suggested action

`enhancement-not-bug`. Nothing here is broken. The remaining work is the design decision
s-perron laid out in 2024, and the comment says so without pre-empting it or implying a
timeline.

The genuinely useful outputs for a five-year-old question, in order:
1. Half of it already works and no one in the thread has said so.
2. Clang already emits both halves, including the `Import` shape being proposed.
3. The symbol-naming divergence between the two compilers is a concrete design input.

## Confidence: high

- Import half: 19 releases + `main`, 6 flag combinations, negative control on every
  release, and a source-level check that no `LinkageType::Import` call site exists.
- Export half: clean single transition, corroborated by upstream lit tests and by the
  source anchors.
- The one soft spot is PR attribution (`5ae95866e` not built at that commit), and the
  comment hedges it with "looks to be". Nothing else in the verdict depends on it.
