# Issue #5739 -- DXC linker debug output isn't a valid PDB (and doesn't work with PIX)

## Repro

`repro.hlsl` is the reporter's exact shader with one addition: a `[shader("compute")]`
attribute on `main` (see "Deviation from the filed repro" below). `cmd.txt` runs the
reporter's exact two dxc invocations (compile with `-Zi -Qembed_debug -Fd testc.pdb`,
then `-link ... -Zi -Fd test.pdb`), followed by a third `dxc -dumpbin test.pdb` step
that turns the produced file's byte layout into text `triage.py` can score (see
`match.json` and `expected.md` for why).

## Result: reproduces on main-debug (89e2f98e29c289ae8ad9e00dd310104fea9fd7df, public
main 13730886e)

```
$ dxc -dumpbin testc.pdb        (compile step's own -Fd output)
; shader debug name: testc.pdb
; shader hash: eba41e9d71c52c629a3e63dca25af48a
;
; Buffer Definitions:
...

$ dxc -dumpbin test.pdb         (link step's -Fd output)
;
; Buffer Definitions:
...
```

`testc.pdb` begins with the standard MSF7 magic
(`4d 69 63 72 6f 73 6f 66 74 20 43 2f 43 2b 2b 20 4d 53 46 20 37 2e 30 30 0d 0a 1a 44 53`
= `"Microsoft C/C++ MSF 7.00\r\n\x1aDS"`) and dxc's own `-dumpbin` recognises it as a PDB,
printing a `shader debug name:` / `shader hash:` header before the disassembly. `test.pdb`
begins with `44 58 49 4c` = `"DXIL"` followed immediately by `42 43 c0 de` = the raw LLVM
bitcode magic -- i.e. it is the ILDB part's bytes with no MSF wrapper at all, and
`-dumpbin` disassembles it (because dumpbin can load bare bitcode too) but cannot print a
debug name, because there is nothing that looks like a PDB compiland stream to read one
from. This is exactly the reported symptom: the link step's `-Fd` output is not a valid
PDB, unlike the compile step's.

Captured in `out-main-debug.txt` (primary) and cross-checked by hand against the raw
bytes (`Show-Header` dump in this session; not separately committed since the dumpbin
text capture already demonstrates the same fact and is what `match.json` scores).

## Control

`variant-control-valid-pdb-main-debug.txt`: `dxc -dumpbin testc.pdb` (the compile step's
own, genuinely valid, `-Fd` output) on the same directory scores `no-repro` against
`match.json`, i.e. the predicate's absence clause does NOT fire on a real PDB. This is the
self-test that the predicate can tell a real PDB from the raw dump, not just that
`-dumpbin` always omits the line.

## History

`bisect --linear` (all stable releases, `.cache` + test-seeded trees):

- v1.4.1907, v1.5.2010, v1.6.2104: `invalid-probe` -- `dxc failed : Unknown argument:
  '-link'`. The `-link` standalone-linker driver flag itself did not exist yet; this is a
  real feature-absence (confirmed by the literal "Unknown argument" diagnostic on all
  three), not an artefact of an unrelated flag, so `bisect` correctly excludes them.
- v1.6.2106 (2021-07-01) through v1.9.2607 (current), plus main-debug: **repro** on every
  probed release, no exceptions.

**Always reproduced for the entire lifetime of the `-link` CLI feature.** There is no
release in the catalog where linking with `-Fd` ever produced a valid PDB. The reporter's
2023-09-18 report (against v1.7.2207.3) sits in the middle of this always-broken range,
not near either end.

## Deviation from the filed repro

The issue's literal shader (`repro-as-filed.hlsl`, no `[shader(...)]` attribute) compiles
fine standalone but its **link** step fails on current main-debug with
`error: Library has no functions to export` (`variant-as-filed-main-debug.txt`, hypothesis
recorded and confirmed: expected `no-match`/no evidence, scored `no-repro` because
`test.pdb` was never produced -- `dumpbin` reports "The system cannot find the file
specified"). This is an unrelated, separate requirement that appeared at some point after
the report (a numthreads-only compute entry point in a `lib_6_x` target needs an explicit
`[shader("compute")]` attribute to be recognised as an export candidate); it is not
investigated further here since it is not what #5739 is about, and no verdict is drawn
from it beyond documenting why `cmd.txt` differs from `cmd-as-filed.txt`.

Confirmed the reporter's literal, unmodified repro (`repro-as-filed.hlsl` +
`cmd-as-filed.txt`) links and reproduces identically at the reporter's own version,
**v1.7.2207 (2022-07-18)**, matching their reported build (`dxcompiler.dll: 1.7 -
1.7.2207.3 (e9137cd1d)`, checked with `dxc --version` against that cached release
binary): compile exit 0, link exit 0, `test.pdb` begins `63 00 06 00 0f 03 00 00 44 58 49
4c ...` ("DXIL..." raw bitcode, no MSF7 magic) while `testc.pdb` begins with the MSF7
magic, same as on main-debug. This establishes the captured evidence is the reporter's
own instance of the bug, not merely a similar-looking reconstruction.

`repro.hlsl` (with the added attribute) was also checked for validity as a probe across
the full stable-release range in the `bisect --linear` run above: every release from
v1.6.2106 onward accepts it and links successfully (no `invalid-probe` verdicts other
than the three pre-`-link` releases), so the added attribute does not itself narrow the
history and the `always-repro'd` finding covers the same range the literal repro would
have, had it kept linking.

## Related open PRs (unmerged, no fix landed)

Two open PRs cross-reference this issue (pre-existing timeline events, both predate this
session -- confirmed via `gh api .../timeline`, `2024-07-30T00:48:52Z` and
`2024-07-30T01:27:27Z`):

- #6833 "Fix `-link -Qstrip_debug` failing" (open, unmerged)
- #6834 "Add PDB output to linker" (open, unmerged)

Both remain open and unmerged as of this triage, consistent with the bug still
reproducing on current main. #6834's title ("Add PDB output to linker") suggests the
maintainers' own diagnosis matches this triage's finding: the linker does not currently
produce PDB output at all, despite accepting `-Fd`.

## Compiler Explorer

Not published. CE's oldest DXC (`dxc_1_6_2112`) and `dxc_trunk` are single-file, and this
repro is inherently two `dxc` invocations against an intermediate `.lib` container passed
between them -- CE cannot express a "compile to library, then link" pipeline in one pane.
A single-file CE pane could show only the (accurate but partial) fact that `-Zi
-Qembed_debug` alone produces a well-formed PDB, which is not in dispute; it cannot show
the link step's broken output at all. `godbolt --skip` reasoning recorded here rather than
forcing a misleading link.
