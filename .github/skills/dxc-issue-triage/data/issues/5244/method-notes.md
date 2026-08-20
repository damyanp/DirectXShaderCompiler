# Method notes — #5244

Confirms, in a new flavour, the "one defect can have two signatures" pattern already in
SKILL.md (`any_of`/`all_of` composition): here the two signatures are `internal_failure`
(Debug, chained LLVM asserts) and a **specific diagnosed E_FAIL text** ("generated SPIR-V is
invalid" / "unknown shader module: invalid") on every Release release binary, rather than the
timeout/internal_failure pair documented for #3873. An `internal_failure`-only predicate
produced a confident, wrong `never-repro'd-in-releases` and tripped the tool's own NDEBUG
warning — which is what caught it here. Worth a line in SKILL.md's `any_of` section
generalising the composed-signature list beyond `{internal_failure, timeout}` to "or a
release-only diagnosed-error text anchor", since this is now two independent issues
(#3873, #5244) needing a signature pair the existing prose only names one member of.
