namespace testNamespace
{
    cbuffer testBuffer
    {
        uint testVariable;
    }

    // The reporter's own workaround: this line UNCOMMENTED "somehow fixes" it.
    Texture2D testTexture;
}

[numthreads(1, 1, 1)]
void main( in uint3 tid : SV_DispatchThreadID )
{
    if( testNamespace::testVariable * tid.x > 0 )
        return;
}
