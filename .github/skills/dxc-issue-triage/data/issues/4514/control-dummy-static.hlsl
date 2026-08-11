// PREDICTION (written before running): compiles CLEAN.
// Mechanism read from source: HLSLBufferDecl::Create hardcodes the semantic
// DeclContext to the TranslationUnitDecl (SemaHLSL.cpp), so a cbuffer in a
// namespace is only LEXICALLY in that namespace. Nothing therefore ever sets
// the namespace's HasLazyLocalLexicalLookups / LookupPtr, and
// DeclContext::lookup() returns empty. Any declaration whose SEMANTIC context
// really is the namespace sets that flag, which makes lookup() run
// buildLookup(), whose transparent-context recursion (HLSLBuffer is
// isTransparentContext()) then does add testVariable to the namespace's map.
// So the texture in the issue is not special: a plain static uint should work
// just as well.
namespace testNamespace
{
    cbuffer testBuffer
    {
        uint testVariable;
    }

    static uint unrelatedDummy;
}

[numthreads(1, 1, 1)]
void main( in uint3 tid : SV_DispatchThreadID )
{
    if( testNamespace::testVariable * tid.x > 0 )
        return;
}
