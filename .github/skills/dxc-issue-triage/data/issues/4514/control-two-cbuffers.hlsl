// PREDICTION (written before running): STILL FAILS with the reported error.
// This is the discriminating case. If the mechanism were "any extra line in
// the namespace fixes it", a second cbuffer would fix it too. Under the
// DeclContext reading it must NOT, because HLSLBufferDecl::Create gives both
// buffers the TranslationUnitDecl as their semantic parent, so neither one
// ever marks the namespace as having lazy local lookups.
namespace testNamespace
{
    cbuffer testBuffer
    {
        uint testVariable;
    }

    cbuffer otherBuffer
    {
        uint otherVariable;
    }
}

[numthreads(1, 1, 1)]
void main( in uint3 tid : SV_DispatchThreadID )
{
    if( testNamespace::testVariable * tid.x > 0 )
        return;
}
