struct PSInput
{
	float4 color : COLOR;
};

float4 PSMain(PSInput input) : SV_TARGET
{
	return ((StructuredBuffer<float>)ResourceDescriptorHeap[int(input.color.x)]).Load(0);
}
