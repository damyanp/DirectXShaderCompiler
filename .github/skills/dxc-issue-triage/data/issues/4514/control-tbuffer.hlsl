// PREDICTION (written before running): STILL FAILS with the same error, with
// "tbuffer" in place of "cbuffer". tbuffer goes through the same
// HLSLBufferDecl::Create, which hardcodes the TranslationUnitDecl as the
// semantic DeclContext regardless of the cbuffer/tbuffer flag.
namespace testNamespace
{
    tbuffer testBuffer
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
