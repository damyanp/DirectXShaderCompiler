// Control for #4549: a *different* SRV-class resource given the same wrong
// register class, in the same two-resource collision shape as repro.hlsl.
//
// StructuredBuffer is SRV-class, exactly like RaytracingAccelerationStructure,
// and DiagnoseRegisterType (tools/clang/lib/Sema/SemaHLSL.cpp) has a case for it.
// So this is the well-formed message about the same subject: DXC names the
// mistake on the declaration that made it and never mentions depth_buffer.
//
// The predicate must NOT fire here. That is what shows it discriminates between
// "diagnosed properly" and "blamed the wrong resource", rather than firing on
// any failing compile.

StructuredBuffer<float> opaque_sb : register(u0);

Texture2D<float> depth_buffer : register(t0);

float4 main(float4 pos : SV_Position) : SV_Target {
  float d = depth_buffer.Load(int3((int2)pos.xy, 0));
  return float4(d, opaque_sb[0], 0, 1);
}
