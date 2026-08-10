# #4384 — Integer vector as enum type causes ICE rather than error

Ground truth: `main-debug`, Debug build, upstream commit `13730886e`,
`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`.
The binary self-reports the fork-local merge `ab5400907`, which resolves for nobody else;
`git diff --name-only 13730886e HEAD` shows no file outside the triage skill directory, and
the control `git diff --name-only 13730886e~2000 13730886e` does show unrelated files, so the
query can detect differences. Cite `13730886e`.

## Verdict

**Both halves of the title still reproduce**, on every stable release and on `main`.

| ask | predicate | result |
| --- | --- | --- |
| "causes ICE" | `match.json` — `internal_failure` | `repro` on all 20 stable releases v1.4.1907..v1.9.2607 and on `main` |
| "rather than error" | `match-diag.json` — presence of the correct diagnostic | not emitted on any build; every release is an `invalid-probe` because it crashed first |

## Repro

`repro.hlsl` is the issue's own two-line snippet plus a trivial `[numthreads(1,1,1)] void
main() {}`; the reporter was compiling a real shader, so the entry point is a restoration, not
an addition. `as-filed.hlsl` is the snippet with nothing added and fails identically
(`variant-as-filed-main-debug.txt`), so the entry point is inert.

`cmd.txt` is `-T cs_6_0 -E main repro.hlsl`. It drops five flags from the filed command line,
each measured rather than assumed — see `cmd-note.md`, `cmd-as-filed.txt`:

| variant | capture | result |
| --- | --- | --- |
| full filed flag set, `-spirv -Zpc -O3 -fspv-target-env=vulkan1.1 -HV 2021` | `variant-as-filed-flags-main-debug.txt` | identical failure |
| `-HV 2021` alone | `variant-hv2021-main-debug.txt` | identical failure |
| `-HV 2018` | `variant-hv2018-main-debug.txt` | identical failure |

Dropping `-spirv` and `-HV 2021` matters: v1.4.1907 has no SPIR-V codegen, and old releases
reject `-HV 2021` with `Unknown HLSL version: 2021`. Either would have made the two oldest
releases unprobeable for reasons unrelated to this bug. llvm-beanz's 2023-07-31 comment that
the crash affects DXIL as well as SPIR-V is confirmed by the DXIL arm reproducing everywhere.

The filed argument string is garbled (`_o3`; `-E -T cs_6_0` leaves `-E` with no entry name).
The reporter drove `IDxcCompiler3::Compile` with an argument array, so the pasted string is a
transcription artifact and is not treated as the command.

## One defect, three faces — why the predicate is exit-status-only

`match.json` is `internal_failure` and deliberately matches no message text. The linear scan
over 20 releases shows why:

| releases | exit | stderr |
| --- | --- | --- |
| v1.4.1907, v1.5.2010 | `0xC0000005` access violation | **empty** |
| v1.6.2104 | `0xE0000002` | `Internal compiler error: LLVM Unreachable` |
| v1.6.2106 .. v1.9.2607, `main` | `0x80AA001C` `DXC_E_LLVM_UNREACHABLE` | `Internal Compiler error: unknown conversion kind` |

A predicate keyed to `unknown conversion kind` would have reported the bug as introduced in
v1.6.2106 and absent from the two oldest releases — a regression that does not exist, and one
that would have discarded the two releases whose behaviour matches the reporter's own words
("reading illegal memory address, address varies from run to run") most closely. Nothing is
claimed here about which face the reporter's own build showed.

`0x80004005` (E_FAIL) appears throughout this directory on the *controls*; it is an ordinary
diagnosed error, not a crash, and `internal_failure` correctly does not match it.

**Not an NDEBUG artefact.** `include/llvm/Support/ErrorHandling.h:101` wraps `llvm_unreachable`
in `#if 1 // HLSL Change`, so it throws in Release builds too. Confirmed observationally: the
shipped Release binaries fail, and Compiler Explorer's Linux Release builds `SIGSEGV`.

