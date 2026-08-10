// Reduction probe for #3906: is the *member* function load-bearing, or does any
// function returning an array do it? Same as reduce-member-array-return.hlsl
// with the function lifted out of the struct.
float3 f()[2] {
    float3 v[2] = {
        0.xxx,0.xxx,
    };
    return v;
}

[numthreads(8, 8, 1)] void main() {
     float3 w[2] = f();
}
