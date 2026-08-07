struct Helper
{
	float getColor() { return 0; }
};

struct Parent
{
	Helper helper;
};

struct Child : Parent
{
	float memberVar;

	float color()
	{
		return helper.getColor();
	}
};

RWStructuredBuffer<float> output;

[numthreads(1, 1, 1)]
void main()
{
	Child instance;
	output[0] = instance.color();
}
