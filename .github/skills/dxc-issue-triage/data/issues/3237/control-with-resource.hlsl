// #3237 control: same function, but it also reads a constant buffer and a
// resource. ConstantBuffers and BoundResources in D3D12_FUNCTION_DESC are
// populated by the same GetDesc call that leaves FunctionParameterCount at 0,
// so this separates "GetDesc does nothing" from "GetDesc omits parameters".
cbuffer Params
{
   float gScale;
};

Buffer<float> gBuf;

export float3 Apply(float3 input)
{
   return input * gScale * gBuf[0];
}
