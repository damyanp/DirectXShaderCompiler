// #3237 control: two parameters instead of one.
// FunctionParameterCount must track the arity if it is populated at all.
export float3 Apply(float3 input, float scale)
{
   return input * scale;
}
