# DXC issue triage — batch 012

**Ground truth:** local Debug build, compiler-source-identical to upstream
[`13730886e`](https://github.com/microsoft/DirectXShaderCompiler/commit/13730886e6a9019e4e0823746470f3ab75341d6b)
(`1.9.0.5433`). The binary's private build identifier is captured evidence, not
a public source citation.

**Nothing was posted, edited, labelled or closed on GitHub. No DXC compiler
source was modified, and no commit or push was made.**

> [!IMPORTANT]
> **Sampling bias:** batches 011 onward are drawn exclusively from the oldest
> 100 open issues, at the user's request. The usual age mixing is deliberately
> suspended. This batch is enhancement-heavy: three enhancement requests, one
> build-system issue and one correctness bug, with no crash or SPIR-V issue.
> The crash path and `internal_failure` predicate were not exercised here.

## Headline

- **3414 is fixed and is the batch's only closure recommendation.** The defect
  appears from v1.6.2104 through v1.8.2502 and is absent from v1.8.2505 onward.
- 3044, 3066 and 3439 share one theme: capability or information exists inside
  DXC but is not exposed through the driver, disassembly or diagnostic surface.
- 3276 is not a compiler repro. A configure-only CMake A/B turned the generated
  install scripts into measurable evidence without inventing a shader predicate.
- The argument-spelling retry had two dangerous failure directions: it could
  destroy its own repro at exit zero, and it could accept a silently ignored
  option as working. Both are fixed and regression-tested.

| Issue | Repro | History | Recommendation | CE |
| --- | --- | --- | --- | --- |
| [3044](https://github.com/microsoft/DirectXShaderCompiler/issues/3044) | `repros` / agent-constructed | all 20 stable releases plus `main` | keep open | [rc8jz9ve7](https://godbolt.org/z/rc8jz9ve7) |
| [3066](https://github.com/microsoft/DirectXShaderCompiler/issues/3066) | `repros` / agent-constructed | overall request remains open; one clause changed after v1.4.1907 | enhancement, not a bug | [e69hs8h97](https://godbolt.org/z/e69hs8h97) |
| [3276](https://github.com/microsoft/DirectXShaderCompiler/issues/3276) | `not-compiler-verifiable` / partial | configure-only A/B, not release history | needs human judgement | n/a — CMake/install issue |
| [3414](https://github.com/microsoft/DirectXShaderCompiler/issues/3414) | `does-not-repro` / complete | regressed in v1.6.2104; fixed in v1.8.2505 | **close fixed** | [9vKr9a34K](https://godbolt.org/z/9vKr9a34K) |
| [3439](https://github.com/microsoft/DirectXShaderCompiler/issues/3439) | `repros` / complete | all 20 stable compiler releases plus `main` | enhancement, not a bug | [e6xsGc8YE](https://godbolt.org/z/e6xsGc8YE) |

Confidence is **high** for all five.

## Reindex

The mandatory first command ran before any shared-tool edit:

```text
reindexed 60 issue(s) and 1035 run(s)

evidence a completed triage should have left behind:
  #3044: verdict.json has no reviewed_by
  #3066: verdict.json has no reviewed_by
  #3276: verdict.json has no reviewed_by
  #3439: verdict.json has no reviewed_by
```

There were initially no changed verdicts, stale captures or failed controls.
That did **not** contradict the orchestrator's expectation: the old classifier
did not yet contain the new behavioural acceptance rule.

After that rule was implemented, `reindex` invalidated 3362's legacy accepted
spelling captures because they had no proof that the alternate spelling changed
behaviour. This is the retroactive movement the finding predicted. The affected
v1.4.1907 repro and positive control were recaptured safely: `-pack_optimized`
is accepted because it changes the predicate result relative to the same command
without the option. 3189 was also recaptured; its ignored slash spelling remains
an `invalid-probe` rather than a false acceptance.

The final pass reports:

```text
reindexed 60 issue(s) and 1035 run(s)
every probe re-scores as captured, none are stale, and no issue is missing required evidence
```

## Tooling repairs

### 1. Spelling probes cannot mutate evidence

Every spelling attempt now runs in a fresh copy under `.cache/scratch`. Files
used as command inputs are SHA-256 hashed before and after every command.
Mutation hard-errors the probe, and nothing is copied back to the issue
directory.

The fix is grammar-independent. It does not special-case `-P`; it enforces the
actual invariant that a probe cannot write over any of its own inputs.

The destructive 3044 case was rerun against v1.6.2112. With an existing value
token, the isolated retry detected mutation of both `repro.hlsl` and its control,
failed the command, and left the committed repro hash unchanged.

### 2. Alternate spellings need behavioural proof

A candidate is no longer accepted merely because it did not print `Unknown
argument`. It must:

1. satisfy a positive predicate anchor; and
2. change predicate-clause results compared with the same command with that
   option removed.

This rejects a silently ignored slash option and still recovers an alternate
spelling when the original release fails silently. Captures record
`# argument-spelling-evidence:` metadata, and `reindex` invalidates legacy
acceptances that lack equivalent proof.

### 3. Value-taking option parsing is audited

The old hand-written value-flag set omitted `-Fi`, so its value could be mistaken
for a source operand by shader retargeting and Compiler Explorer argument
generation. The replacement records option arity, includes `-Fi`, and is shared
by both consumers.

The regression test mechanically compares the table with every active
`JoinedOrSeparate`, `Separate` and `MultiArg` option in `HLSLOptions.td`, plus
the forwarded common options. This prevents the next omission rather than
patching only this one.

### Regression coverage

`scripts/test_predicates.py` now covers:

- destructive retry with the value-token file present;
- harmless old failure with that file absent;
- committed evidence remaining byte-identical;
- silently ignored slash spellings being rejected;
- a silent original failure recovered by a real alternate spelling;
- legacy captures without behavioural proof becoming invalid;
- complete value-option arity coverage; and
- the clean-endpoint/mid-history warning.

All tests pass.

## The orchestrator's remaining findings

### 4. Compiler Explorer changes DXC arguments

SKILL.md now records that CE appends `-Zi -Qembed_debug -Fc -` to DXC panes.
It therefore cannot prove that debug-derived names, source text or line tables
are absent under the requested local command. A mode-sensitive CE claim needs a
local control with the same appended flags.

### 5. Searches under `.github` need hidden-file handling

The previous guidance incorrectly diagnosed the failure as a missing glob.
SKILL.md now states the actual rule: ripgrep skips the `.github` dot-directory
by default and can return a silent `No matches found`. Searches in this skill
must use `Select-String`, `git grep`, or explicit `rg --hidden`.

### 6. Prerelease policy remains unchanged

No prerelease history was reopened. Stable releases define boundaries; an
issue-specific prerelease exception still requires both explicit naming in the
issue and a validated `release-policy.json` opt-in.

### 7 and 14. A non-compiler issue still needs an instrument

3276 correctly has no `match.json` or `cmd.txt`. Instead, two configure-only
CMake trees differ in one setting and their generated `cmake_install.cmake`
files are parsed as the observable output. The `RULE-PARSE-SELFTEST` caught a
real parser defect before the result was trusted.

The A/B confirms that toolchain-only mode reduces installed header trees from
four to one rather than zero: `include/clang-c` is installed outside the guard.
`install-distribution` is also present with the narrow DXC component list.
The counts remain lower bounds because actual install runs stopped on unbuilt
artifacts.

The measurement was on Windows. The relevant rules are not platform-guarded, so
the structural finding transfers, but the exact Linux file list was not
measured. Independent review therefore removed the definite proposal to remove
the `linux` label and left the platform interpretation to maintainers.

### 8. Artifacts outrank summaries

3044's worker summary made destructiveness sound release-dependent. The
artifact exposed the real precondition: the rejected value token must name an
existing file. Once one successful probe created that file, later probes in the
shared directory were armed. The report and SKILL.md state the artifact-backed
mechanism rather than repeating the summary.

### 9. Multi-ask issues need clause-level histories

3066 contains five requests. One was already partly satisfied at filing, two
remain open, and one observable changed between v1.4.1907 and v1.5.2010. The
overall `all_of` result alone hid which clause moved.

SKILL.md now requires decomposing each ask, investigating every `no-repro`
inside a conjunction, and producing a clause-by-capture matrix when useful.
Self-test clauses remain matched while symptom clauses flip, proving that the
subject changed rather than the output disappearing.

### 10. Commit hygiene remains in force

The existing no-issue-reference and no-history-rewrite rules remain intact.
The documented positive controls (`fixes #3377`, `GH-3429`) and negative
controls (`batch 012 (3044, 3066)` and a bare SHA) were rechecked in both
directions. This session created no commit.

### 11. 3414 received a second blind derivation

The independent reviewer first saw only the expected symptom, repro, command,
predicate and captures. Before reading the worker's notes or verdict, it derived:

- `does-not-repro` on `main`;
- regression in v1.6.2104;
- fix in v1.8.2505; and
- `close-fixed`.

The decisive transition is the `traceRay` operand: broken releases pass the
entry parameter `%payload`; fixed releases pass a distinct temporary such as
`%2`, with copy-in/copy-out around the call.

Commit `053e7ac65` is dated 2025-05-16, lies inside the measured release window,
and adds `traceray_scalarrepl.ll`. The attribution remains **strong, not
certain**, because the v1.8.2502-to-v1.8.2505 window contains 162 commits and
the exact commit was not built in isolation.

### 12. Matching endpoints can hide a regression window

`bisect` now warns when both endpoints are clean but the issue filing date lies
inside the release range. SKILL.md requires a linear scan when a hidden
mid-history window is plausible even if the thread never mentions a fix or
revert. 3414 is clean → broken → clean, the same failure mode previously seen
on 3768.

### 13. Remaining method promotions

SKILL.md now also records that:

- IR/disassembly spelling varies across releases; old named SSA values can
  defeat a `%\d+` predicate, and multiline regexes need explicit cross-line
  syntax;
- controls should score the instrument in a separate predicate rather than
  fail on an unrelated symptom anchor;
- cross-compiler silence needs a same-subject diagnostic control;
- catalogued release paths must come from the database, which reconciles cache
  downloads with test-seeded release trees;
- release controls currently require an issue-local matrix with a `--version`
  self-check; and
- no stable release archive in the catalog ships `dxl.exe`, so a linker-only
  history cannot be inferred from release binaries.

## Per-issue findings

### 3044 — comment preservation is present internally but not exposed

**Confirmed verdict:** `repros`, `always-repro'd`, high confidence,
`still-valid-keep-open`.

The grammar-aware matrix covers all 20 stable releases plus `main`. Preprocessing
removes comments everywhere. `-C` and `-CC` are rejected; slash forms are inert,
as shown by byte identity with `/ZZZNONSENSE` and with no flag. The preprocessor
already has comment-retention fields, but the driver has no corresponding
option or plumbing.

The manual matrix remains the citable history even after the safety fix:
the runner now refuses mutation, but one generic command still cannot express
both historical `-P` grammars.

### 3066 — five disassembly asks, not one bit

**Confirmed verdict:** `repros`, `always-repro'd`, high confidence,
`enhancement-not-bug`.

The clause matrix separates the five requests. Resource-derived names were
printed without a debug flag in v1.4.1907; from v1.5.2010 onward the equivalent
default command prints numeric values and needs debug information for names.
Other requested readability improvements remain absent, with an open source
TODO corroborating one of them. The mechanism of that historical names change
was not identified.

### 3276 — generated install rules show a narrower supported path

**Confirmed verdict:** `not-compiler-verifiable`, high confidence,
`needs-human-judgement`.

Generated install scripts demonstrate the broad default and the partial effect
of toolchain-only mode. The repository also defines an
`install-distribution` path for `dxc`, `dxcompiler` and `dxc-headers`. Choosing
which path should become the default or documented workflow is a maintainer
decision, not a compiler verdict.

Suggested additions remain `build` and `up-for-grabs`. No label removal is
proposed after independent review.

### 3414 — recursive payload copy semantics are fixed

**Confirmed verdict:** `does-not-repro`, high confidence, `fixed` in
v1.8.2505 after regressing in v1.6.2104; `close-fixed`.

Broken captures pass the entry payload object directly to `dx.op.traceRay`.
Fixed captures allocate a distinct temporary, pass that object, then copy it
back. The workaround produces the distinct object on the same broken compiler,
which is a positive control on the interpretation.

The issue body was accurate when filed. A 2023 maintainer comment is marked
`text_stale` factually because it predates the fix; no criticism is implied.

### 3439 — mangled function names still reach diagnostics

**Confirmed verdict:** `repros`, `always-repro'd`, high confidence,
`enhancement-not-bug`.

The primary CodeGen diagnostic contains the MSVC-mangled function name on
`main` and all 20 stable compiler releases. A same-subject Sema diagnostic
prints a readable function name, proving the detector is not simply matching
every error. DXC already contains `DemangleFunctionName`, but the diagnostic
path does not use it and a bare-name demangle cannot distinguish overloads.

The linker observation is corroboration, not a stable-linker history: release
archives do not ship `dxl.exe`.

## Cross-issue consistency

3044, 3066 and 3439 all expose a gap between internal capability and the
user-facing surface. None duplicates an issue in the prior-batch overview.

Their actions are intentionally not identical:

- 3044 is already correctly framed and labelled as a feature request, and the
  source inspection identifies a small actionable wiring path, so `keep open`
  adds more information than restating "enhancement".
- 3066 and 3439 ask for broader presentation/diagnostic design choices, so
  `enhancement-not-bug` is the useful disposition.

All three remain open recommendations; none is treated as fixed merely because
the lower-level information exists.

## Independent draft review

The review task was dispatched as `claude-sonnet-4.6`, but the returned review
self-identified as `claude-sonnet-5`. Rather than guess which runtime identifier
is authoritative, the verdicts record `Claude Sonnet independent review
(batch-012 step-10; blind 3414)`. Either identity is a different model family
from every worker's Opus model.

Applied:

- 3276: dropped the definite `linux` label-removal proposal and added an
  explicit maintainer-judgement caveat.
- 3414: normalised the internal `notes_path`.

Retained after challenge:

- 3044 remains `still-valid-keep-open`, rather than being normalised to
  `enhancement-not-bug`, for the consistency reason above.
- 3414's GPU-execution caveat and strong-not-certain fix attribution.

The other three drafts were approved without factual edits. Every batch verdict
now has a non-empty `reviewed_by` from a model different from `triaged_by`.

## Artifact integrity

| Issue | Decisive controls |
| --- | --- |
| 3044 | token-in-code control, rejected-flag predicate, byte-identity matrix and isolated mutation check |
| 3066 | clause matrix whose self-test clauses stay present while symptom clauses move |
| 3276 | configure-only A/B plus `RULE-PARSE-SELFTEST=pass` |
| 3414 | workaround produces a distinct payload object on the same broken release |
| 3439 | readable same-subject Sema diagnostic plus cross-compiler diagnostic-surface control |

## Verification

- Predicate/tool regression tests: pass.
- Final reindex: 60 issues / 1035 runs; no changed verdicts, stale captures,
  evidence gaps or control failures.
- `triage.py audit`: pass for all 60 issues.
- `check_paths.py`: pass; 16 documented matches in four allowlisted files and
  zero unexpected machine paths.
- Git status: 213 changed/untracked paths, all under this skill.
- Staging dry run: 213 candidates, zero binary files by extension or content;
  the index contains zero staged paths.
- Reviewer audit: every verdict has a non-empty reviewer distinct from its
  author.
- Public-citation audit: zero fork-local SHA link targets.
- GitHub access remained read-only; no issue timeline mutation was attempted.

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


### Draft — [#3044](https://github.com/microsoft/DirectXShaderCompiler/issues/3044) Feature request: option to preprocess without removing comments

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3044](https://github.com/microsoft/DirectXShaderCompiler/issues/3044).

Still valid on `main` (checked at
[`13730886e`](https://github.com/microsoft/DirectXShaderCompiler/commit/13730886e)),
and there is a concrete finding: **the capability is already in the library —
only a driver flag is missing.**

`-P` still drops comments, on every stable release from v1.4.1907 to v1.9.2607
and on `main`. Neither clang spelling is accepted:

```
$ dxc -P repro.hlsl -Fi flag-probe.i -CC
dxc failed : Unknown argument: '-CC'
```

The `/` spellings are not an alternative: `dxc` does not diagnose an unknown
`/`-flag, so `-P /CC ...` exits 0 having ignored it — its output is
byte-identical to a run with no flag at all, and to one passing
`/ZZZNONSENSE`. Same result on Compiler Explorer, 1.6.2112 through trunk:
https://godbolt.org/z/rc8jz9ve7

@pow2clk's read in September 2020 looks right. The plumbing that would carry
`-C`/`-CC` already exists everywhere except the dxc driver:

- `PrintPreprocessedOutput.cpp` honours it —
  `PP.SetCommentRetentionState(Opts.ShowComments, Opts.ShowMacroComments)`.
- `CompilerInvocation.cpp` parses `-C`/`-CC` into those fields, but only on the
  `cc1` path, which the dxc driver never takes.
- `dxcompilerobj.cpp` builds `PreprocessorOutputOptions` by hand instead and
  hardcodes both off:

  ```cpp
  // These settings are back-compatible with fxc.
  PPOutOpts.ShowComments = 0;      // Show comments.
  PPOutOpts.ShowMacroComments = 0; // Show comments, even in macros.
  ```

- `HLSLOptions.td` has no `C`/`CC` entry. (`Cc` is unrelated — colour-coded
  assembly listings.)

So the work is an option-table entry plus wiring `DxcOpts` into those two
fields. The `fxc` back-compat comment is presumably why the default has to stay
off. `dxcrewriteunused.cpp` hardcodes the same two values for the rewriter, so
whether the flag should reach it too is a decision to make rather than an
oversight to fix.

Verified by preprocessing a shader whose sentinel token appears only inside
comments, alongside a control shader that also declares it as an identifier:
the control's preprocessed output keeps the token at all 21 builds tested, the
comment-only one never does, and the macro in both expands, so preprocessing
did run.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3066](https://github.com/microsoft/DirectXShaderCompiler/issues/3066) Suggestion: Improved human-readable values in disassembly

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3066](https://github.com/microsoft/DirectXShaderCompiler/issues/3066).

Still current. Checked against `main` at `13730886e` (a local Debug build reporting
`1.9.0.5433`; it self-reports a different, fork-local commit hash) and against all 20 stable
releases from `v1.4.1907` to `v1.9.2607`.

The five requests don't all land the same way, so taking them one at a time. Line references
are to the disassembly of a small pixel shader that exercises all of them at once
(`Texture2D` sample, `cbuffer` load, `max(x, 0.0001)`, `RWStructuredBuffer` store).

**Float constants in the comment (2nd bullet) — unchanged.** The listing still prints your
example almost verbatim:

```
%16 = call float @dx.op.binary.f32(i32 35, float %15, float 0x3F1A36E2E0000000)  ; FMax(a,b)
```

The comment decodes the opcode and names the operands, then stops; `0.0001` appears nowhere.

**Resource names on loads and stores (4th bullet) — unchanged, and there's an open `TODO`
for it.** `printInfoComment` in `tools/clang/tools/dxcompiler/dxcdisassembler.cpp` carries
`// TODO: if an argument references a resource, look it up and write the name/binding`. That
comment was already in the file when this issue was filed and is still there.

**Output Dependencies (5th bullet) — unchanged.** Still bare element indices on both sides:

```
;   output 0 depends on inputs: { 4, 5 }
```

**Resource Bindings (also 5th bullet) — already does what you asked**, and did in 2020; the
table prints `g_diffuseTexture … T0 … t0`. That half looks satisfied.

**Source locations (1st bullet) — partly there.** With `-Zi -Qembed_debug` every instruction
gets `; line:N col:M` and debug-value comments get `var:"…" func:"…"`. No file name and no
source snippet, and nothing without `-Zi`.

**On the `dx.op.storeOutput.f32` example (3rd bullet)** — worth flagging in case it changes
what you'd want: that opcode is decoded, and was in 2020 —
`; StoreOutput(outputSigId,rowIndex,colIndex,value)`. The op-name table is generated from
hctdb for every op, so it has never been limited to unary/binary. What is still missing is
decoding the operand *values*: `outputSigId` isn't resolved to `SV_Target`, and `i8 0` isn't
resolved to `.x`. If that's the substance of the bullet then it stands as written.

**One thing that has moved, and one that moved backwards.**

On SM 6.6+, `annotateHandle` now decodes the resource properties inline —
`; AnnotateHandle(res,props)  resource: Texture2D<4xF32>` — which is the shape the 3rd bullet
asks for.

Going the other way: in `v1.4.1907` the default listing printed resource-derived value names
with no debug flag, e.g. `%dx.types.Handle %g_luminanceOut_UAV_structbuf`. From `v1.5.2010`
onward that same command prints `%dx.types.Handle %1`, and the names only come back with
`-Zi -Qembed_debug`. Bisected over the 20 releases with two independent predicates; the
transition is in that one window both times. I could not find the mechanism — the handle name
is built unconditionally in `DxilCondenseResources.cpp` — so please treat that as an
observation rather than a diagnosis. Net effect is that default disassembly gives *less* of
the 4th bullet than it did in 2019.

Compiler Explorer: https://godbolt.org/z/e69hs8h97 — `dxc_1_6_2112` and trunk, identical text
at all three places. One caveat: Compiler Explorer adds `-Zi -Qembed_debug` to every DXC pane
whatever you type (visible in `!dx.source.args`), so those panes show the compiler at its most
readable, not its default. The named handles you'll see there are *not* what a plain command
line prints.

For contrast, `dxa -dumpreflection` on the same shader already prints
`SystemValueType: D3D_NAME_POSITION`, `Type: D3D_SIT_CBUFFER`, `Name: g_luminanceOut`. The
enum-to-name tables exist in the reflection printer; the disassembly printer just doesn't use
that kind of decoding.

Suggested labels: keep `enhancement` and `dxil`, add `usability`. This is a live enhancement
request, not a bug — nothing here is incorrect output.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3276](https://github.com/microsoft/DirectXShaderCompiler/issues/3276) Install target installs lots of unnecessary LLVM outputs

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3276](https://github.com/microsoft/DirectXShaderCompiler/issues/3276).

Still accurate on `main` (`13730886e`): the default `install` target installs the LLVM and
Clang headers, static archives and developer tools. Two things have changed since 2020 that
aren't recorded here, and both are undocumented.

**1. `install-distribution` does what you asked for.** [#5154](https://github.com/microsoft/DirectXShaderCompiler/pull/5154)
(`4f5e4d1b7`, in releases since v1.7.2308) added a distribution target whose components
default to `dxc;dxcompiler;dxc-headers` ([`CMakeLists.txt:807-825`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/CMakeLists.txt#L807-L825)).
Installing those three components deposits six files — the `dxc` executable, `dxcompiler`, and
`config.h` / `dxcapi.h` / `dxcerrors.h` / `dxcisense.h` under `<prefix>/include/dxc`. DXC's own
Linux artifact is built this way: `ninja -C build install-distribution`
([`gcp-pipelines/x86_64-linux-clang.yml:36-44`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/gcp-pipelines/x86_64-linux-clang.yml#L36-L44)).

**2. `-DLLVM_INSTALL_TOOLCHAIN_ONLY=ON` already removes most of the bloat**, if you want a
normal `install` rather than a distribution one. Configuring twice with only that variable
changed:

| under `<prefix>` | default | `TOOLCHAIN_ONLY=ON` |
| --- | --- | --- |
| `lib/LLVM*` archives | 34 | 0 |
| `lib/clang*` archives | 20 | 1 (`libclang`) |
| `bin/` LLVM developer tools | 11 | 0 |
| `include/` header trees | `llvm`, `llvm-c`, `clang`, `clang-c` | `clang-c` |
| `share/llvm/cmake` | 9 files | absent |

It is not a complete answer. `include/clang-c` survives because
[`tools/clang/CMakeLists.txt:426`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/tools/clang/CMakeLists.txt#L426)
installs it a second time *outside* the `if (NOT LLVM_INSTALL_TOOLCHAIN_ONLY)` block that ends
at line 424; the vendored SPIRV-Tools archives, CMake packages and `lib/pkgconfig` aren't
governed by the LLVM option; and `bin/` still gets `dxa`, `dxl`, `dxopt`, `dxr`, `dxv` and the
test binaries.

The `include/dxc` complaint in the second comment no longer applies to the install tree:
`include/dxc` is now an explicit four-file `install(FILES ...)` list, so `CMakeLists.txt` and
`d3dx12.h` don't reach it.

Neither `install-distribution` nor the option combination appears in any README, build script
or docs page — a grep finds `install-distribution` only in `CMakeLists.txt` itself and that one
CI file. So the practical remainder of this issue may be documentation plus the four gaps
above, rather than the original request.

Measured on Windows with the Visual Studio generator, using DXC's own
`cmake/caches/PredefinedParams.cmake` (the \*nix option set) on both sides of the comparison.
The install rules involved carry no `if(WIN32)`/`if(UNIX)` guard, so the finding should
transfer, but the exact file list on Linux will differ — no Linux build was configured.

Label suggestion: add `build` (this is entirely CMake install rules) and `up-for-grabs`
(matching the 2024-07-09 comment inviting a PR); `linux` may also be inapt, since the rules are not platform-guarded and the same bloat appears on Windows. I measured this only on Windows, though, so I would defer to maintainer judgement on whether that label records a user-facing workflow distinction not visible in the rules.

---
<sub>Triaged with AI assistance. This is a build-system issue, so no compiler output was
produced; the evidence is CMake's own generated install rules, read from two freshly
configured build trees. Please flag anything that looks wrong.</sub>
````

### Draft — [#3414](https://github.com/microsoft/DirectXShaderCompiler/issues/3414) DXIL Modifying recursive payload does not work

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3414](https://github.com/microsoft/DirectXShaderCompiler/issues/3414).

This is fixed. A local Debug build of `main` at `13730886e` compiles the shader from the
report correctly, as does every stable release from **v1.8.2505** (2025-05) onward.

**What was wrong.** `TraceRay(..., ray, payload)` passes the closest-hit shader's own `inout`
payload, which needs copy-in/copy-out. From **v1.6.2104** to **v1.8.2502** DXC instead handed
`dx.op.traceRay` the caller's payload object itself — the parameter and the operand are the
same value:

```llvm
; v1.8.2502, -T lib_6_3
define void @"\01?main@@..."(%struct.Payload* noalias %payload, ...) {
  call void @dx.op.traceRay.struct.Payload(i32 157, ..., %struct.Payload* %payload)
```

v1.8.2505 and `main` emit a distinct temporary, written before the call and read back after:

```llvm
; v1.8.2505, same command — identical register numbering on main
  %34 = getelementptr inbounds %struct.Payload, %struct.Payload* %2, i32 0, i32 0
  store <4 x i32> %20, <4 x i32>* %34, align 8
  call void @dx.op.traceRay.struct.Payload(i32 157, ..., %struct.Payload* nonnull %2)
  %35 = load <4 x i32>, <4 x i32>* %34, align 8
```

All four side by side: https://godbolt.org/z/9vKr9a34K

**Why the two variants in the report behaved differently.** The copy used to be generated
inside SROA's rewrite of alloca values (`RewriteCallArg(CI,
HLOperandIndex::kTraceRayPayLoadOpIdx, ...)` in `ScalarReplAggregatesHLSL.cpp`). The
workaround's `Payload new_payload` is an alloca, so it got one; the incoming payload is a
pointer parameter, so it did not. Compiled on v1.6.2104, the workaround's `dx.op.traceRay`
receives `%2` and the filed version receives `%payload`.

**On the 2023-07-14 question** — both halves of that observation hold on the affected builds:
the module does contain a store to the payload (`store <4 x i32> %19, <4 x i32>* %6` on
v1.7.2308), *and* it passes `%payload` to `dx.op.traceRay`. The store was not where the
problem was.

**History** — 20 stable releases, linear scan, no unusable probes:

| | |
| --- | --- |
| clean | v1.4.1907, v1.5.2010 |
| reproduces | v1.6.2104 … v1.8.2502 (13 consecutive releases) |
| clean | v1.8.2505 … v1.9.2607 |

The likely fix is `053e7ac65` ("Refactor udt intrinsic arg copy to before SROA, flatten
RayDesc", #7440): it moves UDT copy-in/copy-out out of SROA into an unconditional pre-pass and
adds `traceray_scalarrepl.ll`, which checks exactly the payload-as-pointer-parameter case. It
is in v1.8.2505 and not in v1.8.2502. The window is 162 commits, so treat this as strong
rather than certain. That PR was written for #7434 and does not reference this issue, which is
probably why it stayed open.

Nothing here was executed on a GPU; the evidence is the emitted DXIL.

Suggested labels alongside `bug`: `correctness`, `dxil`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3439](https://github.com/microsoft/DirectXShaderCompiler/issues/3439) Better demangling for improved error messages

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3439](https://github.com/microsoft/DirectXShaderCompiler/issues/3439).

**Still reproduces on `main` (1.9.0.5433, `13730886e`)**, verbatim, from the repro as filed:

```
$ dxc -T ps_6_0 -E main repro.hlsl
error: External function used in non-library profile: \01?CallMeMaybe@@YAHM_N@Z
```

Checked every stable release that can be probed — **v1.4.1907 through v1.9.2607, 20 releases,
all mangled**. Never fixed, never regressed, never partially improved. Nothing in the issue text
is stale.

### There is already a demangler in tree, and this path doesn't call it

That seems like the actionable part. The diagnostic is emitted at
[`CGHLSLMSFinishCodeGen.cpp:3405`](https://github.com/microsoft/DirectXShaderCompiler/blob/main/tools/clang/lib/CodeGen/CGHLSLMSFinishCodeGen.cpp),
which formats the name with `dxilutil::PrintEscapedString(f.getName(), os)` — the raw
`llvm::Function` name, escaped but not demangled. Meanwhile `hlsl::dxilutil::DemangleFunctionName`
already exists (`include/dxc/DXIL/DxilUtil.h:117`, `lib/DXIL/DxilUtil.cpp:145`) and is already
called from `DxilContainerAssembler.cpp`, `DxcPixLiveVariables.cpp` and `DxilExportMap.cpp`.

It was added in `47958a941` (2018-02-12); this diagnostic was added in `4ade2fccc` (2018-06-20),
four months later, and the wording hasn't changed since.

One caveat so this isn't oversold: `DemangleFunctionName` recovers the bare name (`CallMeMaybe`),
not a signature — so it wouldn't distinguish overloads, which is the reason a mangled name is
useful in the first place. @llvm-beanz's suggestion above (move the diagnostic to Sema where the
AST name is available) is what would actually produce a readable signature. Calling the demangler
looks like the small fix available today; moving it to Sema is the real one.

### It's more than one message, and it's partial

Two other mangled diagnostics, both reproduced:

```
$ dxc -T lib_6_3 case-export-resource.hlsl
error: Exported function \01?TakesAResource@@YA?AV?$vector@M$03@@V?$Texture2D@V?$vector@M$03@@@@V?$vector@I$01@@@Z must not contain a resource in parameter or return type.
```

```
$ dxl -T ps_6_3 -E main link.dxil -Fo linked.dxil
error: Cannot find definition of function ?NotDefinedAnywhere@@YA?AV?$vector@M$03@@V1@I@Z
```

The first is `ReportDisallowedTypeInExportParam` (`CGHLSLMSFinishCodeGen.cpp:3233`), same shape.
The second is the linker (`DxilLinker.cpp:401`), and notably it *isn't* escaped — no `\01` — so
these sites each format the name their own way and a fix at one shared helper won't cover them.
The linker case also reproduces on all 20 releases.

But it genuinely is partial, and I'd rather say so than claim every message is affected. A DXIL
validator error naming a library entry point comes out fine:

```
error: For amplification shader with entry 'AmplifyWithHugePayload', payload size 32768 is greater than maximum size of 16384 bytes.
```

Entry points keep unmangled names. Reading `DxilValidation.cpp`, most rules do pass raw
`F->getName()`, so a non-entry function inside a library should still be mangled there — but I
didn't manage to construct an input that trips one of those rules on a non-entry function, so
treat that as a source reading rather than a result.

The reason this is a defect and not just taste: the same compiler, on the same function, in the
same run shape, gets it right when the diagnostic comes from Sema —

```
$ dxc -T ps_6_0 -E main control-redefinition.hlsl
error: redefinition of 'CallMeMaybe'
```

### Compiler Explorer

<https://godbolt.org/z/e6xsGc8YE> — DXC 1.6.2112 and trunk, both exit 5 with the mangled error.
The source there is a compute restatement of the pixel shader, because the third pane is
`hlsl_clang_trunk` and its backend can't lower a PS that writes a render target; DXC emits the
same message for both spellings. The `dxl` case above isn't shareable there — CE is single-file.

On the Clang pane, in case it's useful for the HLSL-in-Clang work: it **exits 0**. It accepts the
shader, lowers it, and emits `declare !dbg !111 internal i32 @_Z11CallMeMaybefb(float, i1)` — an
undefined declaration, with no diagnostic at all. So this isn't something the rewrite has already
solved; today it doesn't report the condition. I checked that isn't just an artifact of how CE
invokes it — the redefinition control above errors and exits 1 on the same pane
(<https://godbolt.org/z/EPczds3xM>). CE does run that pane in assembly-listing mode rather than
producing a validated container, so a later stage might still object.

**Suggested labels:** add `diagnostic` ("Issues for diagnostics"). Keep `enhancement` and
`tech-debt`. Not suggesting `validation` (that's DXIL validation specifically, and the one
validator message here is correct) or `shader-linking` (the linker instance is real, but the
issue's subject is the CodeGen message).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

---

## Caveats

- 3044's release history remains an explicit grammar-aware matrix rather than
  a generic bisection.
- 3066's v1.4.1907-to-v1.5.2010 transition is measured, but its implementing
  source change was not identified.
- 3276's exact Linux install file list was not measured; the Windows-generated
  rule A/B supports the structural conclusion only.
- 3414's fix attribution is strong but not isolated to a build of the proposed
  commit, and no GPU execution was performed.
- 3439 has no stable-release linker executable matrix.
