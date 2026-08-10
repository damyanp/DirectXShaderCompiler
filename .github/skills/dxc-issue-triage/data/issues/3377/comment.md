> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3377](https://github.com/microsoft/DirectXShaderCompiler/issues/3377).

**Still reproduces on `main` (1.9.0.5433, `13730886e`), and on every one of the 20 release
binaries from v1.4.1907 (2019-07) to v1.9.2607.** The oldest predates the report by 18 months
and already fails. The repro in the body works exactly as filed, with no edits.

```
$ dxc -T ps_6_0 -E main_fragment repro.hlsl
Internal compiler error: Terminal Error 0x80000003
```

That is all a plain run prints — the assert text goes to `OutputDebugString`. Under `cdb`:

```
Error: 	!(argIdx < endArgIdx)
File:
C:\...\lib\Transforms\Scalar\ScalarReplAggregatesHLSL.cpp(4791)
Func:	AllocateSemanticIndex.
	arg index out of bound
```

reached as `SROA_Parameter_HLSL::flattenArgument` → `allocateSemanticIndex` →
`AllocateSemanticIndex` (recursing four deep) — @Dwedit's 2021 frames, in the same order.

### The reported release crash and this Debug assert are the same failure

Releases are Release builds, where `DXASSERT` is `do { } while (0)`
(`include/dxc/Support/Global.h:356`), so a quiet release binary is not evidence of a fix.
Continuing past the traps under `cdb`, which then runs what a release build runs, reaches
`STATUS_HEAP_CORRUPTION` and dies in `memcpy` under
`DxilParameterAnnotation::AppendSemanticIndex` ← `AllocateSemanticIndex` ← `allocateSemanticIndex`
← `flattenArgument` — @Dwedit's stack frame for frame, including "crashes in a memory copy".

### Smaller repro

@damyanp's 2024 reading holds, and reduces further — no matrix, no `SamplerState`, no second
entry point, and `uniform` is not needed either:

```hlsl
float4 main_fragment(Texture2D<float4> decal : TEXUNIT0) : SV_Target {
  return decal.Load(int3(0, 0, 0));
}
```

Same assert, same line, same frames. In everything tested, the trigger is a semantic on a
resource-typed entry-point parameter.

**Both spellings fail.** Remove the `: TEXUNIT0` and DXC asks for it back:

```
error: Semantic must be defined for all parameters of an entry function or patch constant function
```

(exit `0x80004005`, identical on v1.4.1907, `main` and v1.9.2607).

### Both attempted fixes lapsed

Two PRs reference this issue and neither landed:

- **#4538** "Add extra type null checking to prevent AV" (Jul 2022) — closed unmerged Mar 2024.
- **#4554** "param validation for uniform / resources in entry point functions" (Jul 2022),
  whose body says *"This was causing AV problems as described in #3377"* — closed unmerged
  Feb 2025: *"Merge conflicts, and according to @Tex3D it seems like this is the wrong
  direction"*.

Nothing has replaced them.

### One note for anyone matching on output

Across 10 runs each on four builds, all 40 failed; none printed a source diagnostic or emitted
DXIL. **8 of the 20 release captures have empty stderr** (v1.4.1907, v1.5.2010, v1.7.2308,
v1.8.2405, v1.8.2502, v1.8.2505, v1.8.2505.1, v1.9.2602), and v1.8.2502 alternates run to run
between a silent `0xC0000409` (`STATUS_STACK_BUFFER_OVERRUN`) and a `0xC0000005` with a message.
Exit status is the only reliable signal.

FXC 10.1 compiles the body's shader as `ps_5_0` with exit 0, so the report's opening comparison
also still holds.

Compiler Explorer: **https://godbolt.org/z/rqvfvYc93** — FXC succeeds; `dxc_1_6_2112` and
`dxc_trunk` both `SIGSEGV`. CE builds are Release and Linux, so the assert cannot appear there;
the page shows the post-`NDEBUG` consequence and corroborates the Debug build rather than
standing in for it.

Labels: keep `bug`, `crash`, `incorrect-code`; consider adding `diagnostic` (the resolution both
@tex3d and @damyanp point at is to reject this rather than crash on it) and `fxc-disagrees`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
