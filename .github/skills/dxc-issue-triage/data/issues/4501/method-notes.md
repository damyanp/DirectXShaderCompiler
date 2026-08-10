# Method notes — issue 4501

Observations about the *method and tooling*, not about issue 4501's merits. Recorded per the
skill's step 11. Nothing here belongs in `comment.md`.

---

## 1. `classify()` does not demote `unknown SPIR-V debug info control parameter: <value>`

**What happened.** The linear scan scored v1.5.2010, v1.6.2104 and v1.6.2106 as `no-repro`.
They are not clean negatives. Those releases predate `-fspv-debug=vulkan-with-source` and reject
the *value* of a flag they do recognise:

```
error: unknown SPIR-V debug info control parameter: vulkan-with-source
```

No SPIR-V is produced. The run cannot answer the question, so the correct classification is
`invalid-probe`, not `no-repro`.

**Why it matters beyond this issue.** `no-repro` at v1.6.2106 followed by `repro` at v1.6.2112
looks exactly like a behaviour transition, and `bisect` would happily report a fix/regression
boundary there. Any issue whose `cmd.txt` uses `-fspv-debug=vulkan` or `vulkan-with-source` —
i.e. most NonSemantic debug-info issues — inherits this fake boundary. Here it was caught only
because the primary and instrument predicates were scanned separately and agreed, which showed
the "transition" was the instrument switching on rather than behaviour changing.

**Proposed marker for collation** (as a feature-absence marker, alongside
`SPIR-V CodeGen not available`):

```
unknown SPIR-V debug info control parameter
```

Narrowly scoped: it is emitted only when a `-fspv-debug=` value is unrecognised, which is by
definition "this build cannot be asked the question".

---

## 2. `-Fd is not supported with -spirv` is not demoted either — and it is a live absence trap

The existing marker regex requires the shape
`is not supported (for|on|in|with) (target|profile|shader model|stage)`. The `-Fd` diagnostic
ends in `-spirv`, which matches none of those nouns, so it survives as a real result.

Consequence, and it is the exact hazard the brief flagged: under an **unanchored** absence
predicate such as bare `not_regex: DebugBuildIdentifier`, this run

```
$ dxc -T ps_6_0 -E main -spirv -fspv-debug=vulkan-with-source -Fd spirv-pdb\ -Fo out.spv repro.hlsl
dxc failed : -Fd is not supported with -spirv
```

scores a textbook `repro` while emitting **zero bytes of SPIR-V**. The predicate is satisfied
because the compiler never ran far enough to contradict it. Repeat that across a release
sequence and you manufacture a complete, entirely fictional history.

It is closed here by the two mandatory positive anchors in `match.json` (clause 1
`OpExtInstImport "NonSemantic.Shader.DebugInfo.100"`, clause 2 `DebugCompilationUnit`), which
force every `repro` to be a run that provably produced the instruction set in question.
`variant-fd-with-spirv-main-debug.txt` — 561 bytes against ~8 KB for a real capture — is the
demonstration, and its size alone is the tell.

Two possible tool changes, in preference order:
1. Add a marker for `-Fd is not supported with -spirv` (and ideally generalise the noun list to
   include flag names, since `is not supported with -<flag>` is a growing family — see
   `hasUnsupportedSpirvOption()` in `lib/DxcSupport/HLSLOptions.cpp`, which gates `-Fd`,
   `-Fre`, `-Gec` and `-Qstrip_reflect` this way and carries a comment saying the list is
   explicitly non-exhaustive and expected to grow).
2. Have `audit` warn when a predicate is *purely* negative (`not_regex`/`not_contains` with no
   positive clause). That is a structural property of the JSON and cheap to check.

---

## 3. An anchor-only second predicate is a tool-native per-release feature-presence control

The skill's #2922 lesson — prove the feature under test was actually *available* in each
release before believing a silent negative — is usually done with a hand-rolled matrix. There
is a cheaper form: write a second `match-*.json` containing **only the positive anchors of the
primary predicate**, then run `bisect --linear --match match-instrument.json`.

```
match.json             = [anchor1, anchor2, absence1, absence2]   -> "is the symptom present?"
match-instrument.json  = [anchor1, anchor2]                       -> "could this release answer?"
```

Reading the two scans side by side is diagnostic:

