# Expected behavior (written before running anything)

Issue #5423: "`dxr.exe` doesn't support macro definitions via its CLI".

The reporter's claim has two parts, tested against two different tools:

1. **`dxc.exe -D float4=0 <shader>`** — the reporter says this fails to compile, "which
   proves that the macro was expanded" (the token `float4` is textually replaced by `0`
   everywhere, including in type positions, producing invalid syntax).
2. **`dxr.exe -D float4=0 -E PSMain <same shader>`** — the reporter says the rewriter
   silently ignores `-D` and emits the source **verbatim**, with no error or warning, "which
   proves that the macro wasn't expanded."

"This reproduces" means: (1) still holds (dxc.exe's `-D float4=0` still fails to compile with
a syntax/parse error caused by the macro substitution), AND (2) still holds (dxr.exe still
accepts `-D` without diagnosing it as unsupported, and still does not apply the substitution
to its rewritten output — the CLI parses `-D` into `opts.Defines` but the rewrite entry point
never forwards it to the AST-generation call that actually expands macros).

Repro quality: **complete** for the `dxc.exe` half (the issue names the exact command and a
public Compiler Explorer link). The `dxr.exe` half is described precisely in prose
(`dxr.exe -D float4=0 -E PSMain <file>` rewrites verbatim) but `dxr.exe` is not part of this
skill's ground-truth build and is out of scope to build here (task instructions forbid any
rebuild). That half is evaluated by direct source citation instead of by running the binary:
tracing the exact call site that the reporter's own bug depends on, and confirming it is
unconditional (not gated on shader content, flags, or anything that could vary by input).

Any earlier reference in this file about how the two halves would be measured is preserved
above; see notes.md for how the evidence reconciles with it once gathered (dxc.exe half:
run and captured; dxr.exe half: source-only, `not-compiler-verifiable` by this skill's tooling
without a rebuild).
