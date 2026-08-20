> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#6073](https://github.com/microsoft/DirectXShaderCompiler/issues/6073).

Still reproduces on `main` and on every stable release that can parse HLSL
templates at all (v1.7.2308 through v1.9.2607, the latest).

On the shipping release binaries (asserts compiled out), the repro produces
the exact text quoted in this issue, byte-for-byte, including the mangled
name:

```
Declaration may not be in a Comdat!
i32* @"\01?Num@?$Test@$0CK@@@2HA"
```

On a Debug build this same repro instead crashes earlier, in
`clang::LinkageComputer::getLVForDecl` (a Debug-only assert), before ever
reaching that verifier check -- confirmed to be the same defect by continuing
the debug session past that assert (which is what a Release build does since
the check compiles out) and observing it land on the identical Comdat text.

Both patterns this issue says already work (a non-templated struct with a
non-const static member, and a templated struct with a `static const`
member) still compile cleanly, matching the report.

Releases older than v1.7.2308 don't support HLSL templates yet, so they can't
run this repro at all -- they're not evidence of anything, including a fix.
No release has ever compiled this pattern.

[Compiler Explorer](https://godbolt.org/z/17nh9j5fW): the oldest DXC there
predates templates, and `dxc_trunk` fails with `LLVM ERROR: Broken module
found, compilation aborted!` (matching the local release measurement, though
CE's pane doesn't surface the intermediate Comdat line).

Given @llvm-beanz's comment that a durable fix may need a language change,
consider adding `hlsl-next` alongside the existing `bug`/`crash`/`correctness`
labels.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
