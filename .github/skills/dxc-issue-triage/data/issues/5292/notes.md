# Notes — #5292 "Rewriter: does not remove unused typedef statements and it lead to compile error"

## Ground truth

`main-debug` = `<repo>/build/Debug/bin/dxc.exe`, commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
(already registered correctly before this session started; verified rather than
rebuilt — see "Provenance" below).

```
dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)
```

### Provenance

`.cache/compilers/main-debug.json` already recorded `git_commit =
89e2f98e29c289ae8ad9e00dd310104fea9fd7df`, matching the SHA this task requires
exactly. Confirmed by direct measurement rather than trusting the registry:

- `build\Debug\bin\dxc.exe --version` was run directly and matches the
  registered version string verbatim.
- `git rev-parse HEAD` → `ced72eee...`; `git merge-base --is-ancestor
  89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD` exits 0, i.e. the recorded
  commit is a real ancestor of the checked-out tree.

No rebuild or re-registration was performed or needed — the constraint given
for this task forbids rebuilding shared targets, and the existing
registration was already correct.

## Why this can't go through `dxc.exe`, `bisect`, or a registered "compiler"

`-remove-unused-globals` / `-remove-unused-functions` are declared in
`HLSLOptions.td` with only `Flags<[RewriteOption]>` — not `CoreOption` or
`DriverOption` — so `dxc.exe`'s own argument parser rejects them
(`Unknown argument`). Only the separate `dxr` console tool, or a direct COM
caller, can reach them.

There is no Debug `dxr.exe` in this build tree (only a stale
2026-07-20 **Release**-config `dxr.exe`, from an unrelated commit, and no
shipped stable-release archive bundles `dxr.exe` either — checked
`v1.9.2607`'s asset, which ships only `dxc.exe` / `dxcompiler.dll` /
`dxil.dll` / `dxv.exe`). Building a Debug `dxr.exe` was ruled out by this
task's "no rebuilds" constraint.

`dxr.cpp`'s entire implementation is one COM call: `CLSID_DxcRewriter` →
`IDxcRewriter2::RewriteWithOptions`, into `dxcompiler.dll` — the exact DLL the
ground-truth `dxc.exe` already ships beside. `measure-rewrite.py` is a
ctypes/COM harness that makes this same call directly, against the ground
truth `dxcompiler.dll` or any cached release's `dxcompiler.dll`, without
building or registering anything. This is the skill's sanctioned alternative
for a symptom `dxc.exe` cannot reach ("issue-local `measure.py --history`"),
adapted to avoid registering a new compiler (which would write the shared
`.cache/compilers/` registry and DB row) per this task's "no shared edits"
constraint.

The `argv` shape (`["dxr.exe", "-remove-unused-functions",
"-remove-unused-globals", "-E", "ps_main", "repro.hlsl"]`, program name
included, `skipArgCount=0`) was validated empirically by running the actual
stale Release `dxr.exe` binary with the reporter's exact command line before
writing the harness — it reproduced the exact bug described, confirming the
convention independent of the ctypes plumbing.

## Repro

`repro.hlsl` is the reporter's exact source, verbatim:

```hlsl
struct VSOutput { };
struct PSOutput {};
typedef PSOutput PSPointOutput;

float4 ps_main(VSOutput psIn) { return float4(0.f, 0.f, 0.f, 1.f); }
```

run as `dxr.exe -remove-unused-functions -remove-unused-globals -E ps_main
repro.hlsl` (identical to the issue body).

## Primary result (main-debug)

`RewriteWithOptions` returns `S_OK` (`GetStatus=0`); output:

```
typedef PSOutput PSPointOutput;
float4 ps_main(VSOutput psIn) {
  return float4(0.F, 0.F, 0.F, 1.F);
}
```

`struct PSOutput {};` is gone; `typedef PSOutput PSPointOutput;` remains,
dangling. **This is exactly the reported defect**, confirmed against the
required ground-truth commit.

## Downstream recompile (closes the issue's "leads to compile error" claim)

The issue only asserts the rewritten output fails to recompile; it does not
quote the diagnostic. To check this directly, `variant-recompile.hlsl` adds
`: SV_Target` to `ps_main`'s return (needed only so the *unrewritten* source
is itself a valid, compilable pixel shader — a control, not a change to the
reported defect) and was rewritten the same way, producing
`rewritten-buggy.hlsl`:

```hlsl
typedef PSOutput PSPointOutput;
float4 ps_main(VSOutput psIn) : SV_Target {
  return float4(0.F, 0.F, 0.F, 1.F);
}
```

Compiling this rewritten text with ground-truth `dxc.exe -T ps_6_0 -E
ps_main`:

```
rewritten-buggy.hlsl:1:9: error: unknown type name 'PSOutput'
typedef PSOutput PSPointOutput;
        ^
rewritten-buggy.hlsl:2:16: error: unknown type name 'VSOutput'
float4 ps_main(VSOutput psIn) : SV_Target {
               ^
```
(exit `0x80004005`, E_FAIL — an ordinary diagnosed error, not an internal
failure; consistent with this being a silent wrong-output bug rather than a
crash).

