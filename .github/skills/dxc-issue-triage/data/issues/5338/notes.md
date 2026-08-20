# #5338 — Arrays cast compiler error

**Verdict: repros.** `dxc -T vs_6_0 repro.hlsl` still fails today on
`main-debug` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`, `dxc
--version` reports `1.9.0.5465 (triage, 7665270b9)`): a Debug/assertions
build traps `!(onlyUsedByLifetimeMarkers(BCI))` in
`ScalarReplAggregatesHLSL.cpp`, function `RewriteBitCast` — the exact
assertion `llvm-beanz` quoted in the 2023-06-30 maintainer comment (only the
line number moved, 2548 → 2630). A Release build of the same code instead
hits the reporter's own quoted text, `llvm::cast<X>() argument of
incompatible type!` (confirmed on `dxc_trunk` via Compiler Explorer). Both
are the same defect surfacing differently by build configuration, per
SKILL.md step 4 — `internal_failure` is exit-status based for exactly this
reason.

## Ground truth

`main-debug` is registered at `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
matching the ground-truth sha specified for this batch. Verified by tree, not
by SHA: `git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD`
shows **5405** changed files, **all** under `.github/skills/dxc-issue-triage/`
— zero outside it. Control (an older commit, 5 back): the same diff shows
real source files outside the skill directory (`azure-pipelines.yml`,
`lib/DxilValidation/DxilValidation.cpp`, etc.), proving the check can detect
a real difference. `dxc.exe --version` was run directly and reports
`dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage,
7665270b9)`, matching the registry exactly. The self-reported commit
(`7665270b9`, a local merge commit) differs from the cited public sha because
of intervening fork-local triage commits, exactly as SKILL.md's "Cite a
publicly resolvable commit, not whatever the binary self-reports" note
describes — the tree-diff control is what establishes their equivalence, not
the version string.

## Repro

The issue body supplies the exact command (`dxc -T vs_6_0 test.hlsl`) and the
full source verbatim; used as filed, entry point defaulting to `main`.
Repro quality: **complete**.

```hlsl
void castFunc(out float4 afClipD[MAX_CLIPPINGPLANES_CASCADE_>>2])
{
    [unroll]
    for (int n=0;n<MAX_CLIPPINGPLANES_CASCADE_;++n)
        ((float[MAX_CLIPPINGPLANES_CASCADE_])afClipD)[n]=float(n*n);
}
```

`afClipD` is `float4[2]`; the loop body reinterpret-casts it to `float[8]` and
assigns `n*n` element-by-element.

## Primary predicate (`match.json`, `internal_failure`)

`out-main-debug.txt`: exit `2147483651` (0x80000003, an assert trap) →
`repro`. A plain run only prints `Internal compiler error: Terminal Error
0x80000003` (the assert text goes to `OutputDebugString`, not stderr), so I
captured the actual assertion with `cdb` (`assert-stack.cmd`, committed —
generates `manual-case-assert-stack.txt`, "g;kn 40;q" launch, matching
SKILL.md's guidance for a trapped/breakpoint-style DXASSERT rather than the
`sxe`-based launch used for exception-style asserts elsewhere):

```
Error: 	!(onlyUsedByLifetimeMarkers(BCI))
File:
...\lib\Transforms\Scalar\ScalarReplAggregatesHLSL.cpp(2630)
Func:	`anonymous-namespace'::SROA_Helper::RewriteBitCast.
	expected struct bitcast to only be used by lifetime intrinsics
