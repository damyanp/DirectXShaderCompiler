> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3044](https://github.com/microsoft/DirectXShaderCompiler/issues/3044).

Still valid on `main` (checked at
[`13730886e`](https://github.com/microsoft/DirectXShaderCompiler/commit/13730886e)),
and there is a concrete finding: **the capability is already in the library —
only a driver flag is missing.**

`-P` still drops comments, on every stable release from v1.4.1907 to v1.9.2607
and on `main`. Neither clang spelling is accepted:

```
$ dxc -P repro.hlsl -Fi flag-probe.i -CC
dxc failed : Unknown argument: '-CC'
```

The `/` spellings are not an alternative: `dxc` does not diagnose an unknown
`/`-flag, so `-P /CC ...` exits 0 having ignored it — its output is
byte-identical to a run with no flag at all, and to one passing
`/ZZZNONSENSE`. Same result on Compiler Explorer, 1.6.2112 through trunk:
https://godbolt.org/z/rc8jz9ve7

@pow2clk's read in September 2020 looks right. The plumbing that would carry
`-C`/`-CC` already exists everywhere except the dxc driver:

- `PrintPreprocessedOutput.cpp` honours it —
  `PP.SetCommentRetentionState(Opts.ShowComments, Opts.ShowMacroComments)`.
- `CompilerInvocation.cpp` parses `-C`/`-CC` into those fields, but only on the
  `cc1` path, which the dxc driver never takes.
- `dxcompilerobj.cpp` builds `PreprocessorOutputOptions` by hand instead and
  hardcodes both off:

  ```cpp
  // These settings are back-compatible with fxc.
  PPOutOpts.ShowComments = 0;      // Show comments.
  PPOutOpts.ShowMacroComments = 0; // Show comments, even in macros.
  ```

- `HLSLOptions.td` has no `C`/`CC` entry. (`Cc` is unrelated — colour-coded
  assembly listings.)

So the work is an option-table entry plus wiring `DxcOpts` into those two
fields. The `fxc` back-compat comment is presumably why the default has to stay
off. `dxcrewriteunused.cpp` hardcodes the same two values for the rewriter, so
whether the flag should reach it too is a decision to make rather than an
oversight to fix.

Verified by preprocessing a shader whose sentinel token appears only inside
comments, alongside a control shader that also declares it as an identifier:
the control's preprocessed output keeps the token at all 21 builds tested, the
comment-only one never does, and the macro in both expands, so preprocessing
did run.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
