// #3362 control: does -pack-optimized produce a CONSISTENT layout across every
// stage of a tessellation pipeline, including the patch-constant signature?
//
// One file, five entry points, one shared interstage struct and one shared
// patch-constant struct -- so every stage is guaranteed to be handed the
// "identical signature" that -pack-optimized documents as its precondition.
// The patch-constant struct deliberately carries user semantics (MIDPOINT,
// CLIPPLANE) as well as the tessellation system values, so the optimized packer
// has real work to do in the patch-constant signature too.

struct PixelInput
{
	float4 pos : SV_POSITION;
	float  clip : SV_ClipDistance0;
	float4 pre : PREVIOUSPOSITION;
	float3 nor : NORMAL;
};

struct ConstantOutput
{
	float edges[3] : SV_TessFactor;
	float inside : SV_InsideTessFactor;
	float3 mid : MIDPOINT;
	float4 plane : CLIPPLANE;
};

PixelInput VSMain(float4 p : POSITION, float3 n : NORMAL)
{
	PixelInput o;
	o.pos = p;
	o.clip = p.w;
	o.pre = p;
	o.nor = n;
	return o;
}

ConstantOutput HSPatchConstant(InputPatch<PixelInput, 3> patch)
{
	ConstantOutput o;
	o.edges[0] = 1;
	o.edges[1] = 1;
	o.edges[2] = 1;
	o.inside = 1;
	o.mid = patch[0].nor;
	o.plane = patch[0].pre;
	return o;
}

[domain("tri")]
[partitioning("integer")]
[outputtopology("triangle_cw")]
[outputcontrolpoints(3)]
[patchconstantfunc("HSPatchConstant")]
PixelInput HSMain(InputPatch<PixelInput, 3> patch, uint i : SV_OutputControlPointID)
{
	return patch[i];
}

[domain("tri")]
PixelInput DSMain(ConstantOutput pc, float3 bary : SV_DomainLocation,
                  const OutputPatch<PixelInput, 3> patch)
{
	PixelInput o;
	o.pos = patch[0].pos * bary.x + patch[1].pos * bary.y + patch[2].pos * bary.z;
	o.clip = patch[0].clip * bary.x + patch[1].clip * bary.y + patch[2].clip * bary.z;
	o.pre = patch[0].pre * bary.x + patch[1].pre * bary.y + patch[2].pre * bary.z;
	o.nor = patch[0].nor * bary.x + patch[1].nor * bary.y + patch[2].nor * bary.z;
	o.pre += pc.plane;
	o.nor += pc.mid;
	return o;
}

float4 PSMain(PixelInput input) : SV_Target
{
	return input.pre + float4(input.nor, input.clip);
}
