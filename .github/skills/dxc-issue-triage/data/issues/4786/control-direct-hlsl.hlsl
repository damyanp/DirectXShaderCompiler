RWByteAddressBuffer b : register(u0, space0);

[numthreads(1, 1, 1)]
void main() {
  {
    for(uint i = 0u; (i < 3u); i = (i + 1u)) {
      const uint icb[3] = {0xffbfffcau, 0x09909909u, 1u};
      b.Store((4u * min(i, 2u)), asuint(icb[min(i, 2u)]));
    }
  }
  return;
}
