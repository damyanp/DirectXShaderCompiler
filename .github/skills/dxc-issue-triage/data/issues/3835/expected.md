# 3835 — expected symptom

Written **before** any compiler was run, per step 2. Filed 2021-06-17 by `Gordon-F`; labels
`bug`, `crash`, `incorrect-code`; 6 comments, last 2024-08-28.

## What the issue reports

Body, verbatim:

```
./dxc.exe ./shader.hlsl -T vs_5_0 -E vert_main -Wno-parentheses-equality -Zi -Qembed_debug
Internal compiler error: access violation. Attempted to read from address 0x0000000000000009
```

against release **v1.6.2104**, on the attached ~50-line vertex shader (a naga `hlsl-out`
backend output). The reporter states the shader is *not valid* HLSL, "but `dxc` should be
able to parse it without any ICE".

## The title is misleading and must not steer the predicate

The title says "Internal compiler error on shader **validation**". The evidence in the body is
an **access violation inside the compiler** (`Internal compiler error: access violation`),
which is an internal failure of dxc itself — **not** DXIL validation rejecting a shader.
Those are different outcomes with the same nonzero exit convention on Windows, and only the
first is this issue:

- **is the symptom**: dxc fails internally — exit `0xC0000005` (access violation, as reported),
  `0x80000003`/`0xE0000001` (assert trap in an assert-enabled Debug build), `0x80AA001B-1D`,
  or `E_FAIL` carrying a leaked internal marker such as `llvm::cast<X>()`.
- **is NOT the symptom**: dxc *diagnosing* the input. A syntax error, an unsupported
  construct, an invalid profile, or a **DXIL validation failure** all exit `E_FAIL`
  (`0x80004005`) with an ordinary `error:`/`validation errors` line. Reading any of those as
  "the crash reproduces" would invent a bug. If today's dxc rejects this shader with a clean
  diagnostic, that is `does-not-repro` on the crash and matches tex3d's "diagnose this case and
  fail as unsupported" option, not a reproduction.

## Root cause stated in the thread (tex3d, 2024-08-28)

HLSL array *assignment* initialization from an incomplete array type:

```cpp
assert(!isIncompleteType() && "This doesn't make sense for incomplete types");
```

under `Ty->isConstantSizeType()` from `CodeGenFunction::EmitAutoVarAlloca`, for
`float _expr13[] = perVertexStruct.gl_ClipDistance;` — the decl's incomplete array type is
never completed because SemaHLSL's custom assignment handling bypasses clang's usual path.
FXC compiles the same source. Initializing the other struct fields does **not** remove it.

## Two shapes, so two questions

tex3d's minimal repro (2024-08-28):

```hlsl
int array1[1];
int main() : OUT {
    int error_expr[] = array1;
    return error_expr[0];
}
```

is said to *"hit the assert on debug build"* and *"produce incorrect code on release build"* —
i.e. **no crash** in Release for the minimal case, unlike the reporter's full shader which
access-violates in a Release binary. So:

- **Q1 (primary, `match.json`)** — does the *filed* repro still fail internally? Predicate is
  `internal_failure`, deliberately keyed on exit status rather than on the assert message: the
  Debug ground truth build and the Release release-binaries express the same defect with
  different text and different codes, and a message-matching predicate would score every
  release clean and manufacture a "fixed" verdict.
- **Q2 (secondary)** — does the minimal repro's *Release* shape (accepted, wrong code, no
  crash) still hold, and is it distinguishable from the Debug assert? If ground truth's
  behaviour differs in shape from what was filed, a second predicate file gets its own
  bisection so "fixed" and "changed shape but still broken" do not collapse into one verdict.

## Prediction of what a reproduction looks like on ground truth

`main-debug` is an assert-enabled Debug build. If the defect is unchanged I expect the
`assert(!isIncompleteType())` to fire, i.e. a trapped assert (`0x80000003`) or a C++-exception
assert (`0xE0000001`), **not** necessarily the reporter's `0xC0000005` — that is the Release
face of the same defect. Both are `internal_failure`; neither is "a different bug".

## Non-symptoms to guard against (would falsify a reproduction)

1. `error: invalid profile vs_5_0` or similar — the reporter used a **5.0** profile. If dxc
   refuses that profile the code under test is never reached and the probe is invalid, not
   clean. Must be checked explicitly on ground truth and on every release probed.
2. Any `error:` diagnostic with exit `0x80004005` and no internal marker — a diagnosed
   rejection, i.e. the "fixed by diagnosing" outcome.
3. `error: validation errors` / `Validation failed` — DXIL validation doing its job. Exit
   `E_FAIL`. Not a crash.
4. Exit 0 with DXIL — clean compile.

## Repro quality

**complete** — the issue body carries a full, self-contained shader and the exact command
line, and a maintainer comment adds an independently minimal second repro. Nothing has to be
reconstructed.

## History expectations

Reported against v1.6.2104 (2021-04-20); filed 2021-06-17, which sits **inside** the stable
release range (v1.4.1907 … v1.9.2607). pow2clk re-confirmed "still repros" on 2024-08-27.
Because the filing date is inside the range and matching endpoints would prove only endpoint
agreement, use `--linear` rather than trusting a short-circuit.
