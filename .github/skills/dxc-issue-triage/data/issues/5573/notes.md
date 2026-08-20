# #5573 -- "External declaration [decl name] is unused" after resource assignment

## Ground truth

`main-debug`, commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (Debug, self-reports a
fork-local merge `ab5400907` which is orphaned and resolves nowhere; the build's *tree* is
identical to upstream `main` outside this skill directory, verified by
`git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD` showing only files under
`.github/skills/dxc-issue-triage/`. `dxc --version` at capture time:
`dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)`).

## Repro

Reporter's exact shader (`repro.hlsl`), compiled with `-T cs_6_6 -E CSMain` (the reporter's
`cmd.txt` did not include a profile; `cs_6_6` is required because `ResourceDescriptorHeap`
is a Shader Model 6.6 feature, and it is the minimum profile the shader needs). Repro
quality: **complete**.

```hlsl
RWByteAddressBuffer buffer : register(u0);

[numthreads(8, 8, 1)]
void CSMain(uint3 id : SV_DispatchThreadID)
{
        buffer.Store(id.x, 0);
        buffer = ResourceDescriptorHeap[0];
        buffer.Store(id.x, 0);
}
```

## What ground truth actually does: not the reported diagnostic, a Debug-only crash

`main-debug` does **not** print the reported validation error at all. It exits
`0x80000003` (assert trap) with `Internal compiler error: Terminal Error 0x80000003` and
nothing else on stdout/stderr (see `out-main-debug.txt`). A `cdb -c "g;kn 40;q"` capture
(`manual-case-cdb-raw.txt`, trimmed in `manual-case-assert-stack.txt`) shows the trap is:

```
Error: 	!(GV->user_empty())
File:
<repo>/lib/HLSL/DxilCondenseResources.cpp(1984)
```

inside `(anonymous namespace)::DxilLowerCreateHandleForLib::UpdateResourceSymbols`, called
from the `DxilLowerCreateHandleForLib` module pass. Reading the source
(`lib/HLSL/DxilCondenseResources.cpp`):

```cpp
auto UpdateResourceSymbol = [](DxilResourceBase *res) {
  if (GlobalVariable *GV = dyn_cast<GlobalVariable>(res->GetGlobalSymbol())) {
    GV->removeDeadConstantUsers();
    DXASSERT(GV->user_empty(), "else resource not lowered");
    res->SetGlobalSymbol(UndefValue::get(GV->getType()));
    if (GV->user_empty())
      GV->eraseFromParent();
  }
};
```

**This one assert is the same defect the issue reports, wearing its Debug face.** Under
`NDEBUG` (every shipped release binary), `DXASSERT` compiles out and execution falls
through: `buffer`'s global variable (`GV`) still has a real user at this point -- the first
`buffer.Store(id.x, 0)`, which runs *before* the dynamic `ResourceDescriptorHeap[0]` handle
is created/hoisted, per the maintainer's own comment on the issue -- so `GV` is **not**
erased, but the resource's DXIL-visible symbol is unconditionally replaced with `undef`
regardless. The result is a stale global left in the module that the validator's metadata
walk no longer reaches, which the validator reports exactly as quoted in the issue:
`External declaration '...' is unused.` / `Validation failed.` Under a Debug build the
`DXASSERT` traps first and the validator never runs, so ground truth observes an internal
compiler error instead of that text.

