// Control for #3906: condition 1 of the reporter's three removed.
// The index is read directly from the member (`this.h.handle`) instead of being
// returned from the struct member function `readIndex()`. Everything else --
// the ByteAddressBuffer access and the array return -- is unchanged.
// The reporter states that with any one condition missing there is no hang.
struct RenderResourceHandle {
    uint handle;

    uint readIndex() { return this.handle; }
};

ByteAddressBuffer g_byteAddressBuffer[] : register(t0, space3);

struct Test{
    RenderResourceHandle h;

    float3 infLoop()[2] {
        ByteAddressBuffer b = g_byteAddressBuffer[this.h.handle];
        float3 v[2] = {
            0.xxx,0.xxx,
        };
        return v;
    }
};

[numthreads(8, 8, 1)] void main(uint2 dispatchIdx
                                : SV_DispatchThreadID, uint3 pxInTile
                                : SV_GroupThreadID) {

    RenderResourceHandle resourceHandle;
    resourceHandle.handle = 0;

     Test t;
     t.h = resourceHandle;
     float3 w[2] = t.infLoop();
}
