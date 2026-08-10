// NEGATIVE CONTROL for repro-release-crash.hlsl: identical 32-local shader with the
// template removed (R replaced by uint). Proves the Release access violation is this
// defect and not "a function with 32 locals crashes dxc". Must score no-match, and exits 0
// on the shipped v1.9.2607 release binary that access-violates on the templated version.
void test(uint x, out uint result) {
    uint v1 = 1;
    uint v2 = 2;
    uint v3 = 3;
    uint v4 = 4;
    uint v5 = 5;
    uint v6 = 6;
    uint v7 = 7;
    uint v8 = 8;
    uint v9 = 9;
    uint v10 = 10;
    uint v11 = 11;
    uint v12 = 12;
    uint v13 = 13;
    uint v14 = 14;
    uint v15 = 15;
    uint v16 = 16;
    uint v17 = 17;
    uint v18 = 18;
    uint v19 = 19;
    uint v20 = 20;
    uint v21 = 21;
    uint v22 = 22;
    uint v23 = 23;
    uint v24 = 24;
    uint v25 = 25;
    uint v26 = 26;
    uint v27 = 27;
    uint v28 = 28;
    uint v29 = 29;
    uint v30 = 30;
    uint v31 = 31;
    uint v32 = 32;
    result = 10;
}

[numthreads(32, 32, 1)] void main(uint2 threadId: SV_DispatchThreadID) {
    uint x;
    test(10, x);
}
