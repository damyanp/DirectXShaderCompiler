struct Struct_1 {
  int b;
  float2x2 c;
};

struct main_inputs {
  uint tint_local_index : SV_GroupIndex;
};


RWByteAddressBuffer v5 : register(u0);
static float v6[1] = (float[1])0;
static Struct_1 v7[1] = (Struct_1[1])0;
groupshared float v8[1];
static float2x2 v9 = float2x2((0.0f).xx, (0.0f).xx);
uint zero() {
  return 0u;
}

int tint_mod_i32(int lhs, int rhs) {
  int v = ((((rhs == int(0)) | ((lhs == int(-2147483648)) & (rhs == int(-1))))) ? (int(1)) : (rhs));
  return asint((asuint(lhs) - asuint(asint((asuint((lhs / v)) * asuint(v))))));
}

int safe_index(int index, int size) {
  return tint_mod_i32(index, size);
}

float2x2 func_2(inout float v52[1], float v53, float v54) {
  uint v_1 = min(uint(safe_index(int(0), int(1))), 0u);
  Struct_1 v_2 = v7[v_1];
  Struct_1 v_3[1] = {v_2};
  v7 = v_3;
  return float2x2(asfloat(v5.Load2((0u + (min(uint(safe_index(int(0), int(4))), 3u) * 8u)))), (0.0f).xx);
}

float2x2 func_1(float2x2 v56, Struct_1 v58) {
  return float2x2((0.0f).xx, (0.0f).xx);
}

void main_inner(uint tint_local_index) {
  if ((tint_local_index < 1u)) {
    v8[0u] = 0.0f;
  }
  GroupMemoryBarrierWithGroupSync();
  uint v_4 = min(zero(), 0u);
  func_2(v6, v8[v_4], 0.0f);
  float2x2 v_5 = func_2(v6, asfloat(v5.Load((0u + (min(uint(safe_index(int(0), int(4))), 3u) * 8u)))), 0.0f);
  float2 v_6 = v_5[min(uint(safe_index(int(0), int(2))), 1u)];
  Struct_1 v_7 = (Struct_1)0;
  v9 = func_1(float2x2((0.0f).xx, (0.0f).xx), v_7);
}

[numthreads(1, 1, 1)]
void main(main_inputs inputs) {
  main_inner(inputs.tint_local_index);
}
