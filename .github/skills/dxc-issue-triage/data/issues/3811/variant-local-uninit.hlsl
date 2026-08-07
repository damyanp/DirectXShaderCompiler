// Issue 3811 -- the same defect written with a LOCAL variable instead of an `out` parameter.
// Not a control: it is a probe of how far the 2023 -Wparameter-usage warning reaches.
// If this is silent, the issue's literal claim ("no error/warning") still holds for the
// general shape of the defect and only the `out`-parameter spelling gained a diagnostic.
StructuredBuffer<float> values : register(t0,space0);

float main (int count : IN) : OUT
{
	float result;
	for (int i = 0; i < count; i++)
		result += values[i];
	return result;
}
