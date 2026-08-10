// Workaround check for #3906. The reporter's stated workaround is to wrap the
// returned values in a struct and return the struct instead of an array. This is
// repro.hlsl with exactly that change and nothing else, so that "the workaround
// still works" is a measurement rather than a restatement of the report.
struct RenderResourceHandle {
    uint handle;

    uint readIndex() { return this.handle; }
};

ByteAddressBuffer g_byteAddressBuffer[] : register(t0, space3);

struct Wrapped {
    float3 v[2];
};

struct Test{
    RenderResourceHandle h;

    Wrapped infLoop() {
        ByteAddressBuffer b = g_byteAddressBuffer[this.h.readIndex()];
        Wrapped w;
        w.v[0] = 0.xxx;
        w.v[1] = 0.xxx;
        return w;
    }
};

[numthreads(8, 8, 1)] void main(uint2 dispatchIdx
                                : SV_DispatchThreadID, uint3 pxInTile
                                : SV_GroupThreadID) {

    RenderResourceHandle resourceHandle;
    resourceHandle.handle = 0;

     Test t;
     t.h = resourceHandle;
     Wrapped w = t.infLoop();
}
