StructuredBuffer<float> values : register(t0,space0);

void Accumulate(int count, out float result)
{
	result += values[0];  // <-- This will fail validation and produce an error message
}

float main (int count : IN) : OUT
{
	float result = 0.0;
	Accumulate(count, result);
	return result;
}
