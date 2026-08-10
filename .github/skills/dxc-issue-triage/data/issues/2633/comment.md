> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2633](https://github.com/microsoft/DirectXShaderCompiler/issues/2633).

Tested on `main` (`13730886e`) and on every release back to v1.5.2010. **Half of what
this issue asks for already works and has since v1.6.2104; the other half is still
absent.**

**Producing a library module works.** An `export` function gets SPIR-V linkage
decorations today:

```
dxc -T lib_6_3 -spirv -fspv-target-env=universal1.5 lib-export.hlsl
```
```
OpCapability Linkage
OpDecorate %foo LinkageAttributes "foo" Export
```

`-fspv-target-env=universal1.5` is required — under a Vulkan target env the same
compile stops at `Capability Linkage is not allowed by Vulkan 1.0 specification`,
which is expected for a module that is meant to be linked before a driver sees it.
This first appears in v1.6.2104 (v1.5.2010 does not emit it); PR #3234 looks to be
where it came in.

**Consuming one does not work.** Compiling the other side — @s-perron's example from
this thread, a declared-but-undefined `foo` — still fails on `main` and on all 19
releases from v1.5.2010 to v1.9.2607:

```
repro.hlsl:27:21: error: found undefined function
```

DXC rejects the unresolved call rather than emitting an `Import` decoration, so there
is nothing for `spirv-link` to resolve against. I found no user-code workaround:
`-default-linkage external` is DXIL-only; `dxc -link` rejects SPIR-V as
`Invalid DXIL container`; and the inline attributes split integer and string operands,
so neither can express `LinkageAttributes`.

**Clang's HLSL SPIR-V backend emits both decorations** for the same source without
`universal1.5`. It uses Itanium mangling (`_Z3fooDv4_f`) versus DXC's plain source name
(`foo`), so their modules would not currently resolve each other's symbols.

All five cases side by side: **https://godbolt.org/z/ca49jMrrc** (panes 1–2 export on
dxc, pane 3 import on dxc, panes 4–5 both on clang). Compiler Explorer is single-file,
so the two halves are `#ifdef`-selected in one source rather than separately compiled
and linked — it shows what each compiler emits, not a completed link.

The remaining design questions are the `Import` decoration, global variables, and
`lib_6_x` backwards compatibility, as @s-perron set out in
[this comment](https://github.com/microsoft/DirectXShaderCompiler/issues/2633#issuecomment-2253075613).
Triage does not decide them or imply an implementation commitment.

Suggested label: add `question` — the report is a question about a capability rather
than a defect, and `enhancement` alone does not distinguish the two. (`shader-linking`
looks apt by name but is used exclusively for DXIL linker bugs, so it would misroute
this.)

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
