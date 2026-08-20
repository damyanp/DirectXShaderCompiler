# Method notes for #5117 (not promoted; for collation review only)

- **Filename hygiene interacts with `not_contains` predicates.** The first control I wrote to
  demonstrate the defect on a pure syntax error used the dependency-output filename
  `parse-error.d` and the shader `control-parse-error.hlsl`. Both names are echoed verbatim into
  the captured text via the tool's own `$ dxc <line>` header, so `not_contains "error"` scored
  the run `no-repro` even though stdout/stderr were empty and the exit code was 0 -- the
  predicate was tripped by the *filename*, not the compiler's output. Renamed to
  `control-missing-semicolon.hlsl` / `deps-missing-semicolon.d` and it scored correctly. Worth a
  line in SKILL.md's control-naming guidance: avoid embedding a predicate's own literal tokens in
  any filename that appears on the command line being scored, the same way `godbolt-note.txt`
  must avoid embedding a missing-token literal.

- **Cross-issue relationship, left out of the draft per the per-issue brief.** `#4723` (already
  triaged in this tree, batch-017) is the same `opts.DumpDependencies` special-casing in
  `dxcompilerobj.cpp`, but triggered only in combination with `-P` and manifesting as a missing
  depfile plus a corrupted `-Fi` text output. #5117 is the plain-compile-mode case: no `-P`
  needed, and the defect is that `-M`/`-MD`/`-MF` routes through
  `clang::PreprocessOnlyAction`, which never invokes the parser or Sema at all, so any
  parse/semantic diagnostic that a plain compile would emit is silently absent and the compile
  reports success (exit 0). It is the literal mechanism behind the reporter's complaint ("I have
  to run dxc twice"). The two issues share a root file and a root flag
  (`opts.DumpDependencies`) but are not the same bug -- #4723 needs `-P`, #5117 does not, and
  #5117's defect is broader (it swallows semantic errors, not just a depfile/preprocessed-text
  contamination). Leaving the "duplicate" judgement to collation rather than asserting it here,
  per the per-issue brief.

- **CE could show the contrast, contrary to the neighbouring #3863/#4723 precedent of skipping.**
  Both #3863 and #4723 concluded CE could not display their symptom because it is a
  file-system side effect (a depfile, or the absence of one). #5117's defect, by contrast,
  shows up on stdout/stderr of a single pane: pairing a plain-compile pane against the identical
  `-MD -MF` pane on `dxc_trunk` produces a legible side-by-side (`error: ...` vs
  `<No output file>`, same source, same exit-code shape you'd expect from success). Worth noting
  in SKILL.md's godbolt section as a reminder that "the observable is a file" does not
  automatically rule out CE -- check whether the *console* pane itself already shows the
  contrast before reaching for `--skip`.
