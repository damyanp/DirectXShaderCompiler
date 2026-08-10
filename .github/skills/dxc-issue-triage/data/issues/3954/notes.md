# Issue 3954 — triage notes

**Verdict: `does-not-repro`.** The reported crash is fixed. It reproduced on every stable
release from the bisection floor v1.4.1907 (2019-07-15) through v1.8.2407, and is clean from
v1.8.2502 (2025-02-20) onward and on ground-truth `main`.

Ground truth: `main-debug`, a clean Debug build of upstream `main` at `13730886e`, self-reporting
`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`. The embedded
SHA is fork-local; the public commit is `13730886e`. Provenance checked by tree, with a control:
`git diff --name-only 13730886e HEAD` filtered of `dxc-issue-triage` paths is empty, while the
same query against `HEAD~30` lists `docs/DXIL.rst`, `include/dxc/DXIL/DxilConstants.h` and others
— so the query can detect a difference and did not.

## What was tested

`repro.hlsl` is the issue body's shader verbatim, 29 lines, unmodified — comments included,
because the diagnostic quotes source line numbers.

`cmd.txt` is `-T lib_6_3 repro.hlsl`. **The profile is deliberately the oldest that can express
`[shader("anyhit")]`, not the newest.** Probed on ground truth: `lib_6_1` and `lib_6_2` are
refused outright ("Must disable validation for unsupported lib_6_1 or lib_6_2 targets"),
`lib_6_3` is the floor, and `lib_6_9` refuses this shader for an unrelated forward-in-time
reason (`[raypayload]` attribute now required). Targeting `lib_6_6` or later would have made
every pre-2018 release an invalid probe and could have masked the real floor.

Repro quality: **complete**. The issue body contains a self-contained shader, names the profile
family, quotes the failing output, states a workaround, and needs no reconstruction.

## Predicate

`match.json` is `internal_failure` — `triage.py`'s build-agnostic crash predicate. It was never
a match against this crash's message text, and that decision turns out to be the whole
verdict. **One defect wears four wordings and two silences across the release history:**

| releases | exit | stderr |
| --- | --- | --- |
| v1.4.1907, v1.5.2010 | `0xC0000005` (access violation) | **completely empty** |
| v1.6.2104 | `0xE0000002` | `Internal compiler error: LLVM Unreachable` |
| v1.6.2106, v1.6.2112 | `0x80AA001C` (`DXC_E_LLVM_UNREACHABLE`) | `Internal Compiler error: Unexpected matrix subscript use.` + `...HLMatrixSubscriptUseReplacer.cpp:91!` |
| v1.7.2207 … v1.8.2407 (9 releases) | `0x80004005` (E_FAIL) | `error: Unexpected matrix subscript use.` |

`manual-case-predicate-counterfactual.txt` re-scores the committed captures under four
predicates and prints the history each would have reported:

| predicate | history it reports | scored repro |
| --- | --- | --- |
| `internal_failure` (used) | repro → clean at **v1.8.2502** | 14/20 |
| exit status only, no text markers | clean at v1.7.2207 — **4.5 years early** | 5/20 |
| the reporter's full quoted line | repro only v1.6.2106…v1.6.2112 — **a window that does not exist** | 2/20 |
| `contains "Unexpected matrix subscript use."` | repro starts v1.6.2106 — **wrong start by two years** | 11/20 |

Both halves of `is_internal_failure()` are load-bearing. E_FAIL is deliberately excluded from
`INTERNAL_STATUS` (`triage.py:309`) because ordinary syntax errors use it, so the nine
v1.7.2207–v1.8.2407 probes are classified **only** by the build-agnostic `UNREACHABLE executed`
marker in `INTERNAL_MARKERS` (`triage.py:245–253`). Drop either half and the answer changes.

One note for anyone re-reading the raw scan: `llvm_unreachable` is **not** compiled out in DXC
release builds. `include/llvm/Support/ErrorHandling.h:101` is `#if 1 // HLSL Change - always
throw exception with message for unreachable`, and `lib/Support/ErrorHandling.cpp:139` throws
`hlsl::Exception(DXC_E_LLVM_UNREACHABLE, ...)`. So this is not an assert-only artifact; shipping
binaries hit it, they just report it through four different channels depending on vintage.

## Scan

`bisect --issue 3954 --linear`, 20 stable releases probed, one transition:

