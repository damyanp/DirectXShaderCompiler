# #3005 — Generated separate PDB files have possibly invalid header

*Written before running any compiler. Derived only from the issue text and its two comments.*

Issue: <https://github.com/microsoft/DirectXShaderCompiler/issues/3005>
Filed 2020-06-29 against `dxcompiler.dll: 1.6 - 1.5.0.2616 (6ef33dce)`.
Labels at triage time: `bug`, `debug info`.

## What the reporter claims

Compiling

```hlsl
float4 main() : SV_Target0
{
  return float4(0,0,0,0);
}
```

with

```
dxc -Zi -Qstrip_debug -Zsb input.hlsl -T ps_6_0 -Fd /path/to/output/ -Fo /path/to/output/a.dxbc
```

produces a *separate* PDB (auto-named by hash because `-Fd` ends in a slash) that is
**5120 bytes** long and whose MSF superblock reads:

| offset | field (MSF 7.00) | reported value |
| --- | --- | --- |
| 0x00 | magic `Microsoft C/C++ MSF 7.00\r\n\x1aDS\0\0\0` | present |
| 0x20 | `BlockSize` | 0x200 = 512 |
| 0x24 | `FreeBlockMapBlock` | 1 |
| 0x28 | `NumBlocks` | **9** |
| 0x2C | `NumDirectoryBytes` | 0x30 = 48 |
| 0x30 | `Unknown` | 0 |
| 0x34 | `BlockMapAddr` | 3 |

5120 / 512 = **10 blocks on disk**, so `NumBlocks` is one short. The reporter's diagnosis is
that `DxilPDB.cpp`'s block accounting counts the superblock, the two free-block-map blocks,
the stream blocks and the stream-directory blocks, but **not the block-map block** (the block
holding the list of stream-directory block indices), so `NumBlocks` is short by at least one.

They hedge twice, and both hedges are part of what has to be tested:

* the title says **"possibly** invalid";
* "It's not clear what readers are expected to do if this page count is wrong since it can
  equally be derived by `FileSize / PageSize`."

## Comments (2)

* 2023-07-14 — `llvm-beanz` (collaborator): "@adam-yang can you take a quick look at this to
  evaluate the severity and difficulty to resolve?"
* 2024-06-27 — `damyanp` (member): "it looks like you have a PR prepared for this. How for off
  is that from being ready to go in?"

Neither comment states a verdict, and neither contradicts the body. The second asserts a PR
existed as of 2024-06 — **whether that PR landed is a thing to check, not to assume**, and if
it did, the symptom may be gone. This issue has real "may have been fixed" potential: it is
six years old and the PDB writer has been moved and rewritten since (the reporter's link
points at `lib/DXIL/DxilPDB.cpp`, a path that no longer exists).

## The symptom, stated so it can be falsified

**This issue reproduces iff**, for the PDB file dxc writes via `-Fd`:

> reading the little-endian `uint32` at file offset **0x20** as `BlockSize` and at **0x28** as
> `NumBlocks`, `NumBlocks * BlockSize != <size of the file on disk>`.

with the reporter's specific shape being `NumBlocks == filesize/BlockSize - 1`.

That is a property of **a file dxc writes**, not of anything dxc prints. Nothing dxc emits on
stdout or stderr — and no exit code — carries this information. Recorded here in advance
because it determines the whole shape of the evidence: see "measurement gap" below.

Secondary observations that would refine, but not decide, the verdict:

* off by more than one (the reporter allows for this: "it could be off by more");
* a *different* superblock field being wrong instead;
* `NumBlocks` correct but some other structural invariant violated.

## What does **not** count as the symptom

* `warning: DXIL.dll not found. Resulting DXIL will not be signed...` — the reporter's paste
  includes it, but it is about container signing, not about the PDB container. Whether it has
  any bearing on the PDB has to be established before it is repeated as significant; my prior
  is that it is incidental to their machine and irrelevant here.
* Exit status. A successful compile is expected in every case; the bug is in the artifact.
* Whether the PDB can still be *loaded* by DXC's own reader, or by any particular tool.
  The claim is about header validity, not about round-tripping; a reader that derives the
  block count from the file size will be perfectly happy with a wrong `NumBlocks`. That is
  precisely the reporter's own hedge, and it is the thing that decides severity rather than
  existence.

## Validity has to be established, not assumed

"Invalid header" is an assertion about the MSF container format, so before dating anything I
must establish what the format actually requires of `NumBlocks`. Pre-registered sources, in
descending order of weight:

1. **A conformant reader's validation code** — LLVM's `msf::validateSuperBlock` and
   `PDBFile::parseFileHeaders`, which is the de-facto specification for MSF 7.00 and is what
   `llvm-pdbutil`, LLDB and lld consume PDBs with.
2. **DXC's own container-writing source**, under `lib/DxilContainer/` and `lib/DxilPdbInfo/`.
   Showing in the source that the count omits a block it has just written is far stronger
   evidence than an observation about bytes, and it is also how "off by one" versus "off by
   more" gets settled.
3. The reporter's `FileSize / PageSize` argument, which is a consistency claim rather than a
   spec citation and is therefore the weakest of the three.

It remains possible that the reporter is **right about the bytes and wrong about why**, or
right for a reason they did not give. Both get recorded as found.

## Repro quality

`complete` — the issue supplies a compilable shader and a full command line. Only the paths
have to be made local. The reporter's exact flags, trailing slash on `-Fd` included, are
reproduced first as `cmd-as-filed.txt`; any departure is justified in `cmd.txt`.

## Measurement gap, recorded in advance

Every `match.json` predicate kind (`regex`, `contains`, `internal_failure`, `nonzero_exit`,
`timeout`, and the `any_of`/`all_of` combinators over them) tests **the combined stdout+stderr
text or the exit code**. None of them can inspect a file dxc produced. So the decisive
measurement for this issue cannot be expressed as a predicate at all, and `match.json` will
necessarily be testing something weaker than the symptom.

Consequences, pre-registered so they are not rationalised afterwards:

* the byte-level measurement is made by a committed, re-runnable script in this directory,
  with its verified output captured as `manual-case-*.txt`;
* `match.json` will assert only what a text predicate honestly can — that the compile ran and
  emitted the PDB-producing configuration cleanly — and its `note` will say plainly that it
  does not test the symptom, so that neither `audit` nor any generated report can be read as
  claiming otherwise;
* consequently a `bisect` over `match.json` dates *that* weaker property. Any history claim
  about the **symptom** must come from running the byte measurement across releases, and must
  be labelled as such.

## Decision rule

| observation on ground truth (`main-debug`, ab5400907) | verdict |
| --- | --- |
| `NumBlocks * BlockSize != filesize` | `repros` |
| `NumBlocks * BlockSize == filesize` and no other header field is wrong | `does-not-repro`, then date the change by running the byte measurement across releases |
| header consistent but a different structural defect appears | `changed-behavior` |
| no PDB is produced by the reporter's command at all | investigate the flags before concluding anything; likely `inconclusive` |
