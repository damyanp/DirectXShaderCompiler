# Method notes — #5105

Observations about the *method*, for collation to consider promoting. Nothing here should be
read as a verdict about this issue; see `notes.md`/`verdict.json` for that.

- **`dxa.exe` not being present in a build tree is a real, recurring constraint, not unique to
  this session.** The skill recommends `dxa -dumpreflection` for reflection questions, but this
  build tree only has `dxc.exe`, and building `dxa` would mean rebuilding/relinking a shared
  target while other batch-019 sessions may be measuring the same ground-truth build directory.
  The disassembly's `; Resource Bindings:` comment table (sourced from the same `!dx.resources`
  metadata `ID3D12ShaderReflection` reads) worked as a substitute proxy here, but it's a strictly
  weaker witness — it can't show anything `dxa` would report that isn't also surfaced as a DXIL
  metadata row (e.g. it wouldn't catch a bug that only manifested in the reflection *API* layer
  itself, as opposed to the metadata). Worth a line in the skill's reflection-question guidance:
  when `dxa.exe` isn't built and building it is out of scope, the disassembly comment table is an
  acceptable but *weaker* substitute, and the write-up should say so explicitly (this one does).

- **A feature request whose proposed fix is a *named, in-flight PR that quotes the issue number
  in its own PR body*** is a case the workflow doesn't have an explicit label for. It isn't
  `close-fixed` (nothing merged), isn't quite an ordinary `still-valid-keep-open` either (there's
  concrete, attributable progress, not silence) — I used `still-valid-keep-open` with a summary
  that names both PRs and their unmerged state, since that seemed like the most honest fit among
  the existing `suggested_action` vocabulary, but a future batch might want to consider whether
  "has an open PR" deserves its own tier in `render_overview.py` so it doesn't get buried among
  issues nobody has touched. Not proposing this now since it's a change to shared
  `render_overview.py`/`TIERS`, which is out of scope for a per-issue session.

- **`--O0` as a named workaround the reporter asked about, but not a registered compiler flag
  that fits `run --shader`'s "vary only the source" model** — I ran it once by hand rather than
  through `triage.py run`, since it changes `cmd.txt`'s argument list rather than the source file
  and `run --args` would have replaced the whole command including the input filename (and per
  the skill, doing that without `--label` risks clobbering the primary capture). This is a small
  procedural gap worth naming: there's no first-class way to add a single extra flag to the
  ground-truth command as a *labelled variant* without hand-writing the full `--args` string
  including the source filename. Not a bug, just friction that a future `run --shader X --label Y
  --extra-args "..."` could remove.