**Control:** compiling `variant-recompile.hlsl` *unrewritten* with the same
`dxc.exe -T ps_6_0 -E ps_main` succeeds (exit 0, valid DXIL emitted) —
isolating the compile failure to the rewrite step, exactly as the issue
claims, and ruling out that the added `: SV_Target` itself was the problem.

## Controls

- **`control-no-typedef.hlsl`** — same two structs and function, but no
  typedef aliasing `PSOutput`. Result: `PSOutput` is cleanly removed and no
  dangling reference is emitted (`present=False / False`, output compiles).
  This isolates the defect to the typedef specifically — an unused struct
  with *no* other referencer is handled correctly.
- **`control-typedef-engaged.hlsl`** — `PSPointOutput` (thus `PSOutput`)
  genuinely used: a `static PSPointOutput g_dummy;` global is read inside
  `ps_main`'s body via a plain reference expression. Result:
  `present=True / True` — nothing is removed. This is the engagement
  witness: it proves the removal logic, and the harness's structural
  predicate, both correctly detect real use, so the primary repro's
  "absent" result is not an artifact of a broken reader or an
  always-negative predicate.
- **`control-typedef-used.hlsl`** (declares `PSPointOutput unused_local;` as
  a bare local-variable declaration, never read) — was intended as a second
  engagement control, but its result (`PSOutput` still removed,
  `present=False / True`) turned out to be informative rather than
  confirmatory: see "Broader scope" below.

## Source-level corroboration

`tools/clang/tools/libclang/dxcrewriteunused.cpp`:

- `CollectRewriteHelper` (~line 695–822) walks top-level `tu->decls()`: only
  `VarDecl`s go into `unusedGlobals`, only `FunctionDecl`s into
  `unusedFunctions`, and only `TagDecl`s (struct/union/enum) go into
  `unusedTypes` (line ~751: `if (TagDecl *tagDecl =
  dyn_cast<TagDecl>(tuDecl)) unusedTypes.insert(tagDecl);`). A `TypedefDecl`
  is **never inserted into any of these sets**, so it is never a candidate
  for removal in the first place — regardless of whether the type it names
  is removed. `DoRewriteUnused` (~line 957) then does
  `for (TypeDecl *unusedTy : helper.unusedTypes) tu->removeDecl(unusedTy);`,
  which removes `PSOutput`'s `TagDecl` but has no code path that could ever
  touch `PSPointOutput`'s `TypedefDecl`.
- `VarReferenceVisitor` (~line 128–222) is what marks types "used" by
  reachability from `entryFnDecl`: `VisitDeclRefExpr` (record types of
  referenced `VarDecl`s), `VisitMemberExpr`, `VisitCXXMemberCallExpr`, and
  `VisitHLSLBufferDecl`. None of these visit a function's own **parameter or
  return type** directly — only expression-level references inside the
  body.

This directly explains the observed behaviour without needing to infer
anything from output alone.

## Broader scope than reported (ancillary finding, does not change the verdict)

The reporter's quoted "here is dxr output" retains `struct VSOutput { };` —
but **no** measured capture, on any release nor on main-debug, retains it;
`VSOutput`'s declaration is dropped in every reproducing run, even though it
is `ps_main`'s (retained, live) parameter type. Two follow-up probes explain
why and rule out reader error:

1. Removing either flag alone (`-remove-unused-globals` or
   `-remove-unused-functions`) alone, without `-E ps_main` changing, still
   drops `VSOutput`; only passing **neither** removal flag keeps it. So this
   is the removal engaging, not a printer artifact.
2. `control-typedef-used.hlsl` shows the same class of gap one level down:
   merely *declaring* a local variable of the type
   (`PSPointOutput unused_local;`, never subsequently read) does **not**
   count as "used" either (`PSOutput` is still removed) — because
   `VarReferenceVisitor` has no `VisitVarDecl`/`VisitParmVarDecl` override;
   only a `DeclRefExpr` to an *already-declared* `VarDecl` triggers
   `AddRecordType`. `control-typedef-engaged.hlsl`'s working case needed an
   actual read of an existing global, not just a declaration.

Net effect: `VarReferenceVisitor`'s reachability walk never marks a
function's own **signature types** (parameter/return, or a freshly-declared
local's type) as "used" unless an expression elsewhere reads something of
that type. That is a broader instance of the same class of defect as the
one reported (unreachability analysis undercounts real uses), and it means
the rewriter here is, if anything, *more* broken than the reporter's quoted
transcript shows — dropping `VSOutput` in addition to `PSOutput` should
itself be a second `unknown type name` in the downstream recompile (and is:
see the second error line above). The most likely explanation for the
discrepancy with the reporter's pasted output is that their "here is dxr
output" snippet was hand-typed/approximated rather than an exact paste; this
does not weaken the core verdict, since the exact reported defect (dangling
`typedef`) reproduces byte-for-byte regardless.

This is recorded here as an ancillary observation, not folded into the
primary predicate (`match.json` scores exactly the reported defect), so a
future re-check of this issue is not accidentally invalidated by a change
to an unrelated code path.

