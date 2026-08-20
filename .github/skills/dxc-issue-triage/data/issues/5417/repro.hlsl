float4 VCMain(
    nointerpolation float4 Color:COLOR0)
    : SV_TARGET0 
{
#ifdef USE_GET_ATTRIBUTE_AT_VERTEX
    return GetAttributeAtVertex(Color,0);
#endif
    return Color;
}
