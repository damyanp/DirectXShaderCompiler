namespace testNamespace
{
    cbuffer testBuffer
    {
        uint testVariable;
    }

#ifdef WORKAROUND
    Texture2D testTexture;
#endif
}

[numthreads(1, 1, 1)]
void main( in uint3 tid : SV_DispatchThreadID )
{
#ifdef UNQUALIFIED
    if( testVariable * tid.x > 0 )
#else
    if( testNamespace::testVariable * tid.x > 0 )
#endif
        return;
}
