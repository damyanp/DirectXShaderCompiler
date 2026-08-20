# Expected symptom — #5804 "Fix UBSAN alignment failures"

This is a tech-debt request, not a shader-compile bug report. There is no HLSL repro and none
is implied by the issue text — the reporter (amaiorano) states the subject directly:

- PR #5803 ("Disable UBSAN sanitizing alignment errors") disabled UBSAN's *alignment*
  sub-sanitizer for the whole build, because the reads/writes done through
  `DxilPipelineStateValidation::CheckedReaderWriter` (see
  `include/dxc/DxilContainer/DxilPipelineStateValidation.h`) legitimately do unaligned memory
  access, which UBSAN's alignment check flags as undefined behaviour.
- The reporter attempted a short-term fix (linked from their own fork,
  `amaiorano:fix-ubsan-unaligned-access`, not part of this repo) but judged the resulting code
  "too gnarly and difficult to read" and did not upstream it.
- The ask is to eventually re-enable the alignment sanitizer, ideally by back-porting a proper
  fix `@llvm-beanz` is said to have implemented in upstream Clang.

**This is not compiler-verifiable through a `dxc` compile.** The instrument that can answer
"is this still the case" is the build configuration itself, not shader output. Per the skill's
guidance for build/config issues (`#3276`'s CMake-tree pattern), the producing artifact here is
`cmake/modules/HandleLLVMOptions.cmake`, which is where PR #5803 (and its follow-up #6431,
"Disable ubsan alignment errors properly") added `alignment` to the sanitizer blacklist for
both the `Undefined` and `Address;Undefined` `LLVM_USE_SANITIZER` configurations.

**Reproduces** = at the ground-truth commit, `HandleLLVMOptions.cmake` still lists `alignment`
in `-fno-sanitize=vptr,function,alignment` for both UBSAN configurations, i.e. the suppression
from #5803/#6431 is still present and the underlying `CheckedReaderWriter` alignment problem
has not been fixed.

**Does-not-reproduce** = `alignment` has been removed from that exclusion list (or the whole
`-fno-sanitize=...` clause has been dropped) *and* `CheckedReaderWriter`/`ReadOrWrite` no
longer perform unaligned accesses that would trip the sanitizer if re-enabled. Removing the
exclusion alone without a real fix would just reintroduce the disabled runtime failures —
not something this repro-less issue can distinguish, so text-only confirmation that the
exclusion is gone is the practical bar, not a live sanitizer run.

Repro quality: **prose-only** — issue has no code sample of its own; the reporter's proposed
fix lives in a personal fork and is out of scope to build/run here.
