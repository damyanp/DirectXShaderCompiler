# 3835 — triage notes

**Verdict: still reproduces**, on every stable release tested and on `main`
(`1.9.0.5433`, public commit `13730886e`). Reported 2021-06-17 against v1.6.2104; the defect is
older than the report.

The reported symptom, the root cause named in the thread, and a second silent shape are all
confirmed by measurement below. `expected.md` was written before anything was run.

## The title is wrong, and it matters

"Internal compiler error on shader validation" reads as a DXIL validation problem. It is not.
DXC crashes in **clang CodeGen**, long before any DXIL exists to validate. On Windows an
ordinary diagnosed error, an invalid profile and a genuine DXIL validation failure all exit
`E_FAIL (0x80004005)`, so exit status alone cannot separate "the validator rejected your
shader" from "the compiler fell over". Controls were run for exactly this distinction:

| capture | exit | output | internal? |
| --- | --- | --- | --- |
| `out-main-debug.txt` (the filed repro) | `0xE0000001` | `Internal compiler error: LLVM Assert` | **yes** — assert delivered as a C++ exception |
| `out-v1.6.2104.txt` (the release the reporter named) | `0xC0000005` | `Internal compiler error: access violation. Attempted to read from address 0x0000000000000008` | **yes** — access violation |
| `variant-syntax-error-main-debug.txt` | `0x80004005` | ordinary `error:` | no |
| `variant-validation-error-main-debug.txt` | `0x80004005` | `error: validation errors` / `Semantic 'LOC' overlap at 0.` / `Validation failed.` | no — this is what a real validation failure looks like |
| `variant-good-vertex-main-debug.txt` | `0` | DXIL | no |
| `variant-minimal-sized-main-debug.txt` | `0` | DXIL | no |

So `match.json` uses the `internal_failure` predicate, keyed on exit status, **not** on the
assert text. Keying on text would have been fatal here — see "one defect, three faces" below.

## What triggers it

Two declarations in the filed shader:

```hlsl
float _expr13[] = perVertexStruct.gl_ClipDistance;
float _expr14[] = perVertexStruct.gl_CullDistance;
```

An **incomplete** array type initialised by assignment from an array. Give either one an
explicit bound and the same shader compiles cleanly (`control-sized-array.hlsl`, exit 0). The
5-line minimal repro from the thread reduces it to one token.

## Root cause, confirmed by stack rather than quoted

`manual-case-assert-stack.txt` CASE 1 and CASE 2 (`cdb`, both the minimal and the filed shader):

```
Error: assert(!isIncompleteType() && "This doesn't make sense for incomplete types")
dxcompiler!llvm_assert
dxcompiler!clang::Type::isConstantSizeType
dxcompiler!clang::CodeGen::CodeGenFunction::EmitAutoVarAlloca
dxcompiler!clang::CodeGen::CodeGenFunction::EmitAutoVarDecl / EmitVarDecl / EmitDecl / EmitDeclStmt
... clang::ParseAST
```

This confirms tex3d's 2024-08-28 diagnosis independently: the decl's incomplete array type is
never completed, and CodeGen asks a question that is only meaningful for a complete type.

## One defect, three faces

This is why a message-matching predicate would have produced a false "fixed" verdict.

