## What "reproduces" means for this issue

This is a `docs`-labelled request, not a crash/regression report. The reporter's claim has
two parts:

1. **A documentation claim**: the Microsoft Learn "Flow Control" page
   (https://learn.microsoft.com/en-us/windows/win32/direct3dhlsl/dx-graphics-hlsl-flow-control)
   lists `discard` alongside `break`, `continue`, `for`, `if`, `switch`, `while` as a
   "flow-control statement", where flow control is defined on that same page as something that
   "determines at run time which block of HLSL statements to execute next" / "jump (branch) to
   an instruction other than the one on the next line".
2. **A technical claim**: `discard` does not actually do that. It doesn't jump/branch past
   subsequent statements; it only marks the invocation as a "helper lane" whose UAV writes and
   render-target exports are elided later (after the shader has otherwise run to completion).
   The reporter says this misleads newer HLSL developers into treating `discard` as a kind of
   early `return`.

"Reproduces" here means: (a) the Learn page still groups `discard` under flow control today
(the docs symptom persists), and (b) DXC's own compiled output for `discard` is consistent
with the reporter's technical description -- i.e. code/writes after a `discard` are not
skipped/guarded the way they would be after a real early exit (`return`).

This is fundamentally a **documentation content question about a page outside this
repository** (it lives in `MicrosoftDocs/win32-pr`, not `microsoft/DirectXShaderCompiler`), so
whether that page gets edited is not something a dxc compile can verify or produce --
`not-compiler-verifiable` in the literal "will someone edit this external page" sense. But the
technical premise behind the request *is* compiler-verifiable: dxc's own DXIL codegen for
`discard` either does or does not resemble an early exit, and that can be measured directly by
comparing `discard` against `return` from otherwise-identical source.

Repro quality: **agent-constructed** (`repro.hlsl` / `control-return.hlsl`), built specifically
to expose this contrast; the issue itself contains no shader.

There is no "history"/bisection dimension to test here: the reporter is not claiming a
regression, and nothing suggests DXC's codegen strategy for `discard` (kill-without-branch) has
ever differed across releases -- it follows directly from `discard`'s semantics (mark for later
elision, do not terminate the invocation), which have been stable. `bisect` is not run for this
issue.
