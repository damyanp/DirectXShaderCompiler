> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3005](https://github.com/microsoft/DirectXShaderCompiler/issues/3005).

Still reproduces on `main` (1.9.0.5433, `ab5400907`). The more actionable finding is
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