| primary | instrument | meaning |
|---|---|---|
| `repro` | `repro` | genuine reproduction |
| `no-repro` | `repro` | genuine negative — release could answer and said no |
| `no-repro` | `no-repro` | **instrument absent** — silent negative, do not trust it |

For 4501 the two scans were byte-for-byte identical in classification, which is the signature
of a pure absence issue: every `repro` is "anchors present, symptom absent", and every
`no-repro` is "anchors absent", i.e. uninformative. That identity is itself the finding, and it
is what demoted the apparent v1.6.2112 boundary.

The cost is one extra JSON file and one extra `--linear` run. The benefit over a bespoke script
is that `reindex` re-evaluates it forever, so the control does not rot.

(The hand-rolled matrix was still worth building here, because it answers a *different*
question — which extended instruction set each release emits, and how the `-Fd` diagnostic
changed — but the anchor-only predicate is what makes the history table defensible.)

---

## 4. I reproduced the #2923 broken-reader trap inside my own harness

`measure-releases.py`'s first `summarise()` inferred "produced no SPIR-V" from "no
`OpExtInstImport` line". That is wrong: `-fspv-debug=line` and `-Zi` emit perfectly good SPIR-V
with `OpLine`/`OpSource` and import no extended instruction set at all. The first matrix run
therefore reported 19 releases as producing no SPIR-V in those two modes, which would have
understated the coverage of the negative result.

Fixed by testing for `; SPIR-V` **and** `OpCapability` in the disassembly instead. Third run of
the matrix is the one on disk.

The general shape: *the reader's failure mode looked exactly like the phenomenon under
investigation.* An absence investigation is unusually vulnerable to this, because every bug in
the reader produces more absence. Two independent workers hitting this class of trap is,
per the skill, the bar for promoting a tool change — logging it here as the second instance
in case a first exists elsewhere in this pass.

---

## 5. The Compiler Explorer banner is compiled, and for SPIR-V it lands in the output

`godbolt-note.txt` is prepended to the source, so its text reaches `OpSource` whenever the pane
uses `-fspv-debug=vulkan-with-source` (or any mode that embeds source). For an **absence**
claim this is self-defeating: a banner reading "DXC does not emit DebugBuildIdentifier" puts
the string `DebugBuildIdentifier` in the disassembly, and the reader's Ctrl-F finds it.

Mitigation used: refer to the instructions by **opcode number only** (105, 106) in the banner
and in `repro.hlsl`, never by name. Verified afterwards by grepping
`manual-case-godbolt-verify.txt` for both names — 0 hits.

Worth a line in the skill's Compiler Explorer step: *if the predicate is an absence, the banner
and the shader must not contain the token being claimed absent.* This applies to
`-fspv-debug=vulkan-with-source`, `-Zi`/`-Zs` with source embedding, and any `-Qembed_debug`
path.

---

## 6. Smaller tooling frictions

- **`gh api --jq` is unusable from PowerShell** when the filter contains quotes; escaping is
  eaten before `gh` sees it. Dump the raw JSON to a file and parse it with Python.
- **The agent's ripgrep tool silently returns zero matches under `.github/`** — presumably an
  ignore rule. `Select-String` and `git grep` both work. A zero-hit ripgrep result under
  `.github/` means nothing and must not be cited as evidence.
- **PowerShell interpolates `$` and backticks inside double quotes.** Any `--args` or
  `--summary` containing a `$` (e.g. echoing a `$ dxc ...` command line) must be single-quoted
  or it will be silently corrupted.
- **`run --args` replaces the entire argv** and overwrites the primary capture unless
  `--label` is given; `run --shader` keeps `cmd.txt`'s args and swaps only the source. Both
  were needed here: `--shader` for the token control, `--args` for the two flag controls.
- `cmd.txt` supports `#` comment lines (`triage.py:1491`). Used here to record *why* `-Fd` is
  absent from the repro command, which is otherwise the first thing a reader would query given
  the issue title.

---

## 7. Cross-issue

No duplicate or near-duplicate of #4501 was found: its timeline contains **zero**
cross-reference events, and no other issue in this batch touches
`NonSemantic.Shader.DebugInfo.100` split debug info. Recording the absence here rather than in
`comment.md`, per the boundary on cross-issue claims.
