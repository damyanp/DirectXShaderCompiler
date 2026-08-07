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

float main() : SV_Target
{
	Child instance;
	return instance.color();
}
