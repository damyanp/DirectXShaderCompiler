# Method observations from triaging #2530

Recorded for collation to promote or discard. Nothing here was fixed locally —
this session wrote only `data/issues/2530/`.

## 1. Cross-issue pointer (deliberately absent from `comment.md`)

The thread's only comment, from pow2clk on 2020-08-14, is in full:

> Related to #2188

I have not looked at #2188 and make no claim about it. For a cross-issue
comparison, the concrete facts to match against are:

- **Construct:** an array bound that is a compile-time constant reached through
  a **float→integer conversion** — `uint(<static const float>)`, or a
  `static const uint` whose initializer is such a conversion.
- **Diagnostic:** `error: variable length arrays are not supported in HLSL`
  (`err_hlsl_vla`, `tools/clang/include/clang/Basic/DiagnosticSemaKinds.td:7726`).
- **Code path:** `Sema::BuildArrayType` (`tools/clang/lib/Sema/SemaType.cpp:1978`)
  → `isArraySizeVLA` (`SemaType.cpp:1943`) → `Sema::VerifyIntegerConstantExpression`
  → `CheckICE` (`tools/clang/lib/AST/ExprConstant.cpp:9016`). Non-ICE ⇒
  `getVariableArrayType` at `SemaType.cpp:2098` ⇒ the HLSL-only check at
  `SemaType.cpp:2142-2146`.
- **Exact point of failure inside `CheckICE`:** case 1 at the cast cases,
  `ExprConstant.cpp:9308-9344` — an explicit cast is an ICE only if its operand
  is a `FloatingLiteral` (9317), so `CK_FloatingToIntegral` on a `DeclRefExpr`
  hits `default: return ICEDiag(IK_NotICE, ...)` (9343). Case 2 at
  `Expr::DeclRefExprClass`, `ExprConstant.cpp:9142-9172` — `VD->checkInitIsICE()`
  is false.
- **Not this issue:** the *implicit* conversion (`float array[ARRAY_SIZE]` with
  `ARRAY_SIZE` a `static const float`) never reaches the VLA path. HLSL's
  LangOpts are C++ but not C++11, so `SemaType.cpp:2068-2074` rejects it first
  with `err_array_size_non_int`: `size of array has non-integer type 'float'`.
  Anything triaged as "array bound rejected" needs this distinction checked
  before being called the same defect — the two differ in message *and* in
  which `if` fires.

Two other issues would share this root cause without looking alike: any use of a
converted constant in an ICE context (bitfield width, `switch` case, template
argument) and any `static const` whose initializer chain crosses a float.

## 2. Trap hit: a Clang pane needs a control *and* `-fsyntax-only`

SKILL.md step 7 already documents this (#1702), and it fired again exactly as
written. `hlsl_clang_trunk` on `-T ps_6_0 -E main` fails **every** pixel shader
writing `SV_Target` with

```
error: Unsupported intrinsic llvm.dx.store.output.v4f32 for DXIL lowering
```

including the known-good control. With `-fsyntax-only` the control exits 0 and
the repro still errors, so the difference survives. All four cases are captured
in `manual-case-ce-clang.txt`.

Possible addition to the skill, since the existing text says only "where the
backend is the blocker, `-fsyntax-only` asks the narrower question": for any
issue whose symptom is a **front-end diagnostic**, `-fsyntax-only` is not a
fallback but the correct first choice — the question is entirely answerable
without the backend, and including the backend can only add noise.

## 3. CE returns ANSI-coloured diagnostics; captures inherit them

`triage.py`'s `ce_compile` returns clang's output with SGR escape sequences
embedded, so anything written to a file from it is close to unreadable — see the
first capture attempt for `manual-case-ce-clang.txt`, which was discarded and
re-taken. Adding `-fno-color-diagnostics` to the pane's arguments fixes it and
changes no result (verified: the coloured and uncoloured case-1 outputs are
otherwise character-identical).

Worth considering: have `ce_compile` strip `\x1b\[[0-9;]*m` before returning, so
this is not rediscovered per issue. Doing it in the harness rather than in each
pane's arguments would also keep the published pane args minimal. Not done here
— `scripts/` is shared state.

## 4. `expect` did what it is documented to do

`boundary-implicit-conv.hlsl` was captured with `--expect match` on a prediction
that turned out to be wrong (it gets a *different* diagnostic). `triage.py
expect --issue 2530 --capture ... --expect no-match` revised the declaration and
printed `(scores no-repro; measurement untouched)`. Worked exactly as
documented; no defect. Recorded only as a positive datapoint that the
revise-a-declaration path is used and correct.

One consequence worth knowing: the `.hlsl` file's own comment carried the wrong
prediction, and correcting it risks shifting line numbers so the committed
capture no longer matches a re-run. It was rewritten with an identical line
count to keep `boundary-implicit-conv.hlsl:10:17` valid. A general rule for the
skill: **when editing a repro's comments after capture, preserve the line
count**, or re-capture.

## 5. `bisect` short-circuit vs. the concision reviewer

Plain `bisect` reported `always-repro'd across v1.4.1907..v1.9.2607` after
probing **two** releases. SKILL.md step 10 records that the draft reviewer caught
exactly this overclaim before ("every release back to v1.4.1907" where bisect
short-circuited). Rather than weaken the claim, `--linear` was run — 20 of 20
releases, ~1 minute wall clock on a warm cache, because the symptom is an
immediate front-end error.

Suggestion: for issues where the repro fails fast, `--linear` is cheap enough to
be the default rather than the exception; the two-endpoint result and the
20-release result support noticeably different sentences.

## 6. No tooling defects found

`fetch`, `run`, `expect`, `bisect --linear`, `godbolt`, `labels` and `audit` all
behaved as documented. Specifically, none of the batch-004 regressions
reappeared: probes were filed per-predicate, `audit` ran read-only and returned
a real exit code, and `reindex` was not run.
