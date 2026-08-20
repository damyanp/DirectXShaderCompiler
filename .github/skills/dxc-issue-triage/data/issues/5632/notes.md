# Notes — issue #5632

## Ground truth

`main-debug` self-reports commit `7665270b9` / `dxcompiler.dll 1.9.0.5465 (triage, 7665270b9)`,
built 2026-08-19. Verified equivalent to the assigned public ground-truth commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`:

```
git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df
  | Select-String -NotMatch '^\.github/skills/dxc-issue-triage'
  -> 0 files (only committed skill-data files under .github/skills/dxc-issue-triage differ)

# control -- an older commit must show real source differences:
git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df~50
  | Select-String -NotMatch '^\.github/skills/dxc-issue-triage'
  -> 115 files
```

So no compiler source differs between the local build and the assigned public commit; the
control confirms the diff check can detect a real mismatch when one exists.

## What the issue asks (decomposed)

Title: "Can construct-cast an array type to non-array without compiler complaining (DXIL
Crash)". Reporter's original repro (`godbolt.org/z/dqa1jG41b`) has a struct member
`uint _pad[1u]`, and does `float(lineStyles[45]._pad).xxxx` — a construct-cast from a
single-element array to a scalar. Maintainer llvm-beanz (2023-08-31 comment) separated this
into two claims and supplied a second, DXIL-targeted repro (`godbolt.org/z/97GMh3zjd`):

> The SPIR-V behavior here matches FXC ... DXC crashes when generating DXIL for this code ...
> So I think the only bug here is that DXC is crashing in DXIL, and we should probably issue a
> diagnostic on array->scalar truncation.

- **Ask A (confirmed bug):** DXC crashes generating DXIL for this construct.
- **Ask B (enhancement, not itself a bug per the maintainer):** no diagnostic (warning or
  error) is issued anywhere for an array->scalar truncating construct-cast; the SPIR-V path
  silently takes element 0 and matches FXC's own (also silent) behavior.

Both share one HLSL source; only the compile target/flags differ. `repro.hlsl` is the
maintainer's DXIL-crash source verbatim (`97GMh3zjd`) — this differs from the reporter's own
`dqa1jG41b` only in a `[[vk::binding(3,0)]]` attribute needed for the SPIR-V pane, so the two
sources are otherwise identical and either serves as the DXIL repro.

## Ask A — DXIL crash

`cmd.txt` uses the reduced command `-T ps_6_0 repro.hlsl` rather than the maintainer's
`-HV 2021 -T ps_6_7 -enable-16bit-types` (preserved verbatim in `cmd-as-filed.txt`). Confirmed
by direct run that the crash needs neither `-HV 2021` nor `-enable-16bit-types` nor `ps_6_7` —
`_pad` is a plain `uint` array, so the crash is reachable at the oldest generally-available
profile, which extends the checkable history back to the v1.4.1907 bisection floor instead of
stopping at v1.7.2207 (the release that introduced `ps_6_7`).

`match.json` uses `internal_failure` (crash/assert, exit-status based) per the skill's
crash-classification guidance, since the same defect surfaces differently across build
configurations:

- **main-debug** (Debug, asserts enabled): exit `0xE0000001`, stderr
  `Internal compiler error: LLVM Assert` (see `out-main-debug.txt`). A `cdb`-driven capture
  with `sxe -c "kb 8; gh" e0000001` (`manual-case-crash-stack.txt`) shows the underlying
  assert is `llvm::StoreInst::AssertOK`, `"Ptr must be a pointer to Val type!"`, reached from
  `clang::CodeGen::CodeGenFunction::EmitHLSLVectorElementExpr` while emitting the `.xxxx`
  swizzle store — i.e. CodeGen builds a `Store` whose value type does not match the pointee
  type of the destination it computed for the array-typed member. Continuing past that assert
  with `gh` (which emulates `NDEBUG`, i.e. what a Release build does) hits a second,
  downstream assert in `llvm::Value::replaceAllUsesWith` inside `Mem2Reg`, and finally the
  release-path check that throws `hlsl::Exception(DXC_E_LLVM_CAST_ERROR, ...)` — printed as
  `llvm::cast<X>() argument of incompatible type!` — which is exactly what the release
  binaries below report.
- **Release binaries** (v1.7.2207 onward, and CE's `dxc_trunk`): exit `0x80004005` (E_FAIL)
  with stderr text `llvm::cast<X>() argument of incompatible type!` — the documented "internal
  failure the exit code alone cannot distinguish from an ordinary error" (skill: bad
  `llvm::cast` throws via the E_FAIL path). `match.json`'s text marker catches this.
- **v1.5.2010 only**: neither assert form fires; instead the release binary emits DXIL, then
  its own post-codegen module read fails with `error: Invalid record` — confirmed to persist
  under `-Vd` (`variant-v1.5.2010-vd-v1.5.2010.txt`), so this is not merely the separate DXIL
  validator disagreeing, it is a corrupt/unreadable module produced by the same defective
  CodeGen path. Confirmed *not* a release-wide defect: an unrelated trivial shader compiles
  cleanly at v1.5.2010 (`variant-v1.5.2010-control-trivial-v1.5.2010.txt`, exit 0). So
  v1.5.2010 also never correctly compiles this input — it just fails one step later than every
  neighbouring release, with a self-detected corruption error instead of a debug assert.

**Because the primary `internal_failure` predicate cannot see the v1.5.2010 shape, it scores
that one release as `no-repro` and a plain bisect reports a spurious one-release "fix".**
Composed predicate `match-broken.json` (`any_of[internal_failure, contains "Invalid record"]`)
closes that gap and is confirmed via linear scan to score `repro` at every probeable release:

```
python scripts/triage.py bisect --issue 5632 --match match-broken.json --linear
-> always-repro'd across v1.4.1907..v1.9.2607 (5 probeable prerelease(s) excluded by policy)
```

Under the primary (literal, maintainer-worded) `internal_failure` predicate alone, the plain
`bisect --linear` run reports a non-monotonic transition at v1.5.2010 -> v1.6.2104; that
transition is real for the crash's exact *shape* but not for whether the input compiles
correctly, and should not be read as "temporarily fixed". Both raw captures
(`out-v1.4.1907.txt` .. `out-v1.9.2607.txt`) and the composed-predicate captures
(`out-*--match-broken.txt`) are kept side by side.

No invalid probes were needed once the command was reduced to `ps_6_0`; the earlier attempt
at `-HV 2021 -T ps_6_7 -enable-16bit-types` correctly classified v1.4.1907..v1.6.2112 as
`invalid-probe` ("invalid profile ps_6_7"), confirmed genuine by the "error: invalid profile"
feature-absence marker (see the superseded run in git history / `bisect` output above).

**Source corroboration:** the crash path is `CodeGenFunction::EmitHLSLVectorElementExpr`
(`tools/clang/lib/CodeGen/CGExpr.cpp`), which builds an lvalue for the base of a swizzle/
construct expression and is explicitly commented as cloned from the ordinary
`ExtVectorElementExpr` handling ("Clone ExtVectorElementExpr for now / TODO: difference
between ExtVector and HlslVector") — consistent with an array-typed base never having been
accounted for in that clone.

## Ask B — missing diagnostic on array->scalar truncation

`variant-spirv-no-diag-main-debug.txt` (SPIR-V, reporter's own flags plus `-fvk-use-scalar-
layout -fspv-debug=source -fspv-debug=tool`): exit 0, empty stderr, and the emitted SPIR-V does
exactly `OpAccessChain ... %int_1 %uint_45` then a second `OpAccessChain ... %uint_0` — i.e.
`_pad[0]` — with no warning anywhere. This still reproduces on `main-debug`, matching the
report and the maintainer's "matches FXC" reading.

**Control pair, proving the diagnostic pipeline is reachable and size-checked in general:**
`control-array2-scalar.hlsl` changes only `_pad[1u]` to `_pad[2u]`. Compiling that (still DXIL,
`variant-control-array2-main-debug.txt`) produces a genuine Sema diagnostic:

```
error: too many elements in vector initialization (expected 1 element, have 2)
```

So DXC's construct-cast element-count check exists and fires for a mismatched count — a
single-element array is specifically treated as compatible with a scalar destination (an
implicit collapse) with no diagnostic, which is the precise unchecked special case the
maintainer's proposed fix ("issue a diagnostic on array->scalar truncation") would need to
cover, and which also feeds the malformed DXIL in ask A: the compatible-looking single-element
array leaves an array-typed lvalue where CodeGen expects a scalar-typed one.

No `-fcgl`/`-Vd`-style workaround was present in the original repro, so nothing was removed
from `cmd.txt`.

## History

- **Ask A:** always-repro'd, v1.4.1907 (2019-07, predates the 2023-08-31 report) through
  v1.9.2607 (2026-07, current stable) and `main-debug`, under the composed predicate. Never
  fixed. Confirmed on Compiler Explorer's `dxc_trunk` (rolling build) as well:
  `error: cast<X>() argument of incompatible type!`
  (`https://godbolt.org/z/W9Kr6fvPa`, panes archived in `manual-case-godbolt-verify.txt`).
  CE's oldest DXC (`dxc_1_6_2112`) predates `ps_6_7` and is not applicable to the as-filed
  command, but is irrelevant now that `cmd.txt` no longer needs that profile.
