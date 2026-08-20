# Method observations from triaging #5080

## A release can reject an unrecognised *value* of `-fspv-target-env`, and the classifier
## does not yet catch it

`cmd.txt` uses `-fspv-target-env=vulkan1.3`. The automatic `bisect --linear` run scored
v1.6.2112 `no-repro`, but its capture (`out-v1.6.2112.txt`) shows the run never reached the
code under test:

```
error: unknown SPIR-V target environment 'vulkan1.3'
note: allowed options are:
 vulkan1.0
 vulkan1.1
 vulkan1.2
 universal1.5
```

This is the same class of trap `SKILL.md` already documents for `#7300`
("A release can also reject an unknown *value* of an option it does recognise") but for a
different flag (`-fspv-target-env` rather than `-fspv-debug`) and a different marker text
(`unknown SPIR-V target environment` rather than `unknown SPIR-V debug info control
parameter`). `triage.UNSUPPORTED_MARKER_RE` does not currently include this marker, so
`bisect` reported a false clean endpoint and, without manual follow-up, would have
understated the history as "regressed-in v1.7.2207" (a real regression window) rather than
"reproduces from the first release able to express `-fspv-debug=vulkan-with-source` at
all" (v1.6.2112 onward).

Confirmed by hand (`measure-target-env-v1.6.2112.py`,
`manual-case-target-env-v1.6.2112.txt`): the same v1.6.2112 binary, given the otherwise
identical command with `-fspv-target-env=vulkan1.0` (the oldest value it accepts), crashes
with the same access violation every later "repro" release shows. So v1.6.2112 was never
clean; the `no-repro` verdict the tool produced for it was an artifact of the option value,
not of the defect. This was corrected by hand rather than by editing the shared classifier,
per the per-issue-worker boundary; collation should consider adding
`unknown SPIR-V target environment '` to the marker set the same way the `vulkan-with-source`
case was added after `#7300`.

## Building an ~18-month-old commit with today's toolchain hits two independent,
## defect-unrelated incompatibilities

Attempting to build the candidate fix commit (`1e59ce9185...`) and its parent
(`690ec7cd7d...`) from detached worktrees, to directly test the fix per the skill's "if the
exact commit matters, build it" guidance, failed twice before being abandoned:

1. The machine's only available CMake (4.3.1) refuses `cmake_policy(SET CMP0051 OLD)`,
   which both historical commits' root `CMakeLists.txt` still call but which `main` has
   since removed entirely -- i.e. `main` already made the same forward-compatibility change
   this verification needed, independently.
2. After patching that (identically in both worktrees), the build fails under `/WX` on
   `warning C5285: cannot declare a specialization for 'std::is_nothrow_constructible'... 
   forbidden by N5014 [meta.rqmts]/4` from `include/llvm/ADT/StringRef.h`, against the
   installed MSVC 14.51 standard library -- again a toolchain-drift issue unrelated to the
   defect, and one that recurs across enough translation units that a safe, narrow,
   identically-applied fix was not readily available within this triage's scope.

Full details and the reasoning for abandoning the attempt (rather than force a broader
source patch into the comparison) are in `manual-case-fix-commit-attempt.txt`. The verdict
falls back to "strong, not certain" attribution from the source diff (which removes the
precise assert the issue quotes) plus the two-release stable bisection window
(v1.8.2403.2 crashes, v1.8.2405 clean). Collation/future batches attempting a build-verified
fix attribution against a commit from before this CMake/MSVC generation should expect the
same two obstacles and may want a pinned older CMake/toolchain image if this pattern
recurs often enough to be worth the setup cost.
