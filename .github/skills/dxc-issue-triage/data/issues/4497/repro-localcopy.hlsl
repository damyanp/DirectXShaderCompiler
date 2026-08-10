// Variant of repro.hlsl, agent-constructed, used as a scoping probe only.
//
// The issue contrasts a by-value STRUCT FUNCTION PARAMETER (fct1) against direct
// indexing (fct2).  This file removes the function call entirely and keeps only the
// local struct copy, to establish whether the unconditional load is a property of
// argument copy-in specifically or of any whole-struct copy out of the buffer.
//
// The entry point is deliberately named test1 so that `triage.py run --shader` can
// reuse cmd.txt's exact arguments and differ from the repro in exactly one way.

struct SData
{
	float3 value;
	uint type;
	float4 value2;
};

StructuredBuffer<SData> dataBuffer;

void test1()
{
	SData data = dataBuffer[0];
	[branch]if (data.type == 0)
		[branch] if(data.value.x < 0.0f)
			discard;
}
