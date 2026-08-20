> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5357](https://github.com/microsoft/DirectXShaderCompiler/issues/5357).

**Still reproduces** on `main` (`89e2f98e2`), Debug build, on the shader tex3d posted here in
January 2024:

```hlsl
struct RECORD1 { uint value; };
[Shader("node")] [NodeLaunch("broadcasting")] [NodeDispatchGrid(1,1,1)] [NumThreads(128,1,1)]
void node_1_1([NodeArraySize(128)] [MaxRecords(64)] NodeOutputArray<RECORD1> OutputArray) {
    OutputArray[1].GetThreadNodeOutputRecords(2).OutputComplete();
}
```

```
$ dxc -T lib_6_8 repro.hlsl
Internal compiler error: LLVM Assert          # exit 0xE0000001
```

Under a debugger:

```
Error: assert(pAnno != nullptr && pAnno->GetNumTemplateArgs() == 1 &&
       "otherwise the node record template is not declared properly")
File:  tools\clang\lib\CodeGen\CGHLSLMSFinishCodeGen.cpp(1071)
Func:  AddOpcodeParamForIntrinsic
```

That is exactly the function and file anupamachandra named in this thread. `pAnno` is null
because chaining `GetThreadNodeOutputRecords(2)` straight into `.OutputComplete()` — with no
bound local in between — is the shape that skips the type-annotation path, as the issue
describes. Binding the intermediate result first (`ThreadNodeOutputRecords<RECORD1> outRec =
...; outRec.OutputComplete();`, the shape every existing test uses) compiles cleanly.

**Not Debug-only.** The check compiled out under `NDEBUG` still leaves the null flowing on:
every catalogued stable release that supports `lib_6_8` (`v1.8.2403` through `v1.9.2607`) takes
an access violation instead (`Internal compiler error: access violation. Attempted to read
from address 0x0000000000000028`), and [Compiler Explorer](https://godbolt.org/z/eqjMv4v5Y)
shows the same fault on Linux `dxc_trunk` as `SIGSEGV`. Releases predating `v1.8.2403` reject
`lib_6_8` outright (`error: invalid profile lib_6_8` — Work Graphs didn't exist yet), so this
has reproduced for as long as the feature has been checkable.

PR [#6227](https://github.com/microsoft/DirectXShaderCompiler/pull/6227) ("Fixes: #5357") has
been open in draft, with its own "TODO: Add tests" unaddressed, since January 2024 and is still
unmerged.

Suggested labels: add **`bug`** and **`crash`** — this is a reproducing internal crash, not
only prospective tech debt. Keep `tech-debt`, since the issue's broader ask (auditing every
reference-returning intrinsic/operator for the same gap) remains open beyond this one confirmed
instance.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
