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
// signature worse: callers that have not opted in to the newer option spelling
// keep the semantics they were written against.
unsigned int
FindOrAddSV_Position(hlsl::DxilModule &DM, unsigned UpStreamSVPosRow,
                     SVPositionRowAuthority RowAuthority =
                         SVPositionRowAuthority::Hint);
void ForEachDynamicallyIndexedResource(
    hlsl::DxilModule &DM,
    const std::function<bool(bool, llvm::Instruction *, llvm::Value *)>
        &Visitor);
} // namespace PIXPassHelpers
