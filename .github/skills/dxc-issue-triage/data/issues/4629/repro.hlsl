struct PSInput
{
};

class SurfaceData_BasePBR
{
    float3 albedo;
};

interface ISpecRough
{
    void ApplySpecularAA();
};

class SurfaceData_NewPBR : SurfaceData_BasePBR, ISpecRough
{
    float3 emissiveLighting;

    void ApplySpecularAA()
    {
    } 
};

float4 PSMain( PSInput input ) : SV_TARGET
{
    SurfaceData_NewPBR obj ;
    obj . albedo . x = 1 ;
    return float4 ( obj . albedo , 1 ) ;
} 
