// #2633 -- can the inline-SPIR-V escape hatch express an IMPORT today, without
// any DXC change?
//
// LinkageAttributes is decoration 41 and takes <literal string> <LinkageType>,
// where LinkageType Import = 1 (external/SPIRV-Headers/.../spirv.hpp11:473).
// Capability Linkage is 17.
//
// DXC's two inline-decoration attributes are typed:
//   [[vk::ext_decorate(d, ...)]]         -- VariadicUnsignedArgument, ints only
//   [[vk::ext_decorate_string(d, ...)]]  -- VariadicStringArgument, strings only
// (tools/clang/include/clang/Basic/Attr.td:1453,1470)
// so neither can spell a mixed string+int operand list. This file records what
// actually happens rather than asserting that from the declarations.

struct vertexInfo {
  float4 position : POSITION;
};

struct v2p {
  float4 position : SV_POSITION;
};

[[vk::ext_capability(/* Linkage */ 17)]] [[vk::ext_decorate_string(
    /* LinkageAttributes */ 41, "foo")]] float4
foo(float4 p);

[shader("vertex")] v2p vertexShader(vertexInfo input) {
  v2p output;
  output.position = foo(input.position);
  return output;
}
