# GCC 14 Tree-VRP Miscompilation in DXC

## Summary

GCC 14.2.0 miscompiles a switch statement in `CGMSHLSLRuntime::SetUAVSRV()`
(CGHLSLMS.cpp:3464-3477) due to a bug in the `tree-vrp` (Value Range
Propagation) optimization pass. The resulting assembly has inverted conditional
move operands, causing 45 test failures. This is a GCC compiler bug, not
undefined behavior in DXC code.

**Compiler:** GCC 14.2.0 (Ubuntu 14.2.0-4ubuntu2~24.04.1)  
**Build type:** Release (-O3)  
**Workaround:** `-fno-tree-vrp` on CGHLSLMS.cpp  
**Tests affected:** 45 out of 2804 clang tests

## The Miscompiled Code

In `tools/clang/lib/CodeGen/CGHLSLMS.cpp`, the `SetUAVSRV` function has a
switch that converts unsupported component types (bool, 64-bit, packed) to U32:

```cpp
CompType::Kind kind = BuiltinTyToCompTy(BTy, ...);
// Boolean, 64-bit, and packed types are implemented with u32.
switch (kind) {
case CompType::Kind::I1:
case CompType::Kind::U64:
case CompType::Kind::I64:
case CompType::Kind::F64:
case CompType::Kind::SNormF64:
case CompType::Kind::UNormF64:
case CompType::Kind::PackedS8x32:
case CompType::Kind::PackedU8x32:
    kind = CompType::Kind::U32;  // value 5
    break;
default:
    break;
}
hlslRes->SetCompType(kind);
```

This is lowered to a bitmask check. The switch cases correspond to enum values
1, 6, 7, 10, 15, 16, 17, 18, producing bitmask `492738` (0x78442).

## Assembly Comparison

### Correct assembly (with `-fno-tree-vrp`):

```asm
call  BuiltinTyToCompTy     ; %eax = kind (e.g., 1 for I1)
movl  %eax, %esi             ; %esi = original kind
cmpl  $18, %eax              ; range check
ja    .L10552                 ; skip if out of range
movl  $492738, %eax           ; bitmask of switch cases
btq   %rsi, %rax             ; CF = 1 if kind is in the switch set
movl  $5, %eax               ; %eax = 5 (U32)
cmovc %eax, %esi             ; if CF=1 (in set): %esi = 5 ✓
```

When kind=1 (I1): CF=1 → `cmovc` fires → `%esi` = 5 (U32). **Correct.**

### Buggy assembly (with tree-vrp, default -O3):

```asm
call  BuiltinTyToCompTy     ; %eax = kind (e.g., 1 for I1)
                              ; ← NO range check (VRP eliminated it)
movl  $492738, %edx           ; bitmask
btq   %rax, %rdx             ; CF = 1 if kind is in the switch set
movl  $5, %edx               ; %edx = 5 (U32)
cmovc %eax, %edx             ; if CF=1 (in set): %edx = %eax (original!) ✗
```

When kind=1 (I1): CF=1 → `cmovc` fires → `%edx` = `%eax` = 1 (**NOT converted!**).
When kind=9 (F32): CF=0 → `cmovc` doesn't fire → `%edx` stays 5 (**wrongly converted!**).

**The cmov condition is inverted.** VRP eliminates the range check AND flips
`cmovc` to effectively act like `cmovnc` (or equivalently, swaps the operand
roles). The GIMPLE tree IR is correct; the inversion happens during RTL code
generation when the shift+and+compare pattern is converted to a `bt` instruction.

## Root Cause Analysis

1. **VRP eliminates the range check** (`cmpl $18`): VRP determines that
   `BuiltinTyToCompTy` always returns values ≤ 18, making the range check
   redundant. This elimination is correct in isolation.

2. **The GIMPLE tree IR is correct**: The final optimized GIMPLE
   (`-fdump-tree-optimized`) shows the correct PHI node:
   ```
   kind_42 = BuiltinTyToCompTy(...);
   _73 = 492738 >> kind_42;
   _861 = (bool) _73;
   if (_861 != 0) goto bb113; else goto bb112;
   bb112: [fall through]
   bb113: kind_43 = PHI <kind_42(bb112), 5(bb111)>
   ```
   This correctly says: if the bit is set, use 5; otherwise keep original.

3. **The RTL if-conversion (`ce1`) is correct**: The cmov is generated as:
   ```
   (set kind (if_then_else (eq CCC 0) original_kind 5))
   ```
   Where CCC is the carry flag from `bt`. `(eq CCC 0)` means "not carry",
   which correctly selects the original kind when the bit is NOT set.

4. **The bug is in final code emission**: When translating the RTL
   `if_then_else` with `CCC` mode and `bt` instruction to x86 assembly, GCC
   emits the wrong cmov condition. The correct instruction is `cmovc` (move if
   carry = bit was set), but GCC emits `cmovnc` (move if NOT carry), or
   equivalently swaps the operand roles with `cmovc`.

