# Notes — #5244

## Issue

Feature request: "Add support for RWTexture2DMS in the SPIR-V backend". The reporter's own
shader (recovered verbatim from the linked CE sessions via
`godbolt.org/api/shortlinkinfo/<id>`) compiles cleanly to DXIL (`-T ps_6_7 -E PS`,
https://godbolt.org/z/z8qvbMEjd) but fails for SPIR-V (`-spirv -Zi -fspv-reflect -T ps_6_7
-E PS`, https://godbolt.org/z/59nPrsbdo). A collaborator (s-perron) replied the same day
(2023-05-29) that the SPIR-V generated for this construct "is wrong a lot of ways" and no fix
was expected soon; a 2024-05-16 comment reiterates the feature "still need[s] to implement".
Cross-reference timeline (`gh api .../issues/5244/timeline`) shows two related tickets in a
*different* repository, `llvm/offload-test-suite#1079` and `#1428` ("Support testing of
multi-sampled textures"), which are test-infrastructure requests, not duplicates of this
compiler defect.

## What was tested

Repro: `repro.hlsl` (reporter's shader, unmodified) + `cmd.txt`
(`-spirv -Zi -fspv-reflect -E PS -T ps_6_7`, the reporter's exact SPIR-V command).

Ground truth: `main-debug`, Debug build, `dxc --version` =
`dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)`. The
binary self-reports `7665270b9` (a fork-local merge commit, "Merge remote-tracking branch
'origin/main' into triage", 2026-08-18), which does not resolve on the public repo. Verified
by **tree**, not by SHA: `git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df
7665270b990f4c21253b42414d4e1bfe1702dad5` touches nothing outside
`.github/skills/dxc-issue-triage/`, and `git merge-base --is-ancestor 89e2f98e...HEAD` holds
(exit 0). Control: the same diff against an ~200-commits-older ancestor of `89e2f98e...` (`git
diff --name-only 89e2f98e...~200 89e2f98e...`) shows real source changes outside the skill
directory (`.github/copilot-instructions.md`, `CONTRIBUTING.md`, `README.md`, ...), proving the
diff-based check can actually detect a difference when one exists. So the compiler under test
is equivalent, source-for-source, to public upstream `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
(2026-08-12, "[HLSL] Add LinAlg descriptor I/O offset, stride and layout coverage (#8762)").

### Primary probe: still a crash, not merely "unimplemented"

```
$ dxc -spirv -Zi -fspv-reflect -E PS -T ps_6_7 repro.hlsl
Internal compiler error: LLVM Assert            # exit 0xE0000001
```

`out-main-debug.txt`. Under `cdb` (`assert-stack.cmd` / `manual-case-assert-stack.txt`), continuing past
each assert with `gh` (emulates `NDEBUG`/Release) shows there are *two* chained asserts, both
inside `clang::spirv::PreciseVisitor::isAccessingPrecise`
(`tools/clang/lib/SPIRV/PreciseVisitor.cpp:72`, then `include/llvm/ADT/ArrayRef.h:197` — an
out-of-range access into the multisample resource's SPIR-V `StructType::fields`), and that
continuing past *both* still does not produce valid output: DXC's own embedded SPIRV-Tools
validator then rejects the module before it is written:

```
fatal error: generated SPIR-V is invalid: [VUID-StandaloneSpirv-UniformConstant-04655]
UniformConstant OpVariable <id> '7[%gUav]' has illegal type.
```

So the defect is not "the feature throws an assert" in isolation — it is "SPIR-V codegen for
`RWTexture2DMS` produces an invalid module", and the assert is only how a Debug build happens
to notice it first.

### Controls

- `variant-control-dxil-main-debug.txt` (`--args "-T ps_6_7 -E PS repro.hlsl"`, `--expect
  no-match`): the identical shader compiles to DXIL with exit 0 — matches the reporter's own
  contrast and confirms the predicate does not fire on the (working) DXIL path.
- `variant-control-trivial-spirv-main-debug.txt` (`control-trivial-spirv.hlsl`, a one-line
  `SV_Target` pixel shader with no multisample resource, `--expect no-match`): compiles to
  SPIR-V with exit 0 — confirms the predicate is not "any SPIR-V compile crashes".

### History

`match.json` is `any_of[internal_failure, contains "generated SPIR-V is invalid", contains
"unknown shader module: invalid"]`. A first bisection using `internal_failure` alone scored
**every** stable release `no-repro` and reported `never-repro'd-in-releases` — the tool's own
NDEBUG warning fired (`the ground-truth probe failed with 0xE0000001, a status only an
assert-enabled build produces`). Inspecting the actual release captures showed why: every
release binary reaches the *same* invalid-SPIR-V codepath but, with the assert compiled out
under `NDEBUG`, keeps going far enough for DXC's own validator to catch the malformed module
cleanly and exit `0x80004005` (E_FAIL) instead of crashing — the mirror case to #2191, where an
assert-only defect really is silent in Release. Here the underlying defect is *not* silent in
Release; only its *signature* changes. `out-v1.6.2104.txt` prints the older SPIRV-Tools
message (`error: unknown shader module: invalid`, no VUID); from `out-v1.7.2207.txt` onward the
validator prints the detailed `VUID-StandaloneSpirv-UniformConstant-04655` message — an
instrumentation change in the embedded validator, not a behavioural transition (every release
in the range still fails to produce output either way).

`python scripts/triage.py bisect --issue 5244 --linear` (linear, because the two textual
signatures are compositionally new and monotonicity was unverified going in):

- `v1.4.1907`: `invalid-probe` — `dxc failed : SPIR-V CodeGen not available. Please recompile
  with -DENABLE_SPIRV_CODEGEN=ON.` This build was not compiled with SPIR-V support at all (a
  whole-binary flag, not a feature-specific rejection), so it never reaches the code under
  test.
- `v1.5.2010` through `v1.9.2607` (19 stable releases, no further invalid probes; 5
  probeable prereleases correctly excluded by policy): **`repro`** on every one.

**Result: `always-repro'd`**, as far back as SPIR-V codegen exists in a checkable release
(v1.5.2010, 2020-10-22 — three years before this issue was even filed). This is not a
regression: nothing in the thread claims SPIR-V ever emitted this construct correctly, and no
release ever did.

### Compiler Explorer

https://godbolt.org/z/oj91s731v — `dxc_1_6_2112` (CE's oldest) and `dxc_trunk` both still fail
(`manual-case-godbolt-verify.txt`, full panes; read back and verified via
`api/shortlinkinfo`). `godbolt-note.txt` tells the reader to compare against the DXIL sibling
command, which succeeds.

## Labels

Current: `enhancement`, `spirv`, `sm6.7`. The finding is stronger than "not yet implemented" —
`main` (and every shipped release) crashes/fatal-errors rather than diagnosing the gap
cleanly, and the crash form is a genuine assert reachable from a straightforward, valid HLSL
shader. Proposing to add `bug` and `crash` alongside the existing `enhancement` (label
descriptions: `bug` = "Bug, regression, crash"; `crash` = "DXC crashing or hitting an assert").
Not proposing any removal — `enhancement` still correctly captures that the ask is "implement
this for SPIR-V", and `spirv` / `sm6.7` are both accurate.

## Verdict

- status: `repros`
- repro-quality: `complete`
- history: `always-repro'd` (v1.5.2010..v1.9.2607, 19 probeable stable releases; v1.4.1907
  is an invalid probe — no SPIR-V codegen in that binary at all; 5 prereleases excluded by
  policy)
- confidence: `high`
- suggested-action: `still-valid-keep-open`
