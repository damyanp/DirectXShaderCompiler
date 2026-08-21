// RUN: %dxc -Tcs_6_6 -enable-16bit-types -Emain /Od /Zi %s | %opt -S -dxil-dbg-value-to-dbg-declare | %FileCheck %s

// The same defect as DbgValueToDbgDeclare_mixed_width_bitfields.hlsl, with a 16-bit
// bitfield leading instead of a 32-bit one, because the 16-bit path reaches the
// alloca map through GetLLVMTypeFromDIBasicType's half-width cases.
//
// Small is a 5-bit field of a 16-bit unit and Wide a 20-bit field of a 32-bit unit,
// so dxcompiler declares them at bits 0 and 32. The walk used to place them at bits
// 0 and 5, and Wide's llvm.dbg.value - which refers to bit 32 - matched nothing at
// all, so Wide's store was skipped and its dbg.value erased anyway.

RWByteAddressBuffer RawUAV : register(u0);

struct HalfBitfield
{
    uint16_t Small : 5;
    uint32_t Wide : 20;
};

// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 0, 5)
// The second bitfield opens a new storage unit at bit 32, not at bit 5:
// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 32, 20)

// CHECK: store i16 %{{[0-9]+}}, i16*
// CHECK: store i32 %{{[0-9]+}}, i32*

[numthreads(1, 1, 1)]
void main()
{
    HalfBitfield bitfield;
    bitfield.Small = (uint16_t)RawUAV.Load(2 * 4);
    bitfield.Wide = RawUAV.Load(3 * 4);

    RawUAV.Store(0, bitfield.Small + bitfield.Wide);
}
