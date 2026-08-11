namespace testNamespace
{
    cbuffer testBuffer
    {
        uint testVariable;
    }

    // Same as repro.hlsl; only the reference below differs.
    //Texture2D testTexture;
}

[numthreads(1, 1, 1)]
void main( in uint3 tid : SV_DispatchThreadID )
{
    if( testVariable * tid.x > 0 )
        return;
}
