# Method notes — #5173

Issue-local observations for possible promotion during collation. Not applied
to `SKILL.md`/`triage.py` from this session (single-issue, no shared edits).

- **A COM/libclang AST-walking API is a second, distinct "no CLI surface"
  case beyond the `IDxcOptimizer`-pass one `SKILL.md` already documents.**
  Unlike the PIX-passes case, `ParseTranslationUnit` here takes no
  command-line arguments at all to vary release-to-release, so there is no
  natural `cmd.txt` for a harness-as-compiler wrapper to hold constant, and
  registering one buys little: `bisect` would have nothing to search over
  but "which `dxcompiler.dll` path", which a small issue-local matrix
  (`measure.py` run three times) already covers at far lower cost. Chose
  *not* to register via `triage.py compiler`, and documented that choice and
  its consequence (excluded from `run`/`bisect`/`reindex`'s automatic
  re-scoring) explicitly in `notes.md`, per the reindex section's own
  guidance for exactly this situation.

- **Being outside automatic re-scoring is not the same as being outside the
  completeness check, and the fix for the latter is a header, not a
  registration.** `audit --issue N` wants a tool-made capture for every
  `.hlsl` in the directory regardless of whether the generator is
  `triage.py run` itself, and it recognises one only by the `# variant:
  <label> (<subject>)` header key on a `variant-*.txt` file — a hand-written
  script's own header vocabulary (`# generator:`, `# harness:`) does not
  satisfy it even though the capture is genuinely tool-made. Adding that one
  header key to `measure.py`'s output (plus one extra representative
  `variant-*.txt` capture for `repro.hlsl`, which had no `variant-*.txt` of
  its own since its captures are filed as `manual-case-*.txt`) closed both
  gaps `audit` reported, without re-running anything against a new
  measurement or touching `repro.hlsl`/`control-numthreads.hlsl`'s existing
  `manual-case-*.txt` conclusions.

- **`audit --issue N` also runs the path-hygiene scan** (the same
  machine-checkout-root detector `check_paths.py` implements), not only the
  artifact-completeness checks — this was not obvious from the per-issue
  workflow text alone and was discovered by running it. Useful: it caught a
  real leak (absolute repo-root paths baked into every `manual-case-*.txt`/
  `variant-*.txt` by the harness's own stdout echo) that a completeness-only
  reading of `audit` would have missed until a separate `check_paths.py`
  pass.

- **A bespoke capture generator should redact its own absolute-path
  literals at write time, not rely on a later cleanup pass.** The harness
  (`isense_probe.exe`) echoes the exact paths it was given
  (`# dxcompiler:`, `# source:`) into its stdout, which is exactly the kind
  of "path appears in output the generator writes" case the redaction
  guidance describes. Fixed by adding a small `redact()` helper to
  `measure.py` that substitutes this checkout's repo root for `<repo>`
  (mirroring `triage.py`'s own `display_exe` convention) on every string
  written into a capture, applied uniformly rather than by hand-editing the
  `.txt` files after the fact (which would be indistinguishable from
  falsifying a capture).

- **A same-tree, same-run positive control is stronger than a same-file
  negative-only absence claim.** Rather than only showing "no attribute
  cursor for a semantic", the control shader carries a genuine `Attr`
  (`[numthreads]`) *and* a semantic (`SV_DispatchThreadID`) on the same
  function, in the same parse, so the single capture demonstrates both
  "the harness/traversal does see attribute cursors when the compiler
  creates one" and "it still sees none for the semantic" without needing a
  second, unrelated shader as the presence witness.
