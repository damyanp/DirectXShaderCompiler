// Standalone ABI-behaviour probe for #4786.
//
// This does NOT invoke any DXC code. It isolates the one claim in the issue that
// needs *execution* rather than source reading: that returning a `float` by value
// from a 32-bit x86-compiled function, when the underlying bits are an x87
// signalling NaN, silently gets quieted (bit 22 set) by the hardware on the
// implicit FLD used by the cdecl return sequence -- and that the same code
// compiled for x64 (which returns float in XMM0, no x87 involved) does not.
//
// This mirrors, at the ABI level, exactly what
// `ConstantDataSequential::getElementAsFloat()` does in
// lib/Bitcode/Writer/BitcodeWriter.cpp: read raw bits, return as `float` by
// value, bit-cast the returned value back to `uint32_t` via a union.
//
// Values are the exact three DXBC ICB words quoted in the issue body:
//   0xffbfffca -- the one the reporter observed corrupted (x87 signalling NaN)
//   0x09909909 -- not a NaN pattern; must NOT change (negative control)
//   0x00000001 -- a positive subnormal; must NOT change (negative control)
// Plus two canonical extra x87 signalling NaNs as an additional positive check.

#include <cstdint>
#include <cstdio>

#if defined(_M_IX86)
static const char *kArch = "x86";
#elif defined(_M_X64)
static const char *kArch = "x64";
#else
static const char *kArch = "unknown";
#endif

// noinline + returns by value: forces a real ABI-level float return (ST(0) on
// x86 cdecl, XMM0 on x64), not something the optimizer can fold away at
// compile time. Reads through a volatile pointer for the same reason.
__declspec(noinline) float LoadAsFloat(volatile const uint32_t *bits) {
  uint32_t raw = *bits;
  union {
    float F;
    uint32_t I;
  } u;
  u.I = raw;
  return u.F; // <-- the ABI-level round trip under test
}

int main() {
  struct Case {
    const char *label;
    uint32_t bits;
  };
  static const Case cases[] = {
      {"issue-reported (0xffbfffca)", 0xffbfffcau},
      {"issue-control-int (0x09909909)", 0x09909909u},
      {"issue-control-subnormal (0x00000001)", 0x00000001u},
      {"canonical-snan-min-pos (0x7f800001)", 0x7f800001u},
      {"canonical-snan-min-neg (0xff800001)", 0xff800001u},
  };

  printf("arch=%s\n", kArch);
  int mismatches = 0;
  for (const auto &c : cases) {
    volatile uint32_t bits = c.bits;
    uint32_t roundTripped;
    {
      float f = LoadAsFloat(&bits);
      union {
        float F;
        uint32_t I;
      } u;
      u.F = f;
      roundTripped = u.I;
    }
    bool changed = roundTripped != c.bits;
    if (changed)
      mismatches++;
    printf("%-42s in=0x%08x out=0x%08x %s\n", c.label, c.bits, roundTripped,
           changed ? "CORRUPTED" : "unchanged");
  }
  printf("mismatches=%d\n", mismatches);
  return 0;
}
