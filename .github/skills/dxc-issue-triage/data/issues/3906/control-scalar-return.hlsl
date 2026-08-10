// Control for #3906: condition 3 of the reporter's three removed.
// The member function returns a single float3 instead of an array of them. The
// index still comes from a struct member function and the ByteAddressBuffer is
// still accessed.
// The reporter states that with any one condition missing there is no hang.
struct RenderResourceHandle {
    uint handle;

    uint readIndex() { return this.handle; }
};

ByteAddressBuffer g_byteAddressBuffer[] : register(t0, space3);

struct Test{
    RenderResourceHandle h;

    float3 infLoop() {
        ByteAddressBuffer b = g_byteAddressBuffer[this.h.readIndex()];
        float3 v = 0.xxx;
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
     float3 w = t.infLoop();
}
