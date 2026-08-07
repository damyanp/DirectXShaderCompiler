> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2604](https://github.com/microsoft/DirectXShaderCompiler/issues/2604).

This remains unimplemented on upstream `main` (`1.9.0.5433`, `13730886e`) and
all 21 measured release DLLs from v1.4.1907 through v1.9.2607.

For `-T ps_6_0 -E main -Fc out.asm`, both API entry points return a result
whose status is `E_INVALIDARG`:

```
IDxcCompiler::Compile    call=S_OK  status=0x80070057  "Unknown argument: '-Fc'"
IDxcCompiler3::Compile   call=S_OK  status=0x80070057  "Unknown argument: '-Fc'"
```

With `-Qunused-arguments`, compilation succeeds but `-Fc` is ignored: no file
and no `DXC_OUT_DISASSEMBLY`. `IDxcCompiler::Disassemble` returns a 4104-byte
listing, and `dxc.exe` writes an assembly file.

`-Fc` is
[`DriverOption` only](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e6a9019e4e0823746470f3ab75341d6b/include/dxc/Support/HLSLOptions.td#L505);
the library parses `CoreOption`, while the driver includes `DriverOption`.
Simply adding `CoreOption` would only silence the error: the API compile path
does not use `opts.AssemblyCode` to produce `DXC_OUT_DISASSEMBLY`. The
implementation needs to make `Compile` return the requested listing.

There is also a documentation mismatch:
[`docs/SPIR-V.rst`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e6a9019e4e0823746470f3ab75341d6b/docs/SPIR-V.rst#L4197-L4211)
says `-Fc` is recognized by library API calls, but the measured SPIR-V API
behavior is the same rejection/ignore split above.

I would treat this as an API enhancement rather than a compiler bug. Suggested
labels: `api`, and `up-for-grabs` if the 2024 invitation for a PR still stands.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
