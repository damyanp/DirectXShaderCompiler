// #2633 -- the EXPORT half of "link libraries": the library module that
// defines the function repro.hlsl wants to import.
//
// For linking to be possible this must compile to SPIR-V carrying
//   OpCapability Linkage
//   OpDecorate %foo LinkageAttributes "foo" Export

export float4 foo(float4 p) { return p * 0.5f; }
