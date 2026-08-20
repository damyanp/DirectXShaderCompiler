> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5824](https://github.com/microsoft/DirectXShaderCompiler/issues/5824).

Still unaddressed on `main` (89e2f98e2). `GSMainMissingAttributeFail` and
`GSOtherMissingAttributeFail` are still registered in
`tools/clang/unittests/HLSL/ValidationTest.cpp`:

```cpp
TEST_F(ValidationTest, GSMainMissingAttributeFail) {
  TestCheck(L"..\\CodeGenHLSL\\attributes-gs-no-inout-main.hlsl");
}

TEST_F(ValidationTest, GSOtherMissingAttributeFail) {
  TestCheck(L"..\\CodeGenHLSL\\attributes-gs-no-inout-other.hlsl");
}
```

and are still absent from `tools/clang/unittests/HLSL/VerifierTest.cpp`.

The premise checks out: both tests call `TestCheck()`, which runs the file's
`// RUN: %dxc ... | FileCheck %s` line — not `CheckValidationMsgs()`, the fixture's other
helper that actually calls `IDxcValidator::Validate`. Compiling both backing files directly
confirms it too: each produces `error: stream-output object must be an inout parameter` and
exits `0x80004005` (E_FAIL, an ordinary diagnosed error) before any DXIL container exists to
validate. So despite living in `ValidationTest`, these two are exercising a clang/Sema
diagnostic, exactly as described.

This isn't something a release-history bisection can answer — no `dxc` invocation's output
depends on which `.cpp` file registers a unit test — so there's no Compiler Explorer link;
the evidence here is source reading plus one confirmatory compile.

One thing worth flagging: the issue's second sentence generalizes to "any other tests inside
validationTest that only test clang diagnostics." This review only checked the two named
tests; it did not audit the rest of `ValidationTest.cpp` for further candidates, so the
broader clause is neither confirmed nor refuted here.

For context: the issue carries a `Dormant` milestone (added 2024-10-23), no assignee, and no
linked PR in its timeline.

Labels (`enhancement`, `test`) still look right; no change suggested.

---
<sub>Triaged with AI assistance. This assessment was produced by reading the current source
directly and confirming the diagnostic's layer with one ground-truth compile; please flag
anything that looks wrong.</sub>
