struct Meshlet
{
    int vertexOffset;
    int triangleOffset;
    int numVertices;
    int numTriangles;
};

struct InputVertex
{
    float4 a_Vertex;
};

struct OutputVertex
{
    float v_depth;
};

struct LightSourceParameters
{
    float4 position;
    float4 ambient;
    float4 diffuse;
    float4 specular;
};

struct ShadowMap
{
    row_major float4x4 lightMtx;
    float minZ;
    float maxZ;
    float variance;
    float smoothShadowmapTexelSize;
    float _noise;
    float fadeDistanceMin;
    float fadeDistanceMax;
    float uFrameCount;
};

static const uint3 gl_WorkGroupSize = uint3(124u, 1u, 1u);

ByteAddressBuffer _18 : register(t0, space0);
ByteAddressBuffer _58 : register(t1, space0);
ByteAddressBuffer _108 : register(t2, space0);
cbuffer Model : register(b2, space0)
{
    row_major float4x4 u_ModelMatrix : packoffset(c0);
    row_major float3x3 u_ModelMatrixIX : packoffset(c4);
    row_major float4x4 u_PrevModelMatrix : packoffset(c7);
    int u_MaxSkinInfluences : packoffset(c11);
    float u_ModelMatrixDeterminantSign : packoffset(c11.y);
};

cbuffer View : register(b1, space0)
{
    row_major float4x4 u_ViewMatrix : packoffset(c0);
    row_major float3x3 u_ViewMatrixIX : packoffset(c4);
    row_major float4x4 u_ViewMatrixInv : packoffset(c7);
    row_major float4x4 u_ProjectionMatrix : packoffset(c11);
    row_major float4x4 u_ViewProjectionMatrix : packoffset(c15);
    row_major float4x4 u_ViewProjectionMatrixInv : packoffset(c19);
    row_major float4x4 u_PrevViewProjectionMatrix : packoffset(c23);
    float4 u_Viewport : packoffset(c27);
    float u_NearClip : packoffset(c28);
    float u_FarClip : packoffset(c28.y);
    float u_MotionVectorScale : packoffset(c28.z);
    float u_Time : packoffset(c28.w);
    float3 u_ShadowBias : packoffset(c29);
    float4 u_FrustumPlanes[6] : packoffset(c30);
    float2 u_Jitter : packoffset(c36);
    float2 u_PrevJitter : packoffset(c36.z);
};

cbuffer Skin : register(b3, space0)
{
    row_major float4x4 u_MtxPalette[2] : packoffset(c0);
};

cbuffer SkinPrev : register(b4, space0)
{
    row_major float4x4 u_MtxPalettePrev[2] : packoffset(c0);
};

cbuffer Light : register(b5, space0)
{
    LightSourceParameters u_LightSource[1] : packoffset(c0);
    float4 u_GlobalAmbient : packoffset(c4);
    float4 constColor[10] : packoffset(c5);
    float4 u_FogRange : packoffset(c15);
    float3 u_FogColor : packoffset(c16);
    float u_CubemapSpecIntensity : packoffset(c16.w);
    int u_NumShadows : packoffset(c17);
    ShadowMap u_Shadows[4] : packoffset(c18);
};

cbuffer PostProc : register(b0, space0)
{
    uint u_UseAO : packoffset(c0);
    uint u_UseFog : packoffset(c0.y);
    float u_GlobalAlpha : packoffset(c0.z);
    int u_TintMode : packoffset(c0.w);
    float4 u_TintColor : packoffset(c1);
    float4 u_AOShadowColor : packoffset(c2);
    uint u_ReceiveShadow : packoffset(c3);
    float u_UseGI : packoffset(c3.y);
};

cbuffer Material : register(b6, space0)
{
    float smoothness : packoffset(c1);
    float refractiveIndex : packoffset(c1.y);
};


static uint3 gl_WorkGroupID;
static uint gl_LocalInvocationIndex;
struct SPIRV_Cross_Input
{
    uint3 gl_WorkGroupID : SV_GroupID;
    uint gl_LocalInvocationIndex : SV_GroupIndex;
};

struct gl_MeshPerVertexEXT
{
    OutputVertex outputVertices : TEXCOORD0;
    float4 gl_Position : SV_Position;
};

struct gl_MeshPerPrimitiveEXT
{
};

void mesh_main(inout uint3 gl_PrimitiveTriangleIndicesEXT[124], inout gl_MeshPerVertexEXT gl_MeshVerticesEXT[64])
{
    Meshlet _30;
    _30.vertexOffset = int(_18.Load(gl_WorkGroupID.x * 16 + 0));
    _30.triangleOffset = int(_18.Load(gl_WorkGroupID.x * 16 + 4));
    _30.numVertices = int(_18.Load(gl_WorkGroupID.x * 16 + 8));
    _30.numTriangles = int(_18.Load(gl_WorkGroupID.x * 16 + 12));
    Meshlet _31;
    _31.vertexOffset = _30.vertexOffset;
    _31.triangleOffset = _30.triangleOffset;
    _31.numVertices = _30.numVertices;
    _31.numTriangles = _30.numTriangles;
    Meshlet meshlet = _31;
    SetMeshOutputCounts(uint(meshlet.numVertices), uint(meshlet.numTriangles));
    if (gl_LocalInvocationIndex < uint(meshlet.numTriangles))
    {
        gl_PrimitiveTriangleIndicesEXT[gl_LocalInvocationIndex] = uint3((_58.Load((uint(meshlet.triangleOffset) + gl_LocalInvocationIndex) * 4 + 0) >> uint(16)) & 255u, (_58.Load((uint(meshlet.triangleOffset) + gl_LocalInvocationIndex) * 4 + 0) >> uint(8)) & 255u, _58.Load((uint(meshlet.triangleOffset) + gl_LocalInvocationIndex) * 4 + 0) & 255u);
    }
    if (gl_LocalInvocationIndex < uint(meshlet.numVertices))
    {
        float4 vertexLocal = asfloat(_108.Load4((uint(meshlet.vertexOffset) + gl_LocalInvocationIndex) * 16 + 0));
        float4 vertexWorld = float4(0.0f, 0.0f, 0.0f, 1.0f);
        float4 vertexPrev = float4(0.0f, 0.0f, 0.0f, 1.0f);
        vertexWorld = vertexLocal;
        vertexPrev = vertexWorld;
        vertexWorld = mul(vertexWorld, u_ModelMatrix);
        gl_MeshVerticesEXT[gl_LocalInvocationIndex].gl_Position = mul(vertexWorld, u_ViewProjectionMatrix);
    }
    gl_MeshVerticesEXT[gl_LocalInvocationIndex].outputVertices.v_depth = (gl_MeshVerticesEXT[gl_LocalInvocationIndex].gl_Position.z + u_ShadowBias.x) * u_ShadowBias.y;
}

[outputtopology("triangle")]
[numthreads(124, 1, 1)]
void main(SPIRV_Cross_Input stage_input, out indices uint3 gl_PrimitiveTriangleIndicesEXT[124], out vertices gl_MeshPerVertexEXT gl_MeshVerticesEXT[64])
{
    gl_WorkGroupID = stage_input.gl_WorkGroupID;
    gl_LocalInvocationIndex = stage_input.gl_LocalInvocationIndex;
    mesh_main(gl_PrimitiveTriangleIndicesEXT, gl_MeshVerticesEXT);
}
