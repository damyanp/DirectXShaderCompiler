# Notes: #5117 "Dumping header dependencies to file prevents error output"

## Ground truth

`main-debug`, commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (public upstream `main`).
`dxc --version`: `dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage,
7665270b9)`. The binary self-reports its own local build commit (`7665270b9`), not the public
SHA; the local build tree is proven identical to `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
outside `.github/skills/dxc-issue-triage/` (`git diff --name-only 89e2f98e29c2... HEAD` shows
nothing outside the skill directory; the control `git diff --name-only 13730886e HEAD` shows 33
files outside it, so the diff can in fact detect a difference when one exists).

## The issue's claim

Filed 2023-03-27 against "DXC version 2023-03-01" -- the catalogued release with that exact
build date is `v1.7.2212.1`. The reporter says adding `-MD -MF file.d` to a `dxc` invocation
stops the error log from reaching the console, so they compile twice: once with the flags (to
get the depfile) and once without (to see diagnostics).

## Repro

No shader was attached; `repro.hlsl` is agent-constructed (an otherwise unremarkable pixel
shader whose `main()` references an identifier that was never declared):

```hlsl
// Intentional syntax error to produce a diagnosable compile failure.
float4 main() : SV_Target {
  return badIdentifierNotDeclared;
}
```

`cmd.txt`: `-T ps_6_0 -E main -MD -MF repro.d repro.hlsl`.

## Result: reproduces, and the mechanism is worse than "no console output"

`out-main-debug.txt`: with `-MD -MF repro.d`, `main-debug` exits **0** with **empty**
stdout/stderr. Without the flags (`variant-baseline-no-md-main-debug--match-baseline-error.txt`),
the identical source is rejected as expected:

```
repro.hlsl:3:10: error: use of undeclared identifier 'badIdentifierNotDeclared'
  return badIdentifierNotDeclared;
         ^
```

So this is not merely "the diagnostic text is redirected away from the console" -- dxc reports
**success** (exit 0) for a source it would otherwise, correctly, reject. The `.d` file is
written as though the compile were clean.

### Root cause (traced to source, not inferred from behaviour)

`lib/DxcSupport/HLSLOptions.cpp:650-652` merges three distinct flags into one bit:

```cpp
opts.DumpDependencies =
    Args.hasFlag(OPT_dump_dependencies, OPT_INVALID, false) ||
    opts.WriteDependencies || !opts.OutputFileForDependencies.empty();
```

`-M` (`dump_dependencies`), `-MD` (`write_dependencies`) and `-MF <file>`
(`write_dependencies_to`) are indistinguishable downstream: any of the three sets
`opts.DumpDependencies`. In `tools/clang/tools/dxcompiler/dxcompilerobj.cpp:870-894`, that flag
selects a branch that runs only `clang::PreprocessOnlyAction` -- the front end never invokes the
parser or Sema at all:

```cpp
} else if (opts.DumpDependencies) {
  ...
  clang::PreprocessOnlyAction preprocessAction;
  FrontendInputFile file(pUtf8SourceName, IK_HLSL);
  preprocessAction.BeginSourceFile(compiler, file);
  preprocessAction.Execute();
  preprocessAction.EndSourceFile();
  outStream << (opts.OutputObject.empty() ? opts.InputFile : opts.OutputObject);
  ... // write the make-rule line
}
```

Contrast the ordinary compile branch a few lines later (`dxcompilerobj.cpp:970-981`), the only
one that ever sets `compileOK` from diagnostics:

```cpp
else if (!isPreprocessing) {
  EmitBCAction action(&llvmContext);
  ...
  compileOK = !compiler.getDiagnostics().hasErrorOccurred();
```

`compiler.getDiagnostics().hasErrorOccurred()` is read unconditionally afterwards
(`dxcompilerobj.cpp:1224`) to build the final `IDxcOperationResult`, but since
`PreprocessOnlyAction` never runs anything that could set that flag for a parse/semantic defect,
it stays false and the overall status is `S_OK`. On the driver side,
`lib/DxcSupport/dxcapi.use.cpp:90-101`'s `WriteOperationErrorsToConsole` only prints the error
buffer `if (FAILED(status) || outputWarnings)` -- with `status == S_OK` and no `-Wall`, nothing
is printed. `tools/clang/tools/dxclib/dxc.cpp:308-323` (`DxcContext::ActOnBlob`) then takes the
`DumpDependencies` branch and returns immediately after writing the depfile, without ever
reaching the normal object-writing path either. Every layer behaves exactly as its local
invariant says it should; the defect is that `-M`/`-MD`/`-MF` select a front-end action that
skips the phase capable of noticing the reporter's kind of error in the first place.

### Anti-vacuity controls (both directions)

A predicate of "exit 0 and no error text" would match on *any* `-MD`/`-MF` run of *anything*,
because dependency-scan mode barely inspects the source -- that would prove nothing about a
suppressed diagnostic specifically. Two controls rule that out:

1. **`variant-baseline-no-md-main-debug--match-baseline-error.txt`** (same `repro.hlsl`,
   `-MD`/`-MF` removed, scored against `match-baseline-error.json` which requires the literal
   diagnostic text, `--expect match`): confirms the shader is genuinely rejected absent the
   flags, so a clean run *with* them is the flag suppressing a real diagnostic, not a source
   that always compiled.
2. **`variant-bad-include-main-debug.txt`** (`control-bad-include.hlsl`, a shader whose only
   defect is a `#include` of a nonexistent file, compiled *with* the identical `-MD -MF` flags,
   scored `--expect no-match` against the primary `match.json`): dxc still reports the missing
   header (`fatal error: 'does-not-exist-xyz123.h' file not found`, nonzero exit) even under
   `-MD -MF`. This is exactly what pins the defect to the parser/Sema stage rather than "stderr
   goes nowhere whenever `-MD` is set": the preprocessor itself still emits diagnostics in this
   mode, because `PreprocessOnlyAction` *is* the preprocessor. It is specifically anything a
   parse or semantic check would have caught that goes missing.