- **repro:** v1.4.1907, v1.5.2010, v1.6.2104, v1.6.2106, v1.6.2112, v1.7.2207, v1.7.2212,
  v1.7.2212.1, v1.7.2308, v1.8.2403, v1.8.2403.1, v1.8.2403.2, v1.8.2405, v1.8.2407 (14)
- **clean:** v1.8.2502, v1.8.2505, v1.8.2505.1, v1.9.2602, v1.9.2602.24, v1.9.2607 (6)

**No invalid probes.** No release rejected the input for a profile or feature reason, and the
oldest reproducing release is the oldest release probed — meaning the defect predates the
bisection floor and no "introduced in" claim is available from this scan. `v1.2.0-alpha` was
skipped (no `dxc` asset) and five prereleases were excluded by policy.

The `--linear` result line reads `non-monotonic history (5 probeable prerelease(s) excluded
from the search by policy), transitions at v1.8.2502 -> no-repro`. There is exactly one
transition; the phrase appears to be the generic mode header, not a finding. Recorded in
`method-notes.md`.

## Controls

Run through `triage.py run` against release binaries registered as compiler ids
(`rel-<tag>-3954`), so every control has a tool-written header and is re-scorable. **Controls
were run on four to five representative builds, not on all twenty** — `main-debug`, v1.4.1907
(oldest reproducing), v1.6.2106 (the reporter's own vintage), v1.8.2407 (last reproducing) and
v1.8.2502 (first clean), chosen to span each of the four failure faces.

| control | shader | result |
| --- | --- | --- |
| workaround | `Param.Matrix[2].xxx` — the reporter's stated fix | clean on all builds tested, including the three that crash on the repro |
| feature presence | minimal `lib_6_3` `[shader("anyhit")]` | clean on all builds tested |
| compute stage | the identical subscript in `cs_6_0` | crashes on v1.4.1907, v1.6.2106, v1.8.2407; clean on `main` |
| no-duplicate swizzle | `Param.Matrix[2].r.x` | clean on v1.8.2407 |
| duplicate swizzle | `Param.Matrix[2].r.xx` | crashes on v1.8.2407 |

The feature-presence control is what rules out the most dangerous misreading of this scan.
v1.4.1907 and v1.5.2010 crash with **empty stderr**; without a control it would be reasonable to
suspect those old binaries simply lack raytracing support and are dying for an unrelated reason.
They compile a `lib_6_3` anyhit shader cleanly. The `0xC0000005` is specific to the subscript.

## Mechanism

`HLMatrixSubscriptUseReplacer::replaceUses` (`lib/HLSL/HLMatrixSubscriptUseReplacer.cpp`)
recurses through GEPs on the matrix-subscript pointer and handles exactly two terminal cases,
`LoadInst` and `StoreInst`; anything else falls through to the `llvm_unreachable`. It sits at
lines 93 and 106 today; it was line 91 in 2021, which is what the reporter quoted.

The `-fcgl` captures show what the unexpected use was. On v1.8.2407
(`variant-fcgl-rel-1.8.2407-3954.txt:71`), `Param.Matrix[2].r.xxx` leaves the `.r` as an
**lvalue**, so codegen emits a scalar GEP into the subscript result followed by

```llvm
%6 = bitcast float* %5 to <1 x float>*
```

a `BitCastInst` use of the subscript pointer — neither a load nor a store, so the pass gives up.
On v1.8.2502 (`variant-fcgl-rel-1.8.2502-3954.txt:70-72`) the same source loads the whole
`<3 x float>` and `extractelement`s from it, with no bitcast: an lvalue→rvalue conversion has
happened in the front end, so the lowering pass never sees a shape it cannot handle. **The fix
is in Clang codegen/Sema, not in the lowering pass** — the `llvm_unreachable` is still there,
still reachable in principle, and simply no longer reached by this construct.

`AllowLoweredPtrGEPs = isa<GlobalVariable>(RootPtr)` (`lib/HLSL/HLMatrixLowerPass.cpp:1694`)
explains the shape of the bug: the pointer path is only taken for matrices rooted in a local,
which is why the reporter's local `Parameters Param` triggers it.

**This is not raytracing-specific.** The identical subscript in a `cs_6_0` shader crashes
identically on all three reproducing releases tested. The reporter hedged the observation
("seems to only happen with Ray Tracing shaders") and it was an aside about their own generated
code; it is recorded here as a measurement, not a correction.

## Fix attribution — strong, not proven

`0372fb792`, "Fix assertion on splat of groupshared scalar (#6930)" (Antonio Maiorano,
2024-09-24; PR merged 2024-09-25). It modifies `HLSLExternalSource::LookupVectorMemberExprForHLSL`
in `tools/clang/lib/Sema/SemaHLSL.cpp` to insert a `CK_LValueToRValue` cast when
`positions.ContainsDuplicateElements()` forces `VK_RValue` on an lvalue base — precisely the
missing conversion the IR diff shows.

Ancestry verified: `git merge-base --is-ancestor 0372fb792 v1.8.2502` → 0 (present);
against `v1.8.2407` → 1 (absent). So it is inside the window.

Behaviourally confirmed on v1.8.2407, and **predicted in `expected.md` before running**: the
discriminator the fix keys on is duplicate swizzle elements. `.r.x` (no duplicate) compiles
clean on the last broken release; `.r.xx` (duplicate) crashes. The repro's `.xxx` has
duplicates.

The honest limit: the window between the two tags is **133 commits, of which 4 touch
`SemaHLSL.cpp`**, and nothing was built at `0372fb792` to bisect within it. The mechanism, the
ancestry and the duplicate-element behaviour all point at this commit, but the claim is an
attribution, not a measurement. It should be stated that way anywhere it is repeated.

Note that PR #6930 closes no issue and was filed for an unrelated symptom, which is a plausible
reason nothing ever linked back here.

## The fix produces correct code, not merely silence

A crash that stops crashing can still be a crash that started miscompiling. `check-identity.py`
compiles `repro.hlsl` and the reporter's own workaround `control-workaround.hlsl` — which
expresses the same computation in a form that always worked — and compares the resulting DXIL.

On both `main-debug` and v1.8.2502 the two are **byte-identical** (main-debug sha256
`a85bf2b4…`, shader hash `1e7f621867e0ef7b77e831182f17e506`). On the three reproducing releases
the script reports `NOT COMPARABLE`, because the repro produces no output at all. The DXIL was
also read by hand: one `cbufferLoadLegacy`, `extractvalue ..., 2` selecting the column-major
`M[2][0]` element, and three `fmul`s — the correct semantics for `Color * Param.Matrix[2].r.xxx`.

## Reporter-instance fidelity

`check-quote.py` extracts the quoted failure block from `issue.json`, normalises only the source
tree root, and compares it against all 20 captures. It matches **exactly two**: v1.6.2106 and
v1.6.2112 — including the source line number 91. v1.6.2104 and every v1.7+ release correctly
show as "differs", which is the script's own self-test that it is not matching loosely. The
reporter filed in September 2021, between those two releases. Their build is identified.

## Compiler Explorer

<https://godbolt.org/z/PT7Yqj1r6> — two panes, both `-T lib_6_3`: `dxc_1_6_2112` (the reporter's
vintage) and `dxc_trunk`. Read back via `GET /api/shortlinkinfo/PT7Yqj1r6` and captured in
`manual-case-godbolt-verify.txt`.

