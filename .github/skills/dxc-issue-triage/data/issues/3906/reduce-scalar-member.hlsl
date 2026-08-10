// Reduction probe for #3906: is the *nested struct* member load-bearing, or does
// a plain scalar member do it? Identical to reduce-nested-struct-member.hlsl
// with RenderResourceHandle flattened to a bare uint.
struct Test{
    uint h;

    float3 infLoop()[2] {
        uint i = this.h;
        float3 v[2] = {
            0.xxx,0.xxx,
        };
        return v;
    }
};

[numthreads(8, 8, 1)] void main() {
     Test t;
     t.h = 0;
     float3 w[2] = t.infLoop();
}
