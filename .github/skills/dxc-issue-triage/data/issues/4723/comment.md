> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4723](https://github.com/microsoft/DirectXShaderCompiler/issues/4723).

Still reproduces on `main` (1.9.0.5433, `13730886e`), and it is worse than
"unsupported": under `-P`, the `-M` family writes no depfile and instead
appends the dependency list to the preprocessed output, silently corrupting it.

This changes the issue's category: the title reads as an enhancement request,
but the measured behaviour is a defect in an already-supported flag
combination.

```text
dep4723-artifact depfile-MF dep-preprocess.d MISSING
dep4723-artifact preprocessed-P repro.i PRESENT bytes=354
dep4723-tail repro.i | repro.hlsl: repro.hlsl \
dep4723-tail repro.i |  inc/common.hlsli \
dep4723-tail repro.i |  inc/nested.hlsli
```

Without `-MF`, the same preprocessed file is 291 bytes. The 63-byte
difference is exactly the dependency rule. Feeding the contaminated file back
to DXC produces:

```text
repro.hlsl:9:1: error: unknown type name 'repro'
repro.hlsl: repro.hlsl \
^
```

The `-P` run itself exits 0 with no diagnostic; `-MD` and `-M` behave the same.
The flag is parsed: an invalid `-MF` path is diagnosed in compile mode and
silently accepted under `-P`.

- `DxcContext::Preprocess()` (`dxclib/dxc.cpp`) writes the result blob straight to `-Fi` and
  never reaches `ActOnBlob()`, which is the only place `-MD`/`-MF` are turned into a file.
- In `DxcCompilerObj::Compile` (`dxcompiler/dxcompilerobj.cpp`) the `isPreprocessing` branch
  and the `opts.DumpDependencies` branch both write to the same `outStream`, and the second is
  not suppressed when the first has run.

`HLSLOptions.cpp` already warns for other output flags under `-P`; the `-M`
family is absent from that list.

Unchanged for the life of the issue: v1.7.2207 through v1.9.2607 and `main`
all produce the same 354-byte contaminated file. The five older stable
releases lack `-MF`, so they are unmeasurable rather than clean.

Labels: `bug` and `high-impact` still fit — the corruption is silent and the workflow it breaks
is the one the issue describes. Suggest adding `diagnostic`, since the smallest useful change
here is a warning that these flags are inert under `-P`. Whether to implement the depfile
support itself is a product call.

Compiler Explorer cannot represent this repro: the observable is a multi-file
set of driver outputs, not a single compiled result. Only `dxc.exe` was
measured; the equivalent `dxcompiler.dll` API path remains untested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
