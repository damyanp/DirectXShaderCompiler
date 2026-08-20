// lib_6_9 module A: exported function taking a matrix array parameter
// by reference (byref matrix array argument), storing at a
// caller-supplied index.
export void storeMat(inout float2x2 arr[16], int idx) {
  arr[idx] = float2x2(1, 2, 3, 4);
}