5. **Neither VRP1 nor VRP2 directly eliminates the switch**: The VRP tree dumps
   (`-fdump-tree-vrp1-details`, `-fdump-tree-vrp2-details`) both show "Not
   folded" for the switch. The range information propagated by VRP enables the
   elimination of the range check, which changes the RTL structure enough to
   trigger the condition inversion bug in the backend.

## Why This is NOT Undefined Behavior

1. **Well-defined enum switch**: `CompType::Kind` is `enum class ComponentType :
   uint32_t`. All values in the switch are valid named enumerators. The switch
   uses `default: break;` for unmatched cases.

2. **No strict aliasing violation**: Compiling with `-fno-strict-aliasing`
   globally does NOT fix the issue. This rules out type-punning UB.

3. **No out-of-range enum values**: `BuiltinTyToCompTy` always returns a named
   enum value (0-18). The function has a `default:` case that returns `Invalid`
   (0) for unhandled input.

4. **Pure value semantics**: The switch operates on a local copy of the enum
   value. No pointers, references, or aliasing involved.

5. **Optimization barrier confirms**: Adding `fprintf` to the switch body
   (which acts as an optimization barrier) causes correct code generation —
   the values are correct when VRP cannot optimize across the barrier.

## Observable Symptoms

- `RWBuffer<vector<bool,2>>` gets `CompType=1` (I1/bool) instead of
  `CompType=5` (U32)
- Resource properties second dword: 513 (0x0201) instead of 517 (0x0205)
- 45 test failures in `check-clang`, all related to resource type encoding

## Workaround

Apply `-fno-tree-vrp` to CGHLSLMS.cpp only. In
`tools/clang/lib/CodeGen/CMakeLists.txt`:

```cmake
if (CMAKE_CXX_COMPILER_ID STREQUAL "GNU" AND
    CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL 14)
  set_source_files_properties(CGHLSLMS.cpp
    PROPERTIES COMPILE_OPTIONS "-fno-tree-vrp")
endif()
```

This fixes all 45 test failures with no impact on other files.

## Minimal Reproducer

A standalone minimal reproducer is provided in [`docs/gcc14_vrp_bug.cpp`](gcc14_vrp_bug.cpp).
It triggers the same `bt` + `cmovnc` condition inversion with just two small
functions (~20 lines of logic):

```bash
g++-14 -O3 -o bug docs/gcc14_vrp_bug.cpp && ./bug    # FAIL
g++-14 -O3 -fno-tree-vrp -o ok docs/gcc14_vrp_bug.cpp && ./ok  # PASS
```

## Reproduction with DXC

### Prerequisites
- GCC 14.2.0 (`g++-14`)
- CMake, Ninja

### Steps
```bash
# Configure
cmake -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER=/usr/bin/g++-14 \
  -DCMAKE_C_COMPILER=/usr/bin/gcc-14 \
  -C cmake/caches/PredefinedParams.cmake \
  -DLLVM_ENABLE_ASSERTIONS=On \
  -B build-gcc14

# Build
ninja -C build-gcc14 -j$(nproc)

# Test (expect 45 failures)
ninja -C build-gcc14 check-clang
```

### Verify assembly
```bash
# Generate assembly for the miscompiled file:
# (use the actual compile command from build.ninja for CGHLSLMS.cpp,
#  adding -S -o /tmp/cghlslms.s)

# Search for the bitmask — should see cmovc with wrong operand order:
grep -A 5 '492738' /tmp/cghlslms.s
```

## GCC Bug

**[GCC Bug 119071](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=119071)**:
`[12/13/14/15 Regression] Miscompile at -O2 since r10-7268`

- Component: `rtl-optimization`
- Affected: GCC 10.1.0 through 15 (known to work in 9.5.0)
- Fixed in: GCC 12.5, 13.4, **14.3**, 15.0
- Related: [Bug 118739](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=118739)

## Related Issues

- GitHub Issue: https://github.com/microsoft/DirectXShaderCompiler/issues/7364
- The GCC 13 issue (loop unswitching, fixed with `-fno-unswitch-loops`) is a
  separate bug from this GCC 14 issue

## Investigation Timeline

1. Reproduced 45 test failures with GCC 14.2.0 Release build
2. Confirmed `-fno-strict-aliasing` does NOT fix (not aliasing UB)
3. Confirmed `-fno-tree-vrp` globally fixes all 45 failures
4. Identified miscompiled function: `SetUAVSRV` via `fprintf` instrumentation
5. Identified exact code: switch at lines 3464-3477 via `__builtin_return_address`
6. Confirmed single-file `-fno-tree-vrp` on CGHLSLMS.cpp fixes all failures
7. Compared assembly: found inverted `cmovc` operands as the root cause
