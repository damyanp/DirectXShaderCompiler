> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#2427](https://github.com/microsoft/DirectXShaderCompiler/issues/2427).

The original command still fails on `main` (1.9.0.15422, eff900d5). As @pow2clk explained in
2019, the trailing backslash escapes the closing quote during argv splitting, before dxc sees
the arguments. Measured by issuing each line through `cmd.exe` verbatim:

| command | result |
| --- | --- |
| `-Fd "dbgdir\"` | `dxc failed : Required input file argument is missing.` |
| `-Fd "dbgdir"\` | works |
| `-Fd "dbgdir\\"` | works |
| `-Fd dbgdir\` | works |

The command-line behaviour is unchanged; the proposed directory-option fix has not landed:

- No `-Fdd`, `-Fad` or equivalent directory option exists in current `dxc --help` or in
  `HLSLOptions.td`.
- #2430 ("Add Fdd option") was closed unmerged in Jan 2020.
- #2660 ("Fad option for automatic debug output", `Fixes #2427`) stayed open until it was
  closed unmerged on 2026-01-22 by an inactivity sweep.

@damyanp's 2024 note that a PR was still open was accurate at the time; #2660 is now closed.
Reviving it remains a concrete next step.

The issue is currently unlabelled. Suggested labels: `enhancement`, `usability`,
`up-for-grabs`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag anything that looks wrong.</sub>
