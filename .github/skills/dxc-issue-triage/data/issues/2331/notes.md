# #2331 — Problem with DXIL signing and switch case/enum use

Filed 2019-07-11 by @LautrecOfCarim. Triaged in batch 006 against `main-debug`
(`1.9.0.5433`, commit `ab5400907`), version string verified before any measurement:

```
dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)
```

`expected.md` in this directory was written from the issue text alone, before any compiler
ran; everything below is measured against it.

## Verdict

**Reproduces.** Unchanged since v1.4.1907, the oldest release available, which for a 2019
issue means "for as long as it is possible to check" rather than "since it was filed".

The title's framing is the reporter's inference and is worth correcting: **nothing is being
signed, because nothing valid is produced.** The shader fails DXIL validation, and signing is
downstream of validation.

## What was tested

`repro.hlsl` is the issue body's shader verbatim. The reporter used shader-playground and
quoted no command line, so `-T ps_6_0 -E MainPS` is inferred from the source (`MainPS()`
returning `float4 : SV_Target0`, `ConstantBuffer<T>`). There is therefore no
`cmd-as-filed.txt`: there was no filed command to preserve.

```
$ dxc -T ps_6_0 -E MainPS repro.hlsl                      # main-debug, exit 0x80004005
error: validation errors
repro.hlsl:24:1: error: Instructions must be of an allowed type.
note: at 'unreachable' in block '#4' of function 'MainPS'.
Validation failed.
```

Predicate (`match.json`): `all_of[contains "Instructions must be of an allowed type",
nonzero_exit]`. It matches the **rule text only**, deliberately — see "message wording"
below. Controls, both required to *not* match and both verified:

| control | result |
| --- | --- |
| `control-default-case.hlsl` — the repro plus `default:` | exit 0, clean, on main-debug, v1.4.1907 and v1.9.2607 |
| `control-enum-minimal.hlsl` — `enum class` + switch, no fall-off | exit 0, clean, same three |

The second control does double duty: it establishes that `enum class` and switch are
supported at the v1.4.1907 floor, so a failure there is a result and not a missing feature.

## History

`bisect --linear` over 20 releases, v1.4.1907 → v1.9.2607, plus main-debug: **21 probes, 21
matches, 0 invalid.** Every one exits `2147500037` = `0x80004005` = `E_FAIL`.

`always-repro'd across v1.4.1907..v1.9.2607`.

`E_FAIL` here is an ordinary diagnosed error. It is **not** an internal failure, and this
issue is not a crash.

### Message wording changed; the rule did not

```
v1.4.1907   at 0x2324278c200 inside block #0 of function MainPS Instructions must be
            of an allowed type
main-debug  repro.hlsl:24:1: error: Instructions must be of an allowed type.
            note: at 'unreachable' in block '#4' of function 'MainPS'.
```

The modern form carries a source location and names the offending instruction. That is why
the predicate matches the rule substring and not a whole line — a line-anchored predicate
would have scored the old releases `no-repro` and invented a regression.

It also means @tristanlabelle's 2019 bullet "the validation errors are too obscure" has been
substantially addressed in the intervening six years, even though the underlying defect has
not.

## Source corroboration

The 2019 diagnosis in the thread is still exactly what the code does.

* `utils/hct/hctdb.py:628-631` — `mark_disallowed_operations()` puts `Unreachable` in the
  disallowed list alongside `IndirectBr,Invoke,Resume,LandingPad`.
* that table generates `IsLLVMInstructionAllowed()` (`utils/hct/hctdb_instrhelp.py:955`,
  `hctgen.py:215`).
* `lib/DxilValidation/DxilValidation.cpp:3486-3491` calls it and emits
  `ValidationRule::InstrAllowed` on failure, whose text is
  `"Instructions must be of an allowed type."` (`hctdb.py:8306`).

So: the front end lowers "fall off the end of a non-void function" to `unreachable`, and
`unreachable` is disallowed by construction. Confirmed by compiling the repro with `-Vd`
(validation off), which succeeds and emits exactly that:

```llvm
  switch i32 %4, label %17 [ ... ]
; <label>:17
  unreachable
```

## Finding: two of the body's three secondary claims are now stale

