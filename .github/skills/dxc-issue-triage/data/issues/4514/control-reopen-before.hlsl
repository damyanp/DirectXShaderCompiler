// PREDICTION (written before running): compiles CLEAN.
// The namespace is REOPENED before main() with a declaration that is
// semantically its own. Under the lazy-lookup reading, that marks the
// namespace's primary context as having local lexical decls to build, so the
// lookup at the use site in main() runs buildLookup() and picks the cbuffer
// member up through the transparent-context recursion.
namespace testNamespace
{
    cbuffer testBuffer
    {
        uint testVariable;
    }
}

namespace testNamespace
{
    static uint unrelatedDummy;
}

[numthreads(1, 1, 1)]
void main( in uint3 tid : SV_DispatchThreadID )
{
    if( testNamespace::testVariable * tid.x > 0 )
        return;
}
