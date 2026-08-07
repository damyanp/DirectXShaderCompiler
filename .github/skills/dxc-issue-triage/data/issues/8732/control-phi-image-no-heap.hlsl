// #8732 CONTROL -- corroborates the reporter's aside that an OpPhi of image type
// fails independently of descriptor heaps: a conditional between two BOUND
// textures, no -fspv-use-descriptor-heap. Expected to fail; that is the point.
RWByteAddressBuffer outputBytes : register(u0);
RWTexture2D<uint> a : register(u1);
RWTexture2D<uint> b : register(u2);
[numthreads(1,1,1)]
void main(uint3 tid : SV_DispatchThreadID) {
    RWTexture2D<uint> t = a;
    if (tid.x == 0) t = b;
    t[tid.xy] = 7;
    outputBytes.Store(0, tid.x);
}

