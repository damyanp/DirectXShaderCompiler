// PREDICTION (written before running): STILL FAILS with the reported error.
// Same text as control-reopen-before.hlsl, except the reopening block is moved
// BELOW main(). If the mechanism is a lookup table built lazily at the point
// of use, the declaration that would have triggered the build has not been
// seen yet when main() is parsed, so the qualified reference must still fail.
// If instead this compiles, the "lazy build at point of use" reading is wrong
// and only the AST/DeclContext half of the explanation survives.
namespace testNamespace
{
    cbuffer testBuffer
    {
        uint testVariable;
    }
}

[numthreads(1, 1, 1)]
void main( in uint3 tid : SV_DispatchThreadID )
{
    if( testNamespace::testVariable * tid.x > 0 )
        return;
}

namespace testNamespace
{
    static uint unrelatedDummy;
}
