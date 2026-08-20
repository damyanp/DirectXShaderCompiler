> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5064](https://github.com/microsoft/DirectXShaderCompiler/issues/5064).

Partially addressed as of `main` (`89e2f98e2`) — one of the two asks in this thread is resolved,
the other is not.

**Still open:** a LIT-compatible workflow for testing the DXIL validator itself. The
`%dxilver`/`%dxv` FileCheck-style tests this issue is about
(`tools/clang/test/HLSLFileCheck/validation/`, ~150 files) remain excluded from `lit` discovery —
`tools/clang/test/HLSLFileCheck/lit.local.cfg` still sets `config.suffixes = []`, set by #5537
(2023-08-18) as part of a blanket cleanup of ~10K unsupported-test discoveries, replacing an even
blunter `config.unsupported = True` from #4822 (2022-11-29). I confirmed this directly with
`lit --show-tests` against the built tree: both `HLSLFileCheck` and `DXILValidation` report
"contained no tests". The only way these tests run today is a manual, one-directory-at-a-time
TAEF invocation (`hcttest.cmd -filecheck <path>` → `CompilerTest::ManualFileCheckTest`), not
`check-all`/CI. Tests are still being added to this unreachable tree as recently as #6172
(2024-01-22), so this isn't just stale history. A separate, newer directory,
`tools/clang/test/HLSLFileCheckLit/`, shows a partial LIT migration has begun for HLSL codegen
tests generally — but it has no `validation` subdirectory, so validator tests specifically
haven't been part of that effort.

**Resolved:** the follow-up comment's narrower ask, "missing test coverage for external
validator workflows." `tools/clang/test/DXC/validate_1_6_2112.test`, `validate_1_7_2308.test`,
`validate_1_8_2502.test`, and `version_interface.test` now cover loading an external/older
validator via `DxcDllExtValidationLoader`, and are genuinely `lit`-discovered (confirmed via
`--show-tests`). Added by #7749 (2025-10-27), fixed up by #8075 (2026-01-22).

No shader or single `dxc` invocation applies here (this is a test-infrastructure design
question), so no CE link or release-history bisect is included; the timeline has no PRs
cross-referencing this issue, so this determination rests entirely on the current state of the
test tree rather than a linked resolution.

Given the core LIT-migration ask is still unaddressed, suggest keeping `tech-debt` and adding
`test` (existing label: "Test issues or more test coverage needed") to make this discoverable
alongside other test-infrastructure work.

---
<sub>Triaged with AI assistance from direct `lit --show-tests` discovery runs and `git log`/`git
show` evidence in this repository, not a compiler run against a shader; please flag anything that
looks wrong.</sub>
