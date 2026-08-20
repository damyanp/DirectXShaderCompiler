# Expected symptom (written before running `triage.py run`)

Issue #5739: "DXC linker debug output isn't a valid PDB (and doesn't work with PIX)".

Reported steps: compile a `lib_6_3` shader with `-Zi -Qembed_debug -Fd testc.pdb`, then
link that library with `dxc -link ... -Zi -Fd test.pdb`. The reporter says the *compile*
step's `-Fd` output (`testc.pdb`) has a valid PDB header, but the *link* step's `-Fd`
output (`test.pdb`) does not, and will not load in PIX.

**Reproduces** means: the file the link step writes via `-Fd` does not begin with the
standard MSF7 PDB magic (`Microsoft C/C++ MSF 7.00\r\n\x1aDS\0\0\0`) the way the compile
step's `-Fd` output does -- i.e. it looks like a raw DXIL/ILDB part dump rather than a
container PDB.

**Repro quality: complete.** The issue gives an exact two-command repro and a literal
shader. One deviation was needed to get it to link at all against a current build (see
`cmd.txt` vs `cmd-as-filed.txt` below); that deviation is unrelated to the PDB-validity
question and is recorded, not silently made.

**Predicate approach:** the symptom is a property of a produced binary file's bytes, not
of anything dxc prints to stdout for the compile/link steps themselves. `dxc -dumpbin`
loads an arbitrary binary and, for a genuine PDB, prints a `; shader debug name: <path>`
/ `; shader hash: <hex>` header before the disassembly; for a bare DXIL/bitcode blob it
does not, because there is no PDB "compiland" stream to read that name from. So
`cmd.txt` chains compile -> link -> `-dumpbin` on the link's `-Fd` output, and the
predicate is: the dumpbin disassembly clearly succeeded (anchor: `Resource Bindings:`)
**and** it printed no `shader debug name:` line. This was verified by hand first (see
`notes.md`) against both `testc.pdb` (valid, shows the line) and `test.pdb` (invalid,
does not) on both `main-debug` and the reporter's own v1.7.2207.3 release.

Absence-only predicates are vacuously satisfied by a failed compile/link/dumpbin, so the
positive anchor (`Resource Bindings:`) is required in the same predicate, not just
asserted in prose.
