// Control for issue 4527: the reporter's THIRD stated workaround -- "Moving the static array
// declaration to global scope fixes the error". Same array, same member function reading it,
// same entry point; the only difference from repro.hlsl's failing case is where the
// `static const` array is declared. Compiled with the repro's exact arguments
// (-T ps_6_0 -E mainPS), so it differs from the repro in that one way.
//
// Expected: no-match. If this scored a reproduction, the predicate would be firing on
// something other than the static-local-in-a-member-function construct.

struct VS_OUTPUT_SCENE {
  float4 svPosition : SV_POSITION;
  float3 WorldPos : WORLDPOS;
};

static const float3 kValues[3] = {float3(0, 0, 1), float3(0, 1, 0), float3(1, 0, 0)};

struct MyClass {
  float3 GetTestValue(uint index) {
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
