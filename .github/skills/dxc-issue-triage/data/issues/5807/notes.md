# Notes -- #5807 "Error in implicit conversions when enums are involved"

## Summary

Filed 2023-10-01 against a Linux trunk build (`6b4b0eb5`). The repro is complete and minimal:

```hlsl
enum E : uint {
    A,
    B
};

float4 PSMain() : SV_Target0 {
    uint e = E::A << 1u;
    return 0.0;
}
```

`dxc -T ps_6_0 -E PSMain repro.hlsl` still fails with the exact reported diagnostic:

```
repro.hlsl:7:22: error: cannot convert from 'unsigned int' to 'E'
    uint e = E::A << 1u;
                     ^
```

(`out-main-debug.txt`, ground truth `main-debug` @ `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
`dxc --version` self-reports `1.9.0.5465 (triage, 7665270b9)`). Exit code 2147500037
(0x80004005 / E_FAIL) is DXC's ordinary diagnosed-error status, consistent with this being a
Sema diagnostic rather than an internal failure -- there is no crash here, just a wrong
diagnostic on valid code.

## Maintainer diagnosis (already on the thread)

`llvm-beanz` (2023-10-03, COLLABORATOR) attributed the bug precisely: `SemaHLSL.cpp`'s
`HLSLExternalSource::CanConvert` does not correctly implement the C++ rule that an
explicitly-typed, non-`class` (unscoped) enum implicitly converts to its underlying integer
type. He also tagged `hlsl-next`, expecting the eventual move to C++ overload-resolution rules
in HLSL 202x to fix this incidentally.

## Source corroboration

`SemaHLSL.cpp` does distinguish scoped and unscoped enums at the type-kind level
(`AR_BASIC_ENUM` vs `AR_BASIC_ENUM_CLASS`, chosen by `ET->getDecl()->isScopedUsingClassTag()`
around line 4895-4898), and `AR_BASIC_ENUM` is flagged
`BPROP_ENUM | BPROP_NUMERIC | BPROP_INTEGER` (line 456) -- i.e. the type system already
considers an unscoped enum numeric/integer. `ConvertComponent` (line 10068 on) explicitly
allows `enum -> int/float` for the non-class case ("enum -> int/float", line 10097-10100) and
only forbids enum<->enum and int/float->enum. So the base implicit-conversion machinery this
function drives is not missing enum-to-int support in general -- the defect this issue reports
is localized to how the built-in binary-operator (shift) overload set is resolved for an
`E`/`uint` operand pair, matching llvm-beanz's comment that it's specifically the conversion
path used during operator overload resolution, not `ConvertComponent`'s general rule.

## Controls

- `control-bitor.hlsl` -- same enum, `E::A | 1u` in place of `<<`. Compiles clean, exit 0,
  produces the expected constant-folded DXIL (`variant-bitor-main-debug.txt`), matching the
  reporter's own claim that `|` works and `<<` does not. This anchors that the defect is
  specific to the shift operator's overload resolution, not a blanket "enum can't be used in
  any binary expression" regression.
- `control-badconv.hlsl` -- `E e = 5;` (implicit int-literal-to-enum, which C++ also forbids
  without a cast). Still errors, but with a different message
  (`cannot initialize a variable of type 'E' with an rvalue of type 'literal int'`,
  `variant-badconv-main-debug.txt`) -- confirms the compiler's enum-conversion diagnostics are
  alive and firing in general, so the primary probe's error is not an artifact of a globally
  broken diagnostic pipeline.

`match.json` deliberately quotes the reported diagnostic text verbatim
(`cannot convert from 'unsigned int' to 'E'`), per the "reported symptom IS a diagnostic" case
in SKILL.md, so an old release rejecting the shader for an unrelated reason (e.g. not parsing
unscoped enums with an explicit underlying type at all) is not conflated with this specific
misdiagnosis.

## History

`bisect --issue 5807` checked both endpoints (v1.4.1907 and v1.9.2607), both `repro`, so it
short-circuited: **always-repro'd across v1.4.1907..v1.9.2607** (all probeable stable
releases; 5 prereleases and one release lacking a usable asset excluded from the search per
policy). Both endpoint releases parsed the unscoped-enum-with-explicit-underlying-type syntax
fine (matching `enum2.hlsl` in the test suite, which exercises the same shape at `-HV 2017`),
so neither endpoint is an invalid probe -- the shift-operator overload defect predates the
oldest bisectable release and is not a recent regression.

## Compiler Explorer

`godbolt --issue 5807 --compilers "dxc_1_6_2112,dxc_trunk,hlsl_clang_trunk"`:
https://godbolt.org/z/dE4KrbPjY (full panes in `manual-case-godbolt-verify.txt`).

- `dxc_1_6_2112` and `dxc_trunk`: both reproduce, identical diagnostic to the local build.
- `hlsl_clang_trunk` (the Clang-based HLSL front end that is replacing this parser): **exit 0,
  compiles cleanly**, and its embedded debug info (`!DIEnumerator`) shows `A`/`B` correctly
  typed as `unsigned`/`isUnsigned: true` DXIL is emitted for `PSMain` exactly as the trivial
  reference shader would produce. This is a real, positive finding, not merely "no crash":
  Clang succeeded in constant-folding and lowering the whole shader, so the successor compiler
  does not carry this specific defect forward -- consistent with, though not proof of,
  llvm-beanz's expectation that HLSL 202x/Clang's C++-style overload resolution incidentally
  fixes this.

## Verdict

- status: `repros`
- repro-quality: `complete`
- history: `always-repro'd` (v1.4.1907..v1.9.2607, both stable-release endpoints checked;
  bisect short-circuited since both agree)
- confidence: `high` (maintainer already attributed the defect to a specific function; source
  reading corroborates that the general enum->int conversion path is *not* the broken part,
  narrowing the defect to shift-operator overload resolution; local build, 20-release history,
  and Compiler Explorer trunk/1.6.2112 all agree)
- suggested action: `still-valid-keep-open` -- current labels (`bug`, `hlsl-next`) already
  match the finding; no label change proposed. This is exactly the kind of narrow, described,
  root-caused bug the labels already say it is, and the maintainer's own comment already
  states the intended long-term (HLSL 202x) resolution, so nothing here should be construed as
  asking for a near-term DXC-only fix beyond what's already on the thread.
- text-stale: none. The issue title, body and the one maintainer comment all still accurately
  describe current behavior; no drift found.

`reviewed_by`: intentionally left unset. Per this triage session's brief, the required
different-model draft review (SKILL.md step 10) and `verdict --reviewed-by` are batch-level
collation steps, not part of this single-issue session.