`git log --all -S UpdateResourceSymbols` traces this function (and its `DXASSERT`) to
`dc3ad5efe` (2018-02-05), almost four years before Shader Model 6.6 / dynamic resource heaps
existed and more than five years before this issue was filed. The assert is not new and was
not added to guard this specific pattern; the pattern (using a statically-bound resource,
then reassigning the variable to a dynamic heap handle, then using it again) is simply a new
way to violate an invariant ("this resource has already been fully lowered by the time this
pass runs") that the 2018 code assumed always held.

## Predicate

`match.json` is `any_of` of the reporter's exact validation-error text and
`internal_failure`, composing the two faces of one defect (see the skill's guidance on
compound predicates for a bug whose Debug and Release manifestations differ, e.g. #3873,
#5293). Matching only the regex would have scored `main-debug` (and any future Debug build)
as a clean run, erasing an assert that is really the same bug; matching only
`internal_failure` would score every historical Release-binary probe -- including the one
that produces the reporter's exact text -- as a crash rather than the reported symptom.

## Negative control

`control-no-reassign.hlsl` uses `ResourceDescriptorHeap` alongside a statically-registered
resource of the same type, but never reassigns the static variable and never uses the static
resource before the dynamic handle is created. Run with `--expect no-match`:
`variant-no-reassign-main-debug.txt` shows a clean compile (exit 0) producing well-formed
DXIL with two independent, correctly annotated handles. This isolates the defect to the
specific "use static resource -> reassign to dynamic handle -> use again" pattern, not to
`ResourceDescriptorHeap` or mixed static/dynamic resource use in general.

## History

`bisect --linear` (linear because the symptom's *form* changes between Debug and Release
builds, and to get a full population count rather than only endpoint agreement):

```
v1.4.1907      invalid-probe (error: invalid profile cs_6_6 -- cs_6_6 / ResourceDescriptorHeap did not exist yet)
v1.5.2010      invalid-probe (same: invalid profile cs_6_6)
v1.6.2104      repro  <- oldest release that can even express this repro; already reproduces verbatim
v1.6.2106      repro
v1.6.2112      repro
v1.7.2207      repro  (release current when the issue was filed, 2023-08-20)
v1.7.2212      repro
v1.7.2212.1    repro
v1.7.2308      repro
v1.8.2403      repro
v1.8.2403.1    repro
v1.8.2403.2    repro
v1.8.2405      repro
v1.8.2407      repro
v1.8.2502      repro
v1.8.2505      repro
v1.8.2505.1    repro
v1.9.2602      repro
v1.9.2602.24   repro
v1.9.2607      repro (most recent stable release)
main-debug     repro (internal-failure signature, see above)
```

`v1.4.1907` and `v1.5.2010` are hard, profile-level rejections (`error: invalid profile
cs_6_6`) unrelated to the shader's content -- `cs_6_6` itself is unrecognised, so these two
are unambiguous `invalid-probe`s, not evidence of a fix. `v1.6.2104` (2021-04-20), the oldest
release that accepts the profile, already reproduces the exact text quoted in the issue
(`out-v1.6.2104.txt`). No release between then and `v1.9.2607` (2026-07-29) shows anything
different, and `main-debug` still hits the same defect (as an internal failure). Two
prereleases in the search window that could express `cs_6_6` (`v1.5.2003`, dated before
`cs_6_6` existed and excluded on non-explicit-naming grounds anyway; and none of the others
in range are prereleases) were not probed per the release policy of excluding prereleases
unless the issue explicitly names one; the issue does not.

**Verdict: always reproduces, as far back as it is possible to check** (`cs_6_6` did not
exist before `v1.6.2104`), through the most recent stable release and on current `main`. This
has never been fixed in the ~5 years the underlying assert (and the ~4.5 years the
`ResourceDescriptorHeap` feature) have coexisted with each other.

## Compiler Explorer

`godbolt --issue 5573` (default compilers `dxc_1_6_2112`, `dxc_trunk`; both are Release
builds, so both show the diagnostic text, not the Debug crash):
https://godbolt.org/z/r6TGKo7sv

Both panes fail identically with the issue's exact quoted text
(`manual-case-godbolt-verify.txt`):

```
error: validation errors
<source>:1: error: External declaration '\01?buffer@@3URWByteAddressBuffer@@A' is unused.
Validation failed.
```

CE's oldest DXC (`dxc_1_6_2112`, Dec 2021) also prints an unrelated `DXIL.dll not found`
*warning* first; that is CE environment noise (no signing DLL available), not part of the
bug -- `godbolt-note.txt` says so explicitly so a reader does not mistake it for the symptom.

## Labels

Current: `bug`, `dxil`, `correctness`. All three already fit precisely (silent generation
of DXIL that fails the validator's own consistency check is exactly what `correctness` and
`dxil` describe). No label changes proposed.

## Maintainer comment

llvm-beanz's 2023-08-31 comment already gives the correct root-cause mechanism at a high
level ("we seem to add the dynamic handle binding to the top of the basic block so it gets
put in front of the store") and separately states a design opinion that reassigning a global
resource declaration "shouldn't be allowed" in the first place. Both are still accurate and
current; nothing in the issue's text is stale. The design question (should the front end
diagnose the reassignment at compile time instead of allowing it and mis-compiling) is a
maintainer call this triage does not make; it is worth surfacing again in the draft comment
as a live, unresolved option, without asserting an answer.

## Suggested action

`still-valid-keep-open`, confidence **high**: the reporter's exact repro, compiled with the
exact quoted command shape, reproduces on every probeable release from the oldest that can
express it through the newest, and reproduces on current `main` (as an internal failure that
is the same defect under a different build configuration, confirmed by source reading of the
guarding `DXASSERT` and its call site).
