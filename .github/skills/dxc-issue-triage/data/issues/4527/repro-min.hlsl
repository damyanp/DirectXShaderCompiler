// Minimal restatement of issue 4527, for release history only.
//
// repro.hlsl is the reporter's file verbatim, and it also contains a mesh-shader entry point.
// That makes v1.4.1907 (2019-07, the oldest release with a usable dxc) unable to run it at all:
// it answers `unknown type name 'indices'` and `use of undeclared identifier
// 'SetMeshOutputCounts'`, which is a feature-absence rejection, not a result. This file keeps
// the construct under test -- a `static const` array declared inside a member function -- and
// drops everything the construct does not need, so every release back to the bisection floor
// can express it.
//
// Deliberately identical to the reporter's failing case in the part that matters: same
// `static const float3 kValues[3]` inside a member function of a struct, indexed by a
// runtime value, read from a pixel entry point.

struct VS_OUTPUT_SCENE {
  float4 svPosition : SV_POSITION;
  float3 WorldPos : WORLDPOS;
};

struct MyClass {
  float3 GetTestValue(uint index) {
    static const float3 kValues[3] = {float3(0, 0, 1), float3(0, 1, 0), float3(1, 0, 0)};
    return kValues[index];
  }
};

float4 mainPS(VS_OUTPUT_SCENE Input) : SV_TARGET
{
  uint index = (uint)Input.svPosition.x % 3;
  MyClass classInstance;
  float3 color = classInstance.GetTestValue(index);
  return float4(color, 1.0);
}
