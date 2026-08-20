# Expected symptom -- #5823

## Repro quality: complete (multiple Compiler Explorer links in the thread; reporter also
pasted inline source once)

## What "this reproduces" means

The issue has evolved across 2.5 years and, read end to end, makes **three** distinct claims
that must be scored separately (multi-ask decomposition, step 4):

1. **Original report (2023-10-03):** compiling a templated struct
   (`GaussLegendreValues<Order, float_t>`, partial specialization on `Order==2`) that declares
   `const static float_t wi[2];` in-class and defines it out-of-line as
   `template<typename float_t> const static float_t GaussLegendreValues<2,float_t>::wi[2] = {...};`
   (note: this OOL definition illegally repeats `static`, which cassiebeckley's own later
   analysis calls "always wrong") with `-HV 202x -T ps_6_7 -E PSMain -spirv` **SIGSEGVs the
   compiler**. Without `-spirv` (DXIL) it "works and produces DXIL" per the reporter.
   Root-caused by cassiebeckley (2023-10-19) as an `InitListExpr` carrying type `void` that the
   SPIR-V backend cast-handling does not expect (`error: casting to type 'void' unimplemented`
   is the non-crashing shape of the same defect); confirmed by llvm-beanz that Clang's C++ AST
   also gives the `InitListExpr` type `void`, so the AST is correct and the fix belongs in the
   SPIR-V backend. cassiebeckley said "I'll update the backend then" but the thread has no
   later comment or linked PR confirming a fix landed.
   **Expected if fixed:** the exact 2023 repro (with the illegal `static` at the OOL site) no
   longer SIGSEGVs under `-spirv`; it may legitimately still error (e.g. on the malformed
   `static`), since that input was always ill-formed.

2. **"Also affects DXIL" (2025-12-10 retitle):** using the corrected OOL syntax (`const`
   without the illegal extra `static`) on the same templated partial specialization, **without**
   `-spirv`, still fails with `casting to type 'void' unimplemented` -- i.e. the defect is not
   SPIR-V-backend-specific, it is common Sema/CodeGen for out-of-line initialization of a
   `static const` array member of a **template** (or template partial specialization).
   **Expected if fixed:** a syntactically well-formed OOL definition
   (`template<typename float_t> const float_t GaussLegendreValues<2,float_t>::wi[2] = {...};`)
   compiles successfully for both DXIL and SPIR-V targets.

3. **Two standing complaints restated 2026-02-24** (after the issue was briefly closed and the
   reporter said the repros still fail):
   a. DXC "wrongly requires `static const` at the [out-of-line] definition site" -- i.e. DXC
      *accepts* the illegally-repeated `static` keyword on an OOL member definition without
      diagnosing it (unlike Clang, which errors with `'static' can only be specified inside the
      class definition`), and instead of accepting cleanly or diagnosing the real problem it
      goes on to hit the `casting to type 'void' unimplemented` internal-error path. This claim
      is about the templated case only; the reporter's own non-template `Foo::someConstant`
      link shows the syntactically correct OOL form (`const`, no `static`) working "as
      expected" for a non-template struct.
   b. "I can't OOL define members of a templated struct, even with explicit instantiation" --
      i.e. even a **full explicit specialization** OOL definition
      (`template<> const float GaussLegendreValues<2,float>::wi[2] = {...};`) of a member that
      lives inside a class template still fails, not only the partial-specialization/template
      form from (2).

## Predicate

`internal_failure` for claim (1) -- SIGSEGV under `-spirv` is unambiguously a crash.

A `contains` predicate on `casting to type 'void' unimplemented` for claims (2) and (3b) -- this
is the diagnosed (non-crashing) shape of the same root cause, present in the 2023 root-cause
comment and every later repro link. `internal_failure` is composed in via `any_of` in case the
manifestation has reverted to a crash on the ground-truth build.

Claim (3a) (silently accepting illegal `static` at the OOL site) needs a **missing-diagnostic**
control pair (skill step 4): (a) Clang's diagnostic text
`'static' can only be specified inside the class definition` must NOT appear (DXC has never
implemented this specific check, confirmed by every capture below), and (b) the same shader
with the illegal `static` removed must behave identically to confirm DXC is not instead silently
accepting a semantically different program.

## Not-compiler-verifiable aspects

None identified -- every claim above is a compile-time Sema/CodeGen question answerable by
`dxc`/`dxc -spirv` alone.
