///////////////////////////////////////////////////////////////////////////////
//                                                                           //
// DxilAddPixelHitInstrumentation.cpp                                        //
// Copyright (C) Microsoft Corporation. All rights reserved.                 //
// This file is distributed under the University of Illinois Open Source     //
// License. See LICENSE.TXT for details.                                     //
//                                                                           //
// Provides a pass to add instrumentation to determine pixel hit count and   //
// cost. Used by PIX.                                                        //
//                                                                           //
///////////////////////////////////////////////////////////////////////////////

#include "dxc/DXIL/DxilOperations.h"

#include "dxc/DXIL/DxilInstructions.h"
#include "dxc/DXIL/DxilModule.h"
#include "dxc/DXIL/DxilUtil.h"
#include "dxc/DxilPIXPasses/DxilPIXPasses.h"
#include "dxc/HLSL/DxilGenerationPass.h"

#include "llvm/IR/PassManager.h"
#include "llvm/Transforms/Utils/Local.h"

#include "PixPassHelpers.h"

#include "dxc/Support/Global.h"
#include <winerror.h>

using namespace llvm;
using namespace hlsl;

class DxilAddPixelHitInstrumentation : public ModulePass {

  bool ForceEarlyZ = false;
  bool AddPixelCost = false;
  int RTWidth = 1024;
  int NumPixels = 128;

public:
  static char ID; // Pass identification, replacement for typeid
  explicit DxilAddPixelHitInstrumentation() : ModulePass(ID) {}
  StringRef getPassName() const override {
    return "DXIL Add Pixel Hit Instrumentation";
  }
  void applyOptions(PassOptions O) override;
  bool runOnModule(Module &M) override;
  unsigned m_preferredSVPositionRow = PIXPassHelpers::kUnknownSVPositionRow;
  PIXPassHelpers::SVPositionRowAuthority m_svPositionRowAuthority =
      PIXPassHelpers::SVPositionRowAuthority::Hint;
};

void DxilAddPixelHitInstrumentation::applyOptions(PassOptions O) {
  GetPassOptionBool(O, "force-early-z", &ForceEarlyZ, false);
  GetPassOptionBool(O, "add-pixel-cost", &AddPixelCost, false);

  // GetPassOptionInt leaves the destination untouched when the option
  // string is present but fails to parse as an integer (its return value,
  // which would reveal that, is conventionally left unchecked throughout
  // this pass options API). Seeding both destinations with an invalid
  // sentinel immediately before each call -- rather than relying on the
  // class member's own default, which a reused pass instance could have
  // already advanced past -- guarantees a malformed value can never
  // silently retain a stale, in-range size from a previous parse: it can
  // only retain 0, which the validation immediately below rejects.
  RTWidth = 0;
  GetPassOptionInt(O, "rt-width", &RTWidth, 0);
  NumPixels = 0;
  GetPassOptionInt(O, "num-pixels", &NumPixels, 0);

  // RTWidth and NumPixels size the counter UAV and convert SV_Position to a
  // byte offset into it. Reject a width or pixel count this pass cannot
  // represent -- zero, negative, or large enough that the pixel-cost half's
  // high water mark (NumPixels * 2 * 4 bytes) does not fit in 32 bits --
  // instead of emitting a shader whose offset arithmetic silently wraps.
  if (RTWidth <= 0 || NumPixels <= 0 ||
      static_cast<uint64_t>(NumPixels) * 2 * 4 > UINT32_MAX) {
    throw ::hlsl::Exception(
        E_FAIL, "PIX: the pixel-hit instrumentation was given a render "
                "target width or pixel count it cannot represent.");
  }

  // This option always sets a hint, never a required row: treating an
  // unverified row as required could evict a real interpolant based on a
  // guess.
  //
  // GetPassOptionUnsigned leaves the value untouched when the option is
  // present but unparseable, so seed the member before the call rather than
  // rely on the default argument.
  //
  // "upstream-sv-position-row" is the pre-rename spelling: old PIX versions
  // predate this rename and still send it, so it is kept as an accepted
  // alias indefinitely rather than only for a deprecation window. New
  // callers should prefer "preferred-sv-position-row"; if both are
  // supplied, the preferred spelling wins.
  m_preferredSVPositionRow = PIXPassHelpers::kUnknownSVPositionRow;
  if (!GetPassOptionUnsigned(O, "preferred-sv-position-row",
                             &m_preferredSVPositionRow,
                             PIXPassHelpers::kUnknownSVPositionRow)) {
    GetPassOptionUnsigned(O, "upstream-sv-position-row",
                          &m_preferredSVPositionRow,
                          PIXPassHelpers::kUnknownSVPositionRow);
  }
  m_svPositionRowAuthority = PIXPassHelpers::SVPositionRowAuthority::Hint;

  unsigned RequiredRow = PIXPassHelpers::kUnknownSVPositionRow;
  // GetPassOptionUnsigned's return value reports only whether the option
  // string was present, not whether it parsed: a malformed value (e.g.
  // non-numeric text) leaves RequiredRow at the seeded sentinel just as
  // surely as the option being absent altogether, and an explicit literal
  // UINT_MAX parses successfully to the exact same sentinel value. Treating
  // either case the same as "not specified" would silently downgrade an
  // explicit authoritative request to a hint, letting a caller who
  // deliberately (or accidentally) supplied an invalid required row bypass
  // the row>=32 rejection entirely, since that check only runs on the
  // authoritative path. So presence is tracked separately from the parsed
  // value, and any value that is invalid *while the option was present* --
  // the sentinel itself, or a row past the last real signature register --
  // is rejected outright rather than silently reinterpreted as absence.
  bool const RequiredRowSpecified =
      GetPassOptionUnsigned(O, "required-sv-position-row", &RequiredRow,
                            PIXPassHelpers::kUnknownSVPositionRow);
  if (RequiredRowSpecified) {
    if (RequiredRow == PIXPassHelpers::kUnknownSVPositionRow ||
        RequiredRow >= hlsl::DXIL::kMaxSignatureTotalVectors) {
      throw ::hlsl::Exception(
          E_FAIL, "PIX: the pixel-hit instrumentation was given an "
                  "invalid or unrepresentable required SV_Position row.");
    }
    m_preferredSVPositionRow = RequiredRow;
    m_svPositionRowAuthority =
        PIXPassHelpers::SVPositionRowAuthority::Authoritative;
  }
}

