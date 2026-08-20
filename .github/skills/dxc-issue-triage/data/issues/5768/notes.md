# Issue #5768 — Declare SV_VertexID as float only gets validation error

## Ground truth

`main-debug`, Debug build at `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (verified: registered
`git_commit` matches; `git merge-base --is-ancestor 89e2f98e2... HEAD` exits 0;
`dxc --version` -> `dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage,
7665270b9)`).

## Repro

Issue body's shader has a typo (`SV_VertextID`, extra "t"); the reporter's own linked
Compiler Explorer permalink (https://godbolt.org/z/ahe1fjsEM) uses the correct spelling
`SV_VertexID` in its `og:description` metadata, matching the title. Used the correctly
spelled version, `-T vs_6_0`:

```
float4 main(float V : SV_VertexID) : SV_Position {
   return V;
}
```

## Result on ground truth

```
error: validation errors

error: SV_VertexID must be uint.
Validation failed.
```
Exit `0x80004005` (E_FAIL) — an ordinary diagnosed failure, not an internal error. This is
exactly the reported symptom: the shader is accepted through Sema and lowered to DXIL, and
only the DXIL validator rejects it, rather than the front end reporting a compile-time type
mismatch on the semantic.

## Predicate and controls

`match.json`: `contains "error: validation errors"`. dxc always prints this literal preamble
immediately before the validator's own diagnostics (`tools/clang/tools/dxclib/dxc.cpp`); a
Sema-level error never does — it is only `file:line:col: error: <message>`.

- `control-clean.hlsl` (correct `uint V : SV_VertexID`) — compiles cleanly, exit 0, no
  diagnostic at all. `--expect no-match`: confirmed no-match.
- `control-sema-error2.hlsl` (ordinary Sema error: variable redefinition, same repro
  structure otherwise) — `file:line:col: error: redefinition of 'V'`, exit `0x80004005`, no
  "validation errors" text anywhere. `--expect no-match`: confirmed no-match. (An earlier
  attempt at this control used an undeclared-identifier error, which `triage.py`'s
  invalid-probe classifier treats as a feature-absence marker and auto-demoted; recorded in
  `method-notes.md`.)

Both controls discriminate correctly: the predicate fires only when the compiler actually
reached the validation stage.

## History

`bisect --linear` across all 20 probeable stable releases (v1.4.1907 .. v1.9.2607; 5
prereleases and 1 no-asset tag excluded by policy) — **every single one reproduces**, no
transition anywhere in the release-based history.

**But this is not "never attempted."** The issue's own cross-reference timeline
(`gh api .../issues/5768/timeline`) surfaces PR #3043 "Report error for unsupported types of
SV semantics" (merged `bece3d4fa`, 2021-02-25), whose diff adds
`tools/clang/test/.../unsupported_types_sv_vertexid.hlsl` — a test for exactly this class of
defect. It was reverted 5 days later by `5bdf3574b` ("Revert 'Report error for unsupported
types of SV semantics (#3043)' (#3532)", 2021-03-02): *"Revert system value type checking
code due to regressions. Will re-merge once it's fully verified fixed."* No re-merge has
happened since (`git log --since=2021-03-02 -- lib/HLSL/HLSignatureLower.cpp
lib/DXIL/DxilSemantic.cpp` shows no such commit through the tested commit).

Both the merge and the revert fall strictly between two stable release build dates
(`v1.5.2010`, 2020-10-22, and `v1.6.2104`, 2021-04-20 — confirmed via the release catalog),
so **no stable release ever shipped the attempted fix**; a release-only history search cannot
see it at all, which is exactly why the linear scan above shows a flat, always-repro'd line
even though a fix was written, merged, and pulled back out.

## Compiler Explorer

https://godbolt.org/z/PWdbvjGP3 — `dxc_1_6_2112` (CE's oldest) and `dxc_trunk` (rolling) both
print identical `error: validation errors` / `error: SV_VertexID must be uint.` text, exit 5.
`dxc_1_6_2112` also warns its CE image has no packaged DXIL.dll signer — a CE packaging
detail, the built-in validator still runs and produces the same diagnostic. `godbolt-note.txt`
explains what to look for. CE's DXC panes are Release builds and corroborate rather than
override the local Debug build.

## Verdict

`repros`, `complete` repro quality, `always-repro'd` across the full release-bisectable
range, `high` confidence. Suggested action: `still-valid-keep-open` — this is a real,
long-standing tech-debt gap with a documented prior fix attempt that was reverted for
regressions and never followed up.
