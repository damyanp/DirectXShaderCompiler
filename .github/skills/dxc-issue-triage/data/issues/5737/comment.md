> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5737](https://github.com/microsoft/DirectXShaderCompiler/issues/5737).

Still reproduces on `main` (commit `13730886e`).

```
dxc.exe -T lib_6_3 -Zi -Qstrip_reflect -Qembed_debug -Fd testc.pdb -Fo test.lib test.hlsl
dxc.exe -link -T lib_6_3 -Zi -Qstrip_reflect -Qstrip_debug -Fd test.pdb -Fo test.bin test.lib
```
```
dxc failed : DXIL container does not contain the given part.
```

The failure is actually broader than `-Fd` + `-Qstrip_debug` combined:
`-link -Qstrip_debug` alone, with no `-Fd` at all, fails identically. So the
defect is in linking with `-Qstrip_debug`, not specifically in the
interaction with `-Fd`.

[PR #6833](https://github.com/microsoft/DirectXShaderCompiler/pull/6833)
("Fix -link -Qstrip_debug failing") already targets this and says it fixes
this issue, but it is still open and unmerged.

Bisected across every release with the built-in `-link` mode
(v1.6.2106, 2021-07-01, onward through v1.9.2607): always fails, so this
was never fixed and always affects that whole range, including the
reporter's v1.7.2207.3.

Labels (`bug`, `shader-linking`) look right as-is.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
