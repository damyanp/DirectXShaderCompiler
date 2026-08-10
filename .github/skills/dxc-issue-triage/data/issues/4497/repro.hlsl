struct SData
{
	float3 value;
	uint type;
	float4 value2;
};

StructuredBuffer<SData> dataBuffer;

void fct1(SData data)
{
	[branch]if (data.type == 0)
		[branch] if(data.value.x < 0.0f)
			discard;
}

void test1()
{
	fct1(dataBuffer[0]);
}

void fct2(int id)
{
	[branch] if (dataBuffer[id].type == 0)
		[branch] if (dataBuffer[id].value.x < 0.0f)
		      discard;
}

void test2()
{
	fct2(0);
}
