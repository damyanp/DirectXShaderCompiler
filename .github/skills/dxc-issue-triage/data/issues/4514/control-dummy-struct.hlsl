// PREDICTION (written before running): compiles CLEAN.
// A struct is a TagDecl whose semantic DeclContext is the namespace, so it
// triggers the same lazy-lookup build as the reporter's texture.
namespace testNamespace
{
    cbuffer testBuffer
    {
        uint testVariable;
    }

    struct UnrelatedStruct { uint x; };
}

[numthreads(1, 1, 1)]
void main( in uint3 tid : SV_DispatchThreadID )
{
    if( testNamespace::testVariable * tid.x > 0 )
        return;
}
