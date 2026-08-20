# Method notes from #4805

Three observations about the *method*, not the issue.

## 1. A custom `IDxcIncludeHandler`'s parse-time candidate is resolved, not the raw `#include` spelling

Assumed, before running anything, that `LoadSource` would be called with the
bare quoted spelling from the `#include` directive (`Includes/Uniforms.hlsl`).
It is not: the front end calls `LoadSource` with a candidate **already
resolved relative to the including file's own directory**
(e.g. `.\repro-dir\Includes\Uniforms.hlsl`). An exact-string matcher in the
first harness build failed on this and produced a plain "file not found"
compile error that looked, at first glance, like the custom handler wasn't
being consulted at all — which would have been the wrong conclusion for the
wrong reason.

**Generalisation:** for any issue about a custom `IDxcIncludeHandler`, log
every `LoadSource` candidate string verbatim before writing the matching
logic, and match on a normalised suffix rather than an exact string. The
resolved-vs-raw distinction is itself useful evidence: it is what let this
triage separate "the front end's include resolution is fine" from "the
*separate* debug-source re-read ignores the handler entirely" — two very
different claims that a less careful harness would have conflated.

## 2. A byte-search instrument needs its OWN positive control per container format, not just per issue

The marker byte-search worked cleanly for SPIR-V (`OpString`/`DebugSource`
literals are packed as contiguous ASCII words — confirmed via `dxc.exe -Fc`
before trusting it). When the same technique was pointed at DXIL's
`-Zi -Qembed_debug` path (to check a maintainer's "not SPIR-V specific"
comment), the identical-content positive control **failed** — the marker did
not appear even when the on-disk file was byte-for-byte identical to what the
handler served, meaning DXIL's embedded debug source is not stored as a
contiguous ASCII run (likely compressed/PDB-shaped) and the byte-search cannot
see it either way.

**Generalisation:** an instrument's positive control validates the
instrument for the *specific container format under test*, not for the issue
in general. Reusing an instrument that was validated on one container format
(SPIR-V) against a structurally different one (DXIL) without re-running the
control is exactly the trap SKILL.md warns about ("a control cannot catch a
broken reader") — it did catch it here, and the DXIL angle was correctly
left unmeasured rather than asserted from a silently-broken control.

## 3. A predicate whose absence is the finding needs a control that would make the SAME code path visibly succeed

The primary predicate here (`match.json`) looks for a marker being **absent**
from a successful compile. An absence-as-signal predicate is fragile in a way
a presence-as-signal predicate is not: it is satisfied by both "the defect is
real" and "the harness/byte-search is broken and would report absence no
matter what." `control-identical` (a real on-disk file byte-identical to the
handler's served content) is what closes that gap — it forces the SAME code
path (the raw disk re-read) to produce a hit through an entirely different,
coincidental route (finding a real file with matching bytes), which only
works if the marker text, the compile, and the byte-search are all actually
functioning. Without it, "marker absent in `repro.hlsl`" and "the byte-search
never finds anything" would be indistinguishable.

**Generalisation:** for any `not_contains`/absence-shaped predicate, prefer a
control that produces a *presence* through a structurally different route
than the one under test, not merely a control that is "expected not to
trigger the bug." SKILL.md's existing "a control cannot catch a broken
reader" guidance already says this; this issue is a concrete instance where
the distinction mattered (an unrelated-looking "control" that also happened
to show absence would have proven nothing).

## Minor friction, recorded so the next person does not rediscover it

* Downloading release archives for a fixed-harness history matrix must land
  under the issue's own `data/issues/<n>/` directory (gitignored `scratch/`),
  **not** the skill's shared `.cache/` — that directory is genuinely shared
  across concurrent sessions/issues and is off-limits under a strict
  per-issue write boundary, even though SKILL.md's own examples default
  release caching to `.cache`. Caught this only after already downloading two
  release zips into `.cache/releases-4805/`; deleted and re-downloaded into
  the permitted directory before using them for anything.
* `triage.py compiler --commit <sha>` warns when a harness's own `--version`
  banner doesn't contain the given commit — expected and harmless for
  harness-as-compiler registrations (the harness prints its own banner, not
  DXC's), same as noted for #4619's `refl4619`.
* VS toolset location on this machine is
  `Program Files\Microsoft Visual Studio\18\Enterprise`, not the `2022\...`
  path `build-refl4619.cmd`'s precedent checks first; both are probed by the
  build script's `:try` fallback chain, so this was not a blocker, just worth
  recording for the next person who assumes the `2022` path exists here.
