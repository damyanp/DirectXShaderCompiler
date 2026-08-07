> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3686](https://github.com/microsoft/DirectXShaderCompiler/issues/3686).

This remains true for published releases. I enumerated all 73 assets on the 26
published releases from v1.2.0-alpha through v1.9.2607:

| | Count |
| --- | ---: |
| published releases with a macOS asset | **0** |
| published releases with a Linux asset | **18** |

Linux first appeared in v1.7.2212 and is present on every published release
since. One unpublished draft had zero assets at capture time and is excluded
from those counts.

The checked-in pipeline configures `MacOS_Clang_Release` and
`MacOS_Clang_Debug` to build and test on `macOS-latest`; that job publishes
test results, not a binary artifact. The older DXIL-signing blocker cited in
the thread appears resolved at source level (`lib/DxilHash` and `dxildll` are
in-tree and not `WIN32`-gated), although nothing was built on macOS in this
triage. The later Apple code-signing/distribution concern remains a project
decision.

Suggested action: keep this as an enhancement request, or close it as
`wont-fix` if the stated no-plans position is still current. Suggested label
addition: `enhancement`.

---
<sub>Triaged with AI assistance. The counts come from the GitHub release API
and the CI claims from the checked-in pipeline configuration; please flag
anything that looks wrong.</sub>