1. **Assert-enabled build** — `0xE0000001`, `Internal compiler error: LLVM Assert`.
2. **Release build** — the assert is compiled out and execution runs on into a null deref.
   Proved mechanically, not assumed: CASE 3 of `manual-case-assert-stack.txt` runs the Debug
   binary under `cdb` with `sxe -c "gh" e0000001`, i.e. steps past every assert to emulate
   `NDEBUG`. It reaches

   ```
   Access violation - code c0000005
   dxcompiler!ConvertScalarOrVector
   dxcompiler!AddMissingCastOpsInInitList
   dxcompiler!`anonymous namespace'::CGMSHLSLRuntime::EmitHLSLInitListExpr
   ```

   — the reporter's exact symptom, from the same input, in the same process.
3. **Silent wrong code** — for the minimal repro the Release path does not crash at all
   (CASE 4: exit 0, DXIL emitted). It emits **wrong code**, quietly. See below.

A predicate on "LLVM Assert" scores all 20 releases clean; a predicate on "access violation"
scores `main` clean. Only the exit-status predicate sees all of it.

## History: always reproduced

`bisect --linear` (linear because the filing date falls inside the release range, so agreeing
endpoints would only prove endpoint agreement):

**Reproduces on all 20 bisectable stable releases, v1.4.1907 (2019-07) … v1.9.2607, zero
invalid probes.** No fix window, no regression point. The earliest reproduction predates the
report by nearly two years.

Skipped by policy: 5 prereleases and `v1.2.0-alpha` (no usable asset). The issue text names no
prerelease, so no opt-in was warranted.

### A flag nearly hid the floor

The reporter's command line includes `-Wno-parentheses-equality`. v1.4.1907 does not know that
flag and exits `1` with `Unknown argument`, which the tool correctly demoted to
**invalid-probe** — an option unrelated to the bug was masking the oldest release. Dropping it
was justified by an equivalence control on ground truth: with and without the flag the captures
are byte-identical apart from headers (`variant-noparenflag-*`). `cmd.txt` documents the
single-token deviation; `cmd-as-filed.txt` keeps the reporter's line verbatim, and
`variant-as-filed-main-debug.txt` shows it still reproduces as filed.

### v1.5.2010 crashes with completely empty stderr

Exit `0xC0000005`, no text at all. Any text-based predicate would have drawn a fix boundary
exactly there.

## Second shape: silent wrong code, also on every release

`manual-case-miscompile-matrix.txt` — the 5-line minimal repro against all 20 stable releases:

- Every release **compiles it successfully** (exit 0, passes validation) and emits an **empty
  entry point**: `define void @main() { ret void }`. The `OUT` output is never written; there is
  no load and no `storeOutput`.
- The control differing by exactly one token (`int error_expr[1] = array1;`) emits
  `dx.op.createHandle` + `storeOutput` on every build including `main-debug`.
  `SELFTEST control-emits-storeOutput=pass`.

Restated as a compute shader so the bad value lands somewhere observable, `dxc_trunk` produces
DXIL its **own validator** rejects (`manual-case-godbolt-clang-controls.txt` CASE D):

```
error: validation errors
<source>:7:12: error: Assignment of undefined values to UAV.
note: at 'call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle %1, i32 0, i32 undef, i32 undef, i32 undef, i32 undef, i32 undef, i8 15)'
Validation failed.
```

The front end silently produced `undef` for every component. This is the only place validation
genuinely enters the picture, and the validator is behaving *correctly* — it is catching DXC's
own bad output. Note the exit status is an ordinary nonzero: by exit code alone this case is
indistinguishable from a user error, which is precisely why the crash, not this, anchors the
predicate.

So the crash and the wrong code are the same defect seen at different points: whether the null
deref happens depends on how much work the bad initialiser has to do.

## Cross-compiler, measured (not repeated on trust)

`manual-case-godbolt-clang-controls.txt`, 8 cases, all self-tests pass.

- **FXC accepts the filed shader verbatim** (`/T vs_5_0 /E vert_main`, exit 0) — confirming
  llvm-beanz's comment by measurement. On the unsized compute variant FXC emits
  `store_uav_typed u0.xyzw, l(0,0,0,0), l(7,7,7,7)` — **byte-identical to the sized control**.
  FXC does not merely tolerate the form, it compiles it correctly.
- **Clang's HLSL front end rejects it**: `error: array initializer must be an initializer list`,
  landing on exactly the two crashing declarations. Controlled three ways, because Clang's HLSL
  support is incomplete and fails for unrelated reasons: a trivial vertex shader with the same
  flags compiles clean (CASE A); the compute restatement isolates the construct from the
  `SV_ClipDistance` gap (CASE B); and the one-token sized version compiles clean (CASE C). The
  difference survives all three.

That is a real answer to the language question raised in the thread: the successor front end
has already chosen "diagnose and fail", and FXC has already chosen "support it". They disagree.

## Compiler Explorer

<https://godbolt.org/z/aYedzh96v> — the filed shader, unmodified.
`dxc_1_6_2112` and `dxc_trunk` both `SIGSEGV` (exit 139); `hlsl_clang_trunk -fsyntax-only` shows
the two initializer-list errors. Full pane text in `manual-case-godbolt-verify.txt`.

CE runs Linux **Release** builds, so the assert cannot appear there — CE corroborates the local
Debug build and never overrules it. Ignore the pane's `SV_ClipDistance` / `SV_CullDistance`
errors; those semantics are unimplemented in Clang and are unrelated.

## Labels

Live taxonomy checked with `triage.py labels --refresh` (58 labels), not from memory.

Current: `bug`, `crash`, `incorrect-code` — all three now independently evidenced; keep.

Suggested additions:

- **`correctness`** ("Bugs that impact shader correctness") — the silent empty entry point on
  all 20 releases and the `undef` stores are a wrong-code bug, distinct from `incorrect-code`
  which is about handling *invalid input*.
- **`fxc-disagrees`** ("Issues tracking differences between FXC and DXC") — measured here, not
  inferred: FXC compiles the filed shader and generates correct code for the construct.
- **`hlsl-next`** ("Bugs for consideration on next language version"), tentative — the thread
  ends on an unresolved language question (support it, or diagnose and deprecate it), and Clang
  has already picked one answer. A maintainer call, not a triage call.

Explicitly **not** proposed:

- **`validation`** — its description is "Related to validation or signing", meaning DXIL
  validation. Despite the issue title, the defect is in clang CodeGen. The one validation error
  observed is the validator working correctly on bad input DXC generated.
- **`check-in-clang`** ("See if this repros in clang as well") — that request is a to-do, and it
  has been carried out and answered above.

## Suggested action

`still-valid-keep-open`. The next step is a product/language decision that already has both
options written down in the thread (diagnose-and-fail, or complete the type); triage should not
pre-empt it. Whichever is chosen, the current behaviour — crash on one input, silent wrong code
on another — is not a defensible outcome for either.
