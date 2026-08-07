# #3092 — [SPIR-V] Allow thread group size to be specified with specialization constants

**Verdict: `repros`** — the capability is still absent. Repro is `agent-constructed`.

## Ground truth

| | |
| --- | --- |
| compiler | `main-debug` |
| version | `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)` |
| commit | `ab5400907` |

Provenance verified **by tree**, not by SHA, per SKILL.md:
`git diff --name-only ab5400907 HEAD -- . ":(exclude).github/skills/dxc-issue-triage"` is
empty, so no compiler source differs from the checkout under test.

## What was asked for

A 2020 feature request: GLSL can drive a compute shader's local workgroup size from
specialization constants (`layout(local_size_x_id = 18) in;`), and HLSL→SPIR-V has no
equivalent. The thread supplies what the body does not:

* @shangjiaxuan (2022) pasted `glslc`'s output — the reference for correct SPIR-V:
  `OpDecorate %gl_WorkGroupSize BuiltIn WorkgroupSize` on an `OpSpecConstantComposite`.
* @s-perron (2023) named the syntax he would want, and that is what `repro.hlsl` is:
  `[[vk::constant_id(13)]] const int X = 10;` then `[numthreads(X,1,1)]`.
* @llvm-beanz (2023): "I think this is just a bug. We should allow any compile-time constant in
  that attribute."
* @s-perron (2025-01): draft PR #7084 exists but "cannot go into DXC yet. We would need an HLSL
  spec update", with a three-item checklist. "I do not have any timeline on when we can get to
  this." Later points at PR #7439.

## Repro

`repro.hlsl` + `cmd.txt` (`-T cs_6_0 -E main -spirv repro.hlsl`). Marked
**`agent-constructed`**: the issue body is prose plus a GLSL snippet, so there was nothing to
run. The HLSL is @s-perron's syntax, which is the closest thing the thread has to a
specification of the request.

`cs_6_0` and no extra flags — the oldest profile and smallest flag set that still show the
symptom, per SKILL.md's prevention rule for `invalid-probe`.

## Result on ground truth

`out-main-debug.txt`, exit `0x80004005` (E_FAIL — an ordinary diagnosed error, **not** an
internal failure):

```
repro.hlsl:14:2: error: 'numthreads' attribute requires an integer constant
[numthreads(TGSIZE_X, 1, 1)]
 ^          ~~~~~~~~
repro.hlsl:14:2: warning: Group size of 0 (0 * 1 * 1) is outside of valid range [1..1024] - attribute will be ignored [-Wignored-attributes]
[numthreads(TGSIZE_X, 1, 1)]
 ^~~~~~~~~~~~~~~~~~~~~~~~~~
repro.hlsl:15:6: error: compute entry point must have a valid numthreads attribute
void main(uint3 tid : SV_DispatchThreadID) {
     ^
```

`expected.md` predicted from source that the likelier shape was a **silent fold** —
`ValidateAttributeIntArg` (`SemaHLSL.cpp:13858`) looks up the `VarDecl` and constant-folds
`decl->getInit()`, and `processComputeShaderAttributes` (`SpirvEmitter.cpp:14600`) then emits
`LocalSize {x,y,z}` from the folded integers. That prediction was **wrong**, and the actual
behaviour is better: DXC errors rather than silently ignoring the specialization data. Every
release capture was grepped for `OpExecutionMode` and none has any, so the silent-fold shape
occurs nowhere in the measured history.

## Predicates

