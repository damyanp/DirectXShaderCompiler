# Expected symptom — issue #5999

**Report:** A global variable declared `globallycoherent RWByteAddressBuffer` is passed by
value into a templated function whose parameter type is a template parameter (auto-deduced).
The reporter expects the parameter's deduced type to retain the `globallycoherent` qualifier
(the same way an explicitly-typed `globallycoherent RWByteAddressBuffer` parameter does), but
observes a compiler diagnostic (warning, or error in a related example) suggesting the
qualifier is lost/mismatched during template argument deduction / canonical-type resolution.
The reporter also asks whether the generated DXIL/ISA is actually correct despite the
diagnostic (they saw no visual artifacts in production and their own disassembly inspection
looked correct).

**Reproduces (= issue confirmed) when:** compiling the distilled repro (a `globallycoherent`
resource passed into a template function parameter, alongside a call to an explicitly-typed
`globallycoherent`-parameter function) with `-T cs_6_6` produces a diagnostic naming
`globallycoherent`/coherence loss on the templated call, i.e. the qualifier is not retained
through template argument deduction.

**Maintainer position already on the thread (2024-01-18 / 2024-01-22, llvm-beanz &
pow2clk):** the warning is *not* a false positive — the compiler genuinely drops the
`globallycoherent` annotation during overload resolution / template instantiation because it
is implemented as an attribute rather than a true type qualifier, so it is lost whenever the
compiler computes a "canonical type". Because DXC currently *propagates* `globallycoherent` to
the resolved (non-coherent) resource in most cases, generated code is usually still correct,
merely with a possibly-unwanted extra memory barrier and an accompanying warning. This is
recorded as a known, hard-to-fix design limitation (shared by `row_major`), requiring
`globallycoherent`/matrix-orientation to become real type qualifiers — tracked as a
larger, breaking, future-language-version redesign, not a targeted bug fix. No commit or PR
fixing this is mentioned anywhere in the thread.

**Repro quality:** `complete` — llvm-beanz posted a working Compiler Explorer link
(https://godbolt.org/z/z4TnxrKqr) reproducing the reporter's own construct; KStocky posted a
second, structurally different CE link (https://godbolt.org/z/sP6rKvYov, template
specialization on `globallycoherent RWBuffer<int>` vs `RWBuffer<int>`) illustrating a related
but distinct facet (type-system treatment of the qualifier in template specialization, not
template argument deduction of a call parameter). This triage uses the first (the one
directly matching the issue body) as the primary repro and treats the second as a *related*
control, not a duplicate to be silently merged.

**What would falsify "still reproduces":** the templated-function repro compiling with no
`globallycoherent`/coherency-related diagnostic on `main`, i.e. the qualifier now being
retained through deduction (or the warning demonstrably removed as no-longer-applicable),
which would be a design change nothing on the thread claims has happened.