**Generality control**: **`variant-missing-semicolon-main-debug.txt`**
(`control-missing-semicolon.hlsl`, a shader whose only defect is a missing `;` -- a pure parser
diagnostic rather than a semantic one, compiled with `-MD -MF`, `--expect match`) also scores
`repro`: exit 0, no output. So the defect is not specific to "undeclared identifier"; it is
"any parser- or Sema-level diagnostic", consistent with the mechanism above (both live in phases
`PreprocessOnlyAction` never runs).

## History

`bisect --issue 5117`: `v1.4.1907` through `v1.6.2112` reject the `-MD` option outright
(`invalid-probe` -- these releases predate the flag) and are trimmed from the search.
`v1.7.2207` and `v1.9.2607` (the endpoints of the remaining probeable range) both score
`repro`; binary search short-circuits on agreement. `git log -S"opts.DumpDependencies" --
tools/clang/tools/dxcompiler/dxcompilerobj.cpp` finds the introducing commit,
`ff270c74b` ("Enable printing dependencies of compilation target", #4017, merged
2021-12-21) -- between the `v1.6.2112` (2021-12-08) and `v1.7.2207` (2022-07-18) build dates,
consistent with the bisect boundary. So: **always-repro'd for as long as `-M`/`-MD`/`-MF` have
existed** (since #4017); there is no release in which the flag existed and the defect was
absent. `v1.7.2212.1` (2023-03-01, the reporter's own build) sits inside the always-reproducing
probeable range.

The five stable releases skipped as `invalid-probe` did not merely lack the flag by coincidence
-- each was probed and explicitly rejected `-MD` at the command-line parser
(confirmed in `bisect`'s own warning output), which is the documented signature of a release
that predates an option, not an unrelated failure.

## Compiler Explorer

`godbolt.txt` / `manual-case-godbolt-verify.txt`: link
https://godbolt.org/z/s4Mcsxj66 (`dxc_trunk`, two panes on the identical source). Pane 1
(`-T ps_6_0 -E main repro.hlsl`) shows the diagnostic (CE reports exit `5`; the local Debug build
of the same source reports Win32 `0x80004005`/`2147500037` -- different platforms/build configs,
same outcome: a nonzero failure with the diagnostic printed). Pane 2 (`-T ps_6_0 -E main -MD -MF repro.d repro.hlsl`) shows `<No output file>` at exit 0.
Unlike the neighbouring `#3863`/`#4723`, which both concluded CE could not show their
file-system-level symptom, this one shows entirely on the console pane and CE corroborates the
local finding cleanly. CE runs a Linux Release `dxc_trunk`, not a dated stable release, so it
cannot itself date the defect -- `bisect` above is the source for history.

## Related issues (not asserted as duplicates; left for collation)

- Cross-reference timeline (`gh api .../issues/5117/timeline`) shows one pre-existing
  cross-reference, to `#3863` (2023-06-30), predating this triage.
- `#4723` (already triaged, batch-017, `still-valid-keep-open`) is the same
  `opts.DumpDependencies` special-casing but requires `-P` and manifests as a missing depfile
  plus corrupted preprocessed text -- a different trigger and a different visible defect from
  this issue's silently-accepted invalid input. See `method-notes.md`.

## Multi-ask decomposition

The issue makes one ask: keep diagnostics visible when `-MD`/`-MF` is also requested. There is
no partially-satisfied sub-claim to separate out.

## Suggested action

`still-valid-keep-open`. This is a real, currently-reproducing defect with a source-level root
cause, not a duplicate of `#4723` and not merely a usability nice-to-have: dxc reports **success**
for input it would otherwise reject, whenever dependency-file generation is requested, because
that mode skips parsing and semantic analysis entirely. Labels: keep `high-impact`; propose
adding `bug` (this reports a wrong compile result, not just an inconvenience) and `diagnostic`
(the defect is specifically about diagnostics not being produced/surfaced).
