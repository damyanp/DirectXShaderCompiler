#define MAX_TEXTURES 128
Texture2D _allTextures[MAX_TEXTURES];

SamplerState linearSampler;
SamplerState anisoSampler;

enum TexturePrimitive {
    TexturePrimitive_2D,
    TexturePrimitive_3D,
    TexturePrimitive_Cube
};

static const float floatMax = 1e38;        //Approx

bool getTextureFromId(inout Texture2D tex, uint textureId) {

    //Remove this! Don't use this without checking the return bool!
    //This is super sketchy but otherwise it won't compile.
    //DXC can't understand it otherwise.

    //tex = _allTextures[0];

    if (textureId) {

        if ((textureId >> 20) != TexturePrimitive_2D) // Validate if it's a texture2d
            return false;

        textureId = textureId << 12 >> 12;

        if (textureId > MAX_TEXTURES)
            return false;

        tex = _allTextures[NonUniformResourceIndex(max((int)textureId - 1, 0))];
        return true;
    }

    return false;
}

float4 sampleTextureGrad(
    float2 uv, uint textureId, bool useTriplanar,
    float2 uvDdx, float2 uvDdy,
    float4 defaultValue = 1.rrrr
) {

    float4 t = defaultValue;
    Texture2D tex2d;

    if (getTextureFromId(tex2d, textureId)) {
        
        uint w, h, mips;
        tex2d.GetDimensions(0, w, h, mips);

        //Correct for aspect ratio

        if(useTriplanar) {

            float aspect = float(w) / float(h);

            uv.y    *= aspect;
            uvDdx.y *= aspect;        //uvX - uv. If both .y scale by aspect then it's safe to scale the resulting .y by the same amount.
            uvDdy.y *= aspect;
        }
    
        if(uvDdx.x == floatMax)
            t = tex2d.SampleLevel(linearSampler, uv, 0);

        else t = tex2d.SampleGrad(anisoSampler, uv, uvDdx, uvDdy); 
    }
    
    return t;
}

RWTexture2D<float4> v;

[numthreads(1,1,1)]
void main(int2 i : SV_DispatchThreadID) {
    
    float4 t = sampleTextureGrad(0.xx, i.x & 127, false, 0.xx, 0.xx);
    v[i] = t;
}
