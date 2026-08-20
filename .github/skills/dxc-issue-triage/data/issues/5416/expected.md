# Expected: #5416 "depfile generation isn't supported in the same invocation as compilation"

## Issue's claim

Filed 2023-07-13 against DXC version 1.7.2207 (Win 10). Reporter's exact command:

```
dxc -T lib_6_7 -O3 -MD -MF source.d -Fo source.cso source.hlsl
```

Claimed behavior: the command produces `source.d` (the depfile) but does **not** produce
`source.cso` (the compiled object requested via `-Fo`), and prints no error or warning. The
reporter calls this confusing because nothing tells them compilation was skipped.

The reporter states this is "definitely related to #4723" (which is about `-MD`/`-MF` combined
with `-P` preprocess-only mode specifically, not with an ordinary compile) — implying #5416 is
about the plain-compile case, not the `-P` case.

## Symptom that would count as "still reproduces"

Given a syntactically valid `source.hlsl` (something a normal compile would successfully
produce a `.cso` for), running the reporter's command line (or the same shape: `-MD -MF <dep
file> -Fo <output file> <valid source>`, no `-P`):

- `<dep file>` (`source.d`) is created and non-empty.
- `<output file>` (`source.cso`) is **absent** (or, if a fix instead produces it, that would
  count as fixed for this half).
- The process exits **0** (success) and stdout/stderr are empty, i.e. no diagnostic tells the
  user compilation did not happen.

"Fixed" would mean either: (a) both `-MF`'s depfile *and* `-Fo`'s object file are produced from
one invocation, or (b) dxc explicitly diagnoses/rejects the combination instead of silently
producing only the depfile. A change that merely alters wording without restoring the object
file or adding a diagnostic would not count as fixed.

## Repro quality

`agent-constructed, high-confidence`: the reporter's own command line and profile are used
verbatim; the only agent-supplied part is the body of `source.hlsl`, which is an ordinary valid
`lib_6_7` shader (the issue does not attach one). Because the reported defect is precisely
"nothing happens, no errors" for what should be an otherwise-successful compile, the shader's
exact contents should not matter as long as it compiles cleanly without the dependency flags —
that will be confirmed with a baseline control (no `-MD -MF`) before drawing any conclusion.

## Relationship to prior triage (#5117), noted but to be independently confirmed

`data/issues/5117` (already triaged, `still-valid-keep-open`) traced a mechanism in
`lib/DxcSupport/HLSLOptions.cpp` / `tools/clang/tools/dxcompiler/dxcompilerobj.cpp`: any of `-M`,
`-MD`, `-MF` sets `opts.DumpDependencies`, which makes the front end run only
`clang::PreprocessOnlyAction` and return after writing the depfile, never reaching the normal
compile/emit path that would produce an object file. If that mechanism is confirmed here too,
#5416's missing `.cso` and #5117's missing diagnostic are two visible faces of the same root
cause (the dependency-scan branch short-circuits before the ordinary output-producing path),
not the same bug narrowly restated — this will be checked against #5416's own repro rather than
assumed from #5117's notes.
