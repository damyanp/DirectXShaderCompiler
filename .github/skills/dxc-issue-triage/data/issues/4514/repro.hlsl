namespace testNamespace
{
    cbuffer testBuffer
    {
        uint testVariable;
    }

    // Uncommenting the following line somehow fixes the issue
    //Texture2D testTexture;
}

[numthreads(1, 1, 1)]
void main( in uint3 tid : SV_DispatchThreadID )
{
    if( testNamespace::testVariable * tid.x > 0 )
        return;
}
