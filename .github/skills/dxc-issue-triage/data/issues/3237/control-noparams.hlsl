// #3237 control: the same library function with NO parameters at all.
// If GetFunctionParameter(0) still hands back a stub whose GetDesc returns
// E_FAIL here, the E_FAIL is not "index out of range" -- the index is ignored.
export float3 Apply()
{
   return 2.0f;
}
