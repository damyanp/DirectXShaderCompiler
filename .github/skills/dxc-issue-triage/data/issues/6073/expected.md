# Expected symptom, from the issue text alone

Issue title: "Non-const static data members of templated structs fail to compile".

**Repro quality: `agent-constructed`.** The issue links three external
shader-playground.timjones.io URLs (a non-templated struct with a non-const static
member that works, a templated struct with a *const* static member that works, and
a templated struct with a *non-const* static member that fails) plus a
cpp.godbolt.org C++ link posted by a maintainer illustrating that the underlying
C++ pattern (an out-of-class definition of a static data member of a class
template) is legal. None of these are HLSL committed to this repo, so the HLSL
repro must be constructed from the issue's own quoted output rather than lifted
verbatim from an external interactive playground.

**Reported symptom (quoted verbatim from the issue body):**

> **Actual Behavior**
> Compiler outputs "Declaration may not be in a Comdat!
> i32* @"\01?Num@?$Test@$0CK@@@2HA"

This is an LLVM IR verifier failure message ("Declaration may not be in a
Comdat!") naming a global variable whose mangled name matches a static data
member `Num` of a class template `Test` (the `?$Test@$0CK@@` infix is an MSVC-style
mangled template instantiation, and `$0CK@` encodes an integer non-type template
argument). The maintainer's comment confirms this is a real defect ("we're
crashing in") attributed to how HLSL overrides codegen for `static`/global
variables, i.e. a code-generation bug that emits a `declaration` (no
initializer/body) global into a comdat group, which the LLVM module verifier
rejects.

**What "reproduces" means here:** compiling a templated struct with a
*non-const* `static` data member (with an out-of-class or in-class definition)
must trigger this same class of failure -- an internal/verifier-level failure
message containing the phrase "Declaration may not be in a Comdat", OR any
`internal_failure`-classified exit status (assert/access-violation/fatal-error)
if the verifier failure has since become a hard crash rather than a diagnosed
error. Per the reported title, a non-templated struct with the same
static-member pattern, and a templated struct with a `static const` member,
are NOT expected to show the symptom (the issue explicitly says both of those
already work) -- these make good negative controls.

**Repro-quality caveat:** because no HLSL source is directly available (only
external playground links this triage does not have credentials/tooling to
scrape reliably), the constructed repro is a best-effort HLSL translation of
the pattern described, aimed at reproducing the exact mangled-name shape quoted
in the issue (`Test<T, N>` with an integer non-type template parameter `N`,
`static T Num` member).
