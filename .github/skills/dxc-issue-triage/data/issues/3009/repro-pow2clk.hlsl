int4x4 m;

float4 main (int a : IN) : SV_Position
{
 float2 b;
 b.x = a;
 return mul( b.xyxy, m );
}
