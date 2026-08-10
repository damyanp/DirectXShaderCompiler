// Control for #4351: identical to repro.hlsl except that the `Child` member of
// `Parent` is a plain member rather than an array. The issue's title attributes
// the removal to "a member array", so this control is what makes that
// attribution falsifiable: the predicate must score no-match here.
struct Child {
	uint Test;
};

struct Parent {
	Child SingleChild;
};

RWStructuredBuffer<Parent> ParentBuffer;

[numthreads(1, 1, 1)]
void InitArgs()
{
	ParentBuffer[0] = (Parent)0;
}
