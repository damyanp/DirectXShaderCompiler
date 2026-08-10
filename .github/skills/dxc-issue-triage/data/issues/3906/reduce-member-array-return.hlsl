// Reduction for #3906, not a control: the smallest shape found that still trips
// the SROA assert. Struct member function returning an array, assigned to a
// local array. No ByteAddressBuffer, no handle struct, no member-function index
// -- i.e. two of the reporter's three "necessary" conditions are gone.
struct Test {
    float3 f()[2] {
        float3 v[2] = {
            0.xxx,0.xxx,
        };
        return v;
    }
};

[numthreads(8, 8, 1)] void main() {
     Test t;
     float3 w[2] = t.f();
}
