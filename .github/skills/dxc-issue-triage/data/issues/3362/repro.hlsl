// #3362 -- domain shader signature packing under -pack-optimized.
//
// Reconstruction of the configuration in the issue: the interstage struct is
// declared once and used by both the domain shader and the pixel shader that
// consumes it, exactly as the reporter describes ("it's in a shared header, so
// it should be the same in all stages").  Both entry points live in one file so
// the two invocations in cmd.txt are guaranteed to see the identical
// declaration.
//
// The patch-constant input and the tri domain reproduce the attached
// disassembly's patch-constant signature (SV_TessFactor 0..2 + SV_InsideTessFactor)
// and InputControlPointCount=3.

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

float4 PSMain(PixelInput input) : SV_Target
{
	return input.pre + float4(input.nor, input.clip);
}