bool DxilAddPixelHitInstrumentation::runOnModule(Module &M) {
  // This pass adds instrumentation for pixel hit counting and pixel cost.

  DxilModule &DM = M.GetOrCreateDxilModule();
  LLVMContext &Ctx = M.getContext();
  OP *HlslOP = DM.GetOP();

  // ForceEarlyZ is incompatible with the discard function (the Z has to be
  // tested/written, and may be written before the shader even runs)
  if (ForceEarlyZ) {
    DM.m_ShaderFlags.SetForceEarlyDepthStencil(true);
  }

  unsigned SV_Position_ID = PIXPassHelpers::FindOrAddSV_Position(
      DM, m_preferredSVPositionRow, m_svPositionRowAuthority);

  llvm::Function *EntryPointFunction = PIXPassHelpers::GetEntryFunction(DM);

  CallInst *HandleForUAV;
  {
    IRBuilder<> Builder(dxilutil::FirstNonAllocaInsertionPt(
        PIXPassHelpers::GetEntryFunction(DM)));

    HandleForUAV = PIXPassHelpers::CreateUAVOnceForModule(
        DM, Builder, 0, "PIX_CountUAV_Handle");

    DM.ReEmitDxilResources();
  }
  // Every point where the shader completes must bump the counter. A
  // straight-line shader keeps its Ret in the entry block, but a shader with
  // a loop or branch ends the entry block early, so every basic block is
  // scanned for a Ret.
  llvm::SmallVector<llvm::Instruction *, 4> ReturnInstructions;
  bool FunctionHasWork = false;
  for (llvm::BasicBlock &ThisBlock : EntryPointFunction->getBasicBlockList()) {
    for (llvm::Instruction &ThisInstruction : ThisBlock) {
      LlvmInst_Ret Ret(&ThisInstruction);
      if (Ret) {
        ReturnInstructions.push_back(&ThisInstruction);
      } else if (!llvm::isa<llvm::TerminatorInst>(&ThisInstruction)) {
        FunctionHasWork = true;
      }
    }
  }

  bool Modified = false;

  for (llvm::Instruction *ThisInstruction : ReturnInstructions) {
    LlvmInst_Ret Ret(ThisInstruction);
    if (Ret) {
      // A function that contains nothing but terminators has no pixel work
      // worth counting.
      if (FunctionHasWork) {
        Modified = true;

        // Start adding instructions right before the Ret:
        IRBuilder<> Builder(ThisInstruction);

        // ------------------------------------------------------------------------------------------------------------
        // Generate instructions to increment (by one) a UAV value corresponding
        // to the pixel currently being rendered
        // ------------------------------------------------------------------------------------------------------------

        // Useful constants
        Constant *Zero32Arg = HlslOP->GetU32Const(0);
        Constant *Zero8Arg = HlslOP->GetI8Const(0);
        Constant *One32Arg = HlslOP->GetU32Const(1);
        Constant *One8Arg = HlslOP->GetI8Const(1);
        UndefValue *UndefArg = UndefValue::get(Type::getInt32Ty(Ctx));
        // Compute as uint32_t, not NumPixels' own int: applyOptions
        // guarantees NumPixels * 2 * 4 fits in 32 bits only for unsigned
        // arithmetic. The signed multiply would overflow int32 for a
        // NumPixels this pass accepts, which is undefined behavior on the
        // host, not just a wrapped value in the shader.
        Constant *NumPixelsByteOffsetArg =
            HlslOP->GetU32Const(static_cast<uint32_t>(NumPixels) * 4u);

        // Step 1: Convert SV_POSITION to UINT
        Value *XAsInt;
        Value *YAsInt;
        {
          Function *LoadInputOpFunc =
              HlslOP->GetOpFunc(DXIL::OpCode::LoadInput, Type::getFloatTy(Ctx));
          Constant *LoadInputOpcode =
              HlslOP->GetU32Const((unsigned)DXIL::OpCode::LoadInput);
          Constant *SV_Pos_ID = HlslOP->GetU32Const(SV_Position_ID);
          CallInst *XPos =
              Builder.CreateCall(LoadInputOpFunc,
                                 {LoadInputOpcode, SV_Pos_ID, Zero32Arg /*row*/,
                                  Zero8Arg /*column*/, UndefArg},
                                 "XPos");
          CallInst *YPos =
              Builder.CreateCall(LoadInputOpFunc,
                                 {LoadInputOpcode, SV_Pos_ID, Zero32Arg /*row*/,
                                  One8Arg /*column*/, UndefArg},
                                 "YPos");

          XAsInt = Builder.CreateCast(Instruction::CastOps::FPToUI, XPos,
                                      Type::getInt32Ty(Ctx), "XIndex");
          YAsInt = Builder.CreateCast(Instruction::CastOps::FPToUI, YPos,
                                      Type::getInt32Ty(Ctx), "YIndex");
        }

        // Step 2: Calculate pixel index
        Value *Index;
        {
          Constant *RTWidthArg =
              HlslOP->GetU32Const(static_cast<uint32_t>(RTWidth));
          Value *YOffset = Builder.CreateMul(YAsInt, RTWidthArg, "YOffset");
          Value *Elementoffset =
              Builder.CreateAdd(XAsInt, YOffset, "ElementOffset");

          // Y*RTWidth (and then +X) is computed in 32-bit arithmetic that
          // can itself wrap before any clamp ever inspects the result: for
          // example RTWidth=0x40000000 with Y=4 makes the true element
          // offset 0x100000000, which wraps to 0 in 32 bits --
          // indistinguishable from the shader's actual pixel (0, 0) -- so a
          // clamp applied only to the wrapped value cannot catch it. Detect
          // both the multiply and the add overflowing, in 32-bit arithmetic
          // only (no widening to i64, which would require the optional Int64Ops
          // shader capability this instrumentation should not have to
          // depend on), and saturate to the last valid element directly
          // whenever either one does, bypassing the (already wrapped)
          // computed value entirely.
          //
          // Unsigned multiply overflowed iff dividing the (possibly
          // wrapped) product back by one factor does not recover the
          // other factor. Guard the divisor against zero, for which no
          // multiply can overflow.
          Constant *One32Const = HlslOP->GetU32Const(1);
          Value *YIsZero = Builder.CreateICmpEQ(YAsInt, Zero32Arg, "YIsZero");
          Value *SafeDivisor = Builder.CreateSelect(YIsZero, One32Const, YAsInt,
                                                    "YOffsetSafeDivisor");
          Value *YOffsetQuotient =
              Builder.CreateUDiv(YOffset, SafeDivisor, "YOffsetQuotient");
          Value *MulOverflowed = Builder.CreateAnd(
              Builder.CreateNot(YIsZero, "YIsNonZero"),
              Builder.CreateICmpNE(YOffsetQuotient, RTWidthArg,
                                   "YOffsetQuotientMismatchesWidth"),
              "MulOverflowed");

          // Unsigned add overflowed iff the sum is less than either
          // operand.
          Value *AddOverflowed =
              Builder.CreateICmpULT(Elementoffset, XAsInt, "AddOverflowed");
          Value *AnyOverflow = Builder.CreateOr(MulOverflowed, AddOverflowed,
                                                "ElementOffsetOverflowed");

          // The viewport can be offset from the render target's origin, or
          // smaller than the counter buffer PIX sized for it, so
          // SV_Position's X and Y can land ElementOffset past the last valid
          // element. Clamp the element count before scaling to a byte
          // offset: applyOptions guarantees (NumPixels-1)*4 fits in uint32,
          // so the clamped multiply cannot wrap. Clamping after scaling
          // would let an oversized ElementOffset overflow the multiply
          // first.
          Function *UMinOpFunc =
              HlslOP->GetOpFunc(OP::OpCode::UMin, Type::getInt32Ty(Ctx));
          Constant *UMinOpcode =
              HlslOP->GetU32Const((unsigned)OP::OpCode::UMin);
          Constant *LastElementArg =
              HlslOP->GetU32Const(static_cast<uint32_t>(NumPixels) - 1);
          CallInst *ClampedElementOffsetInRange = Builder.CreateCall(
              UMinOpFunc, {UMinOpcode, Elementoffset, LastElementArg},
              "ClampedElementOffsetInRange");
          // When Y*RTWidth+X itself overflowed, Elementoffset is already
          // wrapped nonsense (possibly a small, in-range-looking value), so
          // the UMin above cannot be trusted: saturate straight to the last
          // valid element instead of clamping the wrapped value.
          Value *ClampedElementOffset = Builder.CreateSelect(
              AnyOverflow, LastElementArg, ClampedElementOffsetInRange,
              "ClampedElementOffset");
          Index = Builder.CreateMul(ClampedElementOffset,
                                    HlslOP->GetU32Const(4), "ByteIndex");
        }

        // Insert the UAV increment instruction:
        Function *AtomicOpFunc =
            HlslOP->GetOpFunc(OP::OpCode::AtomicBinOp, Type::getInt32Ty(Ctx));
        Constant *AtomicBinOpcode =
            HlslOP->GetU32Const((unsigned)OP::OpCode::AtomicBinOp);
        Constant *AtomicAdd =
            HlslOP->GetU32Const((unsigned)DXIL::AtomicBinOpCode::Add);
        {
          (void)Builder.CreateCall(
              AtomicOpFunc,
              {
                  AtomicBinOpcode, // i32, ; opcode
                  HandleForUAV,    // %dx.types.Handle, ; resource handle
                  AtomicAdd, // i32, ; binary operation code : EXCHANGE, IADD,
                             // AND, OR, XOR, IMIN, IMAX, UMIN, UMAX
                  Index,     // i32, ; coordinate c0: byte offset
                  UndefArg,  // i32, ; coordinate c1 (unused)
                  UndefArg,  // i32, ; coordinate c2 (unused)
                  One32Arg   // i32); increment value
              },
              "UAVIncResult");
        }

        if (AddPixelCost) {
          // ------------------------------------------------------------------------------------------------------------
          // Generate instructions to increment a value corresponding to the
          // current pixel in the second half of the UAV, by an amount
          // proportional to the estimated average cost of each pixel in the
          // current draw call.
          // ------------------------------------------------------------------------------------------------------------

          // Step 1: Retrieve weight value from UAV; it will be placed after the
          // range we're writing to
          Value *Weight;
          {
            Function *LoadWeight = HlslOP->GetOpFunc(OP::OpCode::BufferLoad,
                                                     Type::getInt32Ty(Ctx));
            Constant *LoadWeightOpcode =
                HlslOP->GetU32Const((unsigned)DXIL::OpCode::BufferLoad);
            Constant *OffsetIntoUAV =
                HlslOP->GetU32Const(static_cast<uint32_t>(NumPixels) * 2u * 4u);
            CallInst *WeightStruct = Builder.CreateCall(
                LoadWeight,
                {
                    LoadWeightOpcode, // i32 opcode
                    HandleForUAV,     // %dx.types.Handle, ; resource handle
                    OffsetIntoUAV,    // i32 c0: byte offset
                    UndefArg          // i32 c1: unused
                },
                "WeightStruct");
            Weight = Builder.CreateExtractValue(
                WeightStruct, static_cast<uint64_t>(0LL), "Weight");
          }

          // Step 2: Update write position ("Index") to second half of the UAV.
          // Index is already clamped to the first half, so this can only land
          // in the second half without a clamp of its own.
          Value *OffsetIndex = Builder.CreateAdd(Index, NumPixelsByteOffsetArg,
                                                 "OffsetByteIndex");

          // Step 3: Increment UAV value by the weight
          (void)Builder.CreateCall(
              AtomicOpFunc,
              {
                  AtomicBinOpcode, // i32, ; opcode
                  HandleForUAV,    // %dx.types.Handle, ; resource handle
                  AtomicAdd,   // i32, ; binary operation code : EXCHANGE, IADD,
                               // AND, OR, XOR, IMIN, IMAX, UMIN, UMAX
                  OffsetIndex, // i32, ; coordinate c0: byte offset
                  UndefArg,    // i32, ; coordinate c1 (unused)
                  UndefArg,    // i32, ; coordinate c2 (unused)
                  Weight       // i32); increment value
              },
              "UAVIncResult2");
        }
      }
    }
  }

  return Modified;
}

char DxilAddPixelHitInstrumentation::ID = 0;

ModulePass *llvm::createDxilAddPixelHitInstrumentationPass() {
  return new DxilAddPixelHitInstrumentation();
}

INITIALIZE_PASS(DxilAddPixelHitInstrumentation,
                "hlsl-dxil-add-pixel-hit-instrmentation",
                "DXIL Count completed PS invocations and costs", false, false)
