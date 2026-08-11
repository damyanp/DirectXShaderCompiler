// Compute-shader restatement of issue 4527, for the Compiler Explorer link only.
//
// The local evidence is the reporter's own pixel/mesh shader (repro.hlsl, variant-mesh.hlsl).
// This file exists because Clang's HLSL backend cannot lower SV_Target, so a pixel pane would
// fill with errors about the stage and say nothing about the issue. The construct under test
// is not stage-specific, so restating it as a compute shader lets every pane answer the same
// question on the same source.
//
// CONTROL_NO_STATIC removes `static` from the local array and changes nothing else, so a pane
// built with -D CONTROL_NO_STATIC is the one-variable control for every pane without it.
// It is one of the reporter's own stated workarounds.

RWBuffer<float4> Out;

struct MyClass {
  float3 GetTestValue(uint index) {
#ifdef CONTROL_NO_STATIC
    const float3 kValues[3] = {float3(0, 0, 1), float3(0, 1, 0), float3(1, 0, 0)};
#else
    static const float3 kValues[3] = {float3(0, 0, 1), float3(0, 1, 0), float3(1, 0, 0)};
#endif
    return kValues[index];
  }
};

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
  MyClass classInstance;
  Out[tid.x] = float4(classInstance.GetTestValue(tid.x % 3), 1.0);
}
