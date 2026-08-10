// Compute-shader restating of repro.hlsl, agent-constructed.
//
// Why: Compiler Explorer's clang-dxc panes cannot compile the original -- clang
// answers `error: use of undeclared identifier 'discard'`, so a Clang pane on
// repro.hlsl is noise about an unimplemented intrinsic and says nothing about this
// issue.  This file replaces `discard` with a store to an RWBuffer and the pixel
// stage with [numthreads], keeping everything the issue is about: the by-value
// struct parameter in test1, the direct indexing in test2, both [branch] hints, and
// the same field layout.
//
// SKILL step 7 requires a transformed repro to be re-checked before it is trusted.
// The check is local and captured:
//     variant-cs-test1-main-debug.txt   -T cs_6_0 -E test1  --expect match
//     variant-cs-test2-main-debug.txt   -T cs_6_0 -E test2  --expect no-match
// i.e. the asymmetry must survive the translation, scored by the same match.json.

struct SData
{
	float3 value;
	uint type;
	float4 value2;
};

StructuredBuffer<SData> dataBuffer;
RWBuffer<float> outBuf;

void fct1(SData data)
{
	[branch]if (data.type == 0)
		[branch] if(data.value.x < 0.0f)
			outBuf[0] = 1.0f;
}

[numthreads(1, 1, 1)]
void test1()
{
	fct1(dataBuffer[0]);
}

void fct2(int id)
{
	[branch] if (dataBuffer[id].type == 0)
		[branch] if (dataBuffer[id].value.x < 0.0f)
		      outBuf[0] = 1.0f;
}

[numthreads(1, 1, 1)]
void test2()
{
	fct2(0);
}
