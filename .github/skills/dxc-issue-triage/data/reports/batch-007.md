# DXC issue triage — batch 007

**Ground truth:** clean `main` **Debug** build, source-identical to upstream
`13730886e`. All five workers recorded the binary's exact version string before running:
`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`.
That fork-local SHA is captured evidence, not the public citation.
**History:** 20 official release binaries, v1.4.1907 → v1.9.2607 (four were absent from the
shared cache for #2918 — see that issue's findings).
**Nothing was posted, edited, labelled or closed. No DXC source was modified.**

> ### The ground-truth build still measures `main`, and that was checked rather than assumed
>
> The later provenance audit established that the binary's fork-local self-reported SHA and
> upstream `13730886e` differ only under this triage skill; compiler source is identical.
> `dxc --version` was also re-read, with no `-dirty`. Batches 005–007 therefore measured the
> same compiler and are directly comparable. Batches 001–004 measured `eff900d5` and are not.

> ### ⚠ The review gate is still suspended
>
> `SKILL.md`'s hard rule — *"Triage a handful of issues, then stop and let a human review before
> continuing. Verdict quality degrades silently"* — remains knowingly overridden. Batches 006–010
> run continuously at the maintainer's explicit request, with the per-batch email as an
> **asynchronous** checkpoint rather than a blocking one.
>
> The orchestrator's notes are blunt about what this costs, and collation agrees: **nothing in
> `audit`, `test_predicates.py` or the step-10 review checks whether a verdict is *true*.** They
> check that evidence exists and is self-consistent. Batch 006's collation introduced two
> markdown defects into `SKILL.md` and one falsification-adjacent quotation into a draft; both
> were caught by an independent human-side re-check, not by any gate. **The same class of defect
> recurred in this batch and was again caught by a human, not by a tool** — a draft quotation of
> @damyanp's June 2024 comment silently corrected a typo in the original ("How *for* off" →
> "far"), and was replaced with a paraphrase before collation began. That is two batches running
> in which the only thing that caught a quotation defect was a person.
>
> **Collation's read on whether quality slipped in batch 007: no, but the sample cannot support a
> strong claim either way.** Every verdict is reconstructible from `data/issues/<nnnn>/` — which
> is the one check the fresh-collation-session rule buys, and it passed for all five. The
> step-10 review found **three factual errors** across five drafts (batch 006 found nine), all of
> them quantifier scope creep rather than invented facts, and none changed a verdict. Against
> that: this batch produced the highest volume of *tooling* findings of any batch so far, which
> is what happens when you point the method at subsystems it has never touched — and one of
> those findings is that a `text_stale` value has already been silently lost from a committed
> artifact (see [method finding 12](#12-a-text_stale-finding-has-already-been-silently-lost-from-an-artifact-live-defect)).

## Headline

**One closable result, and it is the batch's most expensive finding.** #2918 — PIX numbering
pass fails with `/Od` — **does not reproduce** and was fixed between v1.5.2010 and v1.6.2104,
five and a half years ago. Nobody closed it. The issue's own repro is a `.pix` capture behind an
internal bug number and could not be obtained; the verdict rests on an **agent-constructed**
reconstruction built from the structural detail in the public dump (`column: 1`, no `inlinedAt:`,
lexical-block scope), which *positively* reproduces on v1.5.2010 and succeeds from v1.6.2104
onward. A reconstruction that merely failed everywhere would have been worth nothing.

**The measurement is sound; the commit attribution is not a bisect, and the draft says so.**
Per build, the harness runs three things: a **baseline** (same module, no passes — must succeed,
proving the module went in verifier-clean) and a **negative control** (same module with
`inlinedAt:` deleted from one lexical-block-scoped `!DILocation` — must fail). On `main` the
control still fails with `!dbg attachment points at wrong subprogram for function`, word for word
the assert in the 2020 report, which proves the check is **still live** rather than removed. That
is what makes "v1.9 does not fail" mean something. The attribution of the fix to `ac5630e8e`
(PR #3292, Jeff Noyle, 2020-12-03) is **source reasoning over a 268-commit window**, not a
bisect: three commits in that window touch `DxilDbgValueToDbgDeclare.cpp`, one replaces
`setDebugLoc(GetVariableLocation())` — a four-argument `DILocation::get` with a null `InlinedAt`
and a hard-coded `column: 1` — with the originating instruction's `DebugLoc`, and its message
independently describes the same failure. **Measured verdict, inferred commit.** Both the notes
and the draft carry that distinction verbatim.

**#3005 is `text_stale`, and the stale text is a maintainer's own standing question.** The PDB
defect is real, on `main` and on all 21 builds measured: `lib/DXIL/DxilPDB.cpp:132` computes
`SB.NumBlocks = 3 + m_NumBlocks + GetNumBlocks(SB.NumDirectoryBytes)` and never counts
`NumBlockAddrBlocks`, which line 216 writes — so `NumBlocks` is short by at least one and the
file's own stream directory addresses a block the superblock says does not exist. The comment at
line 63, directly above the field, states the invariant the code breaks. But the actionable
finding is the thread: **PR #5767 ("Fixes #3005", @adam-yang), opened 2023-09-21, was reviewed,
updated in November 2023, and closed unmerged on 2026-01-22 by an inactivity sweep** — verified
independently during collation (`mergedAt: null`). @damyanp's June 2024 question on the issue
about how close that PR was to landing was never answered. A reader arriving today, top-down,
concludes a fix is pending. It is not.

**The other three reproduce and none is closable.** #2673's `-D` defines are still duplicated in
`!dx.source.defines` on every release back to the bisection floor, with the mechanism visible in
source three lines below a fix precedent for the same defect on `-E`/`-T`. #3189's SPIR-V binding
behaviour is deliberate, has a maintainer's stated design position and a named implementation
route, and is `enhancement-not-bug`. #3305's two back ends still disagree about an empty payload,
and the DXIL diagnostic misnames its own cause.

**No batch has previously exercised any of these subsystems.** The PIX passes, the MSF/PDB
writer, SPIR-V descriptor binding and a DXIL-vs-SPIR-V disagreement are all first appearances,
which is why the method section below is the longest of any batch. That was the point of the
selection, and it worked — see [Sampling](#sampling-and-what-this-batch-cannot-conclude).

## Summary

| # | Title | Repro | Status | History | Action | CE |
| --- | --- | --- | --- | --- | --- | --- |
| [#2673](https://github.com/microsoft/DirectXShaderCompiler/issues/2673) | User command line defines are duplicated in debug info and in preprocessor | partial | **repros** | always; all 20 releases v1.4.1907→v1.9.2607, no invalid probes | keep open | [qa68hEf4z](https://godbolt.org/z/qa68hEf4z) |
| [#2918](https://github.com/microsoft/DirectXShaderCompiler/issues/2918) | PIX: Numbering pass fails with /Od when subroutines are used | agent-constructed | **does-not-repro** | **fixed in v1.6.2104** | **close-fixed** | [a4qPPYzvK](https://godbolt.org/z/a4qPPYzvK) |
| [#3005](https://github.com/microsoft/DirectXShaderCompiler/issues/3005) | Generated separate PDB files have possibly invalid header ⚠️ | complete | **repros** | always; 21 builds, measured by hand not by predicate | needs a decision | [s567x57P8](https://godbolt.org/z/s567x57P8) |
| [#3189](https://github.com/microsoft/DirectXShaderCompiler/issues/3189) | [SPIR-V] Descriptor bindings assigned before dead code elimination | complete | **repros** | always v1.5.2010+ (19 of 20; v1.4.1907 a genuine `invalid-probe`) | enhancement, not a bug | [48nqT9roE](https://godbolt.org/z/48nqT9roE) |
| [#3305](https://github.com/microsoft/DirectXShaderCompiler/issues/3305) | Empty Payload struct not recognized in DXIL | complete | **repros** | always; all 20 releases probed linearly, no invalid probes | needs a decision | [Pr3cfczY7](https://godbolt.org/z/Pr3cfczY7) |

Confidence is `high` on all five. **`text_stale` is set on #3005 only** — #2673, #3189 and #3305
each considered it explicitly and rejected it in writing, which is recorded because a field set
out of enthusiasm stops meaning anything. (#2918's issue text is not stale so much as *finished*;
`does-not-repro` already carries that.)

**Compiler Explorer: five links, zero skips.** Unlike batch 006 — where #2128 recorded a
`godbolt_skip` because its symptom was a compression ratio, not text — every issue here has a
published, annotated link, and all five were re-fetched during collation and return **HTTP 200**.
Two of them deserve a warning that a skip would have made louder:

- **#2918's link cannot show the failure at all**, for two independent reasons stated at the top
  of `godbolt-note.txt`: CE runs `dxc` only, and the failure is in a post-compile pass reached
  through `IDxcOptimizer::RunOptimizer`; and CE's oldest DXC is 1.6.2112, which already contains
  the fix. The link exists to show the `inlinedAt:` field whose absence *was* the bug. The
  worker considered `--skip` and judged an annotated link more useful than a blank.
- **#3005's link cannot show the defect either** — the symptom is four bytes at offset `0x28` of
  a file, and CE shows only stdout. Its `godbolt-note.txt` opens with
  `NOTHING IN THIS PANE SHOWS THE BUG, and that is the finding.` The pane's arguments also depart
  from local `cmd.txt` (plain `-Fd repro.pdb`, no `pdb/` subdirectory), recorded in `godbolt.txt`
  and explained in the note, because **CE's sandbox has no subdirectories**.

Drafts were written by `claude-opus-4.6` (#2673, #2918), `claude-opus-4.5` (#3189),
`claude-sonnet-4.6` (#3305) and one worker that could not self-identify its model (#3005 — see
[method finding 13](#13-the-triaged-by-field-still-cannot-be-filled-in-honestly-and-one-row-now-says-so)).
All five were reviewed by `gpt-5.6-sol`.

**Consistency check between `notes.md`, `verdict.json` and the DB: clean for batch 007.** Every
verdict row matches its notes; every claim in every draft was traceable to a committed artifact.
One inconsistency was found *outside* this batch and is reported below.

## Per-issue findings

### #2673 — the fix precedent is three lines above the bug

**Reproduces on every measurable build.** `repro.hlsl` is a byte-identical copy of DXC's own test
`tools/clang/test/HLSLFileCheck/dxil/debug/misc/share_mem_dbg.hlsl`, run with that file's own
`RUN:` line (lit substitutions expanded, the `| FileCheck` pipe dropped). Ground truth emits,
character for character, the node the reporter quoted in 2020:

```
!70 = !{!"DefineA=1", !"DefineB=0", !"DefineA=1", !"DefineB=0"}
```

The same capture shows the mechanism one layer up in `!dx.source.args`: the `-D` pair appears
once where it was typed and a second time appended after `-Qstrip_reflect`. So the duplication
happens in the **argument list**, before the preprocessor or debug info see it — which is exactly
what the issue *title* says and what its body only half-quotes.

**The predicate earns its keep, and one control is why.** `match.json` is a positive regex over a
metadata node definition holding **four or more** `Define` entries — two `-D` flags were passed,
so a correct compile yields two and cannot match. The decisive control is
`variant-onedefine-main-debug.txt`: a single `-DDefineA` produces `!{!"DefineA=1", !"DefineA=1"}`
— *still duplicated*, but only two entries, so the predicate stays silent. That is a duplication
the predicate must **not** match, which is what shows it counts occurrences rather than spotting
a string. It is also a second measurement: the duplication scales with the number of `-D` flags,
so it is a blanket re-application of the whole list.

**Source corroboration is the strong part.** `DxcContext::Compile` (`dxc.cpp:881-885`) hands
`IDxcCompiler::Compile` both the argv — which still holds the user's `-D` flags — *and*
`m_Opts.Defines`, which the option parser extracted from those same flags. `BuildArguments`
appends a fresh `-D <name>` per defines entry (`dxclibrary.cpp:506-508`). Immediately above,
the same function routes arguments through `AddArgumentsOptionallySkippingEntryAndTarget`, whose
comment reads *"This would lead to duplicate or even contradictory arguments in the arg list,
visible in debug information."* **The de-duplication already exists for `-E` and `-T`, and was
never extended to defines.**

**The reported configuration dependence still holds, and is now structural.**
`tools/clang/test/HLSLFileCheck/lit.local.cfg` sets `config.suffixes = []`, so the whole tree is
hidden from lit and run by TAEF instead; `FileCheckerTest.cpp:573-575` calls
`Compile(..., flags.data(), flags.size(), nullptr, 0, ...)` — defines in the arguments only. So
the file's own `// CHECK: !{!"DefineA=1", !"DefineB=0"}` passes while the driver path is broken.
The real distinction is not command-line-vs-API but **whether the caller supplies the defines
twice**. That statement is from source; no API-driven probe was run, and the draft says so.

Not cosmetic for tooling: this metadata is what `IDxcPdbUtils` reports as a compile's defines
(`dxcpdbutils.cpp:584`) and what the PIX/DIA surfaces read.

### #2918 — the only closable result, and the controls are the reason to believe it

Covered in the [Headline](#headline). Three things worth adding.

**The failing pass is not the one in the title.** Running only `-dxil-annotate-with-virtual-regs`
on v1.5.2010 succeeds; the failure is in `-dxil-dbg-value-to-dbg-declare`, which PIX runs first.

**`dxopt` throws the diagnosis away.** On a failing `RunOptimizer` it prints
`Operation failed - error code 0x80004005.`, exits 1, writes nothing to stderr and **discards the
text blob `RunOptimizer` returned** — where the verifier's message lives. True of the Debug build
too. The message text in `manual-case-history.txt` therefore comes from this repo's `opt.exe
-verify` run on the *control*, and is labelled as such; the pass/fail decision is always the
release's own `dxopt`. This is why the pre-registered predicate was `internal_failure`
(shape-based) rather than a text match: the observed shape on v1.5.2010 is an `E_FAIL` with **no
message at all**, which a text predicate would have scored `no-repro`.

**Coverage is 16 releases plus `main`, not 20.** v1.4.1907 has no
`dxil-dbg-value-to-dbg-declare` at all (`invalid-probe`), and four releases were absent from the
shared cache (v1.6.2112, v1.7.2308, v1.8.2502, v1.8.2505.1). All four postdate the transition,
which is bracketed by two releases that *were* probed, so the gap does not touch the finding —
but the draft's original "on every release" was corrected during the step-10 review, and so was
"every release got three runs" (v1.4.1907 got none).

### #3005 — the bug is six years old; the actionable finding is two years old

**The defect, stated in the form that needs no convention.** The reporter said "possibly invalid"
and hedged correctly; the stronger statement is that **the file's own stream directory addresses
a block the superblock says does not exist**. On `main`: 5632 bytes = 11 × 512-byte blocks,
`NumBlocks` = 10, and stream 5 (the DXIL container) occupies blocks 6–10.

**Checked against three readers rather than asserted**, and this analysis is why the verdict is
`needs-human-judgement` rather than a bare "still broken":

1. **LLVM accepts it.** `msf::validateSuperBlock` never compares `NumBlocks * BlockSize` to the
   file length; stream blocks are bounds-checked against the file size, not `NumBlocks`.
   `llvm-pdbutil` opens the file, exits 0 and reports `Number of blocks: 10` — propagating the
   wrong value. Measured, not read (`manual-case-llvm-pdbutil.txt`, which dumps the same PDB as
   written and with `NumBlocks` patched to 11; both accepted).
2. **Microsoft's reference MSF implementation would not.** In microsoft-pdb `PDB/msf/msf.cpp`,
   `NumBlocks` is `pnMac`; `extantPn(pn)` requires `pn < pnMac()` and `readPnOffCb` returns
   `FALSE` for a non-extant page in release builds too. DXC writes the container stream's last
   page *at* `pnMac`. **Source reading of the published reference implementation — msdia140/DIA
   was not executed**, and the notes say so.
3. **DXC's own reader never consults the field**, which is why `dxc -dumpbin` round-trips its own
   PDBs happily and why this went unnoticed for six years.

**The history was measured by reading bytes, not by the predicate**, on all 21 builds and both
`-Fd` spellings (42 rows, every one `PRESENT`). v1.5.2010 — closest to the reporter's
`1.5.0.2616` — reproduces the reporter's hex dump *exactly*: 5120 bytes, `NumBlocks = 9`,
`NumDirectoryBytes = 0x30`. That is the strongest available check that the repro is faithful.

> **Do not read this issue's `bisect` line as a symptom history.** `bisect --linear` reports
> `v1.4.1907 no-repro` and a "transition at v1.5.2010". That is entirely about the *precondition*
> predicate: v1.4.1907 writes the identically short `NumBlocks`, but its `dxc -dumpbin` cannot
> read a PDB (`error: Invalid bitcode signature`), so the second `cmd.txt` line fails. The bisect
> measured the age of a **dxc feature**, not the age of the bug.

Two distractors from the report, both dismissed on evidence: the `DXIL.dll not found` warning is
irrelevant (a signing build produces the identical header, and so does `-Vd`), and the trailing
slash on `-Fd` only changes the file's name.

### #3189 — the design question is already answered, in the thread

**Reproduces exactly as filed** on ground truth and on all 19 probeable releases. With the
reporter's reconstructed shift flags the used cbuffer `c` is decorated `Binding 2` while the two
unused cbuffers are fully DCE-eliminated — no `OpVariable`, `OpName` or `OpDecorate` for either.
**It is not shift-specific**: with a plain `-spirv` the same shader puts `c` at `Binding 4`.

**The mechanism is corroborated in source and then demonstrated.**
`decorateResourceBindings()` runs at `SpirvEmitter.cpp:840`; the module first reaches
`spirvToolsLegalize`/`spirvToolsOptimize` — where the unused variables are removed — at lines 972
and 988. `DeclResultIdMapper::decorateResourceBindings` walks `resourceVars` in declaration order
and consults nothing about liveness. `-O0` proves it in one run: `a`=0, `b`=1, `c`=2, all
present. `c` gets `Binding 2` either way; optimisation only deletes `a` and `b` afterwards.

**Not a defect to fix.** @s-perron stated the design position in 2024 — the default must not
change (users rely on an unused resource still consuming a binding so vertex and fragment layouts
match), and the route he would accept is an opt-in `spirv-opt` renumbering pass, which the SPIR-V
maintainers would review but not write. That objection is substantive: renumbering after DCE
makes a shader's binding layout depend on its own optimisation outcome, across two stages that
must agree. **DXC already ships a flag on this axis pointing the opposite way** —
`-fspv-preserve-bindings` (`HLSLOptions.cpp:1131`) keeps `a` and `b` in the module at bindings 0
and 1.

**Two documentation gaps are the cheap, unambiguous action.** `docs/SPIR-V.rst` describes implicit
assignment as *"next available binding number ... in the declaration order"* and never says a
resource removed by optimisation keeps its number, nor that this is intentional. And
`-fspv-preserve-bindings` — the one shipped flag controlling this interaction — **is not in the
Vulkan-specific options list at all**; only `-fspv-preserve-interface` is.

**v1.4.1907's `invalid-probe` needed a control, and this is the batch's sharpest trap.** The
recorded reason is `Unknown argument: '-fvk-auto-shift-bindings'` — a rejection of a flag *this
triage reconstructed*, not of the feature under test. Only the flag-free feature-presence control
produced `SPIR-V CodeGen not available` and settled it. See
[method finding 5](#5-an-invalid-probe-reason-can-be-true-and-still-not-be-the-real-reason).

### #3305 — DXC's two back ends disagree, and the DXIL message misnames its own cause

**Reproduces on all 20 releases and `main`, with the identical message at the identical source
location** — so this predates the 2020 report rather than having regressed into it. The SPIR-V
half of the *same* capture compiles on 19 of 20 (v1.4.1907 has no SPIR-V codegen). Putting both
invocations in one `cmd.txt` is what made a single `bisect --linear` yield both back ends'
history.

**The diagnostic is wrong about its own trigger.** The message says the shader must *include* an
inout payload structure parameter; the parameter is right there in the signature. What
`CGHLSLMS.cpp:2492` checks is `0 == funcProps->ShaderProps.Ray.payloadSizeInBytes`. Two
measurements pin it down:

- a payload whose only member is itself an empty struct gets the **identical** message, so the
  trigger is zero *size*, not literal emptiness of the outer struct;
- a **genuinely missing** payload parameter no longer produces this message. Measured for `miss`
  on v1.7.2212 vs v1.7.2308, either side of PR #5131 (`f90af4e15`, 2023-04), which moved that
  case to Sema. **The message used to be true and stopped being true in 2023**; today, for `miss`,
  the only input that reaches it is the one the words do not describe.

**Whether an empty payload *should* be legal is a language/product call, and the triage does not
pre-empt it.** The DXIL rejection is deliberate (`6e6f8dbd`, 2018, "Require
payload/attribute/param structs for ray shaders"), DXIL validation has no lower bound on payload
size so the rule lives entirely in the front end, and the zero-member `OpTypeStruct` passes DXC's
own spirv-val run. @damyanp's 2024-04-11 question about the motivating scenario is what this is
actually blocked on. **The diagnostic is separately fixable either way**, which is the part that
does not need the decision.

**`-fspv-target-env` is an instrument, not an inherited workaround.** SPIR-V raytracing is gated
on the target environment; a bare `-spirv` stops at that gate and never reaches the payload,
measured on `main` (`Vulkan 1.1 with SPIR-V 1.4 is required for Raytracing`) and on v1.5.2010
(`Vulkan 1.2 is required for Raytracing`). `vulkan1.2` is the spelling both ends accept —
v1.5.2010 rejects `vulkan1.1spirv1.4` outright.

## Cross-issue analysis

### Relationships

**No duplicates.** `duplicate-of` still has zero rows across 35 issues, and still correctly so.
The two nearest neighbours in this batch are related only by subsystem:

- **#2673 and #3005 both land on the PDB/debug-info surface**, from opposite ends: #2673 puts
  *wrong content* into a structurally valid artifact, #3005 puts correct content into a
  *structurally invalid* one. Neither causes the other, and no draft claims a link.
- **#2918 and #3005 both concern debug information that only a tool ever reads**, which is why
  both survived years: nothing in a build log, a CI check or a compiler-output diff notices
  either.

### A process pattern, now at two instances — and worth a standard step

**#3005's blocker is a review-complete pull request that an inactivity sweep closed.** PR #5767
was reviewed in September 2023, updated and format-clean in November 2023, and closed unmerged on
2026-01-22 with *"This PR was closed as it has not been updated in the last two years."* That is
the **same sweep** `SKILL.md` already records as having closed the `Fixes #2427` PR (batch 003).
Two triaged issues out of 35 whose only blocker is a swept, review-complete fix is not yet a
trend, but it is a shape worth testing for deliberately, because in both cases it **changed the
suggested action** — from "confirmed broken, keep open" to "a person must decide whether to
reopen the fix". #3005's worker proposes making `gh api repos/.../issues/<N>/timeline` a standard
step in the per-issue workflow rather than a hazard note. Collation agrees; see
[method finding 11](#11-checking-the-timeline-for-a-lapsed-fix-should-be-a-step-not-a-hazard-note).

### A diagnostic-quality shape that may be systematically under-labelled

#3305 is a **correctness-looking report that resolves to a diagnostic defect**: DXC does emit an
error, and the error describes a different input than the one that triggered it. #3189 is
adjacent — a report filed as a bug that resolves to a documentation gap plus a feature request.
Both suggest labels the backlog does not currently carry on them (`diagnostic`, `docs`). The
`diagnostic` label exists in the 58-label taxonomy; nothing in this batch was already carrying
it. Worth watching across 008–010 rather than claimed now on a sample of one.

### Patterns across the five verdicts

- **Four of five reproduce; the fifth was fixed in 2020 and never closed.** That ratio is a
  property of the sample, not the backlog.
- **All five predate their own bisection floor or sit within weeks of it.** "Always reproduced"
  means "for as long as it is possible to check" for every one of them.
- **Three of five needed evidence the harness cannot express** — #2918 (two-stage pass pipeline),
  #3005 (bytes in a file), and #3189 to a lesser degree (a second predicate for a second
  constant). That is the batch's defining statistic and the reason the method section is long.
- **Two of five had their `invalid-probe`/precondition results actively mislead**, in opposite
  directions: #3189's demotion reason was true but not the real reason; #3005's `bisect`
  transition was an artefact of a precondition, not a symptom history.

## Proposed label changes

None applied. All are proposals recorded in `verdict.json`.

| # | Current | Proposed additions | Warrant |
| --- | --- | --- | --- |
| #2673 | *(none)* | `bug`, `debug info` | Wrong content in `!dx.source.defines`/`!dx.source.args`. Deliberately **not** `correctness` — the generated DXIL is correct. |
| #2918 | *(none)* | `PIX`, `debug info`, `crash`, `bug` | All four fit the original report; the issue carries no labels at all. If it stays open rather than closing, `needs repro steps` is the accurate state. |
| #3005 | `bug`, `debug info` | *(no change)* | Both apt. **Not** `validation` — that label is DXIL validation and signing, which is a different thing that shares an English word. |
| #3189 | `spirv` | `enhancement`, `up-for-grabs`, `docs` | The reporter asks a question; the maintainer reframes it as an opt-in option and invites the implementation. `docs` for the two `SPIR-V.rst` gaps. |
| #3305 | `bug` | `diagnostic` | The message misnames its cause. **Not** `spirv` — settled in-thread in 2020; the SPIR-V path is the one that works. |

## What batch 007 taught us about the method

This is the longest such section in the effort so far, and that is the direct result of the
selection: four of the five issues touch subsystems no previous batch had exercised. Findings are
**reported, not implemented** — nothing in `scripts/` or `SKILL.md` was changed during this
collation.

### 1. No predicate kind can inspect a file the compiler writes — now confirmed twice, consecutively

**This is the batch's headline method finding, and #3005 hit it harder than #2331 did.** For
#3005 the file *is* the entire symptom; there is no text at all.

`_eval_match` (`scripts/triage.py:453`) takes exactly `(m, text, rc, timed_out, path)`, and every
leaf kind is a function of those values:

| kind | reads |
| --- | --- |
| `contains`, `not_contains`, `regex`, `not_regex` | `text` |
| `internal_failure` | `text`, `rc`, `timed_out` |
| `nonzero_exit` | `rc`, `timed_out` |
| `timeout` | `timed_out` |
| `any_of`, `all_of` | their children |

`text` is built in `cmd_run` (`triage.py:1036-1052`) by concatenating per-invocation
stdout/stderr. **The filesystem the compiler just wrote to is not an input to the predicate
system, at any level.** The strongest demonstration is committed as
`variant-compile-only-main-debug.txt`: the exact compile that produces the defective PDB —
**exit 0, empty stdout, empty stderr**.

What it costs, in order of severity:

1. The real evidence lives in `manual-case-msf-header-history.txt`, which `audit` cannot
   re-derive and `render_overview.py` cannot summarise. **If the bug were fixed tomorrow,
   `reindex` would re-run the predicate, get `repro`, and report the issue as still broken.** The
   self-checking property the whole harness exists for does not extend to this issue, and the
   failure is silent.
2. `match.json` has to assert something *other* than the symptom (see finding 2).
3. A reader of `overview.md` sees `repros` with no way to know it came from a precondition.

**#3005's worker proposes a `script` predicate kind, and the design is worth recording verbatim
because it is the cheapest general fix on the table.** One step in `cmd_run`, between the
invocation loop and `text = "\n".join(chunks)`: if `match.json` names a checker, run it in the
issue directory *after* the dxc commands and append its stdout to `text` as one more chunk. Then
every existing text predicate works unchanged:

```json
{"kind": "all_of", "value": [
  {"kind": "contains", "value": "; shader debug name: pdb/repro.pdb"},
  {"kind": "contains", "value": "SYMPTOM         : PRESENT"}
]}
```

Why this rather than a bespoke `file_bytes` kind: it reuses the whole predicate vocabulary with
no new matching semantics; the measurement lands **in the captured text**, where a human reviewer
reads it and `reindex` re-checks it (a boolean-returning `file_bytes` kind would leave the
capture just as silent as today); it generalises to any artifact symptom — container layout,
reflection blob, `-Fre` output, file size, file *absence*; and the checker stays committed beside
the repro and re-runnable, which is the existing evidence standard. Requirements it would have to
meet, learned the hard way here: run with `cwd` = the issue directory; run *after all* `cmd.txt`
lines (the artifact may be written by line 1 and read by line 2); keep its exit code **out** of
`worst_rc` so "symptom present" does not look like a compiler failure to `nonzero_exit` or to the
`invalid-probe` guard; and be **skipped, with the reason recorded**, when the compile failed —
otherwise a checker reading a *stale* artifact from a previous run produces a false `repro`.

That last one is not hypothetical: it is exactly why #3005's worker rejected a broken-shader
control, because `pdb/repro.pdb` survives from run to run. **Today `--shader` and `--args`
controls are unsafe on any artifact-producing repro for that reason**, and nothing warns you.

**Not implemented here.** It touches shared state mid-effort, and the right time is between
batches, not during one.

### 2. A predicate that asserts a *precondition* silently inverts what `# verdict: repro` means

Two issues in this batch produced this shape independently, which is what makes it a pattern
rather than a quirk.

- **#3005's `match.json` is a feature-presence control**, not a symptom test: it asserts that a
  separate PDB was requested, written and read back, so a compiler scoring `no-repro` is one
  where the measurement had nothing to measure. Both clauses are positive, so the absence-guard
  is satisfied honestly and the runner's absence-only warning correctly did not fire.
- **#2673's `match-defines-present.json` is an anchor**: it asks only whether a defines node
  carrying any `-D` entry was emitted, so a `no-repro` under the primary predicate can be told
  apart from a compile that emitted no debug info at all.

In both cases `# verdict: repro` in the captured output means *"the precondition held"*, not
*"the bug is present"* — and anyone re-reading the tree, including collation, meets a header that
reads backwards unless they open the predicate's `note` first. Both workers mitigated it in prose
(#3005's note opens `READ THIS BEFORE TRUSTING A repro VERDICT ON THIS ISSUE`), and prose in a
file nobody is required to open is a weak guard.

**Converging proposal from two independent workers: a machine-readable role marker** — `"role":
"anchor"` or `"asserts": "precondition"` — that makes the capture header say
`anchor-held`/`anchor-failed` and that `render_overview.py` can render as a flag. Recorded, not
implemented.

### 3. When the predicate is a precondition, `bisect` output becomes actively misleading

The sharpest instance in the effort so far. #3005's `bisect --linear` printed `v1.4.1907
no-repro` and "non-monotonic history, transitions at v1.5.2010". Read naively that says the bug
was **introduced in v1.5.2010**. It says nothing of the sort: v1.4.1907 exhibits the defect
identically, but its `dxc -dumpbin` cannot read a PDB, so the precondition fails. Nothing in the
tool's output could signal this.

The worker recorded it in a blockquote in `notes.md` and in the `history` field of
`verdict.json`, which is the right place — but it is worth noting that **the only reason a
future reader will not be misled is that one worker wrote a warning by hand.** A role marker
(finding 2) would let `bisect` refuse to report a transition at all when the predicate is
declared a precondition.

### 4. `cmd.txt` cannot express a multi-stage repro, and the PIX passes are unreachable without one

`cmd.txt`'s contract is one `dxc` invocation per line, executed as `<compiler exe> <args>`.
**#2918's symptom lives in a PIX DXIL pass, which runs after compilation through
`IDxcOptimizer::RunOptimizer` — a different executable over the *output* of the dxc line.** There
is no way to say that.

The consequence chain, all deliberate and all recorded:

- **No `match.json` was written**, so every capture is `unscored`. Writing an `internal_failure`
  predicate would have scored the *stage-1 compile*, which succeeds on every release **including
  the one that reproduces**, producing a confident and wrong "fixed at v1.4.1907" reading.
- **`bisect` is unusable**, so history was measured by `run-pix-passes.py --history` into
  `manual-case-history.txt`.
- `cmd.txt` still carries the stage-1 line so `run --issue` produces a real capture and `audit`
  sees `repro.hlsl` as covered; the file's comment block says what stage 2 is.

**This is the third issue in the workspace to need a hand-rolled harness** (after #2128 and
#3150). The pattern — `<harness>.py` plus `manual-case-<topic>.txt` with a
`# case:`/`# harness:`/`# why not triage.py bisect:`/`# ran:`/`# verdict: unscored` header — is
now well established and worked cleanly. **The gap is that nothing in `triage.py` knows those
files exist**, so `audit` cannot tell a well-evidenced manual case from an issue where nobody
measured anything. That is the same silent hole as finding 1, one layer out.

Also newly documented, and worth carrying: **the PIX passes are not reachable from a plain
`dxc file.hlsl` at all.** `-opt-enable`/`-opt-disable`/`/Odump` do not reach them either. The
three drivers are `IDxcOptimizer::RunOptimizer`, `dxopt.exe` and this repo's `opt.exe`. **Stage 1
must emit disassembly text** — a container written with `-Fo` carries a stripped DXIL part, so
`dxopt` on it sees no debug info and the defect is unreachable, a silent false negative.
**Releases ship no `dxopt.exe`**, only `dxc.exe`/`dxcompiler.dll`/`dxil.dll`, so probing an old
release means placing *this repo's* `dxopt.exe` beside *that release's* `dxcompiler.dll` and
letting DLL search order do the rest.

### 5. An `invalid-probe` reason can be true and still not be the real reason

`classify` stamps the **first** marker it matches, and argument rejection is checked by the same
regex as feature absence (`unknown argument`). #3189's `out-v1.4.1907.txt` records
`Unknown argument: '-fvk-auto-shift-bindings'` — a rejection of a flag **this triage
reconstructed**, not of SPIR-V codegen. The demotion is correct and the reason is misleading.

The generalisation is the useful part, and it is sharper than what `SKILL.md` currently says:
**whenever a repro carries flags the triage added rather than the reporter supplied, an
`invalid-probe` at the old end may be measuring the triage's own command line.** The existing
advice triggers on "an `invalid-probe` you did not expect" — here it *was* expected, just for the
wrong reason, **which is precisely when nobody runs the control.** #3189's worker ran it anyway
(`variant-no-shift-v1.4.1907--match-no-shift.txt`, flag-free, `--expect invalid-probe`) and got
`SPIR-V CodeGen not available`, which settled it.

### 6. A control that *passes* is not evidence that the checked behaviour is absent

#2918's first negative control deleted `inlinedAt:` from a `!DILocation` and **passed**, which
looked like the verifier check no longer existed. It does. `Verifier::visitDISubprogram`
(`lib/IR/Verifier.cpp:975-1000`) dedupes through a `Seen` set:

```cpp
DILocalScope *Scope = DL->getInlinedAtScope();
if (Scope && !Seen.insert(Scope).second) continue;
DISubprogram *SP = Scope ? Scope->getSubprogram() : nullptr;
if (SP && !Seen.insert(SP).second) continue;   // same node -> insert fails -> check SKIPPED
```

When the location's scope **is** a `DISubprogram`, `Scope` and `SP` are the same node, the second
insert fails, and `continue` skips the assert. A genuinely illegal `!dbg` is accepted, by
`opt -verify` and `dxopt` alike. The check only fires when the scope is a `DILexicalBlock` —
which is exactly the shape in the reporter's dump (`!965`).

**Generalisation worth promoting: pick a control's shape from the reported artefact, not from
what is convenient to edit.** And: a control that passes proves nothing until you have shown the
check can fire at all.

### 7. A control's expected result can be *release-dependent* — a third shape of control

`SKILL.md` documents negative and identity controls. #3305 found a third: a control whose
expected result **changes with the compiler under test**. `variant-noparam-*` was declared
`--expect no-match` on the reasoning that a genuinely-missing payload parameter produces a
different diagnostic. True on `main` and on v1.7.2308; **false before PR #5131**, where both
inputs produce the same message.

The `WARNING: control expected no-match but scored repro` is what surfaced the date of the
change, and `triage.py expect --expect match` was the right response, not a re-run. Nothing in
the tooling can express "no-match from v1.7.2308 onward, match before it"; the per-capture
`# expect:` line supports pinning it per capture only because the filename carries the compiler.
**When running the same control against several releases, expect the declarations to differ, and
treat a violated one as a date to investigate.**

### 8. `godbolt` verifies that a compile happened, not that the symptom is visible

Two independent workers hit this. `cmd_godbolt` compiles on CE and prints `exit=<rc>` plus the
**first non-empty line** of the pane (`triage.py:1569-1573`). For #2673 those lines were
`warning: DXIL.dll not found…` and `;` — neither says anything about the finding, which is one
metadata node inside 500+ lines of DXIL. So *"the link is verified before it is handed over"* is
only true for exit-code-shaped and first-line-shaped symptoms.

**The fix is small and uses code already present**: `ce_compile` returns the full text and
`classify(issue, text, rc, timed_out)` is the same scorer used for local probes. Scoring each
pane and printing `-> repro | no-repro` beside `exit=`, and writing the scored text to
`godbolt-<compiler>.txt`, would make the CE claim mechanical and `reindex`-checkable like every
other capture. #2673's worker worked around it with a per-issue `verify-godbolt.py` that imports
`triage` and re-runs `ce_compile` + `classify` — it works, but a per-issue script is exactly the
"control nobody can re-run" shape `SKILL.md` warns about. **It should be a flag.**

Three further CE limits, all newly documented:

- **`ce_args` reads only the first `cmd.txt` line.** Correct and documented, but for a
  two-invocation repro it is exactly wrong: #3005's second stage is where all the interesting
  output is, and **#3305's whole finding *is* the difference between line 1 and line 2**. #3305
  worked around it with `--compilers "dxc_trunk,dxc_trunk:<line 2 args>"`, written by hand from a
  file the tool had already read. Proposal: offer one pane per invocation by default, or at least
  print the other lines' CE-form arguments.
- **CE's sandbox has no subdirectories.** #3005's local `cmd.txt` writes to `pdb/`; CE returned
  `No such file or directory pdb/a.dxbc` and, on `dxc_1_6_2112`, `exit=139` (SIGSEGV) rather than
  a clean diagnostic. Publishing that link unexamined would have been a wrong result presented as
  evidence. (That `-Fo` into a nonexistent directory makes dxc 1.6.2112 crash rather than
  diagnose may be worth an issue of its own; it is out of scope and appears in no draft.)
- **Two whole classes of defect cannot appear on CE at all**: anything in a post-compile pass
  driven through `IDxcOptimizer` (all of `lib/DxilPIXPasses/`), and anything whose symptom is
  bytes in a written artifact. Add the existing floor — CE's oldest DXC is `dxc_1_6_2112`, so
  anything fixed before 2021-12 can only ever be shown post-fix.

### 9. `cmd.txt` is split with POSIX `shlex`, which silently deletes backslashes on Windows

`triage.py:1039` — `subprocess.run([exe] + shlex.split(line), ...)`. `shlex.split` defaults to
POSIX mode, where a backslash is an escape character. Verified directly:

```
>>> shlex.split(r'-Fd pdb\repro.pdb -Fo pdb\a.dxbc')
['-Fd', 'pdbrepro.pdb', '-Fo', 'pdba.dxbc']
```

**There is no warning.** dxc is handed a different path than `cmd.txt` reads as saying, and it
succeeds, writing to the wrong place. Every artifact-producing repro on Windows is exposed, and
so is anything using `-I`, `-Fh`, `-Fe`, `-Fre`, or an `#include` path. `ce_args`
(`triage.py:1444`) uses the same `shlex.split`, so a CE link built from a backslash `cmd.txt`
would be silently wrong in the same way. Worked around here with forward slashes. Cheapest fix:
`posix=False` on Windows, or at minimum a warning when a token contains a backslash.

### 10. PowerShell damaged a native *argument*, not just prose — and it read like a real result

`SKILL.md` warns that PowerShell eats `$` and backticks out of prose. #3305 found the same class
landing on an argument, and the failure mode is worse:

```
& $exe -T lib_6_3 -spirv -fspv-target-env=vulkan1.2 repro.hlsl
  -> error: unknown SPIR-V target environment 'vulkan1'
& $exe -T lib_6_3 -spirv '-fspv-target-env=vulkan1.2' repro.hlsl
  -> compiles
```

Same shell, same binary, one pair of quotes apart. **`unknown SPIR-V target environment` reads
exactly like a genuine feature-absence result** and would have been recorded as one; it cost a
wrong provisional conclusion ("v1.5.2010 cannot express any target environment") that only
unravelled on a re-run. `triage.py` itself is immune — it `shlex.split`s and passes a list — so
this only bites hand-run exploration, which is precisely where the guard rails are absent.
**Proposed promotion: extend the step-5 warning from prose to arguments, and say the fix is to
single-quote every argument containing `=` or `.`, not just those containing `$`.**

### 11. Checking the timeline for a lapsed fix should be a step, not a hazard note

`gh api repos/microsoft/DirectXShaderCompiler/issues/<N>/timeline` is what found PR #5767 for
#3005, and it **changed the suggested action**. It is now the second issue in the effort whose
only blocker is a swept, review-complete PR. Cheap, one call, and it is the difference between
"confirmed broken, keep open" and "a person must decide whether to reopen the fix".

One tooling nit worth writing down because it cost a round trip: **`gh pr view --json merged` is
rejected**; the field is `mergedAt`.

### 12. A `text_stale` finding has already been silently lost from an artifact (live defect)

Found during collation, **outside this batch, and not repaired here.** The working tree carries an
uncommitted modification to `data/issues/8737/verdict.json` that **deletes its `text_stale`
field**:

```diff
-  "text_stale": "Title says 'silent UB or ICE'; understates it. The silent case emits a DXIL
-   atomic with i32 undef where the sample index belongs, and that container passes validation.",
```

`triage.db` still holds the value, so `overview.md` still renders the finding today — **but
`reindex` rebuilds the DB from the committed `verdict.json` files, so the next `reindex` will
drop it, and `overview.md` will then silently stop reporting a batch-004 stale-text finding.**
`audit` does not catch this, because the artifact is internally consistent without the field.

Collation deliberately did **not** restore it: it belongs to another batch, changing another
batch's recorded verdict without re-reading its evidence is exactly the kind of unreviewed edit
this workflow exists to avoid, and the orchestrator commits. The exact text to restore is quoted
above and is recoverable with
`python scripts/triage.py sql "SELECT text_stale FROM issues WHERE number=8737"` **for as long as
nobody runs `reindex` first.** That ordering constraint is the actual hazard.

Generalisable finding: **`verdict.json` is hand-editable and `audit` has no notion of a field
that used to be there.** If `text_stale` is the highest-value output of this effort, it is
currently the least protected.

### 13. The `triaged-by` field still cannot be filled in honestly, and one row now says so

Nothing in the environment identifies the model — `COPILOT_CLI_BINARY_VERSION` is available, a
model id is not. #3005's worker refused to guess and recorded
`GitHub Copilot CLI 1.0.79-2 (model not self-identifiable)`. Every other row across seven batches
carries a specific model name, **which means some of them were guessed.** `SKILL.md` says
verdicts are weighed by which model produced them; a field that cannot be filled in reliably
cannot carry that weight. **The harness should supply it rather than asking the agent to
introspect.** Recorded as-is rather than back-filled, because an honest gap is more useful than a
plausible fabrication.

### 14. `audit --issue` returns early before a verdict exists, so a clean audit means nothing

`audit_issue` returns early when `verdict.json` does not exist, so `audit --issue 2918` reported
"no missing evidence" while `notes.md`, `comment.md` and the verdict were **all still absent**.
The natural worker instinct is to run `audit` as an "am I done yet?" check, and before the
verdict is written it answers a different question. Worth one explicit line in the skill.

### 15. Two cheap corroborators that earned their place

- **`-O0` for any "X happens before Y" claim.** #3189 proved that binding numbers are assigned
  before DCE in **one run**: at `-O0` the eliminated cbuffers are still present holding bindings
  0 and 1, and the used one has the same number either way. That is stronger than reading the
  emitter and took one command. Worth listing beside "corroborate from source" in step 11.
- **Read the test harness; do not run it.** #2673's obvious corroboration — run lit on
  `share_mem_dbg.hlsl` — writes `Output/` directories into the DXC tree, violating the worker
  boundary. Reading `lit.local.cfg` (`config.suffixes = []`, so lit never runs it) and
  `FileCheckerTest.cpp:573-575` (`nullptr, 0` for defines) answered the same question **more
  precisely**. When an issue's claim is about a *test harness*, read the harness.

Also from #2673, a quieter face of the step-3 `RUN:`-line warning: **`%dxc` is a substitution and
is free to add flags.** This test's `CHECK` line expects `-Qembed_debug` in `!dx.source.args`,
which looks exactly like `%dxc` adding it. It does not (`lit.cfg:294` substitutes the bare
binary) — dxc adds it itself. Worth one grep before treating a RUN line as a command.

### 16. Working with a repro that must never be obtained

#2918's repro is a private customer shader behind an internal bug number. It was treated as a hard
stop: not searched for, not asked after, nothing derived from it beyond the public dump already in
the issue text. Two things made the substitute honest rather than decorative:

- the reconstruction is **named as one every time it is mentioned** — in `repro.hlsl`'s header, in
  `godbolt-note.txt`, in `notes.md` and in `comment.md`;
- it is only load-bearing because it **positively reproduces** on v1.5.2010. A reconstruction that
  merely failed everywhere would have been worth very little, and the honest verdict would then
  have been `needs-repro-from-reporter`.

**The deciding factor was not cleverness in building the shader.** It was that the public dump
contained enough *structural* detail — a hard-coded column, a missing field — to identify the code
that produced it. **When a dump has that, a reconstruction is checkable; when it has only a
message, it is not.** That is the rule worth promoting into the "unavailable repro" guidance.

### 17. Smaller measured defects and conventions

- **One release crashes on a deliberately-broken control.** v1.6.2106 exits `3221226505`
  (`0xC0000409`, STATUS_STACK_BUFFER_OVERRUN) on #2918's broken-metadata control where every other
  release returns `E_FAIL`. Harmless — the requirement is "must fail" and a crash is a failure —
  but a control asserting a *specific* exit code would have flagged it as a broken probe.
  `internal_failure`-shaped requirements should stay shape-based.
- **`report_fatal_error` becomes `hlsl::Exception(DXC_E_LLVM_FATAL_ERROR = 0x80AA001B)`**
  (`ErrorHandling.cpp:117`), but the HRESULT reaching `dxopt` is plain `E_FAIL` `0x80004005`. **Do
  not key anything on the specific code.**
- **`cmd.txt` comments must start at column 0.** The filter is `not ln.startswith("#")`
  (`triage.py:1019`) applied to the raw line, while the same expression `.strip()`s for emptiness.
  An indented `#` comment is passed to dxc as arguments.
- **git cannot store an empty directory and dxc will not create the `-Fd` parent**, so an
  artifact repro needs a committed placeholder. `pdb/.gitignore` with `*` and `!.gitignore` works
  and should be the documented convention if artifact repros become common.
- **`godbolt`'s `id:<args>` override accepts a duplicate compiler id with different arguments**,
  which is what made #3189's three-pane SPIR-V/DXIL contrast possible in one link. Undocumented in
  `SKILL.md`, working, and used by three of the five links in this batch.
- **A "different number" defect needs two predicates, and `--label` + `--match` composes fine.**
  #3189's `match-no-shift.json` is the same structure with a different constant, filed as
  `variant-no-shift-<compiler>--match-no-shift.txt`. `SKILL.md`'s second-predicate discussion is
  written entirely around crash-vs-hang disjunctions; **"same defect, different constant" is a
  distinct and simpler shape.** Related: when the reporter's flags are *arithmetic* rather than
  phase-disabling (`-fcgl`, `-Vd`), the right move is a second predicate, **not** a substitution.
- **A capture with two invocations pays off, and the header format already supports it.** #3305's
  `out-*.txt` keeps a `$ dxc <line>` / `[exit]` block per invocation, so one `bisect --linear`
  gave both back ends' history. The requirement is that the predicate be **positive and specific
  to one invocation's output** — an absence clause, or a clause about the other invocation, would
  have made every pre-SPIR-V release an `invalid-probe` and thrown away a valid DXIL result.
- **`bisect --linear` is cheap on a warm cache.** #3189 scanned 20 releases in well under a
  minute. The "costs one run per release" caveat may be over-stated in practice; `--linear` was
  chosen defensively on three of five issues this batch and cost nothing measurable.
- **The `releases` table has no `sort_key` column** — ordering is by `build_date`. Minor, but the
  `status`/`sql` examples in `SKILL.md` never show the releases schema.

### 18. The `batch` column is inconsistent, and both renderers cope

`triage.db` holds a mix of conventions across seven batches: `batch-001`, `002`, `003`,
`batch-004`, `005`, `006`, `007`. **Checked rather than assumed, and both consumers normalise
correctly:**

- `render_overview.batch_label()` strips non-digits and zero-pads, so all seven group and sort as
  `001`…`007`, and the per-issue `<sub>batch NNN</sub>` lines and the footer links are consistent.
- `render_comments.normalise()` accepts `7`, `007` and `batch-007` and queries all forms.

So this is a cosmetic wart, not a defect, and the historical rows were deliberately **not**
rewritten — a mass edit of committed verdicts to fix formatting is exactly the unreviewed change
this workflow avoids. **Recorded so the next collation does not re-discover it.** If it is ever
normalised, do it in one commit that touches nothing but that field, and re-run `reindex` and both
renderers.

### 19. What the step-10 review changed, and what was rejected

Reviewer: `gpt-5.6-sol`, one pass over all five drafts with the evidence directories, briefed that
concision was the primary criterion and that specific technical evidence and stale-text findings
were off-limits to cut. **Three factual errors, four accepted concision rewrites, three rejected
or narrowed.** All accepted rewrites were re-read against the evidence before applying, per
`SKILL.md`'s "check the review in both directions".

**Accepted — the factual errors, and they are all the same shape.** Every one is a quantifier
reaching past what was measured, which is the class `SKILL.md` predicts and the class this
reviewer keeps finding:

| # | Was | Now | Why |
| --- | --- | --- | --- |
| #2918 | "run the PIX passes over it on **every release**" | "on every release **available here**" | v1.4.1907 lacks the pass and four releases were absent from the cache: 16 releases + `main`, not 20. |
| #2918 | "**every release** got three runs" … "Both held on **every build**" | "every **measured** build" … "on every **measured** build" | v1.4.1907 got none of the three; `manual-case-history.txt` records `n/a n/a n/a` for it. |
| #3305 | "needs an explicit target environment **on any DXC**" | "on `main` and on v1.5.2010 alike" | Two endpoints were measured, not twenty. **The reviewer proposed narrowing to `main` only, which under-states it** — `cmd-as-filed.txt` records the v1.5.2010 measurement too, in a different spelling. Corrected to the measured endpoints rather than to the reviewer's narrower claim. |

**Accepted — concision and speculative claims:**

- #3005, "that silence is why this survived six years" → cut. A causal claim the evidence does not
  reach; the silence itself is observed and stays.
- #3005, "There is a sharper way to say it that doesn't depend on any convention about what
  `NumBlocks` ought to mean" → "Stated without relying on any convention…". Metacommentary about
  the sentence, removed; the sentence kept.
- #3305, "so that path is not accidentally lenient either" → cut. Validator acceptance is
  observed; whether it is *accidental* is an inference about intent.
- #3305, "That part looks separable from the design question" → cut. The preceding sentence
  already establishes separability by construction.
- #3189, "Documenting both … would likely prevent this being re-filed" → "Both belong where the
  shift options are described." Same action, no prediction.
- #2673 and #3189, general tightening of two long paragraphs with every citation retained.
- #2918, "Caveats, plainly." → "Caveats." and "the ask is small and" → cut. Flourish and effort
  claim.

**Rejected, and the reasons matter more than the rejections:**

1. **#3005 — "a reader arriving today would reasonably assume a fix is pending" → "is now
   stale".** Rejected. That clause **is** the `text_stale` finding: it states the *harm* of the
   standing comment, which is the whole reason the field exists. The reviewer read it as
   speculation about a hypothetical reader. This is the documented failure mode of *"it will read
   a caveat aimed at future readers as an accusation"*, in a new dress: **it reads the definition
   of stale-text harm as mind-reading.** Off-limits by the brief; kept verbatim.
2. **#2918 — cut "nothing private needs to leave Microsoft" and the pointer to @damyanp's 2024
   comment from the closing ask.** Rejected as `SKILL.md`'s "it cuts *actionable* caveats". The
   privacy assurance is the direct answer to why the repro was unobtainable in the first place,
   and the @damyanp pointer is the close path a maintainer would actually take. Only "the ask is
   small" — an effort claim — was cut.
3. **#2673 — cut "the defines have been duplicated for as long as it is possible to check"** as
   "unsupported maximalism". Rejected: it is the **bound**, not a claim beyond it, and it is the
   house phrasing `overview.md` uses for the bisection floor. Kept, but shortened ("The oldest
   release with a usable `dxc` predates this report" → "v1.4.1907 predates this report").
4. **#3189 — demote the bolded "all three panes compile successfully" to a trailing clause.**
   Rejected on prominence. `notes.md` records that the bold exists because *"a reader seeing exit
   0 would otherwise conclude nothing is wrong"* — this is a wrong-number issue and the warning
   has to arrive before the reader draws the wrong conclusion. The surrounding sentence was
   shortened instead.
5. **Five house-style inconsistencies** (heading level, bold-vs-plain status openings, four
   different label-section forms, second person in #3005 vs first-person plural in #3305, #2918
   carrying much more methodology than the rest). All real, none acted on: restructuring five
   finished drafts for cosmetic uniformity risks introducing exactly the drafting errors the
   review exists to catch, for no gain to the reader of any single issue. **Recorded as a finding
   for batch 008** — if a house style is wanted, it belongs in step 9 before drafting, not in step
   10 after.

**What the reviewer verified and found correct** — worth recording, because a review that only
reports problems tells you nothing about coverage: the four-entry defines node on all 20 #2673
captures; the 268-commit window and three touching commits for #2918; the transition at
v1.5.2010/v1.6.2104; #3005's 5632/11/10 arithmetic on `main`, the 42 measurements, and the
v1.5.2010 match to the reporter's hex dump; `llvm-pdbutil` exiting 0 and reporting 10; #3189's
`%c Binding 2` across all 19 probeable releases and the `-O0`/`-fspv-preserve-bindings`/DXIL
contrasts; #3305's identical diagnostic at `repro.hlsl:2:23` on all 20 releases and 19-of-20
SPIR-V successes.

**And one note on the reviewer's own limits, consistent with previous batches.** It attempted to
narrow #3305's target-env claim to `main` alone, which would have *lost* a measurement; and it
proposed removing a stale-text harm statement that the brief explicitly protected. Both are the
same underlying behaviour — it optimises the sentence it can see against the evidence it happened
to open. **Give it the evidence files (it used them well here), and re-read every accepted rewrite
against the artifact, not against the original wording.**

## Sampling, and what this batch cannot conclude

**Batch 007 was deliberately weighted toward subsystems no previous batch had touched.** Five
batches of shader-compile issues had stopped finding new tooling gaps, and the two most valuable
findings in batch 006 both came from unusual issue *shapes* rather than unusual bugs. So this
batch took: the PIX pass pipeline (#2918), the MSF/PDB writer (#3005), SPIR-V descriptor binding
(#3189), a disagreement between DXC's own two back ends (#3305), and a driver-plumbing defect
whose symptom is a *countable* metadata list (#2673). **The method findings above are the return
on that choice, and they are correspondingly non-representative: a batch of ordinary
shader-compile bugs would have produced far fewer.**

**The oldest-untriaged pool is now visibly enhancement-flavoured, and that is a property of the
pool, not a discovery about DXC.** Of the 17 oldest untriaged issues at selection time, 6 carried
`enhancement` and several more are feature requests in all but label. Two consequences the
overview must not be read against:

1. **A rising `enhancement-not-bug` rate in later batches is partly an artefact.** #3189 is one
   this batch; do not read a trend into 008–010 without correcting for the pool.
2. **Bisection gets less informative.** A feature that was never implemented reproduces on every
   release by construction, so `always-repro'd` carries little signal in this population.

**Verdict rates from this batch do not generalise.** Selection was oldest-first *and* deliberately
mixed by subsystem, which is two non-random filters stacked. Four of five reproduce; the one that
does not was chosen partly *because* it looked plausibly fixed. A random sample of the open
backlog would be expected to contain duplicates, unreproducible reports and issues fixed long ago
in far greater proportion than any batch here.

**One thing this batch does say about the effort's own history:** #2918 is the **second**
`close-fixed` in 35 issues (after #3038 in batch 003). Both required going beyond the recorded
repro — #3038 by fetching release branches, #2918 by reconstructing an unavailable shader from a
dump. **Neither would have been found by running the issue's own repro against `main` and
stopping.**

## Proposed issue comments

These are **drafts for review, not posted**. No comment, label or state change
has been made on any issue. Each is written to be postable as-is by a maintainer, and every
claim in them is backed by captured evidence in `issues/<nnnn>/`.

They deliberately avoid promising fixes or timelines, and where the next step is a product or
language decision they say so rather than pre-empting it. Quoted compiler output was
re-verified before being written down.

Each draft ends with a trailer disclosing that it came from an assisted triage pass.

Source of each is `issues/<nnnn>/comment.md` — edit there, then re-run
`scripts/render_comments.py <batch>` to refresh this section.


### Draft — [#2673](https://github.com/microsoft/DirectXShaderCompiler/issues/2673) User command line defines are duplicated in debug info and in preprocessor

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2673](https://github.com/microsoft/DirectXShaderCompiler/issues/2673).

Still reproduces on `main` (1.9.0.5433, `13730886e`), and on all 20 releases tested, from
v1.4.1907 (2019-07) through v1.9.2607. v1.4.1907 predates this report, so the defines have
been duplicated for as long as it is possible to check.

Compiling the cited `share_mem_dbg.hlsl` with its own `RUN:` line, `dxc.exe` driven from the
command line, gives the node exactly as filed:

```
!dx.source.defines = !{!70}
!70 = !{!"DefineA=1", !"DefineB=0", !"DefineA=1", !"DefineB=0"}
```

`!dx.source.args` shows it one layer earlier — the `-D` pair appears once where it was typed
and again after `-Qstrip_reflect`:

```
!72 = !{!"-E", !"main", !"-T", !"cs_6_0", !"-Zi", !"-Od", !"-D", !"DefineA", !"-D",
        !"DefineB=0", !"-Qstrip_reflect", !"-D", !"DefineA", !"-D", !"DefineB=0",
        !"-Qembed_debug"}
```

Compiler Explorer, `dxc_1_6_2112` and `dxc_trunk`: https://godbolt.org/z/qa68hEf4z

The compile succeeds and the DXIL is unaffected; only the recorded defines are wrong. With a
single `-D` the node is `!{!"DefineA=1", !"DefineA=1"}`, so the whole list is applied twice
rather than this being a two-define quirk.

### Where it happens

`DxcContext::Compile` passes `IDxcCompiler::Compile` both the argument array — still holding
the user's `-D` flags — and `m_Opts.Defines`, which the option parser extracted from those same
flags (`tools/clang/tools/dxclib/dxc.cpp:881-885`). `BuildArguments` then appends a fresh
`-D <name>` for every entry of the defines array
(`tools/clang/tools/dxcompiler/dxclibrary.cpp:506-508`), and that doubled list is what reaches
`PPOpts.addMacroDef` and `CodeGenOpts.HLSLDefines`.

Immediately above, `BuildArguments` routes arguments through
`AddArgumentsOptionallySkippingEntryAndTarget`, whose comment reads: *"skip extra entry/profile
arguments in the arg list when already specified separatly. This would lead to duplicate or
even contradictory arguments in the arg list, visible in debug information."* Defines arrive by
the same route and get no such treatment.

That accounts for the configuration dependence in the report, which still holds. The harness
running `share_mem_dbg.hlsl` calls `Compile(..., flags.data(), flags.size(), nullptr, 0, ...)`
(`tools/clang/unittests/HLSLTestLib/FileCheckerTest.cpp:573-575`), so nothing is appended and
the `CHECK` line passes. The trigger is a caller supplying the defines *both* ways, as
`dxc.cpp` does, so the test cannot catch it as written. Only the command-line path was
measured; the statement about the API path is from source.

The same metadata is what `IDxcPdbUtils` and the PIX/DIA compilation-info surfaces report as a
compile's defines, so this is not purely cosmetic for tooling reading a PDB.

Suggested labels: `bug`, `debug info` (currently none). Not `correctness` — the generated DXIL
is unaffected.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#2918](https://github.com/microsoft/DirectXShaderCompiler/issues/2918) PIX: Numbering pass fails with /Od when subroutines are used

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2918](https://github.com/microsoft/DirectXShaderCompiler/issues/2918).

**This looks fixed — most likely by [`ac5630e8e`](https://github.com/microsoft/DirectXShaderCompiler/commit/ac5630e8e6e224195a9d39b1b0dbe04275f5c1b8)
("Fixes for adding -Od", #3292, Dec 2020), six months after the report.**

The repro here is a `.pix` capture behind an internal bug number, so it could not be run. What
*could* be done is read the dump as a specification and rebuild an input with the same shape —
a compute shader built `-Od -Zi` with a local array inside a non-inlined helper function — then
run the PIX passes over it on every release available here:

```
dxc  -T cs_6_0 -E main -Od -Zi -Qembed_debug repro.hlsl > module.ll
dxopt module.ll -opt-mod-passes -dxil-dbg-value-to-dbg-declare -dxil-annotate-with-virtual-regs
```

| release | PIX passes | |
| --- | --- | --- |
| v1.4.1907 | — | no `dxil-dbg-value-to-dbg-declare` in that build |
| **v1.5.2010** | **fails, `E_FAIL`** | last release before the fix |
| **v1.6.2104** | succeeds | first release after it |
| v1.6.2106 … v1.9.2607, and `main` (`13730886e`) | succeeds | 14 further builds |

Running only `-dxil-annotate-with-virtual-regs` succeeds on v1.5.2010, so despite the title the
failing pass is `-dxil-dbg-value-to-dbg-declare`.

**Why that commit.** 268 commits sit in that window; three touch
`DxilDbgValueToDbgDeclare.cpp`, and one changes the debug location:

```diff
-  DbgDeclare->setDebugLoc(GetVariableLocation());
+  DbgDeclare->setDebugLoc(m_dbgLoc);
```

`GetVariableLocation()` built its own location and is now `#if 0`'d as unused:

```cpp
const unsigned DefaultColumn = 1;
return llvm::DILocation::get(m_B.getContext(), m_Variable->getLine(),
                             DefaultColumn, m_Variable->getScope());
```

That is the four-argument `DILocation::get` — **`InlinedAt` is null** — with a hard-coded
column of 1. Attached to a `llvm.dbg.declare` the pass had just synthesised in the *entry*
function, for a variable whose scope belongs to the helper, it produces exactly the metadata in
the report:

```
!970 = !DILocation(line: 96, column: 1, scope: !965)     <- column 1, no inlinedAt:
!965 = distinct !DILexicalBlock(scope: !966, ...)        <- scope is inside CullAirprobeVolumes
```

which `Verifier::visitDISubprogram` rejects with `!dbg attachment points at wrong subprogram
for function`. `DxcOptimizer` appends the verifier to the pass pipeline, and a verifier failure
there becomes a thrown `hlsl::Exception` — the `std::exception` in `WinPixEngineHost.exe`. The
commit message says the same thing independently: *"The value-to-declare pass was adding an
incorrect debug location, which tripped up the verifier."*

**Caveats.** The shader above is a **reconstruction written during triage** — not the reported
shader, and no claim is made that it is equivalent to it. And the fix is attributed by narrowing
a 268-commit window in source, not by a bisect: strong, not certain.

Compiler Explorer, for the metadata only: **https://godbolt.org/z/a4qPPYzvK** — CE runs `dxc`
alone and cannot run a PIX pass, and its oldest DXC (1.6.2112) already contains the fix, so both
panes succeed. What they show is the `inlinedAt:` on the `!DILocation`s scoped to the helper's
`DISubprogram` — the field whose absence was the bug.

**If closing needs more than an inference,** nothing private needs to leave Microsoft: re-run
that same `.pix` capture against any DXC ≥ 1.6.2104, or attach the failing DXIL *module text*
(not the shader source) containing the offending `!DILocation`. Either would settle it;
otherwise this seems to be the "no longer relevant" case @damyanp asked about in 2024.

**Suggested labels:** `PIX` and `debug info` both fit and neither is applied — this issue has no
labels at all. `crash` and `bug` also apply to the original report. If it stays open rather than
being closed, `needs repro steps` is the accurate state.

<details>
<summary>Method — repeatable</summary>

The PIX passes are DXIL module passes in `lib/DxilPIXPasses/`, reachable only through
`IDxcOptimizer::RunOptimizer` over an already-compiled module — never from a plain
`dxc file.hlsl`. `dxopt.exe` is the command-line front end for that interface; the pass pairing
above is the one the in-tree tests use (`PixTestUtils.cpp` `RunAnnotationPasses`,
`test/HLSLFileCheck/pix/*.hlsl`). Stage 1 must emit disassembly text: a container written with
`-Fo` has a stripped DXIL part, so the passes then see no debug info and nothing can fail.

Releases ship no `dxopt.exe`, so each release's `dxcompiler.dll` was driven by this repo's
`dxopt.exe` placed beside it. To keep that honest, every measured build got three runs, not one:
a **baseline** (same module, no passes) that must succeed, showing the module went in
verifier-clean; a **control** (same module with `inlinedAt:` removed from one
lexical-block-scoped `!DILocation`, no passes) that must fail, showing that build still performs
the wrong-subprogram check and that the pairing can report a failure at all; and then the
measurement. Both held on every measured build.

One trap if you repeat this: `Verifier::visitDISubprogram` dedupes through a `Seen` set, and
when a location's scope *is* a `DISubprogram` the scope and the subprogram are the same node, so
the second insert fails and the check is skipped entirely. Breaking a location whose scope is a
`DISubprogram` produces no diagnostic. The control has to use a `DILexicalBlock`-scoped
location — which is what the report's `!965` is.

</details>

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
````

### Draft — [#3005](https://github.com/microsoft/DirectXShaderCompiler/issues/3005) Generated separate PDB files have possibly invalid header

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3005](https://github.com/microsoft/DirectXShaderCompiler/issues/3005).

Still reproduces on `main` (1.9.0.5433, `13730886e`). The more actionable finding is
that a fix was written, reviewed, and then closed unmerged.

### Measured

Reporter's shader and flags, `ps_6_0`, separate PDB via `-Fd`:

```
size on disk           5632 bytes = 11 x 512-byte blocks
NumBlocks       @0x28  10          -> declares blocks 0..9
stream 5 (DXIL container) occupies blocks 6, 7, 8, 9, 10
```

Your arithmetic holds — `NumBlocks * BlockSize` is 5120 against a 5632-byte
file. Stated without relying on any convention about what `NumBlocks` should
mean: **the file's own stream directory addresses a block the superblock says
does not exist.**

### Cause

`lib/DXIL/DxilPDB.cpp:132`

```cpp
SB.NumBlocks = 3 + m_NumBlocks + GetNumBlocks(SB.NumDirectoryBytes);
```

`NumBlockAddrBlocks` (line 194) — the block holding the list of
stream-directory block indices — is written at line 216 but never counted here,
so `NumBlocks` is always short by at least one. Unchanged since `2dec1cd0d`
(2019-05-29). The comment at line 63, directly above the field, states the
invariant the code breaks: *"In practice, NumBlocks \* BlockSize is equivalent
to the size of the MSF file."*

### On "possibly" — checked against three readers

- **LLVM accepts it.** `msf::validateSuperBlock` never compares
  `NumBlocks * BlockSize` to the file length, and stream blocks are bounds-checked
  against the file size, not `NumBlocks`. `llvm-pdbutil` opens the file, exits 0,
  and reports `Number of blocks: 10` — propagating the wrong value.
- **Microsoft's reference MSF implementation would not.** In
  [microsoft-pdb `PDB/msf/msf.cpp`](https://github.com/microsoft/microsoft-pdb/blob/master/PDB/msf/msf.cpp),
  `NumBlocks` is `pnMac`; `extantPn(pn)` requires `pn < pnMac()`, and
  `readPnOffCb` returns `FALSE` for a non-extant page in release builds too.
  DXC writes the container stream's last page *at* `pnMac`. (Source reading —
  msdia140/DIA was not executed.)
- **DXC's own reader never consults the field**, which is why `dxc -dumpbin`
  round-trips its own PDBs happily and why this went unnoticed.

So the header is wrong by DXC's own documented invariant, and no reader tested
here rejects the file.

### History

All 21 builds measured — every release from v1.4.1907 (2019) through v1.9.2607,
plus `main` — write a short `NumBlocks`, with and without the trailing slash on
`-Fd`. Against v1.5.2010, closest to your `1.5.0.2616`, the numbers land on your
hex dump exactly: 5120 bytes, `NumBlocks = 9`, `NumDirectoryBytes = 0x30`.

Two details from the report that turned out not to matter: the
`DXIL.dll not found` warning is unrelated (a build that has `dxil.dll` and signs
produces the identical header), and the trailing slash on `-Fd` only changes the
file's name.

[Compiler Explorer](https://godbolt.org/z/s567x57P8) — it can show stdout but
not the PDB bytes, so it cannot show the defect. The compile succeeds and
prints nothing at all.

### The actionable part

[#5767](https://github.com/microsoft/DirectXShaderCompiler/pull/5767)
("Fixes #3005", @adam-yang) diagnoses this identically, fixes it, and adds a
regression test with a checked-in legacy PDB for read-compatibility. It was
reviewed in September 2023, updated in November 2023, and closed unmerged on
2026-01-22 by an inactivity sweep. @damyanp asked here in June 2024 how close
that PR was to going in, and the question was never answered; a reader arriving
today would reasonably assume a fix is pending.

The decision left is whether to reopen and rebase #5767 or to accept the defect
and close this. Its author's own note on impact: *"Symsrv does not check this
property currently, but it's best to fix this in case something changes in the
future."*

### Labels

`bug` and `debug info` are both right; no changes suggested. Not `validation` —
that label is for DXIL validation and signing, which is unrelated to MSF
container well-formedness.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3189](https://github.com/microsoft/DirectXShaderCompiler/issues/3189) [SPIR-V] Descriptor bindings assigned before dead code elimination

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3189](https://github.com/microsoft/DirectXShaderCompiler/issues/3189).

**Still reproduces exactly as filed**, on `main` (1.9.0.5433, `13730886e`) and on all 19 tested
releases from v1.5.2010 to v1.9.2607. v1.4.1907 cannot answer — `SPIR-V CodeGen not available` —
so this has reproduced for as long as it is measurable. Nothing in the issue text is stale.

Repro: https://godbolt.org/z/48nqT9roE — **all three panes compile successfully; the finding is
in the `OpDecorate` lines.** The shader is the issue body's, with the "shift functionality"
reconstructed as `-fvk-auto-shift-bindings -fvk-t-shift 100 0 -fvk-s-shift 200 0`, which yields
the reported numbers. Cbuffers `a` and `b` have no `OpVariable`, `OpName` or `OpDecorate` at
all:

```
               OpDecorate %g_texture2D DescriptorSet 0
               OpDecorate %g_texture2D Binding 100
               OpDecorate %g_sampler DescriptorSet 0
               OpDecorate %g_sampler Binding 200
               OpDecorate %c DescriptorSet 0
               OpDecorate %c Binding 2
```

**It is not specific to the shift options.** With a plain `-T ps_6_0 -E mainPS -spirv` the same
shader puts `c` at `Binding 4`, after `g_texture2D` 0, `g_sampler` 1, `a` 2, `b` 3.

**The mechanism is exactly what the title says.** `decorateResourceBindings()` runs at
`SpirvEmitter.cpp:840`; the module first reaches `spirvToolsLegalize`/`spirvToolsOptimize` —
where spirv-opt's performance passes delete the unused variables — at lines 972 and 988.
`DeclResultIdMapper::decorateResourceBindings` walks `resourceVars` in declaration order and
consults nothing about liveness. At `-O0`, where no spirv-opt pass runs, `a` and `b` are still
there holding the numbers they were given:

```
               OpDecorate %a DescriptorSet 0
               OpDecorate %a Binding 0
               OpDecorate %b DescriptorSet 0
               OpDecorate %b Binding 1
               OpDecorate %c DescriptorSet 0
               OpDecorate %c Binding 2
```

`c` gets `Binding 2` either way; optimisation only deletes `a` and `b` afterwards.

@damyanp's DXIL observation checks out — the same shader without `-spirv` puts `c` at `cb0` and
omits `a`/`b` from the binding table (pane 3 of the link). Note the two are not directly
comparable: DXIL registers are per-type (`cb0`/`s0`/`t0`) whereas SPIR-V has one binding
namespace per descriptor set, which is why the shift flags are needed here at all.

@s-perron's position is that the default must not change and that the route forward is an opt-in
`spirv-opt` renumbering pass, so this is a feature request rather than a bug, and whether to add
such an option is a product decision. DXC already has a flag pointing the *opposite* way:
`-fspv-preserve-bindings` keeps `a` and `b` in the module at bindings 0 and 1, so the module
matches the numbering (`c` stays at 2 either way).

Two documentation gaps, actionable regardless of that decision. `docs/SPIR-V.rst` describes
implicit assignment as *"next available binding number ... in the declaration order"* and never
says that a resource removed by optimisation keeps its number, or that this is intentional. And
`-fspv-preserve-bindings` is not listed in the Vulkan-specific options section at all — only
`-fspv-preserve-interface` is. Both belong where the shift options are described.

**Labels:** suggest adding `enhancement` (the ask is an opt-in option, not a fix),
`up-for-grabs` (the implementation route is named and reviewers are offered) and `docs`.
No removals — `spirv` is correct.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3305](https://github.com/microsoft/DirectXShaderCompiler/issues/3305) Empty Payload struct not recognized in DXIL

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3305](https://github.com/microsoft/DirectXShaderCompiler/issues/3305).

Still reproduces on `main` (`1.9.0.5433`, `13730886e`), and on all 20 releases from v1.4.1907
(2019-07) through v1.9.2607 — the same DXIL message at the same location on every one, so this
predates the report rather than having regressed into it. The SPIR-V half of the same probe
succeeds on 19 of those 20 (every release that has SPIR-V codegen at all; v1.4.1907 does not).

Both back ends, same source, `-T lib_6_3`
([Compiler Explorer](https://godbolt.org/z/Pr3cfczY7)):

```
$ dxc -T lib_6_3 repro.hlsl
repro.hlsl:2:23: error: shader must include inout payload structure parameter.
[shader("miss")] void main(inout Payload payload) {}
                      ^

$ dxc -T lib_6_3 -spirv -fspv-target-env=vulkan1.2 repro.hlsl        # exit 0
    %Payload = OpTypeStruct
%_ptr_IncomingRayPayloadKHR_Payload = OpTypePointer IncomingRayPayloadKHR %Payload
```

(The SPIR-V half needs an explicit target environment — raytracing is gated on it, on `main` and
on v1.5.2010 alike — so a bare `-spirv` stops at that gate rather than on the payload. Not part
of this defect.)

## The DXIL error misnames its own cause

The shader *does* include an inout payload structure parameter. What DXC actually checked is
the payload's **size** — `CGHLSLMS.cpp:2492`, `if (0 == funcProps->ShaderProps.Ray.payloadSizeInBytes)`.
Two consequences worth knowing before anyone tries to fix this:

- A payload whose only member is itself an empty struct (`struct Inner {}; struct Payload { Inner i; };`)
  gets the identical message, so the trigger is zero size, not an empty outer struct.
- A *genuinely* missing payload parameter no longer produces this message — measured for `miss`
  on v1.7.2212 vs v1.7.2308, either side of #5131 (`f90af4e15`, 2023-04), which moved that case
  to Sema:
  `error: incorrect number of entry parameters for raytracing stage 'miss': 0 parameter(s) provided, expected one payload parameter`.
  The codegen message was accurate before then; today, for `miss`, the only input that reaches
  it is the one the words do not describe.

## What we think needs deciding

Whether an empty payload should compile for DXIL is a language/product call, not something the
current behaviour settles. The rejection is deliberate — it dates to
[`6e6f8dbd`](https://github.com/microsoft/DirectXShaderCompiler/commit/6e6f8dbdf) (2018),
"Require payload/attribute/param structs for ray shaders" — and DXIL validation has no lower
bound on payload size, so the rule lives entirely in the front end. On the SPIR-V side the
zero-member `OpTypeStruct` passes DXC's own spirv-val run. @damyanp's 2024-04-11 question about
the motivating scenario is still the thing this is blocked on.

The diagnostic, though, is wrong whichever way that goes: if empty payloads stay illegal the
message should say the payload is empty, and if they become legal the check goes away.

**Labels:** keep `bug`; suggest adding `diagnostic` for the misleading message. Not `spirv` —
as established in this thread, the SPIR-V path is the one that works.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
````

---

## Caveats

- **Sampling is deliberately unrepresentative and doubly filtered.** See
  [Sampling](#sampling-and-what-this-batch-cannot-conclude). Nothing here is a statement about the
  backlog.
- **The review gate was suspended.** See the callout at the top. Collation's judgement that
  quality held is made by the same run it is judging, and the one quotation defect this batch
  produced was caught by a human before collation started, not by any gate.
- **#2918's `close-fixed` rests on an agent-constructed repro.** The reporter's shader is private
  and was never sought. The reconstruction positively reproduces on v1.5.2010 and succeeds from
  v1.6.2104, with a working baseline and negative control on every measured build — but it cannot
  prove *the reporter's* module is clean today, only that the mechanism the dump shows was
  removed. The draft states the residual risk and names the narrow ask that would settle it.
- **#2918's attribution to `ac5630e8e` is a 268-commit window, not a bisect.** The behaviour
  change was measured on release binaries either side of the window; the commit was **not** built
  in isolation. Strong, not certain, and labelled that way in the notes, the summary and the
  draft.
- **#2918 covers 16 releases plus `main`, not 20.** v1.4.1907 is a genuine `invalid-probe` (no
  `dxil-dbg-value-to-dbg-declare`); v1.6.2112, v1.7.2308, v1.8.2502 and v1.8.2505.1 were absent
  from the shared release cache. All four postdate the transition, which is bracketed by two
  probed releases.
- **#3005's history was measured by hand, not by the predicate**, and the predicate asserts a
  *precondition*. `reindex` will re-run that predicate and re-derive `repro` **whether or not the
  bug is still present**. This is the single most important caveat in the batch and it is a
  tooling limit, not a worker choice — see method findings 1–3.
- **#3005's "Microsoft's reference implementation would refuse this" is source reading, not
  execution.** msdia140/DIA was **not** run. The microsoft-pdb analysis is of the published
  reference source.
- **#3005's `-Fd` path and CE arguments both depart from the reporter's literal command line**,
  in three documented ways (named PDB instead of hash-named, forward slashes because of the
  `shlex` defect, output under `pdb/`). Both `-Fd` spellings were measured on all 21 compilers and
  produce byte-identical structure.
- **#3189's shift flags are a reconstruction.** The issue gives no command line. They are verified
  to produce the reported number (`Binding 2`), but the reporter's real command line is unknown and
  their real shader may use `:register()`. The no-shift form reproduces too, and was probed at
  **both ends of the release range, not at every release**.
- **#3305's `-fspv-target-env=vulkan1.2` was added by the triage.** It is an instrument, not an
  inherited workaround — the bare `-spirv` behaviour is captured separately — but the SPIR-V half
  of every capture carries a flag the reporter never wrote.
- **#3305's post-#5131 finding is measured for the `miss` stage only.** PR #5131 also deleted the
  closesthit/anyhit tests that asserted the same message, but those stages were not probed.
- **#2673's repro is `partial`** — a byte-identical copy of an in-tree test file, referenced by the
  reporter, rather than pasted code. Its claim about the **API** path is from source only; no
  API-driven probe was run.
- **#2673's CE pane shows `-Zi` twice for an unrelated reason** — Compiler Explorer's wrapper
  injects `-Zi -Qembed_debug`. The published banner says so, to stop a reader mistaking it for the
  finding.
- **No `--repeat` hit rate is quoted anywhere in this batch.** All five repros are deterministic,
  so `SKILL.md` step 5's rule is satisfied vacuously.
- **Nothing in `scripts/` or `SKILL.md` was changed during this collation.** Every method finding
  above is reported, not implemented. `test_predicates.py` passes unchanged and `audit` exits 0.
- **`data/issues/8737/verdict.json` carries an uncommitted deletion of its `text_stale` field**
  that this collation did **not** make and did **not** repair. See method finding 12; the value is
  still in `triage.db` and will survive only until the next `reindex`.
- **`overview.md` is generated and was regenerated last**, after `reviewed_by` was set on all
  five, because `audit`'s staleness gate compares it against the newest `verdict.json`.
- **`reindex` was not re-run during this collation.** The batch-007 verdicts were written by the
  per-issue sessions and re-read here; re-scoring 35 issues and ~500 runs is expensive and the
  orchestrator's brief ruled it out. `audit` passes without it.

## Suggested next step

1. **Implement the `script` predicate kind** (method finding 1), between batches rather than
   during one. Two consecutive batches have now hit "no predicate can see a file", and #3005 is
   the case where it costs a genuinely self-checking verdict rather than merely being awkward. The
   design, including the four requirements learned here, is written out above and in
   `data/issues/3005/method-notes.md`.
2. **Add the predicate role marker** (`"role": "anchor"` / `"asserts": "precondition"`), proposed
   independently by two workers this batch. It is small, it fixes the backwards `# verdict: repro`
   header, and it would let `bisect` refuse to report a transition it cannot mean.
3. **Fix `shlex.split`'s POSIX mode on Windows**, or warn on a backslash-containing token. It is
   a two-line change guarding a silent wrong-path failure that affects every artifact repro.
4. **Restore `#8737`'s `text_stale` before the next `reindex`**, from the value quoted in method
   finding 12 or from `triage.db` while it is still there. Ordering matters.
5. **Decide whether a house style for drafts is wanted**, and if so put it in step 9 before
   drafting rather than leaving step 10 to find five inconsistencies it cannot safely fix.
6. **Compose batch 008 to test the enhancement skew directly.** The pool is now
   enhancement-flavoured; if 008 is drawn oldest-first it will likely produce more
   `enhancement-not-bug` verdicts for reasons that have nothing to do with DXC. Either correct for
   it in selection or state the correction in the report — but do not let the overview accumulate
   a trend that is an artefact of the queue.
