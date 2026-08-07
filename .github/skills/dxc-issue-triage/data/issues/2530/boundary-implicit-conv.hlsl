// #2530 boundary probe: no explicit cast at all, so the float->integral
// conversion at the array bound is implicit. MEASURED: this does not reach the
// VLA path -- SemaType.cpp's !CPlusPlus11 branch rejects it earlier with
// "size of array has non-integer type 'float'". So it is outside the issue as
// filed; expectation revised match -> no-match. Line numbers below are pinned.
static const float ARRAY_SIZE = 1;

float4 main() : SV_Target
{
    float array[ARRAY_SIZE] = { 1.0f };
    return (float4)0;
}
