// declaration of functions
#pragma ps pixelShader
#pragma vs vertexShader

// data structure : before vertex shader (mesh info)
struct vertexInfo
{
    float4 position : POSITION;
};

// data structure : vertex shader to pixel shader
// also called interpolants because values interpolates through the triangle
// from one vertex to another
struct v2p
{
    float4 position : SV_POSITION;
};

float4 foo(float4 p);

// vertex shader function
[shader("vertex")]
v2p vertexShader(vertexInfo input)
{
    v2p output;
    output.position = foo(input.position);
    return output;
}
