> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2673](https://github.com/microsoft/DirectXShaderCompiler/issues/2673).

Still reproduces on `main` (1.9.0.5433, `13730886e`), and on all 20 releases tested, from
v1.4.1907 (2019-07) through v1.9.2607. v1.4.1907 predates this report, so the defines have
been duplicated for as long as it is possible to check.

Compiling the cited `share_mem_dbg.hlsl` with its own `RUN:` line, `dxc.exe` driven from the
command line, gives the node exactly as filed:

```
!dx.source.defines = !{!70}
!70 = !{!"DefineA=1", !"DefineB=0", !"DefineA=1", !"DefineB=0"}
```

`!dx.source.args` shows it one layer earlier — the `-D` pair appears once where it was typed
and again after `-Qstrip_reflect`:

```
!72 = !{!"-E", !"main", !"-T", !"cs_6_0", !"-Zi", !"-Od", !"-D", !"DefineA", !"-D",
        !"DefineB=0", !"-Qstrip_reflect", !"-D", !"DefineA", !"-D", !"DefineB=0",
        !"-Qembed_debug"}
```

Compiler Explorer, `dxc_1_6_2112` and `dxc_trunk`: https://godbolt.org/z/qa68hEf4z

The compile succeeds and the DXIL is unaffected; only the recorded defines are wrong. With a
single `-D` the node is `!{!"DefineA=1", !"DefineA=1"}`, so the whole list is applied twice
rather than this being a two-define quirk.

### Where it happens

`DxcContext::Compile` passes `IDxcCompiler::Compile` both the argument array — still holding
the user's `-D` flags — and `m_Opts.Defines`, which the option parser extracted from those same
flags (`tools/clang/tools/dxclib/dxc.cpp:881-885`). `BuildArguments` then appends a fresh
`-D <name>` for every entry of the defines array
(`tools/clang/tools/dxcompiler/dxclibrary.cpp:506-508`), and that doubled list is what reaches
`PPOpts.addMacroDef` and `CodeGenOpts.HLSLDefines`.

Immediately above, `BuildArguments` routes arguments through
`AddArgumentsOptionallySkippingEntryAndTarget`, whose comment reads: *"skip extra entry/profile
arguments in the arg list when already specified separatly. This would lead to duplicate or
even contradictory arguments in the arg list, visible in debug information."* Defines arrive by
the same route and get no such treatment.

That accounts for the configuration dependence in the report, which still holds. The harness
running `share_mem_dbg.hlsl` calls `Compile(..., flags.data(), flags.size(), nullptr, 0, ...)`
(`tools/clang/unittests/HLSLTestLib/FileCheckerTest.cpp:573-575`), so nothing is appended and
the `CHECK` line passes. The trigger is a caller supplying the defines *both* ways, as
`dxc.cpp` does, so the test cannot catch it as written. Only the command-line path was
measured; the statement about the API path is from source.

The same metadata is what `IDxcPdbUtils` and the PIX/DIA compilation-info surfaces report as a
compile's defines, so this is not purely cosmetic for tooling reading a PDB.

Suggested labels: `bug`, `debug info` (currently none). Not `correctness` — the generated DXIL
is unaffected.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
