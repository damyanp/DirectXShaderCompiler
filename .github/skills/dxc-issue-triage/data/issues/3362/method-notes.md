# Method notes — #3362 (batch 011)

Observations about the *method and tooling*, not about the issue. Recorded, not fixed.

## 1. `invalid-probe` for `Unknown argument` deserves a spelling re-probe before you believe it

`bisect --linear` demoted v1.4.1907 with `Unknown argument: '-pack-optimized'`, which reads
exactly like "the feature did not exist yet at the floor". It is not what happened. v1.4.1907
accepts both `-pack_optimized` and `/pack-optimized`; only the hyphenated long form is missing.
Re-probed with the underscore, that release compiles all 11 configurations of this issue and
produces layouts **identical** to `main`.

That matters because the two readings lead to opposite conclusions. "Flag added after
v1.4.1907" invites a regression story; "flag present since 2019, behaviour unchanged" is the
truth, and it is the single most load-bearing history claim in this triage.

Corroboration that the underscore is the older spelling: all three in-tree DXIL tests
(`tools/clang/test/HLSLFileCheck/hlsl/compile_options/pack_optimized/optimized{,2,3}.hlsl`)
still write `-pack_optimized`.

**Suggested rule:** when `triage.py` demotes a probe with a reason containing
`Unknown argument`, re-probe the same release with the `_`/`-` transposition and the `/` prefix
before recording anything about feature availability. It costs one command and it changes the
verdict. Doing this generically would need the runner to know a flag's aliases; doing it by
hand needs only the discipline.

## 2. A signature-layout predicate must be anchored on a column that appears in only one table

DXC's disassembly prints the signature tables **twice**: the DXIL tables
(`Name Index Mask Register SysValue Format Used`) and then, under
`Pipeline Runtime Information` / `PSVRuntimeInfo`, a second set with
`Name Index InterpMode DynIdx`. A pattern as reasonable as
`SV_ClipDistance\s+0\s+\S+\s+\d+` false-positives on `; SV_ClipDistance 0  linear` in the PSV
table. Anchoring on the SysValue token (`CLIPDST`) is what makes the predicate mean "the row in
the layout table". Worth generalising to any predicate about registers or masks.

## 3. Prefer a positive anchor over an absence predicate, even when the symptom is "they disagree"

The symptom here is a *mismatch* between two tables, which naturally invites "assert X is
absent" — and an absence predicate scores `repro` for a compile that never ran. The predicate
used instead is an `all_of` whose first clause is a positive anchor (`SV_ClipDistance ... w 2
CLIPDST`, a layout only optimized packing can produce for this struct) and whose second clause
looks for a *second, different* clip row. A failed compile, or a build that ignores the flag,
satisfies neither. `triage.py`'s absence warning correctly stayed silent.

## 4. Run the positive control across the whole release set, not just at ground truth

`bisect --linear` returned `never-repro'd` across 19 releases. On its own that is
indistinguishable from a predicate that cannot fire — a typo in a regex produces the same
report. Running `control-subset-ps.hlsl` with `--expect match` on **all 19 releases plus the
demoted floor** turned "nothing matched" into "the predicate was alive at every probe point and
still nothing matched".

This generalises: **a `never-repro'd-in-releases` history is only worth as much as the evidence
that the predicate was alive at each probe.** It cost 20 `run` invocations and it is the reason
the history claim can be stated with confidence rather than hedged. A `bisect --control
<shader>` flag that interleaved this automatically would make the strong form the cheap form.

## 5. `run --args` takes one invocation; `cmd.txt` takes many

`cmd.txt` supports multiple `dxc` lines and scores their concatenated output, which is exactly
right for a cross-stage issue. But the two escape hatches do not compose with it:

* `run --shader X` retargets **every** line, so a control shader has to define *all* entry
  points named in `cmd.txt` (both controls here define `DSMain` and `PSMain` for that reason —
  worth knowing before writing a one-entry-point control).
* `run --args` replaces the whole argv and accepts a single invocation, so a control that
  varies *per-stage flags* cannot be expressed at all.

The 11-case matrix (stage × flag × shader) therefore needed a local harness, `run-matrix.py`.
It echoes every command with `subprocess.list2cmdline` so the file is self-verifying, takes the
compiler and flag spelling from `DXC` / `PACK3362` env vars (which is what made the v1.4.1907
re-probe a one-liner), and emits `PARSE-WARNING` markers when a parsed table is internally
inconsistent. The output is prose, so — as in #2331 — the most decision-relevant table in this
triage is invisible to `audit` and to any cross-batch query.

## 6. Old releases print `Patch Constant signature signature:`

Pre-~v1.5 DXC duplicates the word. It is visible in the reporter's own 2021 attachment. Any
header regex written as `^; Patch Constant signature:$` silently drops the table on exactly the
releases where you are least able to notice — and for a domain shader that table is half the
evidence. `run-matrix.py`'s `SIG_HEAD` tolerates both.

## 7. Unpack the attachment before reconstructing anything

The verdict here turns on a single line that is not in the issue text: each dump in
`disasm.zip` begins with the command line that produced it, and the pixel shader's has no
`-pack-optimized`. Everything else in this triage is corroboration of a fact the reporter had
already attached, unknowingly, three years before anyone looked.

Generalising: for any issue whose attachment is compiler *output*, the header lines are primary
evidence about **how it was built**, and they are cheap to read. The workflow's step 1 talks
about reading the issue and its comments; "unpack the attachment and read the first line of
every file" deserves the same billing.

## 8. Compiler Explorer

* **The same compiler id can appear more than once** in `--compilers` with different
  `id:<args>` overrides. That is what allowed a three-pane story
  (`dxc_1_6_2112:ds` / `dxc_trunk:ps -pack-optimized` / `dxc_trunk:ps` plain) where the point is
  a *difference between panes* rather than between compilers. Verified by reading back
  `/api/shortlinkinfo/a1hKP6Tvs`: three panes, correct ids, correct per-pane options.
* Confirms #2331's finding that the printed `CE args:` line shows the `cmd.txt` default even
  when every pane overrides it. With a multi-invocation `cmd.txt` you also get
  `warning: multi-invocation cmd.txt; linking the first only` — correct, and the reason every
  pane needs an explicit override here.
* Confirms #2331's finding that `godbolt-note.txt` must be plain prose: `annotate()` adds the
  `// `. Written that way from the start; no superseded link.
* The filters that keep DXC's comment tables are what make this issue visible on CE at all —
  the entire symptom lives in the `; ` table that CE strips by default.

## 9. Small environment frictions

* The agent `grep` tool returns zero matches in this tree unless a `glob` filter is given;
  `Select-String` was used for every absence check, including the machine-path audit.
* `[array]::IndexOf` against a `Get-Content` result matches on exact string equality including
  trailing spaces — a `for` loop with `-eq` on the known header text was more predictable than
  `Where-Object` piping for locating case blocks.

## 10. Cross-issue observation (kept out of the draft, per instruction)

The DS **patch-constant** table's `Used` column is self-inconsistent on `main-debug`:
`SV_TessFactor` shows `xyzw` against a `w`-only Mask, `MIDPOINT` shows `w` against an `xyz`
Mask, and a `CLIPPLANE` the shader demonstrably reads is blank. v1.4.1907 prints `xyzw` on every
row instead, so something changed. It is identical with and without `-pack-optimized`, so it is
not #3362, and it is recorded in `notes.md` without a diagnosis. If someone is looking for a
small, self-contained investigation, this is one — but it needs its own issue and its own
predicate, not a paragraph in this one's draft.
