// Issue 3811 -- compute restatement of repro.hlsl, for a Compiler Explorer session that all
// three compilers (dxc, dxc trunk, clang) can answer on the SAME source. Clang's DXIL backend
// cannot lower vertex signature I/O, so the vs_6_0 original would fill a Clang pane with noise
// about the stage rather than about this issue.
// The local, stage-accurate evidence is repro.hlsl at vs_6_0, exactly as filed.
StructuredBuffer<float> values : register(t0, space0);
RWStructuredBuffer<float> result_out : register(u0);

void Accumulate(int count, out float result)
{
	// result += values[0];  // <-- straight-line spelling: rejected by DXIL validation
	for (int i = 0; i < count; i++)
		result += values[i];  // <-- loop spelling: accepted
}

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
	float result = 0.0;
	Accumulate((int)tid.x, result);
	result_out[0] = result;
}
