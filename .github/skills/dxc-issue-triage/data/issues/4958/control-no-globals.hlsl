// Control: same shader as repro.hlsl but with BOTH unused module-scope globals
// removed (the float3x3 arithmetic initialiser and the static Texture2D<float4>
// array). Everything reachable from mainHS/constHS is otherwise byte-identical.
// Per the issue and the maintainer comment, removing either global alone already
// stops the crash; this control removes both to give the strongest "known good"
// anchor. --expect no-match: this must compile cleanly on every build.

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
