# Method observation

The stable-release scan classified v1.5.2010, v1.6.2104, and v1.6.2106 as
`no-repro`, although each capture exits 1 with `unknown SPIR-V debug info
control parameter: vulkan-with-source`. Those releases did not accept the mode
under test, so they are invalid probes rather than evidence that the crash was
absent. The invalid-probe classifier recognizes unsupported SPIR-V codegen but
not an unsupported value of a recognized SPIR-V option. Collation should
consider adding a narrowly anchored marker and re-score the batch.
