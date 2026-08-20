// RUN: %dxc -T ps_6_6 -HV 2021 %s

float4 main(float f: F) : SV_Target {

       uint i = 7;
       for (uint i = 0; i < 3; i++) {
         f += i;
       }
       return f + i;
}
