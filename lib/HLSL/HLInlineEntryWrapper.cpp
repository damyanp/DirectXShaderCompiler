///////////////////////////////////////////////////////////////////////////////
//                                                                           //
// HLInlineEntryWrapper.cpp                                                  //
// Copyright (C) Microsoft Corporation. All rights reserved.                 //
// This file is distributed under the University of Illinois Open Source     //
// License. See LICENSE.TXT for details.                                     //
//                                                                           //
///////////////////////////////////////////////////////////////////////////////

#include "dxc/DXIL/DxilShaderModel.h"
#include "dxc/HLSL/DxilGenerationPass.h"
#include "dxc/HLSL/HLModule.h"
#include "llvm/ADT/SetVector.h"
#include "llvm/ADT/SmallVector.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/Pass.h"
#include "llvm/Transforms/Utils/Cloning.h"

using namespace llvm;

namespace {

// The bottom-up inliner fully expands a callee before cloning it into its
// caller. For a callee with exactly one call site in the entry, that clone
// copies the whole expanded body only to delete the original. Inlining such
// callees top-down first lets their own callees be expanded once, directly in
// the entry.
Function *getSingleUseCallee(CallInst *CI, hlsl::HLModule &HLM) {
  Function *Callee = CI->getCalledFunction();
  if (!Callee || Callee->isDeclaration() || !Callee->hasLocalLinkage() ||
      !Callee->hasOneUse() ||
      !Callee->hasFnAttribute(Attribute::AlwaysInline) ||
      Callee->hasFnAttribute(Attribute::NoInline) || CI->isNoInline() ||
      Callee->isVarArg() || Callee->hasPersonalityFn() ||
      Callee->getCallingConv() != CallingConv::C ||
      CI->getCallingConv() != CallingConv::C || CI->isMustTailCall() ||
      CI->canReturnTwice() || HLM.IsEntry(Callee) ||
      Callee == CI->getParent()->getParent())
    return nullptr;
  return Callee;
}

class HLInlineEntryWrapper : public ModulePass {
  bool InsertLifetime;

public:
  static char ID;
  explicit HLInlineEntryWrapper(bool InsertLifetime = false)
      : ModulePass(ID), InsertLifetime(InsertLifetime) {}

  bool runOnModule(Module &M) override {
    if (!M.HasHLModule())
      return false;
    hlsl::HLModule &HLM = M.GetHLModule();
    if (!HLM.GetShaderModel() || HLM.GetShaderModel()->IsLib() ||
        HLM.GetHLOptions().bDisableOptimizations)
      return false;
    Function *Entry = HLM.GetEntryFunction();
    if (!Entry || Entry->isDeclaration())
      return false;

    SmallVector<WeakTrackingVH, 16> Worklist;
    for (BasicBlock &BB : *Entry)
      for (Instruction &I : BB)
        if (CallInst *CI = dyn_cast<CallInst>(&I))
          if (getSingleUseCallee(CI, HLM))
            Worklist.push_back(CI);

    bool Changed = false;
    // Visit calls in program order, as the bottom-up inliner does, so hoisted
    // static allocas keep the same relative order.
    for (unsigned Next = 0; Next < Worklist.size(); ++Next) {
      CallInst *CI = dyn_cast_or_null<CallInst>(Worklist[Next]);
      if (!CI)
        continue;
      Function *Callee = getSingleUseCallee(CI, HLM);
      if (!Callee)
        continue;
      // InlineFunction only reports inlined calls when given a call graph, so
      // find the callee's own callees and revisit those left with one use.
      SmallSetVector<Function *, 8> Nested;
      for (BasicBlock &BB : *Callee)
        for (Instruction &I : BB)
          if (CallInst *Nest = dyn_cast<CallInst>(&I))
            if (Function *F = Nest->getCalledFunction())
              if (!F->isDeclaration())
                Nested.insert(F);
      InlineFunctionInfo IFI;
      if (!InlineFunction(CI, IFI, InsertLifetime))
        continue;
      Changed = true;
      HLM.RemoveFunction(Callee);
      Callee->eraseFromParent();
      for (Function *F : Nested)
        if (F->hasOneUse())
          if (CallInst *Inlined = dyn_cast<CallInst>(F->user_back()))
            if (Inlined->getCalledFunction() == F &&
                Inlined->getParent()->getParent() == Entry &&
                getSingleUseCallee(Inlined, HLM))
              Worklist.push_back(Inlined);
    }
    return Changed;
  }
};

} // namespace

char HLInlineEntryWrapper::ID = 0;
ModulePass *llvm::createHLInlineEntryWrapperPass(bool InsertLifetime) {
  return new HLInlineEntryWrapper(InsertLifetime);
}

INITIALIZE_PASS(HLInlineEntryWrapper, "hl-inline-entry-wrapper",
                "Inline single-use HLSL entry callees top-down", false, false)
