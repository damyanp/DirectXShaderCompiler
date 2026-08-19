# Pre-probe expectation

The issue reports that compiling the supplied ray-generation library shader with SPIR-V rich
debug information crashes DXC. The symptom reproduces if DXC fails internally (assert, access
violation, or another compiler-internal failure) with the exact filed options:
`-T lib_6_4 -spirv -fspv-target-env=vulkan1.2 -enable-16bit-types -HV 2021
-fspv-debug=vulkan-with-source`.

A normal diagnostic is not the reported symptom. Successful compilation means the crash does
not reproduce. The no-RayQuery control must compile without an internal failure to show that
the option combination alone does not trip the predicate.

Repro quality: **complete**. The issue supplies the full shader, command options, and a public
Compiler Explorer link.