## Root cause

`manual-case-unreachable-stack.txt`:

```
02 dxcompiler!llvm::llvm_unreachable_internal
03 dxcompiler!CheckConvertedConstantConversions
04 dxcompiler!CheckConvertedConstantExpression
05 dxcompiler!clang::Sema::CheckConvertedConstantExpression
06 dxcompiler!clang::Sema::CheckEnumConstant
07 dxcompiler!clang::Sema::ActOnEnumConstant
08 dxcompiler!clang::Parser::ParseEnumBody
```

`CheckConvertedConstantConversions` (`tools/clang/lib/Sema/SemaOverload.cpp:5101-5154`)
switches over `SCS.Second` and lists upstream clang's conversion kinds plus `ICK_Flat_Conversion`.
The five HLSL-specific kinds declared at `tools/clang/include/clang/Sema/Overload.h:94-101`
(`ICK_HLSLVector_Scalar`, `ICK_HLSLVector_Conversion`, `ICK_HLSLVector_Splat`,
`ICK_HLSLVector_Truncation`, `ICK_HLSL_Derived_To_Base`) are not listed, so they fall through
to the closing `llvm_unreachable("unknown conversion kind")` at line 5154 — which is the exact
file and line every build names in its message.

The kind is not inferred. `manual-case-suppressed-diagnostics.txt` reads it out of the failing
frame: `SCS->Second` is `ICK_HLSLVector_Truncation (0n29)` — `uint3(0,0,0)` truncated to the
`int` that `CheckEnumUnderlyingType` recovered to after rejecting `uint3`.

## The compiler already has the right diagnostic; the ICE throws it away

This is the sharpest finding, and it is measured three ways.

1. `control-uint3-scalar-init.hlsl` — the same invalid enum base, scalar enumerator — is
   diagnosed correctly: `error: non-integral type 'uint3' is an invalid underlying type`.
   `manual-case-diag-control-matrix.txt` runs it on all 20 stable releases and `main`:
   **21/21 builds emit that exact message, and all 21 compile a valid `enum : uint` cleanly**
   (instrument self-test). So the check has existed at least since v1.4.1907 (2019-07), and
   `match-diag.json`'s regex is not dead — the absence of that message from `repro.hlsl` on
   every build is a real absence.
2. `control-lost-diagnostics.hlsl` puts `undeclared_symbol` on line 1 *above* the enum. On its
   own that line is diagnosed (`variant-prior-diag-alone-main-debug.txt`,
   `use of undeclared identifier`); with the enum present, the run prints only the internal
   error (`variant-lost-diagnostics-main-debug.txt`). Diagnostics buffered before an internal
   error do not reach the user.
3. `manual-case-suppressed-diagnostics.txt` steps over the throw with cdb's `gh` and the
   compile continues, printing what was already in the buffer:

   ```
   repro.hlsl:1:11: error: non-integral type 'uint3' is an invalid underlying type
   repro.hlsl:2:9: error: enumerator value is not a constant expression
   ```

   That first line is precisely the diagnostic pow2clk asked for in 2022. It is produced and
   then discarded.

The consequence for triage bookkeeping: **the diagnostic half is not independently
measurable while the ICE is present.** `bisect --match match-diag.json --linear` marks all 20
releases `invalid-probe` (`# invalid-probe-reason: the probe failed internally, so it measured
nothing about the reported symptom`) and then prints *"no release could run this repro;
retarget it at a profile/flag set the releases support"*, which misattributes the cause — the
profile and flags are fine, the compile crashed. The per-release control matrix is what turns
that into a finding rather than a tooling artifact.

## Cross-compiler

`https://godbolt.org/z/rMsGE4K4s` (read back through `/api/shortlinkinfo/`; three panes,
arguments `-T cs_6_0 -E main`). Full text in `manual-case-godbolt-verify.txt`:

