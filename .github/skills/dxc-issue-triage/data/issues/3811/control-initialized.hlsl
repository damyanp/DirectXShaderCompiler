// Issue 3811 -- negative control: correct code. Identical to repro.hlsl except that
// `result` is initialised before the loop. The predicate must NOT fire on this.
StructuredBuffer<float> values : register(t0,space0);

void Accumulate(int count, out float result)
{
	result = 0.0;
	for (int i = 0; i < count; i++)
		result += values[i];
}

float main (int count : IN) : OUT
{
	float result = 0.0;
	Accumulate(count, result);
	return result;
}