**Read the link with one caveat.** CE runs Linux Release builds, and the `dxc_1_6_2112` pane
reports only `Program terminated with signal: SIGSEGV` and `<Compilation failed>` — no message
text at all, unlike the Windows binary of the same version which prints the reporter's exact
lines. The link demonstrates *that* the old compiler dies and the new one does not; the Windows
captures in this directory are what carry the message evidence. The banner was rewritten once to
say so accurately, and again to strip a searchable token that DXC was compiling into the clean
pane's `!dx.source.contents`.

## Labels

Current: `bug`, `crash`. Proposed addition: `matrix-bug` — the defect is in matrix subscript
lowering and the issue is not currently findable under that label. This only matters if the
issue stays open; on a close it is cosmetic.

## Suggested action

`close-fixed`. The reported crash does not reproduce on `main`, the fix is bounded to a single
release transition, the emitted code is verified correct rather than merely non-crashing, and
the reporter's specific build is identified. The scan cannot say when the defect was
*introduced* — it predates the oldest available release — but that question is moot for a close.

Required for a `close-fixed` verdict, a blind re-derivation was run: a separate agent was given
the issue directory with `notes.md`, `verdict.json` and `comment.md` withheld, and independently
reached the same status, the same v1.8.2407 → v1.8.2502 boundary, the same "no invalid probes",
the same repro quality and the same suggested action. It also found two real defects in the
draft evidence — a `match.json` note that misdescribed how the predicate scored the E_FAIL
releases, and a claim in `expected.md` about v1.8.2502's IR with no committed capture behind it.
Both are fixed above; both are recorded in `method-notes.md`.