`match.json` — `contains "'numthreads' attribute requires an integer constant"`. The symptom of
this capability being absent *is* a diagnostic, so the diagnostic is written in verbatim (the
#3055 shape; `_predicate_quotes` needs the exact string). It carries a positive clause by
construction, so it cannot be satisfied by a run that failed early.

`match-no-spec-link.json` — `not_regex "LocalSizeId|BuiltIn WorkgroupSize"`, a hedge against the
silent-fold shape that `match.json` would have scored as a fix. Absence-only, so `run` warns on
every probe; it confirms rather than carries the verdict.

## Controls — all captured, all as declared

| capture | shader | expect | result |
| --- | --- | --- | --- |
| `variant-control-static-const-main-debug.txt` | `static const uint` group size | `no-match` | exit 0, `OpExecutionMode %main LocalSize 4 1 1` |
| `variant-control-specconst-literal-main-debug.txt` | spec constant declared + used, literal group size | `no-match` | exit 0, `OpDecorate %TGSIZE_X SpecId 1` |
| `variant-static-specconst-main-debug.txt` | `[[vk::constant_id(1)]] static const` | `no-match` | `error: specialization constant must be externally visible` |
| `variant-execmodeid-main-debug--match-no-spec-link.txt` | inline-SPIR-V `LocalSizeId`, `vulkan1.3` | `no-match` | exit 0, emits `LocalSizeId` |
| `variant-control-specconst-literal-main-debug--match-no-spec-link.txt` | successful compile, no link | `match` | exit 0 |
| `variant-execmodeid-default-env-main-debug--match-no-spec-link.txt` | same, default target env | `no-match` | see below |

The first two are what make the primary predicate discriminating: it does not fire because a
named constant appears in `numthreads`, and it does not fire because a specialization constant
is present. The third shows the obvious workaround is closed — a spec constant may not be
`static`, and `static` is what makes an initialiser usable as a `numthreads` argument, so no
declaration satisfies both.

The last one was declared `--expect match` and the runner rejected it. It is a real predicate
trap, not a mistake in the shader: at the default target environment the escape hatch fails,
and DXC's validation **echoes the rejected instruction into the diagnostic**, so the literal
text `LocalSizeId` appears in the output of a compile that emitted nothing usable. A text
absence predicate cannot tell that apart from a successful emission. Corrected to `no-match`
with `triage.py expect`; written up in `method-notes.md` and in the predicate's own `note`.

## History

`bisect --linear` (`--linear` because the thread contains a merged PR and two open ones, so a
fix-then-revert history was plausible):

```
v1.4.1907    n/a (never compiled the repro)
v1.5.2010 .. v1.9.2607   repro   (19 releases, every one)
result: always-repro'd across v1.5.2010..v1.9.2607 (1 release skipped as unprobeable)
```

`out-v1.4.1907.txt` is `invalid-probe`, reason recorded in the header:
`dxc failed : SPIR-V CodeGen not available. Please recompile with -DENABLE_SPIRV_CODEGEN=ON.`
It is evidence of nothing, and is not a "release where this worked".

Every one of the 19 probeable captures contains the diagnostic verbatim (older releases stop
after it; from v1.8.2403 onward the `Group size of 0` warning and the follow-on error appear
too), and none contains `LocalSizeId`, `BuiltIn WorkgroupSize` or any `OpExecutionMode` line —
checked across all captures, not inferred from the endpoints.

**Coverage caveat.** v1.5.2010 was built 2020-10-22; the issue was filed 2020-08-19. The oldest
probeable release is therefore two months *younger* than the report, so this history cannot
speak for the build the reporter used. It does cover every release it is possible to check.

## Clang — the successor front end has the same gap

Captured with controls in `manual-case-clang-panes.txt` (`hlsl_clang_trunk` on Compiler
Explorer, via `ce-probe.py`):

| case | result |
| --- | --- |
| `repro.hlsl` | `error: 'numthreads' attribute requires an integer constant` — DXC's first diagnostic, word for word (the follow-on differs: `missing numthreads attribute for compute shader entry`) |
| control: `static const uint` group size | exit 0, `OpExecutionMode %24 LocalSize 4 1 1` |
| control: spec constant declared + used, literal group size | exit 0, `OpDecorate %23 SpecId 1`, `%23 = OpSpecConstant %3 4` |

Both controls compile, so the failure is not Clang's incomplete stage/backend support and not a
missing `[[vk::constant_id]]`. `-fsyntax-only` was unnecessary: the front end hard-errors, so
the backend never runs and the pane is already clean.

`godbolt`'s summary line for that pane shows only
`clang: warning: argument unused during compilation: '-Qembed_debug'`, which says nothing — the
finding is on the pane's second line. SKILL.md warns about exactly this; noted again in
`method-notes.md`.

## What has changed since the 2025-01 checklist

@s-perron listed three prerequisites. One has landed:

- [ ] a new `vk::LocalSizeId` attribute, or an HLSL spec change to `numthreads` — **not done**.
      There is no `LocalSizeId` in `Attr.td`; `HLSLNumThreads` is still
      `[IntArgument<"X">, IntArgument<"Y">, IntArgument<"Z">]` (`Attr.td:670`). PR #7084 is
      still a draft; PR #7439 (`Fixes #3092`) is open and awaiting review, last pushed
      2025-11-06.
- [ ] update the compute-derivatives spec for an unknown dimension size — **not done**, and the
      coupling is still in the code: `addDerivativeGroupExecutionMode` picks the quad layout by
      *reading back* the already-emitted `LocalSize` parameters
      (`SpirvEmitter.cpp:16542`, `findExecutionMode(entryFunction, ExecutionMode::LocalSize)`
      then `numThreadsEm->getParams()`), which cannot work if a dimension is a spec constant.
- [x] refactor DXC's `OpExecutionModeId` implementation — **merged**: PR #7378
      "[SPIRV] Refactor OpExecutionModeId", `e866b4bac`, 2025-04-29, confirmed an ancestor of
      the tested commit.

A consequence of that merge, measured: `LocalSizeId` is now reachable from inline SPIR-V.
`variant-execmodeid.hlsl` compiles with `-fspv-target-env=vulkan1.3` and emits

```
OpExecutionMode   %main LocalSize   1 1 1
OpExecutionModeId %main LocalSizeId %TGSIZE_X %uint_1 %uint_1
OpDecorate %TGSIZE_X SpecId 1
%TGSIZE_X = OpSpecConstant %uint 4
```

It is not a substitute for the feature: `[numthreads]` remains mandatory on a compute entry
point, so the module carries **both** execution modes. DXC's bundled SPIR-V validation accepts
it (exit 0); runtime behaviour needs a driver and was not tested. At the default target
environment it is rejected outright — `LocalSizeId` requires SPIR-V 1.2+, i.e. Vulkan 1.3 or
`VK_KHR_maintenance4`.

## Assessment

Still absent, everywhere it is possible to check, and absent in the successor front end too.

The measurement narrows the scope of the remaining work in one useful way. `[numthreads]`
already accepts a named compile-time constant — `control-static-const.hlsl` compiles — so what
is missing is not "compile-time constants in `numthreads`" but a group-size dimension that is
*not* known at compile time. That is a language change, which is what @s-perron's 2025 comment
says, and it is a product/language design decision this triage must not pre-empt.

`enhancement-not-bug`: the implementation is not defective so much as unspecified, and the two
outstanding checklist items are both spec work. `enhancement` and `hlsl-next` are proposed on
that basis. `check-in-clang` was considered and **not** proposed: its description is "See if
this repros in clang as well", i.e. a to-do, and the check has been done and captured — the
result is in the comment instead.

`text_stale` was considered and **not** set. The title and body still describe what the
compiler does. @llvm-beanz's 2023 "we don't correctly support [any compile-time constant]" is
narrower than the measurement shows — `static const` works — but it is explicitly hedged
("I think"), it does not mislead a reader into "cannot reproduce", and calling a hedged 2023
remark stale is the #8737 failure mode. The clarification is in the draft comment as a fact,
not as a correction.

Confidence: **high**. Twenty releases plus ground truth plus two Clang panes agree; five
controls behave as declared; the absent capability is corroborated from source
(`Attr.td:670`, `SemaHLSL.cpp:13858`, `SpirvEmitter.cpp:14600`) as well as from output.

## Compiler Explorer

https://godbolt.org/z/5dG5M5EnP — `dxc_1_6_2112`, `dxc_trunk`, `hlsl_clang_trunk`, banner from
`godbolt-note.txt`. Link verified through CE's `shortlinkinfo` API: three panes, all with
`-T cs_6_0 -E main -spirv`, banner present.
