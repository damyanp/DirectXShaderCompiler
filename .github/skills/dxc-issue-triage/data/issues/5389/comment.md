> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5389](https://github.com/microsoft/DirectXShaderCompiler/issues/5389).

Still reproduces on `main` (Debug build, commit
[89e2f98](https://github.com/microsoft/DirectXShaderCompiler/commit/89e2f98e29c289ae8ad9e00dd310104fea9fd7df)).

Reporter's minimal repro
([comment](https://github.com/microsoft/DirectXShaderCompiler/issues/5389#issuecomment-2332351850)):

```hlsl
RWByteAddressBuffer sb : register(u0);
[numthreads(1, 1, 1)]
void main() {
  sb.Store(0, asuint(int2(123, 123))); // Okay
  sb.Store(0, asuint((123).xx)); // Boom
}
```

- On a Debug (assert-enabled) build, trips the `CallInst::init` "Calling a function with a
  bad signature!" assert.
- On every stable release binary from v1.4.1907 through v1.9.2607, and on today's Compiler
  Explorer `dxc_trunk`, the assert is compiled out and the malformed call instead fails DXIL
  validation (`Invalid record` / `Validation failed.` — CE's older `dxc_1_6_2112` prints a
  differently-worded but equivalent diagnostic, `Call parameter type does not match function
  signature!`).
- Linear scan of all 20 probeable stable releases (v1.4.1907..v1.9.2607): repros on all 20; no
  invalid probes.

[Compiler Explorer link](https://godbolt.org/z/Y45Yhd3P5) — 4 panes over the same source:
default mode fails on both `dxc_1_6_2112` and current `dxc_trunk`. `-HV 2021` also still
fails and is not a workaround; only the still-experimental `-HV 202x` preview mode compiles
clean.

Separately, #5082 (filed earlier, same underlying bare-literal-swizzle-into-fixed-width-arg
defect at a different call site) was closed on the same "fixed in HLSL 202x" reasoning
(2024-08-28); this issue later got pushback on that same reasoning (2024-09-10) and was
marked dormant instead (2024-09-12). Noting the difference for awareness, not proposing
either be revisited.

Suggested labels: `crash` (the Debug-build assert), `type-system` (the likely root-cause
area — literal constant-folding/typing across a swizzle), `hlsl-next` and `up-for-grabs` (per
the maintainer's own framing: fixed by the language change, and a targeted codegen fix would
be reviewed).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
