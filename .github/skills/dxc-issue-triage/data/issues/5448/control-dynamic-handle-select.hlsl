Texture2D<float4> tex0 : register(t0);
Texture2D<float4> tex1 : register(t1);
RWBuffer<float4> outBuf : register(u0);

[numthreads(1,1,1)]
void main(uint3 id : SV_DispatchThreadID) {
    Texture2D<float4> t = id.x == 0 ? tex0 : tex1;
    uint w, h;
    t.GetDimensions(w, h);
    outBuf[0] = float4(w, h, 0, 0);
}
