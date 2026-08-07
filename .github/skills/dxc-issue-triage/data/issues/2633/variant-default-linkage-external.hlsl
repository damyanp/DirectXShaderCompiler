// #2633 -- does the DXIL-era knob `-default-linkage external` make the SPIR-V
// back end export this function, without the `export` keyword?
//
// `dxc --help`: "-default-linkage <value>  Set default linkage for non-shader
// functions when compiling or linking to a library target (internal, external)".
// If it drove SPIR-V linkage too, an existing lib_6_x build could be turned
// into a relocatable SPIR-V module with no source change at all -- which would
// be the cheapest possible answer to this issue. Captured as
// variant-default-linkage-external-main-debug--match-export.txt.

float4 bar(float4 p) { return p * 0.25f; }