The body makes three claims beyond the main symptom. All three were measured at every
release. This is a **body** staleness, not a title or comment one.

| claim | 2019 (v1.4.1907) | today |
| --- | --- | --- |
| **B1** comment out one case → validates clean, "but it shouldn't" | holds exactly: exit 0, valid DXIL | **stale** — clean front-end error, never reaches the validator |
| **B2** add a fourth enumerator `Fake` → still a validation error | holds: fails validation | **stale** — same front-end error; the validator is not reached |
| **B3** add `default:` → compiles clean | holds | **holds** (it is this triage's control) |

Today both B1 and B2 stop at Sema:

```
case-two-cases.hlsl:22:10: warning: enumeration value 'High' not handled in switch [-Wswitch]
case-two-cases.hlsl:28:1: error: control may reach end of non-void function [-Wreturn-type]
```

v1.4.1907 emitted both as *warnings* and compiled on. The transition is between
**v1.4.1907 and v1.5.2010** — measured, by running both variants against all 20 releases
(`variant-two-cases-*.txt`, `variant-four-enumerators-*.txt`), not inferred.

The cause is visible in source: `tools/clang/include/clang/Basic/DiagnosticSemaKinds.td:387`
and `:391` carry `DefaultError,   // HLSL Change: DefaultError` on
`warn_maybe_falloff_nonvoid_function` / `warn_falloff_nonvoid_function`. `git log -S` on that
exact string returns one commit: `8c43a1456` (2020-06-29), *"Default to error on missing
return from non-void function"*. Ancestry checked with both refs confirmed to resolve —
`git merge-base --is-ancestor 8c43a1456 v1.5.2010` exits 0, and against `v1.4.1907` exits 1,
with `git rev-parse` succeeding on both so the negative is a real negative.

The window v1.4.1907..v1.5.2010 holds **434 commits**, so this is attribution by ancestry
plus an exactly-matching source change and commit subject — strong, not certain; it was not
tested by building at the commit.

**Why this matters to the issue rather than being trivia:** @tristanlabelle's fourth bullet
asked for precisely this ("falling off the end of a non-void function should be a Sema
error"). It was delivered in 2020 — but only for switches the front end can *see* are
non-exhaustive. A switch covering every declared enumerator still slips past Sema, because
`-Wswitch` is satisfied, and lands on the validator. That is the entire remaining bug, and it
is exactly the gap tristanlabelle predicted when he pointed out that nothing constrains an
enum-typed value to its declared enumerators. The repro's own `(::QualityT)(shaderKey & 3)`
can produce `3`, which is not one of `Low/Medium/High`.

## Signing and `dxil.dll` (see `manual-case-signing.txt` for the full workings)

The reporter's output includes `warning: DXIL.dll not found.  Resulting DXIL will not be
signed for use in release environments.`, which is why the issue is titled as it is. That
warning is environmental (shader-playground shipped no `dxil.dll`) and incidental to the bug.
Established rather than assumed, because a history built on "half these releases had no
validator" would be worthless:

* **every cached release ships a `dxil.dll` beside its `dxc.exe`**, and **no probe in this
  triage printed the not-found warning** — so no probe ran without a validator available;
* `dxc --version` corroborates directly: v1.7.2207–v1.8.2505 report a loaded `dxil.dll:`;
  v1.9.2602 onward and main-debug do not. v1.4.1907–v1.6.2106 do not accept `--version`;
* the warning text is **not in current DXC source**. Binary-scanning `dxcompiler.dll` finds
  it v1.4.1907→v1.8.2407 and absent from v1.8.2505 on; `git log -S` attributes removal to
  `77b2ff676`, *"NFC: remove dead external validation code paths from dxcompiler"*;
* ground truth has a `dxil.dll` beside it and **ignores it**. Since that change,
  `dxcompiler.dll` no longer probes for a sibling; `dxc.exe` loads an external validator only
  when `DXC_DXIL_DLL_PATH` names an absolute path
  (`lib/DxcSupport/dxcapi.extval.cpp:433-462`).

Forcing the external validator via `DXC_DXIL_DLL_PATH` **changes the failure's shape without
changing the verdict**: exit becomes `0x80AA0009` (`DXC_E_IR_VERIFICATION_FAILED`) instead of
`0x80004005`, and the source location is lost (`Function: MainPS:` replaces
`repro.hlsl:24:1:`). Both are diagnosed errors, not internal failures. A predicate keyed to a
specific exit code, rather than to the rule text, would have been wrong under one of the two.

Container signing was measured directly, by reading the 16-byte digest at offset 4 of the
`DXBC` header of a `-Fo` output:

| configuration | digest |
| --- | --- |
| main-debug, control shader, default env | `787986802743ecdd403360764860bb71` |
| main-debug, control shader, `DXC_DXIL_DLL_PATH` set | `787986802743ecdd403360764860bb71` (identical) |
| main-debug, control shader, `-Vd` | all zeros — **unsigned** |
| v1.4.1907, control shader | `92c0940d85b841f27b958aa403b824d8` |
| v1.9.2607, control shader | `27f119687e6ad9ca88bbdc7de5072ed0` |

So on a current build signing is **not** contingent on `dxil.dll`, and `-Vd` is the only
configuration measured that leaves a container unsigned. `-Vd` was run only as an explicitly
labelled variant (`variant-vd-novalidation-main-debug.txt`); it is not in `cmd.txt`, since
nothing in the report uses it.

## Clang comparison (see `manual-case-clang.txt`)

@llvm-beanz said in 2024 that he had filed an issue to remove these instructions during DXIL
lowering in Clang, which makes `hlsl_clang_trunk` the most interesting comparison available.
Measured on Compiler Explorer:

* clang's backend rejects the repro — **but it rejects a known-good input identically**
  (`case-compute-default.hlsl`, which compiles clean locally on ground truth), and compiles
  an unrelated control cleanly. The failure is therefore unrelated to this issue, and the
  published link carries **DXC panes only**. This is SKILL.md's #1702 trap, and it took a
  control to see it;
* on a cut-down form clang *can* compile (`case-clang-minimal.hlsl`), DXC still fails with
  the same rule — locally as well as on CE — and clang emits **no `unreachable`**: the
  default edge targets the merge block and the undefined path contributes `poison` to the
  phis. So on this construct clang already behaves as described — on a restating, not on the
  issue's own shader, and "no illegal instruction" is not the same as "correct".

## Compiler Explorer

https://godbolt.org/z/nEqsn9nEW — `dxc_1_6_2112` and `dxc_trunk`, both exit 5, both showing
the validation error, with a banner (`godbolt-note.txt`) telling a reader what to look at and
two edits to try. Verified after publication by reading back
`/api/shortlinkinfo/nEqsn9nEW`: 2 panes, correct ids, correct args, 63-line source.

CE runs Linux builds with no `dxil.dll`, so the 1.6.2112 pane prints the reporter's exact
signing warning for free — the cleanest available demonstration that the warning is
incidental and that validation runs regardless.

CE cannot date anything here: its oldest DXC is 1.6.2112, newer than the local floor.

## Labels

Now: `bug`. Proposed additions, from the live descriptions rather than the names:

* **`validation`** — *"Related to validation or signing"*. Both halves apply literally: this
  is a DXIL validation failure, and the issue is titled for signing.
* **`incorrect-code`** — *"Issues relating to handling of incorrect code"*. The shader is
  incorrect (a reachable fall-off-the-end in a non-void function) and the complaint is about
  *how* DXC handles it — rejected six passes late, by the validator, instead of by Sema.

No removals: `bug` is right, and this is not a crash.

`check-in-clang` (*"See if this repros in clang as well"*) was considered and rejected — it
requests work this triage has already done, and the answer is in the draft.

## Assessment

`still-valid-keep-open`, confidence **high**.

The defect is real, reproduces on main, and has never not reproduced within measurable
history. But the maintainers' stated position (2024) is that it will not be fixed in DXC and
is being handled in Clang, and this triage neither disturbs that nor supports closing the
issue as fixed. Whether "dormant for DXC" should mean closing it is a product decision, not
one this triage should pre-empt.

What is new and actionable is the staleness: a reader spot-checking the body's B1 and B2
today gets a front-end error, not what the body describes, and could reasonably conclude the
whole report no longer applies. It does. Only its secondary claims have moved, because half
of what the thread asked for was delivered in 2020.
