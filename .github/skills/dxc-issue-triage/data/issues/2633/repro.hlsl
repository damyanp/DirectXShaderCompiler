// #2633 -- the IMPORT half of "link libraries".
//
// This is @s-perron's own case from his 2024-07-26 comment
// (https://godbolt.org/z/4s8xaEdTK), retargeted from lib_6_6 to lib_6_3, the
// profile #2633 actually asks about. His words: "We could add the 'import'
// decoration to undefined function. In [that link], `foo` would be an import
// function instead of issuing an error."
//
// `foo` is declared here and defined in lib-export.hlsl. For linking to be
// possible, this module must compile to SPIR-V carrying
//   OpCapability Linkage
//   OpDecorate %foo LinkageAttributes "foo" Import
// so that spirv-link can resolve it against lib-export.hlsl's module.

struct vertexInfo {
  float4 position : POSITION;
};

struct v2p {
  float4 position : SV_POSITION;
};

float4 foo(float4 p);

[shader("vertex")] v2p vertexShader(vertexInfo input) {
  v2p output;
  output.position = foo(input.position);
  return output;
}
