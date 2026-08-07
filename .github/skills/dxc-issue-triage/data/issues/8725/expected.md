# Expected symptom - #8725 [SER] Passing a payload by value to `HitObject::Invoke` asserts in CodeGen

**Written before any compiler was run.** Derived only from the issue text
(`issue.json`, fetched 2026-08-06; issue filed 2026-07-31, **zero comments**).

**Repro quality: complete.** The body supplies a self-contained shader and the command line
(`-T lib_6_9`). Nothing has to be invented: entry point is declared with
`[shader("raygeneration")]`, so a library profile with no `-E` is correct as filed.

## What was reported

Passing a ray payload to `dx::HitObject::Invoke` through an **`in` (by value)** function
parameter crashes the compiler in CodeGen. `Invoke`'s payload parameter is `inout`, so a
by-value argument is not valid for it, but instead of a Sema diagnostic it reaches CodeGen and
asserts while emitting the call.

Reported manifestations, both quoted in the body:

| build | symptom |
| --- | --- |
| **Debug (asserts on)** | `Internal compiler error: LLVM Assert`, at `assert(castIsValid(op, S, Ty) && "Invalid cast!")` in `llvm::CastInst::Create`, reached from `CodeGenFunction::EmitCall` via `IRBuilder::CreateBitCast`. A *preceding* assert also fires: `assert(type->isReferenceType() == E->isGLValue() && "reference binding to unmaterialized r-value!")` |
| **Release (`NDEBUG`)** | the assert is compiled out, an invalid `bitcast` is emitted, and the user sees `error: validation errors` / `Function: ?RayGen@@YAXXZ: error: Instructions must be of an allowed type.` / `note: at 'unreachable' in block '#0' ...` / `Validation failed.` |

Reporter's environment: built from source at `7676b1f90` (`main`), x64, MSVC, Debug and
Release. Labels as filed: `bug`, `needs-triage`.

The body also states three things that are claims to **check**, not to assume:

1. it is **not** a payload-access-qualifier problem - "it reproduces with
   `-disable-payload-qualifiers` too";
2. it appears **specific to `HitObject::Invoke`** - "the same shader using `TraceRay` instead
   compiles fine";
3. `Function(inout Payload p)` compiles successfully, and is the workaround.

Each of these becomes a `variant-*` control below. The report's expected behaviour is a Sema
diagnostic ("the payload argument ... must be an `inout`-compatible lvalue"), not a successful
compile - so **a clean exit 0 would not be correct behaviour either**; it would be
`changed-behavior`, not a fix.

## The symptom reproduces if

**dxc fails internally while compiling the repro** - `internal_failure` per SKILL.md step 4:
0x80000003 / 0xE0000001 (trapped or thrown assert), 0xC0000005 (access violation),
0xE0000002/3 (`llvm_unreachable` / `report_fatal_error`), a POSIX signal on Linux builds, or
one of dxc's internal-failure text markers.

**Deliberately not keyed to the assert text.** The same defect wears two faces here and the
issue says so explicitly: a trapped assert in Debug, a bad `bitcast` surviving into DXIL in
Release. A predicate matching `Invalid cast!` would score every release build clean and
manufacture a "fixed" verdict.

Because the reporter documented the Release manifestation as well, the predicate is a
disjunction (SKILL.md's `any_of` guidance, measured on #3873): internal failure **or** the
specific DXIL-validation signature quoted above. Either face is the same defect - dxc failing
to compile, or miscompiling, a shader it should have diagnosed in Sema.

**A well-formed Sema/parse error is NOT this symptom.** dxc exits E_FAIL (0x80004005) for
ordinary diagnosed errors, so nonzero exit must not be read as a crash. In particular, if the
fix for this issue lands as the requested Sema diagnostic, the repro will exit 0x80004005 with
an `error:` line and the predicate must score that as **no-repro**.

## The forward feature-absence trap dominates the history axis here

SER / `dx::HitObject` is a Shader Model **6.9** feature and this issue is three weeks old. Every
shipping release older than SM 6.9 support will reject the repro before reaching CodeGen -
`invalid profile lib_6_9`, `use of undeclared identifier 'dx'`, `no member named ...` - which is
`invalid-probe` and is **evidence of nothing**. Separately, every release binary is a Release
build with `NDEBUG`, so the assert face cannot appear in one at all (the #2191 lesson).

I therefore expect the release axis to be **unmeasurable or near-unmeasurable**, and record in
advance that:

- `never-repro'd-in-releases` here would **not** be a fix and must not be reported as one;
- the honest history statement, if every release is an invalid probe, is "no shipping release
  can express this repro; the release axis is unmeasurable";
- `lib_6_9` is already the *oldest* profile that can express `dx::HitObject::Invoke`, so there
  is no lower target to retreat to. If a flag (validator override, experimental gate) turns out
  to be needed to reach CodeGen, prefer the *smallest* such set, and record it.

## Controls (all declared before running)

| variant | input | must |
| --- | --- | --- |
| `control-inout` | `Function(inout Payload p)`, otherwise identical | **not** match - the reporter's own workaround; if it matches, the predicate is not isolating the by-value parameter |
| `control-traceray` | same by-value parameter, `TraceRay` instead of `HitObject::Invoke` | **not** match - tests claim 2 |
| `nopaq` | repro with `-disable-payload-qualifiers` and no `[raypayload]`/access annotations | **match** - tests claim 1 |
| `control-hello` | a trivial `lib_6_9` shader with no SER at all | **not** match - proves `lib_6_9` itself is compilable by whatever compiler is under test, i.e. distinguishes "the feature is absent" from "the bug is present" |

`control-hello` is the one that matters most for this issue: it is what separates the three
outcomes the brief warns about - a release that ran the repro clean, a release that could not
express it at all, and a release that rejected it for an unrelated reason.

## What would make this inconclusive

- If the ground-truth Debug build does **not** assert: then either the repro is not faithful, or
  the defect was fixed between `7676b1f90` and the triage commit. That is a `does-not-repro` or
  `changed-behavior` claim needing a bisect over `main`, which is out of scope here; prefer
  `changed-behavior` if a diagnostic now appears, and say what the diagnostic is.
- If the assert fires on `control-inout` too, the repro is not isolating what #8725 describes.
