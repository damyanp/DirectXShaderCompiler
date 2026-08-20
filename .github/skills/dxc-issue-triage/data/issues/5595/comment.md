> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5595](https://github.com/microsoft/DirectXShaderCompiler/issues/5595).

Checked against `main` at `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`. This is a
test-infrastructure request, so there's no shader repro to run — the finding comes from the
repository and its history instead.

**Still open, and the text is accurate: no lit-native hash-stability mechanism exists in
`main` today.** `tools/clang/test/HLSLFileCheckLit` (the lit side) has 29 tracked files and
none carries a hash-stability check; `tools/clang/test/HLSLFileCheck` (the TAEF side, where
the 10 `CodeGenHashStability*` tests run today) has 2212. `utils/lit/lit/formats/` has no
hash-related format.

There was an attempt: PR #5600, "[lit] Add hash stability test for lit.", opened the same
day as this issue and explicitly "Fixes #5595". It added a `DxcHashTest` lit format that
compiled each shader twice (with/without `-Zi`) and compared container hashes. It got three
weeks of substantive review, including a design objection from the reviewer that was never
resolved — that the new format doesn't traverse using the normal lit shell-test flow and
doesn't respect local configs the way expected, which surfaced two real hash mismatches that
got worked around (two tests disabled) rather than fixed. The PR's last commit is from
2023-09-22; it has had no further commits since, and `gh pr view` reports it's still open
and unmerged (confirmed directly: its head commit is not an ancestor of `main`).

A related duplicate, #5552, was filed nine days earlier and closed in favor of this one.

So the ask here is unchanged and still valid, and there's a concrete, reviewed starting
point (PR #5600) that stalled on one design question rather than being abandoned outright.

Suggest: keep open (`still-valid-keep-open`); worth flagging as `up-for-grabs` given #5600's
review history already narrows down what a mergeable version needs to fix.

---
<sub>Triaged with AI assistance. This finding is based on repository/PR history rather than
a compiler run; please flag anything that looks wrong.</sub>
