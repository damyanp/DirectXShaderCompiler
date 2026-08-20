float4 main(float4 val: F): SV_TARGET
{
   return WaveMatch( val );
}
