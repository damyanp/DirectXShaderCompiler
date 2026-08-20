# Issue #6005 — `[Assert Triggered] MaybeODRUseExprs.empty() && "Leftover expressions for odr-use checking"`

## Summary

Confirmed. `main` (commit `13730886e`, local Debug build self-reports fork-local
`ab5400907` / `7665270b9`; git-commit provenance for `main-debug` is registered and the
tree is verified identical to upstream `main` outside this skill directory) still trips this
assert on the reporter's construction: typedef aliases (`float32_t`, `uint32_t3`, etc.) built
from HLSL's own builtin `vector<T,N>`/`matrix<T,R,C>` templates, declared inside a
user namespace, alongside ordinary use of HLSL's built-in vector/matrix sugar. The
compile completes ("the shader still compiles" per the report) — this is an internal
consistency assert in Sema's ODR-use tracking, not a functional/codegen failure that a user
would otherwise notice, and it is invisible on any Release build because C/C++ `assert()`
compiles out under `NDEBUG`.

## Repro

`repro.hlsl` / `cmd.txt` are the exact preprocessed source and command line s-perron
(a maintainer) posted on 2024-09-16, recovered verbatim from pow2clk's public Compiler
Explorer short link (https://godbolt.org/z/zGaGPaKK3) referenced two comments earlier in the
same thread — both are public artifacts of this public issue, so reuse is within this repo's
"public repros only" policy.

```
dxc -spirv -HV 202x -T cs_6_7 -Zpr -enable-16bit-types -fvk-use-scalar-layout \
    -Wno-c++11-extensions -Wno-c++1z-extensions -Wno-gnu-static-float-init \
    -fspv-target-env=vulkan1.3 -fspv-debug=source -fspv-debug=tool repro.hlsl
```

## Ground truth

`main-debug`, exit `0xE0000001` (C++-exception form of the assert — see
`out-main-debug.txt`), verdict `repro` under `match.json` (`internal_failure`, keyed on exit
status per this skill's crash-classification rule, never on message text).

A `cdb` capture using the documented `gh` ("go handled", emulates `NDEBUG`) trick
(`gen-assert-stack.py` → `manual-case-assert-stack.txt`) confirms:

```
Error: assert(MaybeODRUseExprs.empty() && "Leftover expressions for odr-use checking")
File:
<repo>/tools/clang/lib/Sema/SemaDecl.cpp(11156)
Func:   clang::Sema::ActOnFinishFunctionBody
```

— the same assert message, file and function s-perron quoted (their build hit line 11119;
line drift of 37 lines over ~2 years of unrelated `SemaDecl.cpp` edits is expected and not a
different assert). Critically, after `gh` continues *past* the assert (i.e. running exactly
the code path a Release build's compiled-out assert would run), the compile finishes and
emits a well-formed, valid-looking SPIR-V module (`OpEntryPoint`/`OpFunction`/... all present,
`main` correctly defined) — direct evidence for the report's own observation that "the shader
still compiles" and that this defect has no other externally-visible symptom in this repro.

### Not SPIR-V-specific

`variant-no-spirv-main-debug.txt` — the same repro compiled to DXIL (no `-spirv`) trips the
identical exit-`0xE0000001` assert. This corroborates s-perron's 2023-08-23 comment that they
"checked and it fails when `-spirv` is removed". This is a Sema (front-end) issue, unrelated
to the SPIR-V backend.

## History

`bisect --linear` across the stable release catalog:

- `v1.4.1907`–`v1.6.2112` (5 releases): `invalid-probe` — these predate HLSL version
  identifier `202x`/`2021` support (`dxc failed : Unknown HLSL version: 202. Valid versions:
  2016, 2017, 2018, 2021`, confirmed in `out-v1.6.2112.txt`) and never reach the code under
  test.
- `v1.7.2207`–`v1.9.2607` (15 releases): `no-repro`, exit 0, clean compile.

**This "no-repro" history is not evidence of a fix.** Every catalogued release is a Release
build, and `assert()` compiles out entirely under `NDEBUG` — a Release binary cannot exhibit
this symptom regardless of whether the underlying defect exists, exactly as
`bisect`'s own warning states. Only one assert-enabled (Debug) build was available to test
(`main-debug`); no older Debug build exists in this environment to check whether the assert
predates today, so the honest statement is "reproduces on the only assert-enabled build
measured; unmeasured on any Debug build older than today's `main`", not "always reproduced"
and not "fixed".

Compiler Explorer corroborates the same shape at the historical boundary: `dxc_1_6_2112`
rejects `-HV 202x` (`manual-case-godbolt-verify.txt`), and `dxc_trunk` (a Linux Release build,
current as of this triage) compiles cleanly — again showing only that Release builds are
unaffected, not that the assert is gone. Link:
https://godbolt.org/z/h7WEM3v8G (`godbolt-note.txt` states this limitation on the shared page
itself).

## Assessment

- **Status:** `repros` (on the only assert-enabled build available).
- **Repro quality:** `complete`.
- **History:** unmeasurable further back than today's `main-debug`; release history shows only
  that Release binaries never show this symptom (expected, uninformative about a fix).
- **Confidence:** high — matches a maintainer's own independently-obtained repro, exact assert
  message, file and function, and is corroborated by a from-scratch cdb capture on this
  session's ground-truth build.
- **Text staleness:** none. The report ("the shader still compiles, I just hit this nasty
  assert") is exactly what still happens; no maintainer comment asserts otherwise.
- **Suggested action:** `still-valid-keep-open`. This is a real, currently-reproducing Debug
  assert with a maintainer-confirmed repro and no indication of a fix in progress; the only
  reason it reads as dormant is the assert's own invisibility on Release binaries and
  Compiler Explorer.
- **Label proposal:** add `crash` (assert-only crashes are exactly what this label is for and
  it is currently missing) and `type-system` (the trigger is a user-namespace typedef whose
  name collides with the type HLSL's builtin `vector<T,N>`/`matrix<T,R,C>` templates produce,
  an inconsistency in how the front end tracks such declarations). Not proposing `spirv`: the
  defect is confirmed independent of `-spirv`.

## Method notes

- No new tooling defects found; see `method-notes.md`.