- **Ask B:** always-repro'd (as an open enhancement request) across the same range; no release
  was found to emit a diagnostic for this construct.

## Compiler Explorer

`https://godbolt.org/z/W9Kr6fvPa` — `dxc_1_6_2112` (invalid profile, expected — see above) and
`dxc_trunk` (crashes with the release-path `cast<X>()` text). A Clang pane was considered and
not added: this construct only manifests as a crash once CodeGen actually lowers the
`SV_TARGET`-writing pixel shader, and Clang's DXIL backend cannot lower pixel-stage output at
all (`Unsupported intrinsic llvm.dx.store.output` per the skill's documented Clang-pane
limitation), so a Clang pane would show only that unrelated backend gap rather than answering
anything about this issue. A compute-shader translation was not attempted given the narrow
scope of this single-issue triage; if produced later it should reuse `_pad` as a plain global
array member, not a `StructuredBuffer` element, to keep the construct-cast the only variable.

## Labels

Current: `bug, dxil, crash, diagnostic`. All four already match the findings precisely (a
DXIL-codegen crash, tagged `bug`+`crash`+`dxil`, plus the maintainer's own diagnostic-gap ask
tagged `diagnostic`); no proposed change.

## Draft review (step 10 — advisory only; `reviewed_by` intentionally left pending)

