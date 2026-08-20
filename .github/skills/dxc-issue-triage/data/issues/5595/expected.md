# Expected symptom / resolution criterion

Issue #5595 is a test-infrastructure feature request, not a compiler-behavior bug. There is
no HLSL repro and no compiler output that can confirm or refute it — the DXC compiler itself
is not the instrument here; the lit test-runner configuration is.

**Repro quality: `none`.** The issue body contains no shader, no command line, and no
compiler output. It is a design/tooling ask.

**What "resolved" would look like:** a lit test format (or equivalent lit-driven mechanism)
exists in the tree that reproduces what the TAEF `CodeGenHashStability*` test methods do today
— compiling each test shader twice (matching hash-affecting flag variants, e.g. with/without
`-Zi`) and comparing the resulting container hashes — so that a `.hlsl`/`.ll` file can be
moved from `tools/clang/test/HLSLFileCheck` (TAEF-only) to
`tools/clang/test/HLSLFileCheckLit` (lit) without losing hash-stability coverage.

**What would NOT count as resolved:** the existing `lit.formats.TaefTest` adapter
(`utils/lit/lit/formats/taef.py`), which lets `lit` invoke whole TAEF test **methods**
(including the existing `CodeGenHashStability*` methods) as opaque pass/fail units. That
already lets hash-stability tests be *listed and executed through* `lit`, but it does not let
an individual lit/FileCheck-style test file assert hash stability the way a file under
`HLSLFileCheck` implicitly gets today — it is not "a lit format for hash stability test" in
the sense the issue asks for, and it does nothing to unblock moving individual files out of
`HLSLFileCheck`.

**Falsifiable predictions to check:**
- current tree contains no lit format / harness (e.g. a `DxcHashTest` lit format class,
  a `HashStability.py` script, or a `%hash_stability` lit substitution) implementing this;
- no `.hlsl`/`.ll` file under `HLSLFileCheckLit` carries a hash-stability directive;
- any PR that attempted this and referenced #5595 is either merged (issue resolved) or not
  (issue still open and accurately described).
