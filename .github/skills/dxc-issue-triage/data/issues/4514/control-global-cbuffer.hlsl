cbuffer testBuffer
{
    uint testVariable;
}

[numthreads(1, 1, 1)]
void main( in uint3 tid : SV_DispatchThreadID )
{
    if( testVariable * tid.x > 0 )
        return;
}
