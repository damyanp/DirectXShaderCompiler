//--------------------------------------------------------------------------------------
// test_dxc_bug.hlsl
// author: Calvin Hsu (calhsu@nvidia.com)
//--------------------------------------------------------------------------------------
#define kMaxTris 1
#define kMaxVerts 3

#define CASE_MEMBER_FUNCTION_STATIC 0
#define CASE_MEMBER_FUNCTION_CONST  1
#define CASE_GLOBAL_FUNCTION_STATIC 2

#define TEST_CASE CASE_MEMBER_FUNCTION_CONST 

#define SHADER_TYPE_MESH 0
#define SHADER_TYPE_PIXEL 1
#define TEST_SHADER_TYPE SHADER_TYPE_PIXEL

struct VS_OUTPUT_SCENE {
  float4 svPosition : SV_POSITION;  // vertex position
  float3 WorldPos : WORLDPOS;       // vertex position
};

#if TEST_CASE == CASE_MEMBER_FUNCTION_STATIC
struct MyClass {
  float3 GetTestValue(uint index) { 
    static const float3 kValues[3] = {float3(0, 0, 1), float3(0, 1, 0), float3(1, 0, 0)};
    return kValues[index];
  }
};
#elif TEST_CASE == CASE_MEMBER_FUNCTION_CONST
struct MyClass {
  float3 GetTestValue(uint index) {
    const float3 kValues[3] = {float3(0, 0, 1), float3(0, 1, 0), float3(1, 0, 0)};
    return kValues[index];
  }
};
#elif TEST_CASE == CASE_GLOBAL_FUNCTION_STATIC
float3 GetTestValue(uint index) {
  static const float3 kValues[3] = {float3(0, 0, 1), float3(0, 1, 0), float3(1, 0, 0)};
  return kValues[index];
}
#endif

[numthreads(64, 1, 1)]
[OutputTopology("triangle")]
void TestDxcBugMS(
  uint gtid : SV_GroupThreadID,
  uint gid : SV_GroupID,
  out indices uint3 tris[kMaxTris],
  out vertices VS_OUTPUT_SCENE verts[kMaxVerts])
{
  SetMeshOutputCounts(3, 1);

  if (gtid == 0) {
    tris[gtid] = uint3(0, 1, 2);
  }

  if (gtid < 3) {

    float3 position = 0;

    #if TEST_SHADER_TYPE == SHADER_TYPE_MESH
#if TEST_CASE == CASE_GLOBAL_FUNCTION_STATIC
    position = GetTestValue(gtid);
#else
    MyClass classInstance;
    position = classInstance.GetTestValue(gtid);
#endif
    #endif

    VS_OUTPUT_SCENE vout;
    vout.WorldPos = position;
    vout.svPosition = float4(vout.WorldPos, 1.0f);
    verts[gtid]  = vout;
  }
}

float4 mainPS(VS_OUTPUT_SCENE Input) : SV_TARGET 
{
  float3 color = float3(Input.WorldPos.x, Input.WorldPos.y, Input.WorldPos.z);

#if TEST_SHADER_TYPE == SHADER_TYPE_PIXEL

  uint index = (uint)Input.svPosition.x % 3;
#if TEST_CASE == CASE_GLOBAL_FUNCTION_STATIC
  color = GetTestValue(index);
#else
  MyClass classInstance;
  color = classInstance.GetTestValue(index);
#endif

#endif
  return float4(color, 1.0);
}
