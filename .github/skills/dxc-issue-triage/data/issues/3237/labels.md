# #3237 -- label review (recorded, never applied)

`python scripts\triage.py labels --issue 3237` output:

    #3237 now:      bug, reflection
    #3237 proposed + -

The tool proposed no change. The notes below are my own reading of the label
**descriptions** in the repo taxonomy against the evidence gathered here.
Nothing was applied; this is a suggestion for a maintainer.

## Keep

- **`reflection`** -- "Related to Reflection data". Unambiguous; the whole
  issue is `ID3D12FunctionReflection` / `ID3D12FunctionParameterReflection`.

- **`bug`** -- "Bug, regression, crash". Defensible and I would not remove it.
  An API that returns `E_FAIL` where the D3D11 counterpart returns data is a
  reasonable thing to call a bug from a caller's seat. But see the note under
  `enhancement`: the label description bundles "regression" with "bug", and
  this is provably not a regression (see source-analysis.md §5 -- the code has
  not changed since 2018-04-11, and all 21 measured releases behave alike).
  If the project uses `bug` to mean "something that used to work, or that the
  implementation intends to do and gets wrong", it is a poor fit.

## Worth considering (with the evidence for each)

- **`api`** -- "Issues related to compiler library API". Strong fit and
  currently absent. The defect is only observable through the compiler library
  API; `dxc.exe` cannot show it at all, which is precisely why this issue was
  hard to triage. Adding `api` would make that visible to anyone scanning the
  backlog for API work.

- **`enhancement`** -- "Feature suggestion". This is the substantive question.
  The source shows the feature was never implemented, and RDAT carries no
  parameter data at all (source-analysis.md §4), so a fix is a container
  format addition rather than filling in a getter. @tex3d said as much in
  <https://github.com/microsoft/DirectXShaderCompiler/issues/657>: "The
  implementation of DXIL library reflection in this interface was limited to
  known use cases that were needed for developers using them at the time (for
  DXR)." I am not proposing `bug` be swapped for `enhancement` -- that is a
  product judgement of exactly the kind @tex3d asked for ("we would like to
  know how high a priority this is for developers"). I am recording that the
  evidence supports the "unimplemented" reading, so that whoever decides has
  it.

- **`test`** -- "Test issues or more test coverage needed". Directly supported
  by evidence rather than inference: `git grep GetFunctionParameter` finds no
  caller anywhere in the repository, tests included, and `D3D12_PARAMETER_DESC`
  appears in exactly one file (the implementation). @pow2clk wrote in #657 "I
  notice we have no testing for it. :disappointed:" and that is still true at
  `ab5400907`.

- **`up-for-grabs`** -- "Contributors welcome". Supported by the issue's own
  triage comment: "We'd consider PR's that address the issue." Only meaningful
  alongside a scoping decision, since the work is larger than it looks.

- **`shader-linking`** -- "Bugs related to library targets and linking". Fits
  the reporter's stated use case (deciding link eligibility by inspecting
  library function signatures, replacing a D3D11 function-linking-graph
  workflow). Weaker than the others -- the defect is in reflection, not in
  linking -- so I would not push for it.

## Explicitly not proposed

- **`needs repro steps`** -- the repro is complete and reproduces; see
  `out-main-debug-refl.txt`.
- **`wont-fix`**, **`external`** -- not my call, and no evidence supports them.
- **`crash`** -- nothing crashes; `E_FAIL` is returned cleanly.
- **`fxc-disagrees`** -- tempting, since the reporter's complaint is precisely
  that the D3D11 path returns data where the D3D12 path does not. But the
  label description says "differences between FXC and DXC", and I did not
  measure the FXC/D3D11 side (see notes.md, "what I did not measure"). Not
  proposed, because I would be asserting a comparison I did not make.

## Caveat

Label history is not visible in the fetched issue payload, so a label may have
been considered and deliberately removed before. Treat all of the above as
suggestions from evidence, not as a claim that anything is missing by mistake.