Per the skill, `reviewed_by` is a batch-level sign-off run once over every draft in the batch
at collation, not a per-issue step — this is a single-issue task, so `verdict.json`'s
`reviewed_by` is deliberately left blank here for that collation pass to fill in later. As an
advisory check within this session, `comment.md` was nonetheless run past `gpt-5.4` (a
different model from the one that produced the draft and these notes), briefed with
`comment.md` + `notes.md` and told concision was the primary criterion and it should propose
subtraction only, so the draft would not sit unreviewed in the meantime. It found two issues:

1. Flagged "every stable release ... through today's v1.9.2607 fails this input ... None of
   the 20 stable releases produces valid DXIL" as redundant (the count is stated twice) and
   queried whether "20 stable releases" was supported. Recounting the `bisect --linear --match
   match-broken.json` output confirms exactly 20 stable release lines were probed (v1.4.1907
   through v1.9.2607), so the reviewer's premise that the figure was unsupported was wrong —
   but the redundancy it flagged was real. Accepted the concision fix, folded the count into
   one sentence, rejected the "unsupported number" framing.
2. Flagged "closing that gap would address both halves of this issue at once, since it's the
   same unchecked case that reaches the crashing DXIL path" as more speculative/prescriptive
   than the evidence supports — it reads as recommending a specific fix rather than reporting
   what was measured. Accepted: cut the prescriptive clause, kept the underlying factual
   observation (the same unchecked single-element-array case is what reaches the crashing DXIL
   path).

Also noted for the record: it did not flag anything as psychoanalysing the reporter or
maintainer, did not propose paraphrasing any of the literal quoted diagnostic text, and its
overall assessment was that the draft was close to ready pending those two fixes.
