// #3237 -- the function from the issue body, marked `export` so that it is
// actually present in the library. See repro-as-filed.hlsl and notes.md: the
// source exactly as filed reflects zero functions on every DXC that has ever
// shipped, so it cannot reach the reported call at all.
export float3 Apply(float3 input)
{
   return input * 2.0f;
}
