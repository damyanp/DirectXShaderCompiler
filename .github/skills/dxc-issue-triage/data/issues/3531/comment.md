> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3531](https://github.com/microsoft/DirectXShaderCompiler/issues/3531).

Still reproduces on `main` (1.9.0.5433, `13730886e`) and on every stable release that can
compile the repro: v1.6.2104 through v1.9.2607. v1.4.1907 and v1.5.2010 answer
`error: invalid profile cs_6_6`, so SM 6.6 predates them.

The snippet needs one repair to compile — `floatRWUAV` is never declared; I added
`RWBuffer<float> floatRWUAV : register(u0);` and changed nothing else. Built with
`-T cs_6_6 -E DynamicResources -Zi -Qembed_debug`, the DXIL carries three debug-variable
entries:

```llvm
!11 = !DIGlobalVariable(name: "DynamicBuffer", scope: !0, file: !1, line: 10, type: !12, isLocal: true, isDefinition: true)
!13 = !DIGlobalVariable(name: "floatRWUAV", linkageName: "\01?floatRWUAV@@3V?$RWBuffer@M@@A", scope: !0, file: !1, line: 8, type: !14, isLocal: false, isDefinition: true)
!42 = !DILocalVariable(tag: DW_TAG_auto_variable, name: "val", scope: !7, file: !1, line: 14, type: !43)
```

and none for `DynamicallyIndexedDynamicBuffer`. Its `createHandleFromHeap` does keep a source
location (`!dbg ... line:15 col:59`), so what is missing is the variable entry rather than
every trace of the declaration.

Two things the triage adds to the report:

- **It is not specific to dynamic resources.** The same shader with the local aliasing a bound
  `RWByteAddressBuffer : register(u1)` also gets no `!DILocalVariable`. Dynamic resources are
  where it bites, because there is no binding for a tool to fall back on.
- **The front end emits it and DXIL lowering drops it.** At `-fcgl` both the variable and its
  declare are present:
  `!55 = !DILocalVariable(tag: DW_TAG_auto_variable, name: "DynamicallyIndexedDynamicBuffer", scope: !7, file: !1, line: 15, type: !12)`.
  `-Od` shows the same three entries and the same absence, so it is not an optimisation
  artefact.

Control for the absence: changing that local's type to `uint` and nothing else makes
`!DILocalVariable(... name: "DynamicallyIndexedDynamicBuffer" ... line: 15)` appear — on main
and on all 18 releases that compile the repro. So each of those compilers could name the
variable and did not.

[Compiler Explorer](https://godbolt.org/z/b11P9EvaG) — dxc 1.6.2112 and trunk, same result.
Note that Compiler Explorer appends `-Zi -Qembed_debug -Fc -` to every DXC pane; here that
matches the flags used locally, and the banner shifts pane line numbers relative to the ones
quoted above.

Label suggestion: add `debug info`; `bug` still fits.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
