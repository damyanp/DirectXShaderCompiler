# Pre-run expectation

The issue reports that the supplied compute shader crashes DXC v1.8.2502 with an
access violation only when `-fspv-debug=vulkan-with-source` is added to the
otherwise successful SPIR-V command.

The symptom reproduces if the as-filed command terminates with an internal
compiler failure (regardless of the exact crash message). A normal diagnostic or
successful compile is not the reported symptom. The same command without
`-fspv-debug=vulkan-with-source` is the negative control and is expected not to
fail internally.

Repro quality: **complete**. The issue provides the full shader, target, entry
point, optimization mode, SPIR-V environment, extension setting, and the flag
that distinguishes the crash from a successful compile.
