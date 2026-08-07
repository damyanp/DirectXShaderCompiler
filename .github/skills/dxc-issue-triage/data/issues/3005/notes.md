# #3005 — Generated separate PDB files have possibly invalid header

- **Status:** `repros`
- **Repro quality:** `complete`
- **History:** `always-repro'd` (every dxc release from v1.4.1907 to v1.9.2607, plus `main`)
- **Confidence:** `high`
- **Suggested action:** `needs-human-judgement`
- **Ground truth:** `main-debug`, commit `ab5400907`
- **Compiler Explorer:** https://godbolt.org/z/s567x57P8

Version string checked before anything was trusted:

```
dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)
```

Exact match to the ground truth named in the brief.

---

## 1. The headline

Two things are true and only the second is worth a maintainer's time.

1. **The bug reproduces, unchanged, on `main`.** It has reproduced in every dxc
   release ever measured here, back to v1.4.1907 (2019).
2. **A maintainer already wrote the fix, it was reviewed, and it was closed
   unmerged by an inactivity sweep on 2026-01-22.** Confirming that the bug is
   real adds almost nothing to this issue; the actionable finding is that its
   resolution lapsed.

`gh api repos/microsoft/DirectXShaderCompiler/issues/3005/timeline` lists two
cross-referenced pull requests, both by @adam-yang, both titled *"Fixed
incorrect BlockSize in PDB header"*, both opening with `Fixes #3005`:

