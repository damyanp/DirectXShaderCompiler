///////////////////////////////////////////////////////////////////////////////
//                                                                           //
// PixPassHelpers.h
// // Copyright (C) Microsoft Corporation. All rights reserved. // This file is
// distributed under the University of Illinois Open Source     // License. See
// LICENSE.TXT for details.                                     //
//                                                                           //
///////////////////////////////////////////////////////////////////////////////

#pragma once

#include <functional>
#include <vector>

#include "dxc/DXIL/DxilModule.h"
#include "llvm/IR/DebugInfoMetadata.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Instructions.h"

// #define PIX_DEBUG_DUMP_HELPER
#ifdef PIX_DEBUG_DUMP_HELPER
#include "dxc/Support/Global.h"
#endif

namespace PIXPassHelpers {

class ScopedInstruction {
  llvm::Instruction *m_Instruction;

public:
  ScopedInstruction(llvm::Instruction *I) : m_Instruction(I) {}
  ~ScopedInstruction() { delete m_Instruction; }
  llvm::Instruction *Get() const { return m_Instruction; }
};

void FindRayQueryHandlesForFunction(
    llvm::Function *F, llvm::SmallPtrSetImpl<llvm::Value *> &RayQueryHandles);
enum class PixUAVHandleMode { NonLib, Lib };
llvm::CallInst *CreateUAVOnceForModule(hlsl::DxilModule &DM,
                                       llvm::IRBuilder<> &Builder,
                                       unsigned int hlslBindIndex,
                                       const char *name);
hlsl::DxilResource *CreateGlobalUAVResource(hlsl::DxilModule &DM,
                                            unsigned int hlslBindIndex,
                                            const char *name);
llvm::CallInst *CreateHandleForResource(hlsl::DxilModule &DM,
                                        llvm::IRBuilder<> &Builder,
                                        hlsl::DxilResourceBase *resource,
                                        const char *name);
llvm::Function *GetEntryFunction(hlsl::DxilModule &DM);
void EraseIfUnused(hlsl::DxilModule &DM, llvm::Function *OpFunction);
std::vector<llvm::Function *>
GetAllInstrumentableFunctions(hlsl::DxilModule &DM);
// Inlines every function that is not one of the module's entry points into its
// callers, so a non-library module is left with nothing but the functions the
// runtime itself invokes.
//
// PIX identifies one shader invocation by one record stream in the debug UAV,
// and its trace reader maps that stream to exactly one function by instruction
// ordinal range. A [noinline] helper therefore cannot be instrumented as a
// function in its own right without appearing to PIX as a second, unrelated
// invocation of the same thread, whose records the reader then discards for not
// matching the invocation being debugged. Inlining the helper instead keeps one
// invocation per thread, and leaves the helper visible exactly where PIX
// already looks for it: the inlinedAt chain of the debug locations, which is
// how a helper the front end inlined of its own accord is presented today.
//
// This has to run before anything numbers instructions or synthesizes shadow
// storage, because the ordinals PIX steps through are assigned to the module
// this leaves behind, and because llvm::InlineFunction stamps the call site's
// debug location onto every inlined instruction that had none - which would
// move a helper's shadow stores to the line of the call. Both of the passes
// that can come first in a PIX pipeline therefore call it, and it is idempotent
// so that the second finds nothing left to do.
//
// Library modules are left alone: every function they export is an invocation
// in its own right, so there is no single entry point to inline into.
bool InlineNonEntryFunctions(hlsl::DxilModule &DM);
hlsl::DXIL::ShaderKind GetFunctionShaderKind(hlsl::DxilModule &DM,
                                             llvm::Function *fn);
#ifdef PIX_DEBUG_DUMP_HELPER
void Log(const char *format, ...);
void LogPartialLine(const char *format, ...);
void IncreaseLogIndent();
void DecreaseLogIndent();
void DumpFullType(llvm::DIType const *type);
#else
inline void DumpFullType(llvm::DIType const *) {}
inline void Log(const char *, ...) {}
inline void LogPartialLine(const char *format, ...) {}
inline void IncreaseLogIndent() {}
inline void DecreaseLogIndent() {}
#endif
class ScopedIndenter {
public:
  ScopedIndenter() { IncreaseLogIndent(); }
  ~ScopedIndenter() { DecreaseLogIndent(); }
};

struct ExpandedStruct {
  llvm::Type *ExpandedPayloadStructType = nullptr;
  llvm::Type *ExpandedPayloadStructPtrType = nullptr;
};

ExpandedStruct ExpandStructType(llvm::LLVMContext &Ctx,
                                llvm::Type *OriginalPayloadStructType);
void ReplaceAllUsesOfInstructionWithNewValueAndDeleteInstruction(
    llvm::Instruction *Instr, llvm::Value *newValue, llvm::Type *newType);
// Passed as UpStreamSVPosRow when the caller could not determine which row the
// previous stage put SV_Position on. See FindOrAddSV_Position.
constexpr unsigned kUnknownSVPositionRow = UINT_MAX;

// Says how much the caller of FindOrAddSV_Position knows about UpStreamSVPosRow.
//
// The two are not interchangeable and the difference cannot be inferred from the
// row value, so it has to be carried explicitly: PIX builds that predate the
// relocating behaviour send row 0 both for "the previous stage really uses row 0"
// and for "I could not read the previous stage", and acting on the second of
// those displaces an element that is genuinely bound to the upstream signature.
// Each pass therefore accepts two differently named options, and only the newer
// spelling promises the row was read off a real upstream signature.
enum class SVPositionRowAuthority {
  // The row may have been fabricated. SV_Position is placed there only if the
  // row is free; nothing already in the signature is moved.
  Hint,
  // The row is the register the previous stage really writes SV_Position to, so
  // SV_Position has to land there and any occupants are repacked elsewhere.
  Authoritative,
};

// Hint is the default because it is the behaviour that cannot make an existing
// signature worse: nothing already in the signature is moved.
//
// Note this is not bug-for-bug identical to the pre-relocation behaviour, and
// cannot be. That code placed SV_Position on the requested row unconditionally,
// overlapping whatever was already there and producing a signature the driver
// may reject outright. Hint instead leaves the occupant alone and places
// SV_Position on a free row, so an occupied row now yields a valid signature
// whose position register does not match the upstream stage, where it used to
// yield an invalid one. Both are wrong for a caller that needed the register to
// match; only the newer spelling can get that right, which is why it exists.
unsigned int
FindOrAddSV_Position(hlsl::DxilModule &DM, unsigned UpStreamSVPosRow,
                     SVPositionRowAuthority RowAuthority =
                         SVPositionRowAuthority::Hint);
void ForEachDynamicallyIndexedResource(
    hlsl::DxilModule &DM,
    const std::function<bool(bool, llvm::Instruction *, llvm::Value *)>
        &Visitor);
} // namespace PIXPassHelpers