## History

`measure-rewrite.py --history` (full transcript:
`manual-case-release-history.txt`) ran the identical `repro.hlsl` and argv
against every cached stable release's `dxcompiler.dll` plus main-debug:

| release | result |
| --- | --- |
| v1.4.1907 (2019-07-15) | **invalid-probe** — `RewriteWithOptions` itself returns `0x80070057` (E_INVALIDARG); this release's rewriter COM surface cannot service this call at all (predates `IDxcRewriter2`/this exact entry point) |
| v1.5.2003 (2020-03-25) | **invalid-probe** — call succeeds but `GetStatus=0x80070057`, `errors: "Unknown argument: '-remove-unused-functions'"` — this release's rewriter option table does not yet recognise the flag |
| v1.5.2010 (2020-10-22) → v1.9.2607 (2026-07-29), all 19 remaining probeable stable releases | **repro** — struct absent, typedef present, identical shape each time |
| main-debug (89e2f98e2...) | **repro** — identical shape |

Neither invalid-probe result is a "clean" measurement — the earlier one
never reached the code under test, the latter never reached parsing this
repro's flags at all — so per the skill's `invalid-probe` handling, this
issue's effective bisection floor is **v1.5.2010**, not v1.4.1907.

**Verdict: always-repro'd**, for every release capable of running this
probe, from 2020-10-22 through the required ground-truth commit today. The
issue was filed 2023-06-14, comfortably inside this always-reproducing
window — there is no fix-then-regression shape to look for here (endpoints
agree and every probeable intermediate release agrees too, so a linear scan
was unnecessary; `--history` already visited every release, which is
stronger than a binary search).

## `text_stale`

Not applicable — the issue's title and body still accurately describe
current behaviour. No maintainer comment exists (0 comments on the issue).

## What `triage.py`'s automatic machinery can and cannot re-check here

Because the symptom is reached through `IDxcRewriter2::RewriteWithOptions`
rather than a `dxc.exe` invocation, and no compiler was registered for it
(deliberately, per this task's "no shared edits" constraint), `triage.py
run`/`bisect`/`reindex` cannot drive or re-score this evidence — the same
situation documented for #2923/#2952. Re-verifying this issue means re-running
`measure-rewrite.py --history` (or `--shader <file>` for a single control),
which is deterministic and reads only the shared, already-populated
`releases` table (read-only SQL, no writes). `triage.py audit --issue 5292`
was still run as the safe, read-only per-issue completeness check.

`triage.py audit --issue 5292` originally flagged `control-no-typedef.hlsl`,
`control-typedef-engaged.hlsl`, `control-typedef-used.hlsl`,
`variant-recompile.hlsl` and `rewritten-buggy.hlsl` as having no
`triage.py run`-produced capture — `run` drives an ordinary `dxc.exe`
compile with `cmd.txt`'s arguments, and none of these five files are meant
to be compiled directly by `dxc.exe` as the interesting measurement. This
is the same category of gap already documented for #2923/#2952: the
tool's per-`.hlsl` completeness check assumes every source file is a
`dxc.exe` compile target, which is false for a rewriter-only issue. That
gap is now closed, without `dxc.exe` ever compiling a rewriter-input file
directly and without changing any measurement above:

- The four rewriter-COM inputs (`control-no-typedef.hlsl`,
  `control-typedef-engaged.hlsl`, `control-typedef-used.hlsl`, plus the
  primary `repro.hlsl` already covered via `cmd.txt`) are scored by
  `match.json`'s existing structural predicate — the same one already
  quoted above — via `measure-rewrite.py --shader <file> --label <name>
  --expect match|no-match`, a small addition to the harness that reuses
  `triage.classify`/`triage.probe_path` verbatim to file a
  `variant-<label>-main-debug.txt` capture in exactly the shape `audit`
  and `reindex` already understand, instead of inventing a parallel
  format. The three captured this way score exactly what is written above
  (`control-no-typedef` → no-repro/`no-match`, `control-typedef-engaged` →
  no-repro/`no-match`, `control-typedef-used` → repro/`match`, matching
  its "Broader scope" ancillary finding).
- `rewritten-buggy.hlsl` and `variant-recompile.hlsl` are not rewriter
  inputs but the ordinary-`dxc.exe` downstream-recompile check already
  described above, so they *are* driven by `triage.py run --shader
  --label --args "-T ps_6_0 -E ps_main <file>"` directly — but scored
  against a new issue-local `match-recompile.json` (`{"kind":
  "nonzero_exit"}`, an existing `triage.py` predicate kind, not a new
  mechanism) rather than `match.json`, because `match.json`'s
  rewrite-output regex is meaningless applied to `dxc.exe`'s own
  compiled/disassembled output. `rewritten-buggy.hlsl` scores
  repro/`match` (fails to compile, exit `0x80004005`) and
  `variant-recompile.hlsl` scores no-repro/`no-match` (clean compile),
  matching the exit codes already quoted above.

`triage.py audit --issue 5292` now reports no missing evidence (aside from
the batch-level `reviewed_by` step, which is step 10's job, not this
session's).
