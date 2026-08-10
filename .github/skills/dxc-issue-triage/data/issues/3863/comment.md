> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3863](https://github.com/microsoft/DirectXShaderCompiler/issues/3863).

Still reproduces on `main` (1.9.0.5433, `13730886e`), and on **all 21 stable
releases from v1.4.1907 to v1.9.2607** — every one of them accepted `-H` under
`-P`, and none of them printed anything.

```
$ dxc -T ps_6_0 -E main -H control-compile.hlsl
; Opening file [./inc-comp-a.h], stack top [0]
; Opening file [./inc-comp-b.h], stack top [1]

$ dxc -P repro.hlsl -Fi preprocessed.i -H
[exit] 0
--- stdout ---

--- stderr ---
```

`-H` is parsed, not swallowed: an unknown dash-flag in the same position exits 1
with `dxc failed : Unknown argument: '-ZZZNONSENSE3863'`. It is also completely
inert — the preprocessed output is byte-identical (SHA-256) with `-H`, with
`-Vi`, and with neither.

**The trace is not missing; it is dropped.** `EnableDisplayIncludeProcess()`
runs before the `isPreprocessing` branch
([dxcompilerobj.cpp#L674](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/tools/clang/tools/dxcompiler/dxcompilerobj.cpp#L674)),
and the common tail stores stdout into `DXC_OUT_REMARKS` for both paths.
Driving `IDxcCompiler3::Compile` directly with `-P -Fi out.i -H` confirms it —
the API already returns exactly what this issue asks for:

```
IDxcResult::GetOutput(DXC_OUT_REMARKS) ->
Opening file [./inc-pp-a.h], stack top [0]
Opening file [./inc-pp-b.h], stack top [1]
```

(controls: without `-H` that output is empty; on a normal compile it is
present.) `DxcContext::Compile()` prints it —
[dxc.cpp#L918](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/tools/clang/tools/dxclib/dxc.cpp#L918)
— while `DxcContext::Preprocess()`
([dxc.cpp#L1005](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/tools/clang/tools/dxclib/dxc.cpp#L1005))
never asks for it. The combination is not diagnosed and is absent from the
"compiler options ignored with Preprocess" warning list
([HLSLOptions.cpp#L980](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/lib/DxcSupport/HLSLOptions.cpp#L980)),
so this looks unimplemented rather than deliberately rejected.

Since 2021 the dependency-listing flags referenced in the 2021-11-18 comment
did land: `-M` prints the include list from **v1.7.2207** onward, and composes
with `-H`. It is a compile mode, though — it needs `-T`, and it does not
combine with `-P`.

```
$ dxc -T ps_6_0 -E main -M -H repro.hlsl
repro.hlsl: repro.hlsl \
 inc-pp-a.h \
 inc-pp-b.h

; Opening file [./inc-pp-a.h], stack top [0]
; Opening file [./inc-pp-b.h], stack top [1]
```

Suggested labels: **`usability`** (today's alternative is a full compile you did
not want) and **`low-hanging-fruit`** — the data is already produced and already
returned by the library, so the remaining work is confined to the `dxc.exe`
preprocess path. Whether to do it is a maintainer call.

No Compiler Explorer link: the symptom is a *missing* include trace, a CE pane
is single-source, and with no header to open `-H` prints nothing there even on a
normal compile — so a pane could show neither the symptom nor the working case.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
