struct EmptyStruct
{
};

struct BaseStruct
{
	EmptyStruct emptyStructMember;

	//float makeMeNotEmpty;	// Uncomment to prevent assert
};

struct ChildStruct              // BaseStruct held as a MEMBER, not a base
{
	BaseStruct base;
	float4 m_childMember;

	float4 func() { return m_childMember; }
};

float4 main() : SV_Position
{
	ChildStruct var_1;
	EmptyStruct var_2;
	var_1.base.emptyStructMember = var_2;
	var_1.m_childMember = 0;
	return var_1.func();
}
