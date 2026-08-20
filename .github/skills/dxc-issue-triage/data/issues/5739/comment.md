> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5739](https://github.com/microsoft/DirectXShaderCompiler/issues/5739).

Still reproduces on `main` (commit 13730886e, built locally at
89e2f98e29c289ae8ad9e00dd310104fea9fd7df, which is source-identical to that public
commit).

Using the repro from the issue: after `dxc -T lib_6_3 -Zi -Qembed_debug -Fd testc.pdb ...`
then `dxc -link ... -Zi -Fd test.pdb ...`, `dxc -dumpbin` shows the difference directly:

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

`testc.pdb` starts with the standard MSF7 PDB magic
(`Microsoft C/C++ MSF 7.00\r\n\x1aDS...`); `test.pdb` starts with `DXIL` followed by the
raw LLVM bitcode magic (`BC\xc0\xde`) — it's the ILDB part's bytes with no PDB container
around them, so `-dumpbin` disassembles it but can't print a debug name.

Checked history across every stable release that supports `-link` at all (v1.6.2106,
2021-07-01, onward — `-link` itself didn't exist before that): every one reproduces the
same symptom, so this has never worked since the linker CLI shipped, and the 2023-09-18
report sits in the middle of that range, not near either end.

Two open PRs already target this: #6833 ("Fix `-link -Qstrip_debug` failing") and #6834
("Add PDB output to linker"). Neither is merged yet.

Suggested labels: keep `bug`, `shader-linking`, `debug info` — no changes needed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
