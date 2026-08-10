// A library that CALLS a function it does not define. Compiles cleanly to a
// lib_6_3 container; the unresolved reference is only diagnosed at link time by
// DxilLinker (kUndefFunction, lib/HLSL/DxilLinker.cpp:401/1428), which builds
// the message from the LLVM function name with no demangling step.
float4 NotDefinedAnywhere(float4 v, uint i);

[shader("pixel")]
float4 main(float4 c : COLOR) : SV_Target {
  return NotDefinedAnywhere(c, 7);
}
