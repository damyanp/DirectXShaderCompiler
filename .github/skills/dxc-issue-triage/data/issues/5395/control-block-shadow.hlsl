float4 main(float f: F) : SV_Target {
       uint i = 7;
       {
         uint i = 3;
         f += i;
       }
       return f + i;
}