```

This is word-for-word the maintainer's quoted message and function; only the
source line moved (2548 in 2023 → 2630 today).

**Control** (`control-no-cast.hlsl`, `--expect no-match`): identical struct,
signature and `[unroll]` loop, without the reinterpret cast — assigns
`float4` elements directly. `variant-no-cast-main-debug.txt`: exit 0,
`no-match`, as declared. This proves the predicate does not fire on ordinary
array/out-parameter code, only on the specific cast construct.

## History — non-monotonic, and the "fixed" window was never a fix

`bisect --linear` (mandatory here per SKILL.md — the maintainer's comment
already implies more than one code path, so endpoint agreement would be
unsafe to trust):

| release | `match.json` (crash) | `match-diagnostic.json` (validation error) |
| --- | --- | --- |
| v1.4.1907 (2019-07) | **repro** — genuine hang, confirmed at 240s (see below), not a 60s-timeout artefact | n/a — never got that far |
| v1.5.2010 .. v1.6.2112 (2020-10 .. 2021-12, 5 releases) | no-repro | **repro** |
| v1.7.2207 .. v1.9.2607 + main-debug (2022-07 .. today) | **repro** | n/a — crashes instead |

`triage.py bisect --issue 5338` (no `--linear`) reports this directly:
*"non-monotonic history ... transitions at v1.5.2010 -> no-repro, v1.7.2207
-> repro"*.

**The middle window is not a fix.** `out-v1.5.2010.txt` /
`out-v1.6.2104.txt` / `out-v1.6.2112.txt` all exit `2147500037` (E_FAIL) with
an ordinary DXIL-validation diagnostic:

```
error: validation errors
...: error: Not all elements of output SV_ClipDistance were written.
Validation failed.
```

That is a genuine diagnosed rejection, not success — the reinterpret-cast
still confuses the compiler's output-write tracking for `SV_ClipDistance`,
it just gets caught by validation instead of an unchecked `cast<>`. I added
`match-diagnostic.json` (a `contains` predicate on that exact message) and
re-ran `bisect --match match-diagnostic.json --linear`: it reports
*"always-repro'd across v1.5.2010..v1.6.2112"* for that predicate, and `n/a`
(never reached, by timeout or by crash) everywhere else. **At no release in
the tested history, v1.4.1907 through v1.9.2607, nor on `main-debug`, does
this input ever compile successfully.** Reading `out-v1.5.2010.txt` alone as
"fixed" — which a single-predicate bisect would invite — would be wrong;
SKILL.md's "An `all_of`/multi-signature result hides which clause moved"
warning generalises to this case even though the two predicates are
independent files rather than clauses of one.

**v1.4.1907's hang is real, not a 60-second artefact.** Re-ran it with a
240-second timeout (four times the tool's default) via the committed
`hang-check.py` harness; capture in `manual-case-v1.4.1907-hang-check.txt`.
It still did not return. So the oldest probeable release fails this input a
*third* way (hang) rather than compiling it — reinforcing that the
construct has never worked, only failed differently across the compiler's
history.

**Regression window, unverified due to scope.** `git log --oneline
v1.6.2112..v1.7.2207 -- lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp`
finds 7 commits; the most plausible is `ed717499a` ("Fix memcpy replacement
removing memcpy to output argument (#4456)", 2022-05-12), which changes
`LowerMemcpy`'s decision about which `Dest` values get replaced specifically
for `Argument` (i.e. `out`/`inout` parameter) destinations — directly on
point for `castFunc`'s `out float4[]` parameter. This is a plausible
candidate, not a proven one: this task's scope explicitly excludes rebuilding
or relinking any target (no parent/candidate commit build was performed), so
I did not confirm it the way SKILL.md recommends for an exact-commit claim.
Treat it as an unverified lead for a future session, not an attribution.

## Compiler Explorer

`godbolt --compilers "fxc_10_0_19041:/T vs_5_0 /E main,dxc_1_6_2112,dxc_trunk"`
— https://godbolt.org/z/5nqjfhfve (link re-verified by read-back; full panes
in `manual-case-godbolt-verify.txt`). `-T vs_6_0` cannot be given to FXC at
all (`Unsupported shader model specified "vs_6_0"`, confirmed as an
`invalid-probe`-shaped rejection in a first attempt with `/T vs_6_0`, not a
finding); `/T vs_5_0` is the correct control for the reporter's "5.1 and
lower" claim:

- **`fxc_10_0_19041` (`/T vs_5_0`): exit 0.** FXC not only accepts the cast,
  it constant-folds the whole `[unroll]` loop: `mov o1.xyzw,
  l(0,1.000000,4.000000,9.000000)` / `mov o2.xyzw,
  l(16.000000,25.000000,36.000000,49.000000)` — exactly `n*n` for
  `n=0..7` split across the two `SV_ClipDistance` registers. This is
  independent, strong confirmation that the construct expresses a
  well-defined, executable semantic that DXC has never correctly compiled.
- **`dxc_1_6_2112` (CE's oldest DXC, sits in the "no-crash" window):
  exit 5**, the same validation error as the local v1.6.2112 capture — CE
  corroborates the release-matrix result, not a clean compile.
- **`dxc_trunk`: exit 5, `CRASH`**, `error: cast<X>() argument of
  incompatible type!` (Linux spelling, no `llvm::` prefix — build-agnostic
  per SKILL.md) — reproduces the reporter's own quoted message on current
  trunk. CE runs Release builds and cannot show the Debug assert directly;
  `godbolt-note.txt` states this limitation.

## Labels

Current: `bug`, `crash`, `fxc-disagrees`. All three remain accurate and are
directly supported by this triage: it is a crash-shaped defect (`crash`), it
is a real bug still present on `main` (`bug`), and FXC's exit-0,
correctly-folded compile versus DXC's crash/hang/validation-reject across its
entire history is exactly what `fxc-disagrees` describes. **No label changes
proposed.**

## Cross-reference / duplicate note

The issue's only cross-reference, `#5987` ("Error assigning struct into
amplification payload"), was created 2023-11-08, predates this triage, and
concerns a different surface symptom in the same SROA/bitcast area. Left for
batch collation to judge relatedness; not asserted here.

## What I did not measure

- The exact regressing commit was not built or tested (task scope forbids
  rebuilds); the `#4456` lead above is a candidate, not a finding.
- Prereleases (`v1.5.2003`, etc.) were excluded from the search by policy, per
  SKILL.md; the issue text does not name any of them explicitly.
- No repeat/`--repeat` runs were needed: every release's result was a single
  consistent outcome (hang, diagnosed-reject, or crash), with no reported or
  observed nondeterminism.

## Suggested action

`still-valid-keep-open`. This is an always-currently-reproducing crash
(assert on Debug, `llvm::cast` internal error on Release) on an input that
has never compiled successfully at any measured point in the compiler's
history, contrasted with a legacy compiler that handles it correctly.
Confidence **high**.
