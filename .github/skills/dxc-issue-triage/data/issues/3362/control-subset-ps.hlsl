// #3362 control: the reporter's actual configuration, in which the two stages
// are NOT handed an identical signature.
//
// The domain shader emits the full four-element struct; the pixel shader
// declares only the three elements the reporter's prepass PS input signature
// actually lists (SV_Position, SV_ClipDistance0, PREVIOUSPOSITION -- no NORMAL,
// see attach/pixel_pack_optimized).  Both stages are compiled with
// -pack-optimized, so this isolates the "identical signature" precondition from
// the "same flag on every stage" precondition.

struct PixelInput
{
	float4 pos : SV_POSITION;
	float  clip : SV_ClipDistance0;
	float4 pre : PREVIOUSPOSITION;
	float3 nor : NORMAL;
};

struct PixelInputSubset
{
	float4 pos : SV_POSITION;
	float  clip : SV_ClipDistance0;
	float4 pre : PREVIOUSPOSITION;
};

struct ConstantOutput
{
	float edges[3] : SV_TessFactor;
	float inside : SV_InsideTessFactor;
};

[domain("tri")]
PixelInput DSMain(ConstantOutput pc, float3 bary : SV_DomainLocation,
                  const OutputPatch<PixelInput, 3> patch)
{
	PixelInput o;
	o.pos = patch[0].pos * bary.x + patch[1].pos * bary.y + patch[2].pos * bary.z;
	o.clip = patch[0].clip * bary.x + patch[1].clip * bary.y + patch[2].clip * bary.z;
	o.pre = patch[0].pre * bary.x + patch[1].pre * bary.y + patch[2].pre * bary.z;
	o.nor = patch[0].nor * bary.x + patch[1].nor * bary.y + patch[2].nor * bary.z;
	return o;
}

float4 PSMain(PixelInputSubset input) : SV_Target
{
	return input.pre + float4(input.pos.xy, input.clip, 1);
}
