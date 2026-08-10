// Reduction probe for #3906: control-no-buffer-access still asserts, so keep
// cutting. Here the global ByteAddressBuffer array is gone entirely and the
// index is read directly (`this.h.handle`, no readIndex() call). What remains is
// a struct with a NESTED STRUCT member whose array-returning member function
// reads that nested member through `this`.
struct RenderResourceHandle {
    uint handle;
};

struct Test{
    RenderResourceHandle h;

    float3 infLoop()[2] {
        uint i = this.h.handle;
        float3 v[2] = {
            0.xxx,0.xxx,
        };
        return v;
    }
};

[numthreads(8, 8, 1)] void main() {
     Test t;
     t.h.handle = 0;
     float3 w[2] = t.infLoop();
}
