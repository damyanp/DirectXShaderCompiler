> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#3768](https://github.com/microsoft/DirectXShaderCompiler/issues/3768).

**This appears to be fixed.** It no longer reproduces on `main` (1.9.0.15422, `eff900d5`) or in
any release from v1.6.2112 through v1.9.2607.

Running `tools/clang/test/CodeGenSPIRV/intrinsics.printf.hlsl` against every SPIR-V-capable
release puts the failure in a narrow window:

| Release | Result |
| --- | --- |
| v1.5.2010 | compiles cleanly |
| v1.6.2104 | **crashes — `STATUS_HEAP_CORRUPTION` (`0xC0000374`)** |
| v1.6.2106 | **crashes — same** |
| v1.6.2112 → v1.9.2607 | compiles cleanly |

(v1.4.1907 can't be probed — that build has no SPIR-V codegen.) `0xC0000374` is consistent with
the corruption Application Verifier reported.

**The crash is intermittent, as you suspected.** In the affected releases it fires on 27/40 runs
at v1.6.2104 and 33/40 at v1.6.2106, so a single clean run there would not rule it out. The
v1.9.2607 release binary was clean in 55/55 runs (`ps_6_0` as originally reported, and
`cs_6_0`). A `main` Debug build was also clean in 55/55, though your local Debug build worked
too, so that configuration proves less. Output was inspected on current `main`: the DebugPrintf
import, six `OpString`s and six matching `OpExtInst` calls, as expected.

**The `-fcgl -Vd` flags are no longer needed for this test case**, and the 110 current-build runs
above omit them, so legalization and validation actually run. The SPIRV-Tools crash they were
avoiding (KhronosGroup/SPIRV-Tools#4219) was fixed by KhronosGroup/SPIRV-Tools#4280, merged the
day after you filed this. They also do not appear to have been masking anything here: at
v1.6.2104 and v1.6.2106, all four combinations (`-fcgl -Vd`, each alone, and neither) crash at
similar rates.

Current test case: https://godbolt.org/z/e5KT1E6W9 — Compiler Explorer's oldest DXC is 1.6.2112,
already past the affected window, so it can only show current behaviour.

Worth noting before closing: the Application Verifier / page-heap check was not re-run, and it
detected the corruption earlier than the retail heap did.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
