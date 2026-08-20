# Expected symptom

*Written before any investigation, from the issue text alone (step 2 of the skill).*

Reporter: `bob80905` (Joshua Batista), 2023-10-03. Labels: `enhancement`, `test`. No comments.

This is a test-organization request, not a bug report with a shader repro. It observes that
two GTest/TAEF methods in `tools/clang/unittests/HLSL/ValidationTest.cpp` --
`GSMainMissingAttributeFail` and `GSOtherMissingAttributeFail` -- only exercise a **clang
(Sema) diagnostic** ("stream-output object must be an inout parameter"), not DXIL
validation, and so are filed under the wrong test fixture. The ask: move these (and any
other `ValidationTest` entries that only test clang diagnostics) to
`tools/clang/unittests/HLSL/VerifierTest.cpp`, converting them to use `-verify` if the new
lit framework applies.

"This reproduces" (i.e. the request is still unmet) means: `GSMainMissingAttributeFail` and
`GSOtherMissingAttributeFail` (or their equivalents) are still registered as `TEST_F`/
`TEST_METHOD` entries in `ValidationTest.cpp` at ground truth, rather than in
`VerifierTest.cpp`. "Fixed"/does-not-repro would mean they have been moved (and, if
applicable, converted to `-verify`).

This is fundamentally a **source-code-verifiable** question about test-suite layout, not a
question a `dxc` invocation over the referenced `.hlsl` files can answer by itself --
compiling `attributes-gs-no-inout-main.hlsl` / `attributes-gs-no-inout-other.hlsl` will
produce the same diagnostic regardless of which C++ file registers the test that checks for
it. Running `dxc` on those two files is still useful as a **secondary** check: it can
confirm or refute the premise that the diagnostic is a Sema-layer error (not a DXIL
validation failure), which is the substantive part of the reporter's classification. But the
actual ask -- move the test registration -- is decided by reading
`ValidationTest.cpp`/`VerifierTest.cpp`, not by release-history bisection; no release
matrix applies.

Expected status: **`not-compiler-verifiable`** for the history/bisection question (there is
no compiler-version axis on which "which C++ file registers a unit test" could vary), with a
compiler-confirmed premise. Repro quality: **complete** -- the issue names two specific,
still-locatable test methods and their backing `.hlsl` files precisely enough that nothing
needs to be reconstructed or agent-constructed.
