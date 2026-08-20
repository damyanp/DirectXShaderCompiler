// -T hs_6_6 -E mainHS -Fo output.dxil debug_hs.hlsl
//
//

#define g_ACESAP1ToY				float3(0.2722287, 0.6740818, 0.0536895)
#define g_ACESRRTDesaturationFactor	0.96

// Commenting out this stops the "Internal compiler error"
// Seems to be the arithmetic?
// This isn't used in the file!
static const float3x3 g_ACESRRTDesaturationMatrix = float3x3(
	g_ACESAP1ToY.x * (1.0 - g_ACESRRTDesaturationFactor) + g_ACESRRTDesaturationFactor,	g_ACESAP1ToY.y * (1.0 - g_ACESRRTDesaturationFactor),									g_ACESAP1ToY.z * (1.0 - g_ACESRRTDesaturationFactor),
	g_ACESAP1ToY.x * (1.0 - g_ACESRRTDesaturationFactor),									g_ACESAP1ToY.y * (1.0 - g_ACESRRTDesaturationFactor) + g_ACESRRTDesaturationFactor,	g_ACESAP1ToY.z * (1.0 - g_ACESRRTDesaturationFactor),
	g_ACESAP1ToY.x * (1.0 - g_ACESRRTDesaturationFactor),									g_ACESAP1ToY.y * (1.0 - g_ACESRRTDesaturationFactor),									g_ACESAP1ToY.z * (1.0 - g_ACESRRTDesaturationFactor) + g_ACESRRTDesaturationFactor
);

// 0 is ok?
// 1 is bad - Attempted to read from address 0xFFFFFFFFFFFFFFFF
// 2 is ok?
// greater than 2 is bad - Attempted to read from address 0x0000000000000000
#define ARRAY_SIZE 2

// OR Commenting out this stops the "Internal compiler error"
// This isn't used in the file!
static Texture2D<float4> gProjTextureMaps[ARRAY_SIZE];

struct VS_OUTPUT
{
	float4 Position : SV_POSITION;
};

struct HS_OUTPUT
{
	 float3 PositionWS : POSITION_WS;
};

struct HS_OUTPUT_CONST
{
	uint VertexID : VERTEX_ID;
	float EdgeTessFactors[3] : SV_TessFactor;
	float InsideTessFactors[1] : SV_InsideTessFactor;
};

HS_OUTPUT_CONST constHS(InputPatch<VS_OUTPUT, 12> hsInputPatch, OutputPatch<HS_OUTPUT, 3> hsOutputPatch)
{
	HS_OUTPUT_CONST hsOutputConst = (HS_OUTPUT_CONST)0;
	return hsOutputConst;
}

[domain("tri")]
[partitioning("integer")]
[outputtopology("triangle_cw")]
[outputcontrolpoints(3)]
[patchconstantfunc("constHS")]
[maxtessfactor(64.0)]
HS_OUTPUT mainHS(InputPatch<VS_OUTPUT, 12> hsInputPatch, uint primitiveID : SV_PrimitiveID, uint controlPointID : SV_OutputControlPointID)
{
	HS_OUTPUT hsVertexOutput = (HS_OUTPUT)0;
	return hsVertexOutput;
}
