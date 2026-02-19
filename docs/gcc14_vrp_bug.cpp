// Minimal reproducer for GCC 14.2.0 tree-vrp miscompilation.
//
// VRP (Value Range Propagation) proves the return value of convert() is in
// [0,17], allowing it to eliminate the range check before the bt (bit test)
// instruction. In doing so, it flips the cmov condition from cmovc to cmovnc,
// inverting the switch logic: values IN the set are left unchanged while
// values NOT in the set are incorrectly replaced with 5.
//
// Buggy:    g++-14 -O3 -o bug gcc14_vrp_bug.cpp && ./bug    → FAIL
// Fixed:    g++-14 -O3 -fno-tree-vrp -o ok gcc14_vrp_bug.cpp && ./ok → PASS
// Also bad: g++-14 -O2 -o bug gcc14_vrp_bug.cpp && ./bug    → FAIL
//
// Correct assembly (-fno-tree-vrp):
//   call  convert
//   cmpl  $17, %eax        ← range check (present)
//   ja    .L5
//   movl  $131138, %edx    ← bitmask for cases {1, 6, 17}
//   btq   %rax, %rdx       ← CF = 1 if kind is in the set
//   movl  $5, %edx
//   cmovc %edx, %eax       ← if CF=1 (in set): eax = 5 ✓
//
// Buggy assembly (-O3, tree-vrp enabled):
//   call  convert
//                           ← range check eliminated by VRP
//   movl  $131138, %edx
//   btq   %rax, %rdx
//   movl  $5, %edx
//   cmovnc %edx, %eax      ← if CF=0 (NOT in set): eax = 5 ✗ INVERTED!
//
// See: https://github.com/microsoft/DirectXShaderCompiler/issues/7364
// Tested: GCC 14.2.0 (Ubuntu 14.2.0-4ubuntu2~24.04.1), x86-64

#include <cstdio>

// A switch whose return values VRP can prove are in [0, 17].
// This range proof enables VRP to eliminate the range check in process(),
// which triggers the cmov condition inversion bug.
__attribute__((noinline))
static unsigned convert(int ty) {
    switch (ty) {
    case 0: return 17;
    case 1: return 4;
    case 2: return 1;
    default: return 0;
    }
}

// The second switch is lowered to: bt kind, bitmask; cmov.
// With VRP, the cmov condition is inverted.
__attribute__((noinline))
unsigned process(int ty) {
    unsigned kind = convert(ty);
    switch (kind) {
    case 1: case 6: case 17:
        kind = 5;
        break;
    default:
        break;
    }
    return kind;
}

int main() {
    // convert(2) = 1, which is in {1, 6, 17}, so process(2) should return 5.
    unsigned r = process(2);
    if (r != 5) {
        printf("FAIL: process(2) = %u, expected 5\n", r);
        return 1;
    }

    // convert(1) = 4, which is NOT in {1, 6, 17}, so process(1) should return 4.
    r = process(1);
    if (r != 4) {
        printf("FAIL: process(1) = %u, expected 4\n", r);
        return 1;
    }

    printf("PASS\n");
    return 0;
}