| PR | opened | closed | merged | files |
| --- | --- | --- | --- | --- |
| [#5507](https://github.com/microsoft/DirectXShaderCompiler/pull/5507) | 2023-08-07 | 2023-09-21 | no | 2 (+123/−31) |
| [#5767](https://github.com/microsoft/DirectXShaderCompiler/pull/5767) | 2023-09-21 | **2026-01-22** | **no** | 5 (+195/−66) |

#5507 was superseded by #5767 on the same day #5767 opened, so there is only
one live attempt. Its history:

- 2023-09-21 — @pow2clk reviews (`COMMENTED`): *"As is typical for my reviews
  lately, I feel more strongly about the test comments than the implementation
  comments"*. Not a rejection; a review of test wording.
- 2023-11-07 — @adam-yang replies to the review comments; the clang-format bot
  reports *"With the latest revision this PR passed the C/C++ code formatter"*.
- **Then nothing for two years and two months.**
- 2024-06-27 — on *this issue*, @damyanp asks: *"it looks like you have a PR
  prepared for this. How far off is that from being ready to go in?"* — never
  answered.
- 2026-01-22 — @damyanp closes #5767: *"This PR was closed as it has not been
  updated in the last two years. Please feel free to reopen if this PR should
  be merged and is in a reviewable state."*

So the answer to the question left standing in this issue's thread since June
2024 is: it was review-complete and format-clean in November 2023, and it has
since been swept. This is the same shape SKILL.md records for #2427 — the
agreed fix lapsed, and the same sweep closed it.

#5767 touches `include/dxc/DXIL/DxilPDB.h`, `lib/DXIL/DxilPDB.cpp`,
`tools/clang/unittests/HLSL/CompilerTest.cpp` and adds a regression test with a
checked-in `old_pdb.pdb` input — i.e. it also carries backward-compatibility
coverage for reading PDBs written by the buggy versions. That is worth noting,
because it means the PR is not merely a one-line arithmetic change.

The PR body also supplies the maintainer's own severity assessment, which
matches what was measured here:

> The purpose of wrapping shader PDB as a MSF file is to allow them to be
> stored in symbol servers. Symsrv does not check this property currently, but
> it's best to fix this in case something changes in the future.

---

## 2. What was measured

### The repro

`repro.hlsl` is the reporter's shader verbatim. `cmd-as-filed.txt` holds the
reporter's command line unaltered; `cmd.txt` is what the harness runs and
departs from it in three documented ways (all recorded in `cmd.txt` itself):

1. `-Fd pdb/repro.pdb` instead of `-Fd <dir>/`. The reporter's trailing slash
   makes dxc auto-name the PDB by hash, which a committed repro cannot predict.
   **Checked, not assumed:** both spellings were measured on all 21 compilers
   and produce byte-identical structure (`manual-case-msf-header-history.txt`,
   columns `as-filed` / `named`). The trailing slash is not material.
2. Forward slashes, because the harness splits `cmd.txt` with POSIX `shlex`
   and silently deletes backslashes (see `method-notes.md`).
3. Output goes under `pdb/` inside the issue directory, so the repro is
   runnable from a clone. `pdb/.gitignore` keeps the directory in git and its
   contents out.

### The symptom

`measure_msf.py` parses the MSF superblock, walks the stream directory the way
DXC's own `PDBReader` does, and re-implements LLVM's validation. On ground
truth:

```
size on disk        5632 bytes = 11 x 512-byte blocks
BlockSize   @0x20   512
FreeBlockMap@0x24   1
NumBlocks   @0x28   10        <-- declares blocks 0..9 only
NumDirBytes @0x2c   52
BlockMapAddr@0x34   3
stream 5 (DXIL container) occupies blocks 6, 7, 8, 9, 10
```

The reporter's arithmetic claim — `NumBlocks * BlockSize != filesize` — holds:
10 × 512 = 5120, file is 5632. Short by exactly one block.

**A sharper statement of the same defect, and the one worth quoting:** the
file's own stream directory addresses block 10, while the superblock says
block 10 does not exist. The file is internally inconsistent, not merely
inconsistent with its own length. That framing does not depend on any
convention about what `NumBlocks` "should" mean.

### Source corroboration

`lib/DXIL/DxilPDB.cpp` (unchanged in this respect since `2dec1cd0d`,
2019-05-29 — `git log -S 'SB.NumBlocks = 3 + m_NumBlocks'` returns that one
commit):

- **line 63**, DXC's own comment above the field, states the invariant its
  code goes on to break:
  > `In practice, NumBlocks * BlockSize is equivalent to the size of the MSF file.`
- **line 132**: `SB.NumBlocks = 3 + m_NumBlocks + GetNumBlocks(SB.NumDirectoryBytes);`
- **line 194**: `const uint32_t NumBlockAddrBlocks = GetNumBlocks(BlockAddrSize);`
- **line 216**: `Writer.WriteBlocks(NumBlockAddrBlocks, BlockAddr.data(), BlockAddrSize);`

`NumBlockAddrBlocks` — the block holding the *list of stream-directory block
indices* — is written to the file but never added at line 132. So `NumBlocks`
is short by `NumBlockAddrBlocks`, which is ≥ 1 for any PDB. This is exactly
the diagnosis in #5767's body, arrived at here independently before the PR was
found.

---

## 3. Is the header actually invalid? (the claim the reporter hedged)

The reporter said "possibly invalid". This was checked against three readers
rather than asserted, because "invalid" is a claim about the MSF format, not
about DXC.

**a. It violates the invariant DXC itself documents.** See line 63 above. On
DXC's own stated terms the field is wrong. This is the strongest available
statement and it does not require any external authority.

**b. LLVM's PDB reader accepts the file.** `msf::validateSuperBlock`
(`llvm/lib/DebugInfo/MSF/MSFCommon.cpp`) checks the magic, that `BlockSize` is
one of {512, 1024, 2048, 4096}, `NumDirectoryBytes % 4 == 0`, the
directory-block count, `BlockMapAddr != 0`, `BlockMapAddr < NumBlocks`, and
`FreeBlockMapBlock ∈ {1, 2}`. It **never** compares `NumBlocks * BlockSize` to
the file length. `PDBFile::parseFileHeaders` adds only
`filesize % BlockSize == 0`, and `parseStreamData` bounds-checks stream blocks
against `getFileSize()` — not against `NumBlocks`. These checks are
re-implemented faithfully in `measure_msf.py::llvm_superblock_checks`,
including what they deliberately omit.

Measured, not just read: `llvm-pdbutil` 22.1.5 opens the file, exits 0, and
prints `Number of blocks: 10` — propagating the wrong value verbatim.
`manual-case-llvm-pdbutil.txt` dumps the same PDB twice, as written and with
`NumBlocks` patched to 11 (a 4-byte difference); both are accepted and only the
reported block count changes.

**c. Microsoft's reference MSF implementation would refuse to read the last
block.** This is the finding that settles the question, and it points the other
way from LLVM. In
[microsoft/microsoft-pdb `PDB/msf/msf.cpp`](https://github.com/microsoft/microsoft-pdb/blob/master/PDB/msf/msf.cpp),
`NumBlocks` is `pnMac`, documented in the header struct as *"current end of
file page no."*:

```cpp
BOOL validPn(UPN pn)  { return 0 <= pn && pn < pnMax(); }   // format limit
BOOL extantPn(UPN pn) { return validPn(pn) && pn < pnMac(); }  // pnMac == NumBlocks

BOOL readPnOffCb(UPN pn, OFF off, CB cb, PV buf) {
    assert(extantPn(pn));
    if (!extantPn(pn)) {
        return FALSE;
    }
    assert(!cb || extantPn(pn + cpnForCbLgCbPg(cb, lgCbPg()) - 1));
    if (cb && !extantPn(pn + cpnForCbLgCbPg(cb, lgCbPg()) - 1)) {
        return FALSE;
    }
    ...
}
```

Both `return FALSE` paths are unconditional, not `#ifdef _DEBUG`. A page at or
past `pnMac` is not readable, and the second check catches multi-page spanning
reads too. DXC writes stream 5's last page *at* `pnMac`. So the reference
implementation would fail the read.

Note what it does **not** do: `MSF_HB::fValidHdr()` checks only the magic and
`validCbPg(cbPg)` — it does not validate `pnMac` at open time. The file opens
fine and fails later, at the read.

**d. DXC's own reader never looks at the field.** `PDBReader` in the same file
reads the magic and the stream directory and never consults `m_SB.NumBlocks`
for bounds. That is why `dxc -dumpbin <pdb>` round-trips its own output
happily, and why this went unnoticed for six years.

**Conclusion.** The reporter is right, and right for a stronger reason than the
one they gave. Practically: no reader tested here rejects the file, and
@adam-yang's own PR body says symsrv does not check it either — so this is a
latent correctness defect in a written artifact, not a live breakage.
**Caveat, stated because it bounds the claim:** msdia140 / DIA was **not**
tested. The microsoft-pdb reading above is source-level, from the published
reference implementation, not an execution of the shipping DIA SDK.

---

## 4. History

`manual-case-msf-header-history.txt` is the history evidence — 21 compilers ×
2 `-Fd` spellings, 42 rows, every one `PRESENT`:

| compiler span | size | blocks | NumBlocks | symptom |
| --- | --- | --- | --- | --- |
| v1.4.1907, v1.5.2010 | 5120 | 10 | 9 | PRESENT |
| v1.6.2104 … v1.9.2607 (18 releases) | 5632 | 11 | 10 | PRESENT |
| main-debug (ab5400907) | 5632 | 11 | 10 | PRESENT |

v1.5.2010 — the release closest to the reporter's `1.5.0.2616` — yields
*exactly* the reporter's hex dump: 5120 bytes, `NumBlocks = 9`,
`NumDirectoryBytes = 0x30`, `FreeBlockMapBlock = 1`, `BlockMapAddr = 3`. That
is the strongest available check that this repro is faithful to the report.

So: `always-repro'd`, with the standard caveat that v1.4.1907 is the floor of
the cached release set, not the floor of the bug. Source dating puts the
introduction at `2dec1cd0d` (2019-05-29), before v1.4.1907.

> **Do not read the `bisect` output as a symptom history.** `bisect --linear`
> over `match.json` prints `v1.4.1907 no-repro` and calls the history
> non-monotonic with a transition at v1.5.2010. That is entirely about the
> *precondition* predicate. v1.4.1907 compiles fine, exits 0, and writes a
> defective PDB just like every other release; what it cannot do is
> `dxc -dumpbin` a PDB file (`error: Invalid bitcode signature`, exit 1), so
> the second line of `cmd.txt` fails and the predicate's second clause is
> absent. The byte measurement, not the bisect, is the history.

---

## 5. The predicate, and what it does and does not claim

`match.json` is an `all_of` of two **positive** `contains` clauses over the
combined output of `cmd.txt`'s two invocations:

- `; shader debug name: pdb/repro.pdb`
- `call void @dx.op.storeOutput.f32`

**It does not test the symptom, and it cannot.** No predicate kind in this
harness (`regex`, `contains`, `internal_failure`, `nonzero_exit`, `timeout`)
can inspect a file dxc produced; they all test captured stdout/stderr or the
exit code. The symptom of #3005 is four bytes at offset 0x28 of a `.pdb`.

What the predicate is actually for: it is the **feature-presence control** for
the byte measurement. It asserts that a separate PDB was requested, written,
and read back successfully — so a compiler scoring `no-repro` on it is one
where the measurement had nothing to measure, rather than one where the bug is
absent. It also demonstrates that the readback reaches block 10, the disowned
block. Both clauses are positive, so there is no absence-predicate hazard and
the runner's absence-only warning did not fire.

`match.json`'s `note` field says all of this in situ, beginning *"READ THIS
BEFORE TRUSTING A `repro` VERDICT ON THIS ISSUE"*, because the `# verdict:`
header in the captured output files means "the precondition held", not "the bug
is present".

### Controls

| file | what it does | expected | got |
| --- | --- | --- | --- |
| `variant-compile-only-main-debug.txt` | same compile, no `-dumpbin` | no-match | no-repro ✓ |
| `variant-no-pdb-main-debug.txt` | drop `-Zi -Qstrip_debug -Zsb -Fd` | no-match | no-repro ✓ |

`variant-compile-only-main-debug.txt` is the rhetorically important one: exit
0, **empty stdout, empty stderr**. It is the permanent, `reindex`-rechecked
proof that no text predicate could ever see this issue.

A broken-shader control was considered and rejected: it would leave a *stale*
`pdb/repro.pdb` on disk from the previous run, and the `-dumpbin` line would
read that and falsely match. The two controls above have no such hazard.

---

## 6. The two distractors in the report, both dismissed on evidence

**`warning: DXIL.dll not found. Resulting DXIL will not be signed for use in a
production environment` — irrelevant to the PDB.** The Debug build used as
ground truth *does* have `dxil.dll` beside it, signs the container, and prints
no such warning — and produces the identical defective header. A `-Vd`
(validation disabled, unsigned) run also shows the identical defect. Signing
and PDB container layout are independent. Do not repeat this warning as
significant.

**The trailing slash on `-Fd` — not material.** Measured both ways on all 21
compilers; identical structure. It only changes the file's name.

---

## 7. Labels

Current: `bug`, `debug info`. **No changes proposed.**

- `bug` — "Bug, regression, crash". Apt.
- `debug info` — "Related to debug info generation". Apt; the PDB is the
  debug-info artifact.
- `validation` — deliberately **not** proposed. Its description is "Related to
  validation or signing", meaning DXIL validation and container signing. This
  issue is about MSF container well-formedness, which is a different thing that
  happens to share the English word.
- `correctness` — "Bugs that impact shader correctness". Not apt; the compiled
  shader is correct.
- `up-for-grabs` — not apt; the fix is already written by a maintainer, and the
  blocker is a decision about #5767, not a shortage of contributors.

A maintainer may want `revisit-sooner` given the swept PR, but that is a
prioritisation call, not a triage fact, so it is not proposed here.

---

## 8. Stale text

Recorded via `--text-stale`. The title and body are both still accurate — the
hex dump reproduces exactly on v1.5.2010. What is stale is a **maintainer
comment left standing in the thread**: @damyanp's 2024-06-27 *"it looks like
you have a PR prepared for this. How far off is that from being ready to go
in?"* reads, top-down, as though a fix is imminent. It was never answered, and
the PR it refers to (#5767) was closed unmerged on 2026-01-22. A reader
spot-checking this issue would come away with the opposite of the truth.

---

## 9. Assessment

The bug is real, unfixed on `main`, present in every release measured, six
years old, and understood well enough that a reviewed fix exists. Its
practical impact is low today — no reader tested rejects the file, and the
author of the fix said symsrv does not check the field — but it is a
correctness defect in an artifact DXC hands to symbol servers, and the cost of
carrying it is that every PDB DXC has ever emitted is malformed by its own
documented invariant.

`needs-human-judgement` rather than `still-valid-keep-open`, because there *is*
an outstanding action beyond labels and it is not one triage can take: someone
has to decide whether to reopen and rebase
[#5767](https://github.com/microsoft/DirectXShaderCompiler/pull/5767), or to
declare the defect acceptable and close this issue as `wont-fix`. Either is
defensible. Leaving the issue open with a swept PR behind it and an unanswered
maintainer question on top is the one outcome that helps nobody.
