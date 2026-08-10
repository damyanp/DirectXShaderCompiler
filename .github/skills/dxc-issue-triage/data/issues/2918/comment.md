> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2918](https://github.com/microsoft/DirectXShaderCompiler/issues/2918).

**This looks fixed — most likely by [`ac5630e8e`](https://github.com/microsoft/DirectXShaderCompiler/commit/ac5630e8e6e224195a9d39b1b0dbe04275f5c1b8)
("Fixes for adding -Od", #3292, Dec 2020), six months after the report.**

The repro here is a `.pix` capture behind an internal bug number, so it could not be run. What
*could* be done is read the dump as a specification and rebuild an input with the same shape —
a compute shader built `-Od -Zi` with a local array inside a non-inlined helper function — then
run the PIX passes over it on every release available here:

```
dxc  -T cs_6_0 -E main -Od -Zi -Qembed_debug repro.hlsl > module.ll
dxopt module.ll -opt-mod-passes -dxil-dbg-value-to-dbg-declare -dxil-annotate-with-virtual-regs
```

| release | PIX passes | |
| --- | --- | --- |
| v1.4.1907 | — | no `dxil-dbg-value-to-dbg-declare` in that build |
| **v1.5.2010** | **fails, `E_FAIL`** | last release before the fix |
| **v1.6.2104** | succeeds | first release after it |
| v1.6.2106 … v1.9.2607, and `main` (`13730886e`) | succeeds | 14 further builds |

Running only `-dxil-annotate-with-virtual-regs` succeeds on v1.5.2010, so despite the title the
failing pass is `-dxil-dbg-value-to-dbg-declare`.

**Why that commit.** 268 commits sit in that window; three touch
`DxilDbgValueToDbgDeclare.cpp`, and one changes the debug location:

```diff
-  DbgDeclare->setDebugLoc(GetVariableLocation());
+  DbgDeclare->setDebugLoc(m_dbgLoc);
```

`GetVariableLocation()` built its own location and is now `#if 0`'d as unused:

```cpp
const unsigned DefaultColumn = 1;
return llvm::DILocation::get(m_B.getContext(), m_Variable->getLine(),
                             DefaultColumn, m_Variable->getScope());
```

That is the four-argument `DILocation::get` — **`InlinedAt` is null** — with a hard-coded
column of 1. Attached to a `llvm.dbg.declare` the pass had just synthesised in the *entry*
function, for a variable whose scope belongs to the helper, it produces exactly the metadata in
the report:

```
!970 = !DILocation(line: 96, column: 1, scope: !965)     <- column 1, no inlinedAt:
!965 = distinct !DILexicalBlock(scope: !966, ...)        <- scope is inside CullAirprobeVolumes
```

which `Verifier::visitDISubprogram` rejects with `!dbg attachment points at wrong subprogram
for function`. `DxcOptimizer` appends the verifier to the pass pipeline, and a verifier failure
there becomes a thrown `hlsl::Exception` — the `std::exception` in `WinPixEngineHost.exe`. The
commit message says the same thing independently: *"The value-to-declare pass was adding an
incorrect debug location, which tripped up the verifier."*

**Caveats.** The shader above is a **reconstruction written during triage** — not the reported
shader, and no claim is made that it is equivalent to it. And the fix is attributed by narrowing
a 268-commit window in source, not by a bisect: strong, not certain.

Compiler Explorer, for the metadata only: **https://godbolt.org/z/a4qPPYzvK** — CE runs `dxc`
alone and cannot run a PIX pass, and its oldest DXC (1.6.2112) already contains the fix, so both
panes succeed. What they show is the `inlinedAt:` on the `!DILocation`s scoped to the helper's
`DISubprogram` — the field whose absence was the bug.

**If closing needs more than an inference,** nothing private needs to leave Microsoft: re-run
that same `.pix` capture against any DXC ≥ 1.6.2104, or attach the failing DXIL *module text*
(not the shader source) containing the offending `!DILocation`. Either would settle it;
otherwise this seems to be the "no longer relevant" case @damyanp asked about in 2024.

**Suggested labels:** `PIX` and `debug info` both fit and neither is applied — this issue has no
labels at all. `crash` and `bug` also apply to the original report. If it stays open rather than
being closed, `needs repro steps` is the accurate state.

<details>
<summary>Method — repeatable</summary>

The PIX passes are DXIL module passes in `lib/DxilPIXPasses/`, reachable only through
`IDxcOptimizer::RunOptimizer` over an already-compiled module — never from a plain
`dxc file.hlsl`. `dxopt.exe` is the command-line front end for that interface; the pass pairing
above is the one the in-tree tests use (`PixTestUtils.cpp` `RunAnnotationPasses`,
`test/HLSLFileCheck/pix/*.hlsl`). Stage 1 must emit disassembly text: a container written with
`-Fo` has a stripped DXIL part, so the passes then see no debug info and nothing can fail.

Releases ship no `dxopt.exe`, so each release's `dxcompiler.dll` was driven by this repo's
`dxopt.exe` placed beside it. To keep that honest, every measured build got three runs, not one:
a **baseline** (same module, no passes) that must succeed, showing the module went in
verifier-clean; a **control** (same module with `inlinedAt:` removed from one
lexical-block-scoped `!DILocation`, no passes) that must fail, showing that build still performs
the wrong-subprogram check and that the pairing can report a failure at all; and then the
measurement. Both held on every measured build.

One trap if you repeat this: `Verifier::visitDISubprogram` dedupes through a `Seen` set, and
when a location's scope *is* a `DISubprogram` the scope and the subprogram are the same node, so
the second insert fails and the check is skipped entirely. Breaking a location whose scope is a
`DISubprogram` produces no diagnostic. The control has to use a `DILexicalBlock`-scoped
location — which is what the report's `!965` is.

</details>

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