- `dxc_1_6_2112` and `dxc_trunk`: `SIGSEGV`, exit 139.
- `hlsl_clang_trunk`: `<source>:11:11: error: non-integral type 'uint3' (aka 'vector<uint, 3>')
  is an invalid underlying type`, plus `warning: implicit conversion turns vector to scalar
  ... [-Wconversion]` on the enumerator. Exit 1, no crash.

Controlled in `manual-case-clang-control.txt`: the same Clang build with the same arguments
compiles `control-valid-enum.hlsl` cleanly (exit 0), so the pane is not failing on everything,
and it produces the same base-type error for `control-uint3-scalar-init.hlsl`. The HLSL
front end being built in Clang therefore already does what this issue asks for, and it
survives the same vector-to-scalar conversion with a warning instead of an unreachable.

## Test coverage

`tools/clang/test/SemaHLSL/enums.hlsl` already asserts
`non-integral type '<T>' is an invalid underlying type` for `half`, `float`, `double`,
`min16float` and `min10float`, but has no vector case. Its `RUN:` lines use `-HV 2017`.

## Labels

Current: `bug`, `hlsl2021`, `crash`, `incorrect-code`.

- **add `diagnostic`** ("Issues for diagnostics") — the ask is exactly that an error be
  produced instead of an ICE.
- **remove `hlsl2021`** — the crash is language-version independent: identical at `-HV 2018`
  and at `-HV 2021` on `main`, and present on v1.4.1907 (2019-07), whose default predates
  HLSL 2021 entirely. DXC's own enum tests run at `-HV 2017`. The label was plausibly added
  because the reporter's command line carried `-HV 2021`. Proposed, not applied; the thread
  may hold history this triage cannot see.
- `crash`, `incorrect-code` ("Issues relating to handling of incorrect code") and `bug` all
  still fit and are kept.

## Not marked `text-stale`

The title — "causes ICE rather than error" — is exactly what the compiler does, and both
maintainer comments are accurate as written (measured: DXIL crashes too; the desired behaviour
is the `float` diagnostic, which is exactly the message that is being suppressed). The only
sentence that has moved is the reporter's description of the crash *form*: current builds
report a deterministic internal error rather than a varying illegal read. Two of the twenty
releases (v1.4.1907, v1.5.2010) still fail exactly as described, and the substance of the
report is unchanged, so this is a symptom-form note for the comment, not a staleness claim
about the reporter's writing.

## Evidence integrity

Seven captures contained the local Debug build's `UNREACHABLE executed at <path>:5154!` line,
in which `<path>` is `__FILE__` — the operator's checkout root, baked in at build time.
`prove-path-is-compiler-output.py` establishes that the path comes from `dxc` itself, by
running it directly with no harness and no shell. `triage.py` now redacts checkout, triage and
cache roots in stdout and stderr *before writing and before scoring*, so all seven were
regenerated with `run --force` and now read `<repo>\tools\clang\...`. A before/after comparison
of the `# verdict:` and `# exit:` headers of all 54 captures in this directory is empty, so
nothing load-bearing changed. Five of the seven had also been hand-redacted mid-session and
were regenerated once already; that mistake, and why an allowlist entry was the wrong
instrument, are recorded in `method-notes.md`. Release captures were never affected — the
shipped binaries embed Microsoft's build root instead.

## What was not determined

- Which crash face the reporter's own 2022-04-08 build (`dbd8db0e8`, one day before filing,
  between v1.6.2112 and v1.7.2207 — both of which reproduce) showed through
  `IDxcCompiler3::Compile`. Their described symptom matches the two oldest releases' face;
  no attempt was made to reconstruct their host process.
- Whether any diagnostic other than the two recovered under `gh` would be desirable; the
  second one, `enumerator value is not a constant expression`, is a consequence of the
  recovery to `int` and may or may not be wanted alongside the first.
- Nothing is claimed about a fix landing anywhere; no commit was built.
