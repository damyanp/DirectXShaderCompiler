template <
   bool PARAM1,
   bool PARAM2>
struct TEST_STRUCT{};


template <bool PARAM1>
struct TEST_STRUCT<PARAM1, true> {
   static const bool FIELD = PARAM1;
};

struct PSInput
{
	float4 color : COLOR;
};

float4 PSMain(PSInput input) : SV_TARGET
{
	bool test = TEST_STRUCT<true, true>::FIELD;
	return input.color;
}
