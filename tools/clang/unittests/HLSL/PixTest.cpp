///////////////////////////////////////////////////////////////////////////////
//                                                                           //
// PixTest.cpp                                                               //
// Copyright (C) Microsoft Corporation. All rights reserved.                 //
// This file is distributed under the University of Illinois Open Source     //
// License. See LICENSE.TXT for details.                                     //
//                                                                           //
// Provides tests for the PIX-specific components                            //
//                                                                           //
///////////////////////////////////////////////////////////////////////////////

#ifndef UNICODE
#define UNICODE
#endif

#include <algorithm>
#include <array>
#include <cassert>
#include <cctype>
#include <cfloat>
#include <cstring>
#include <functional>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#include "dxc/DxilContainer/DxilContainer.h"
#include "dxc/DxilContainer/DxilRuntimeReflection.h"
#include "dxc/DxilRootSignature/DxilRootSignature.h"
#include "dxc/Support/WinIncludes.h"
#include "dxc/dxcapi.h"
#include "dxc/dxcpix.h"
#ifdef _WIN32
#include <atlfile.h>
#endif

#include "dxc/DXIL/DxilConstants.h"
#include "dxc/DXIL/DxilModule.h"
#include "dxc/DXIL/DxilOperations.h"
#include "dxc/DXIL/DxilSubobject.h"

#include "dxc/Test/DxcTestUtils.h"
#include "dxc/Test/HLSLTestData.h"
#include "dxc/Test/HlslTestUtils.h"

#include "dxc/DXIL/DxilUtil.h"
#include "dxc/Support/Global.h"
#include "dxc/Support/HLSLOptions.h"
#include "dxc/Support/Unicode.h"
#include "dxc/Support/dxcapi.use.h"
#include "dxc/Support/microcom.h"

#include "llvm/ADT/STLExtras.h"
#include "llvm/ADT/SmallString.h"
#include "llvm/ADT/SmallVector.h"
#include "llvm/ADT/StringSwitch.h"
#include "llvm/Bitcode/ReaderWriter.h"
#include "llvm/IR/DebugInfo.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/IntrinsicInst.h"
#include "llvm/IR/Intrinsics.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Metadata.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/ModuleSlotTracker.h"
#include "llvm/IR/Operator.h"
#include "llvm/Support/FileSystem.h"
#include "llvm/Support/MSFileSystem.h"
#include "llvm/Support/MemoryBuffer.h"
#include "llvm/Support/Path.h"
#include "llvm/Support/raw_ostream.h"
#include <fstream>

#include <../lib/DxilDia/DxcPixLiveVariables_FragmentIterator.h>
#include <../lib/DxilPIXPasses/PixPassHelpers.h>
#include <dxc/DxilPIXPasses/DxilPIXPasses.h>
#include <dxc/DxilPIXPasses/DxilPIXVirtualRegisters.h>

#include "PixTestUtils.h"

using namespace std;
using namespace hlsl;
using namespace hlsl_test;
using namespace pix_test;

static std::vector<std::string> Tokenize(const std::string &str,
                                         const char *delimiters) {
  std::vector<std::string> tokens;
  std::string copy = str;

  for (auto i = strtok(&copy[0], delimiters); i != nullptr;
       i = strtok(nullptr, delimiters)) {
    tokens.push_back(i);
  }

  return tokens;
}

#ifdef _WIN32
class PixTest {
#else
class PixTest : public ::testing::Test {
#endif
public:
  BEGIN_TEST_CLASS(PixTest)
  TEST_CLASS_PROPERTY(L"Parallel", L"true")
  TEST_METHOD_PROPERTY(L"Priority", L"0")
  END_TEST_CLASS()

  TEST_CLASS_SETUP(InitSupport);

  TEST_METHOD(DebugUAV_CS_6_1)
  TEST_METHOD(DebugUAV_CS_6_2)
  TEST_METHOD(DebugUAV_lib_6_3_through_6_8)

  TEST_METHOD(CompileDebugDisasmPDB)

  TEST_METHOD(AddToASPayload)
  TEST_METHOD(AddToASGroupSharedPayload)
  TEST_METHOD(AddToASGroupSharedPayload_MeshletCullSample)
  TEST_METHOD(SignatureModification_Empty)
  TEST_METHOD(SignatureModification_VertexIdAlready)
  TEST_METHOD(SignatureModification_SomethingElseFirst)

  TEST_METHOD(AccessTracking_ModificationReport_Nothing)
  TEST_METHOD(AccessTracking_ModificationReport_Read)
  TEST_METHOD(AccessTracking_ModificationReport_Write)
  TEST_METHOD(AccessTracking_ModificationReport_SM66)

  TEST_METHOD(PixStructAnnotation_Lib_DualRaygen)

  TEST_METHOD(PixStructAnnotation_Simple)
  TEST_METHOD(PixStructAnnotation_CopiedStruct)
  TEST_METHOD(PixStructAnnotation_MixedSizes)
  TEST_METHOD(PixStructAnnotation_StructWithinStruct)
  TEST_METHOD(PixStructAnnotation_1DArray)
  TEST_METHOD(PixStructAnnotation_2DArray)
  TEST_METHOD(PixStructAnnotation_EmbeddedArray)
  TEST_METHOD(PixStructAnnotation_FloatN)
  TEST_METHOD(PixStructAnnotation_SequentialFloatN)
  TEST_METHOD(PixStructAnnotation_EmbeddedFloatN)
  TEST_METHOD(PixStructAnnotation_Matrix)
  TEST_METHOD(PixStructAnnotation_MemberFunction)
  TEST_METHOD(PixStructAnnotation_BigMess)
  TEST_METHOD(PixStructAnnotation_AlignedFloat4Arrays)
  TEST_METHOD(PixStructAnnotation_Inheritance)
  TEST_METHOD(PixStructAnnotation_ResourceAsMember)
  TEST_METHOD(PixStructAnnotation_WheresMyDbgValue)

  TEST_METHOD(VirtualRegisters_InstructionCounts)
  TEST_METHOD(VirtualRegisters_AlignedOffsets)

  TEST_METHOD(RootSignatureUpgrade_SubObjects)
  TEST_METHOD(RootSignatureUpgrade_Annotation)
  TEST_METHOD(ToolsUav_TwoPixPassesShareOneResource)
  TEST_METHOD(ToolsUav_LibraryWithTwoEntryPointsCreatesOnePair)
  TEST_METHOD(ToolsUav_ExtendsEveryGlobalRootSignatureSubobject)
  TEST_METHOD(DebugInstrumentation_RawBufferShaderFlagDeclared)
  TEST_METHOD(ToolsUav_RootSignatureSerializationFailurePreservesSignature)
  TEST_METHOD(ToolsUav_PreservesUnrelatedRootDescriptorFlagsWhenAlreadyPresent)
  TEST_METHOD(ToolsUav_BudgetOneUAVSucceedsAtExactly64Dwords)
  TEST_METHOD(ToolsUav_BudgetOneUAVRejectsWhenAlreadyAt64Dwords)
  TEST_METHOD(ToolsUav_BudgetOneUAVRejectsAt63PlusTwoDwords)
  TEST_METHOD(ToolsUav_BudgetTwoUAVsSucceedsAtExactly64Dwords)
  TEST_METHOD(ToolsUav_BudgetTwoUAVsRejectsAtomically)
  TEST_METHOD(
      ToolsUav_BudgetRejectionAcrossMultipleGlobalRootSignaturesIsAtomic)
  TEST_METHOD(ToolsUav_DuplicateNewRequestsNoRootSignatureAreDeduped)
  TEST_METHOD(ToolsUav_DuplicateNewRequestsWithRootSignatureAreDeduped)
  TEST_METHOD(ToolsUav_DuplicateRequestsForExistingResourceAreIdempotent)
  TEST_METHOD(ToolsUav_OptimizerPassRejectsOverBudgetRootSignature)
  TEST_METHOD(ConstantColor_UnusedIntOverloadIsErased)
  TEST_METHOD(ConstantColor_NoTargetOverloadsAreErased)
  TEST_METHOD(RemoveDiscards_UnusedDiscardOverloadIsErased)
  TEST_METHOD(OperationCacheCleanup_RemovesErasedFunctions)
  TEST_METHOD(DynamicResourceCleanup_VisitorStopsEarly)

  TEST_METHOD(DxilPIXDXRInvocationsLog_SanityTest)
  TEST_METHOD(DxilPIXDXRInvocationsLog_EmbeddedRootSigs)
  TEST_METHOD(DxilPIXDXRInvocationsLog_ZeroCapacityEmitsNothing)
  TEST_METHOD(DxilPIXDXRInvocationsLog_OneEntryUsesEntryCountBound)
  TEST_METHOD(DxilPIXDXRInvocationsLog_ExactCapacityUsesEntryCountBound)
  TEST_METHOD(DxilPIXDXRInvocationsLog_OverflowGuardValidates)
  TEST_METHOD(
      DxilPIXDXRInvocationsLog_EntryCountCheckRejectsLongerBoundWithSamePrefix)

  TEST_METHOD(DebugInstrumentation_TextOutput)
  TEST_METHOD(DebugInstrumentation_BlockReport)

  TEST_METHOD(DebugInstrumentation_VectorAllocaWrite_Structs)

  TEST_METHOD(DebugBreakInstrumentation_Basic)
  TEST_METHOD(DebugBreakInstrumentation_NoDebugBreak)
  TEST_METHOD(DebugBreakInstrumentation_Multiple)

  TEST_METHOD(NonUniformResourceIndex_Resource)
  TEST_METHOD(
      NonUniformResourceIndex_MissingInstructionNumberPreservesRootSignature)
  TEST_METHOD(NonUniformResourceIndex_QualifiedCleanupValidates)
  TEST_METHOD(NonUniformResourceIndex_DescriptorHeap)
  TEST_METHOD(NonUniformResourceIndex_Raytracing)

  // Control tests for the PIX pass validation harness below
  // (ValidateInstrumentedModule / VerifyInstrumentedModuleIsValid).
  TEST_METHOD(Validation_ControlValidModulePasses)
  TEST_METHOD(Validation_ControlAlreadyValidModuleFastPath)
  TEST_METHOD(Validation_ControlInvalidModuleFails)
  TEST_METHOD(Validation_ControlNonPixUnusedMetadataIsRejected)
  TEST_METHOD(Validation_ControlBoilerplateOnlyFailureIsRejected)
  TEST_METHOD(Validation_ControlDiagnosticsArePreservedHelper)
  TEST_METHOD(Validation_ControlCanonicalPartMetadataDivergenceIsRejected)
  TEST_METHOD(Validation_ControlCanonicalKnownPixMetadataIsAccepted)
  TEST_METHOD(Validation_ControlCanonicalMixedForeignMetadataIsRejected)
  TEST_METHOD(Validation_NonUniformResourceIndex_WaveOpsFlag)

  dxc::DxCompilerDllLoader m_dllSupport;
  VersionSupportInfo m_ver;

  HRESULT CreateContainerBuilder(IDxcContainerBuilder **ppResult) {
    return m_dllSupport.CreateInstance(CLSID_DxcContainerBuilder, ppResult);
  }

  std::string GetOption(std::string &cmd, char *opt) {
    std::string option = cmd.substr(cmd.find(opt));
    option = option.substr(option.find_first_of(' '));
    option = option.substr(option.find_first_not_of(' '));
    return option.substr(0, option.find_first_of(' '));
  }

  CComPtr<IDxcBlob> ExtractDxilPart(IDxcBlob *pProgram) {
    CComPtr<IDxcLibrary> pLib;
    VERIFY_SUCCEEDED(m_dllSupport.CreateInstance(CLSID_DxcLibrary, &pLib));
    const hlsl::DxilContainerHeader *pContainer = hlsl::IsDxilContainerLike(
        pProgram->GetBufferPointer(), pProgram->GetBufferSize());
    VERIFY_IS_NOT_NULL(pContainer);
    hlsl::DxilPartIterator partIter =
        std::find_if(hlsl::begin(pContainer), hlsl::end(pContainer),
                     hlsl::DxilPartIsType(hlsl::DFCC_DXIL));
    const hlsl::DxilProgramHeader *pProgramHeader =
        (const hlsl::DxilProgramHeader *)hlsl::GetDxilPartData(*partIter);
    uint32_t bitcodeLength;
    const char *pBitcode;
    CComPtr<IDxcBlob> pDxilBits;
    hlsl::GetDxilProgramBitcode(pProgramHeader, &pBitcode, &bitcodeLength);
    VERIFY_SUCCEEDED(pLib->CreateBlobFromBlob(
        pProgram, pBitcode - (char *)pProgram->GetBufferPointer(),
        bitcodeLength, &pDxilBits));
    return pDxilBits;
  }

  PassOutput RunValueToDeclarePass(IDxcBlob *dxil, int startingLineNumber = 0) {
    CComPtr<IDxcOptimizer> pOptimizer;
    VERIFY_SUCCEEDED(
        m_dllSupport.CreateInstance(CLSID_DxcOptimizer, &pOptimizer));
    std::vector<LPCWSTR> Options;
    Options.push_back(L"-opt-mod-passes");
    Options.push_back(L"-dxil-dbg-value-to-dbg-declare");

    CComPtr<IDxcBlob> pOptimizedModule;
    CComPtr<IDxcBlobEncoding> pText;
    VERIFY_SUCCEEDED(pOptimizer->RunOptimizer(
        dxil, Options.data(), Options.size(), &pOptimizedModule, &pText));

    std::string outputText;
    if (pText->GetBufferSize() != 0) {
      outputText = reinterpret_cast<const char *>(pText->GetBufferPointer());
    }

    return {
        std::move(pOptimizedModule), {}, Tokenize(outputText.c_str(), "\n")};
  }

  PassOutput RunDebugPass(IDxcBlob *dxil, int UAVSize = 1024 * 1024) {
    CComPtr<IDxcOptimizer> pOptimizer;
    VERIFY_SUCCEEDED(
        m_dllSupport.CreateInstance(CLSID_DxcOptimizer, &pOptimizer));
    std::vector<LPCWSTR> Options;
    Options.push_back(L"-opt-mod-passes");
    Options.push_back(L"-dxil-dbg-value-to-dbg-declare");
    Options.push_back(L"-dxil-annotate-with-virtual-regs");
    std::wstring debugArg =
        L"-hlsl-dxil-debug-instrumentation,UAVSize=" + std::to_wstring(UAVSize);
    Options.push_back(debugArg.c_str());
    Options.push_back(L"-viewid-state");
    Options.push_back(L"-hlsl-dxilemit");

    CComPtr<IDxcBlob> pOptimizedModule;
    CComPtr<IDxcBlobEncoding> pText;
    VERIFY_SUCCEEDED(pOptimizer->RunOptimizer(
        dxil, Options.data(), Options.size(), &pOptimizedModule, &pText));

    std::string outputText = BlobToUtf8(pText);

    return {
        std::move(pOptimizedModule), {}, Tokenize(outputText.c_str(), "\n")};
  }

  PassOutput RunDebugBreakPass(IDxcBlob *dxil) {
    CComPtr<IDxcOptimizer> pOptimizer;
    VERIFY_SUCCEEDED(
        m_dllSupport.CreateInstance(CLSID_DxcOptimizer, &pOptimizer));
    std::vector<LPCWSTR> Options;
    Options.push_back(L"-opt-mod-passes");
    Options.push_back(L"-dxil-annotate-with-virtual-regs");
    Options.push_back(L"-hlsl-dxil-debugbreak-instrumentation");
    Options.push_back(L"-hlsl-dxilemit");

    CComPtr<IDxcBlob> pOptimizedModule;
    CComPtr<IDxcBlobEncoding> pText;
    VERIFY_SUCCEEDED(pOptimizer->RunOptimizer(
        dxil, Options.data(), Options.size(), &pOptimizedModule, &pText));

    std::string outputText = BlobToUtf8(pText);

    return {
        std::move(pOptimizedModule), {}, Tokenize(outputText.c_str(), "\n")};
  }

  // Runs one named PIX or DXIL pass and returns the resulting module and
  // its disassembly lines.
  struct SinglePassOutput {
    CComPtr<IDxcBlob> Module;
    std::vector<std::string> Lines;
  };

  SinglePassOutput RunSinglePass(IDxcBlob *dxil, LPCWSTR passOption) {
    CComPtr<IDxcOptimizer> pOptimizer;
    VERIFY_SUCCEEDED(
        m_dllSupport.CreateInstance(CLSID_DxcOptimizer, &pOptimizer));
    std::vector<LPCWSTR> Options;
    Options.push_back(L"-opt-mod-passes");
    Options.push_back(passOption);
    Options.push_back(L"-hlsl-dxilemit");

    CComPtr<IDxcBlob> pOptimizedModule;
    CComPtr<IDxcBlobEncoding> pText;
    VERIFY_SUCCEEDED(pOptimizer->RunOptimizer(
        dxil, Options.data(), Options.size(), &pOptimizedModule, &pText));

    SinglePassOutput ret;
    ret.Module = pOptimizedModule;
    ret.Lines = Tokenize(BlobToUtf8(pText).c_str(), "\n");
    return ret;
  }

  // PIX does not validate the shaders its passes instrument, so a pass
  // that produces invalid DXIL goes undetected elsewhere. Validate here
  // instead.
  struct ValidationResult {
    bool Valid;
    std::string Errors;
  };

  // Some pass runners return a bare bitcode module; others already return
  // a container. The validator (and the assembler used to reconstruct a
  // container from bare bitcode) both need a container.
  CComPtr<IDxcBlob> NormalizeToContainer(IDxcBlob *pModule) {
    if (hlsl::IsDxilContainerLike(pModule->GetBufferPointer(),
                                  pModule->GetBufferSize()) != nullptr) {
      return pModule;
    }
    return pix_test::WrapInNewContainer(m_dllSupport, pModule);
  }

  ValidationResult RunValidator(IDxcBlob *pContainer) {
    CComPtr<IDxcValidator> pValidator;
    VERIFY_SUCCEEDED(
        m_dllSupport.CreateInstance(CLSID_DxcValidator, &pValidator));

    CComPtr<IDxcOperationResult> pValidationResult;
    VERIFY_SUCCEEDED(pValidator->Validate(pContainer, DxcValidatorFlags_Default,
                                          &pValidationResult));

    HRESULT validationStatus;
    VERIFY_SUCCEEDED(pValidationResult->GetStatus(&validationStatus));
    if (SUCCEEDED(validationStatus)) {
      return {true, {}};
    }

    CComPtr<IDxcBlobEncoding> pValidationErrors;
    VERIFY_SUCCEEDED(pValidationResult->GetErrorBuffer(&pValidationErrors));
    return {false, BlobToUtf8(pValidationErrors)};
  }

  // The four metadata kinds that PIX's virtual-register annotation pass
  // intentionally leaves unused for downstream tools to consume. See
  // DxilPIXVirtualRegisters.h.
  static constexpr const char *KnownPixVirtualRegisterMetadataKinds[] = {
      pix_dxil::PixDxilInstNum::MDName, pix_dxil::PixDxilReg::MDName,
      pix_dxil::PixAllocaReg::MDName, pix_dxil::PixAllocaRegWrite::MDName};

  // Structurally removes only the four known PIX virtual-register metadata
  // kinds from every function and instruction in the module. Used to build
  // an isolated copy that should validate cleanly if the only unused
  // metadata in the original was PIX's own.
  void StripKnownPixVirtualRegisterMetadata(llvm::Module &M) {
    llvm::LLVMContext &Ctx = M.getContext();
    for (const char *kind : KnownPixVirtualRegisterMetadataKinds) {
      unsigned kindID = Ctx.getMDKindID(kind);
      for (llvm::Function &F : M) {
        F.setMetadata(kindID, nullptr);
        for (llvm::BasicBlock &BB : F) {
          for (llvm::Instruction &I : BB) {
            I.setMetadata(kindID, nullptr);
          }
        }
      }
    }
  }

  // Parses pModule into an isolated, owned LLVM module, applies Mutate to
  // it, and re-serializes the result into a fresh validator-ready
  // container. The caller's original blob is untouched.
  //
  // partKind selects which part of a full container to parse (see
  // ModuleAndHangersOn); it defaults to DFCC_ShaderDebugInfoDXIL, preserving
  // every existing caller's behavior. ValidateInstrumentedModule's fallback
  // passes DFCC_DXIL explicitly so it parses the exact same canonical part
  // RunValidator validated, rather than a debug-info-carrying copy that can
  // diverge in content that survives debug-info stripping (see
  // SerializeDxilContainerForModule).
  CComPtr<IDxcBlob>
  CloneModuleAndMutate(IDxcBlob *pModule,
                       std::function<void(llvm::Module &)> Mutate,
                       hlsl::DxilFourCC partKind = DFCC_ShaderDebugInfoDXIL) {
    CComPtr<IDxcBlob> pContainer = NormalizeToContainer(pModule);
    ModuleAndHangersOn moduleEtc(pContainer, partKind);
    llvm::Module *M = moduleEtc.GetDxilModule().GetModule();
    Mutate(*M);

    llvm::SmallVector<char, 0> bitcode;
    {
      llvm::raw_svector_ostream OS(bitcode);
      llvm::WriteBitcodeToFile(M, OS);
    }

    CComPtr<IDxcLibrary> pLibrary;
    VERIFY_SUCCEEDED(m_dllSupport.CreateInstance(CLSID_DxcLibrary, &pLibrary));
    CComPtr<IDxcBlobEncoding> pBitcodeBlob;
    VERIFY_SUCCEEDED(pLibrary->CreateBlobWithEncodingFromPinned(
        bitcode.data(), static_cast<UINT32>(bitcode.size()), CP_ACP,
        &pBitcodeBlob));

    return pix_test::WrapInNewContainer(m_dllSupport, pBitcodeBlob);
  }

  // Extracts the raw bytes of a single container part exactly as stored
  // (DxilProgramHeader-wrapped for a program part), for copying into
  // another container via IDxcContainerBuilder::AddPart.
  CComPtr<IDxcBlob> ExtractPartContent(hlsl::DxilFourCC fourCC,
                                       IDxcBlob *pContainer) {
    CComPtr<IDxcContainerReflection> pReflection;
    VERIFY_SUCCEEDED(m_dllSupport.CreateInstance(CLSID_DxcContainerReflection,
                                                 &pReflection));
    VERIFY_SUCCEEDED(pReflection->Load(pContainer));
    UINT32 partIndex;
    VERIFY_SUCCEEDED(pReflection->FindFirstPartKind(fourCC, &partIndex));
    CComPtr<IDxcBlob> pPart;
    VERIFY_SUCCEEDED(pReflection->GetPartContent(partIndex, &pPart));
    return pPart;
  }

  // Builds a container whose DFCC_DXIL part is exactly pCanonicalContainer's
  // own (untouched -- IDxcContainerBuilder cannot replace DFCC_DXIL, only
  // DFCC_ShaderDebugInfoDXIL and a few auxiliary parts), but whose
  // DFCC_ShaderDebugInfoDXIL part is replaced with pIldbPartContent (already
  // DxilProgramHeader-wrapped part content, e.g. from ExtractPartContent).
  // Used to construct a container whose canonical and debug-info-carrying
  // parts deliberately diverge, to prove ValidateInstrumentedModule
  // validates only the canonical part.
  CComPtr<IDxcBlob>
  BuildContainerWithDivergentIldbPart(IDxcBlob *pCanonicalContainer,
                                      IDxcBlob *pIldbPartContent) {
    CComPtr<IDxcContainerBuilder> pContainerBuilder;
    VERIFY_SUCCEEDED(CreateContainerBuilder(&pContainerBuilder));
    VERIFY_SUCCEEDED(pContainerBuilder->Load(pCanonicalContainer));
    // pCanonicalContainer always has a DFCC_ShaderDebugInfoDXIL part of its
    // own (WrapInNewContainer/SerializeDxilContainerForModule always
    // produces one alongside DFCC_DXIL when debug info is present, which it
    // always is here -- see PixTestUtils.cpp's unconditional
    // /Zi /Qembed_debug args); remove it before adding the replacement.
    VERIFY_SUCCEEDED(pContainerBuilder->RemovePart(DFCC_ShaderDebugInfoDXIL));
    VERIFY_SUCCEEDED(
        pContainerBuilder->AddPart(DFCC_ShaderDebugInfoDXIL, pIldbPartContent));

    CComPtr<IDxcOperationResult> pBuildResult;
    VERIFY_SUCCEEDED(pContainerBuilder->SerializeContainer(&pBuildResult));
    CComPtr<IDxcBlobEncoding> pBuildErrors;
    VERIFY_SUCCEEDED(pBuildResult->GetErrorBuffer(&pBuildErrors));
    if (pBuildErrors && pBuildErrors->GetBufferSize() != 0) {
      OutputDebugStringA(static_cast<LPCSTR>(pBuildErrors->GetBufferPointer()));
      VERIFY_SUCCEEDED(E_FAIL);
    }
    CComPtr<IDxcBlob> pNewContainer;
    VERIFY_SUCCEEDED(pBuildResult->GetResult(&pNewContainer));
    return pNewContainer;
  }

  // Wraps rootSigBytes (already-serialized root-signature bytes, e.g. from
  // BuildFillerRootSignatureBytes) into an IDxcBlob and adds it to
  // pContainer as a DFCC_RootSignature part -- the container-level
  // representation IDxcOptimizer::RunOptimizer actually restores a root
  // signature from (see DxcOptimizer.cpp's "RST0" handling), unlike a
  // DxilModule::ResetSerializedRootSignature call alone, which only takes
  // effect for callers sharing that same in-memory DxilModule and is lost
  // across a bitcode-only serialize/reload round-trip.
  CComPtr<IDxcBlob>
  AddRootSignaturePart(IDxcBlob *pContainer,
                       std::vector<uint8_t> const &rootSigBytes) {
    CComPtr<IDxcLibrary> pLibrary;
    VERIFY_SUCCEEDED(m_dllSupport.CreateInstance(CLSID_DxcLibrary, &pLibrary));
    CComPtr<IDxcBlobEncoding> pRootSigBlob;
    VERIFY_SUCCEEDED(pLibrary->CreateBlobWithEncodingFromPinned(
        rootSigBytes.data(), static_cast<UINT32>(rootSigBytes.size()), CP_ACP,
        &pRootSigBlob));

    CComPtr<IDxcContainerBuilder> pContainerBuilder;
    VERIFY_SUCCEEDED(CreateContainerBuilder(&pContainerBuilder));
    VERIFY_SUCCEEDED(pContainerBuilder->Load(pContainer));
    VERIFY_SUCCEEDED(
        pContainerBuilder->AddPart(DFCC_RootSignature, pRootSigBlob));

    CComPtr<IDxcOperationResult> pBuildResult;
    VERIFY_SUCCEEDED(pContainerBuilder->SerializeContainer(&pBuildResult));
    CComPtr<IDxcBlobEncoding> pBuildErrors;
    VERIFY_SUCCEEDED(pBuildResult->GetErrorBuffer(&pBuildErrors));
    if (pBuildErrors && pBuildErrors->GetBufferSize() != 0) {
      OutputDebugStringA(static_cast<LPCSTR>(pBuildErrors->GetBufferPointer()));
      VERIFY_SUCCEEDED(E_FAIL);
    }
    CComPtr<IDxcBlob> pNewContainer2;
    VERIFY_SUCCEEDED(pBuildResult->GetResult(&pNewContainer2));
    return pNewContainer2;
  }

  // ValidateInstrumentedModule's fallback needs an embedded canonical DXIL
  // part to parse the module (see ModuleAndHangersOn / CloneModuleAndMutate,
  // both now targeting DFCC_DXIL for this pipeline). Check safely first (the
  // same find-the-part pattern ModuleAndHangersOn uses, without the assert)
  // so a container that legitimately lacks one does not abort the whole
  // test; the caller falls back to the original direct validation result.
  // DFCC_DXIL is the same part RunValidator's "direct" validation targets,
  // so this also covers every bare-bitcode-normalized container (see
  // NormalizeToContainer / WrapInNewContainer), which always has DFCC_DXIL.
  bool HasCanonicalDxilPart(IDxcBlob *pContainer) {
    const DxilContainerHeader *pHeader = IsDxilContainerLike(
        pContainer->GetBufferPointer(), pContainer->GetBufferSize());
    if (pHeader == nullptr) {
      return false;
    }
    if (!IsValidDxilContainer(pHeader, pContainer->GetBufferSize())) {
      return false;
    }
    DxilPartIterator it =
        std::find_if(begin(pHeader), end(pHeader), DxilPartIsType(DFCC_DXIL));
    return it != end(pHeader);
  }

  // True only if every diagnostic in `required` also appears in
  // `available`, counting duplicates (multiset containment). Used to prove
  // that a reassembly round trip did not silently drop or alter even one
  // of the original diagnostics while another, unrelated one kept the
  // clone failing overall.
  bool DiagnosticsArePreserved(const std::vector<std::string> &required,
                               const std::vector<std::string> &available) {
    std::multiset<std::string> pool(available.begin(), available.end());
    for (const std::string &diagnostic : required) {
      std::multiset<std::string>::iterator it = pool.find(diagnostic);
      if (it == pool.end()) {
        return false;
      }
      pool.erase(it);
    }
    return true;
  }

  ValidationResult ValidateInstrumentedModule(IDxcBlob *pModule) {
    CComPtr<IDxcBlob> pContainer = NormalizeToContainer(pModule);

    ValidationResult direct = RunValidator(pContainer);
    if (direct.Valid) {
      return direct;
    }

    // The clone/serialize/reassemble pipeline needs an embedded canonical
    // DXIL part to parse the module (see ModuleAndHangersOn). If it is
    // absent, do not attempt structural inspection; report the original
    // failure.
    if (!HasCanonicalDxilPart(pContainer)) {
      return direct;
    }

    // If the original failure carries no significant diagnostic at all
    // (only the "Validation failed." boilerplate), there is nothing to
    // structurally attribute to known PIX metadata. Opening the
    // identity/strip fallback here would let DiagnosticsArePreserved's
    // multiset-containment check vacuously "succeed" against any identity
    // clone diagnostics (required is empty, so nothing needs to be
    // present). Fail closed instead: report the original failure directly.
    std::vector<std::string> directDiagnostics =
        GetSignificantValidationDiagnostics(direct.Errors);
    if (directDiagnostics.empty()) {
      return direct;
    }

    // The module may have unused metadata from the four known PIX
    // virtual-register kinds; PIX passes intentionally leave this metadata
    // for downstream tools to consume. The validator's diagnostic text
    // never names the attachment kind (it prints only the metadata node's
    // own operands), so text alone cannot tell known PIX metadata apart
    // from any other unused metadata. Settle it structurally instead, by
    // revalidating copies with metadata removed.
    //
    // Both clones below explicitly target DFCC_DXIL -- the same canonical
    // part `direct` just validated -- rather than the debug-info-carrying
    // DFCC_ShaderDebugInfoDXIL part. Parsing a different part than the one
    // actually validated would let the two diverge: DFCC_DXIL is produced
    // by stripping debug info from the pre-strip module that becomes
    // DFCC_ShaderDebugInfoDXIL (see SerializeDxilContainerForModule), and a
    // defect present in one is not guaranteed to be present, or to produce
    // matching diagnostic text, in the other. Parsing DFCC_DXIL consistently
    // removes that divergence at its source rather than trying to detect it
    // after the fact from diagnostic text alone, which the validator's own
    // generic "unused metadata" message cannot reliably distinguish (two
    // different metadata kinds can produce identical diagnostic text if
    // their operands happen to match).
    //
    // Reassembly itself (clone -> serialize -> reassemble) can still repair
    // derived container parts or validator-version metadata unrelated to
    // metadata stripping. It is not enough for the identity clone (no-op
    // mutation) to merely still fail: reassembly could silently repair one
    // original diagnostic while a different, unrelated diagnostic (such as
    // Meta.Used) keeps the identity clone failing overall, which would hide
    // the repair. So require every diagnostic from the original direct
    // failure to still be present in the identity clone's diagnostics
    // (multiset containment, in case of duplicates). This check is now sound
    // because both sides derive from the same canonical part: it guards
    // against reassembly artifacts, not cross-part content divergence. Only
    // when it holds, and the stripped clone then validates, is known PIX
    // metadata the sole cause.
    CComPtr<IDxcBlob> identityContainer = CloneModuleAndMutate(
        pContainer,
        [](llvm::Module &) {
          // No-op: proves the round-trip alone does not change the
          // outcome, before trusting the stripped clone's result.
        },
        DFCC_DXIL);
    ValidationResult identity = RunValidator(identityContainer);
    std::vector<std::string> identityDiagnostics =
        GetSignificantValidationDiagnostics(identity.Errors);
    if (identity.Valid ||
        !DiagnosticsArePreserved(directDiagnostics, identityDiagnostics)) {
      return direct;
    }

    CComPtr<IDxcBlob> strippedContainer = CloneModuleAndMutate(
        pContainer,
        [this](llvm::Module &M) { StripKnownPixVirtualRegisterMetadata(M); },
        DFCC_DXIL);
    ValidationResult stripped = RunValidator(strippedContainer);
    if (stripped.Valid) {
      return {true, {}};
    }

    // A real defect remains even with the known PIX metadata removed.
    // Preserve the original diagnostic alongside the stripped-copy result
    // instead of silently discarding it.
    return {false, direct.Errors +
                       "\n--- after removing known PIX virtual-register "
                       "metadata ---\n" +
                       stripped.Errors};
  }

  // Filters out boilerplate ("Validation failed.") and blank lines. There
  // is no metadata exception here: ValidateInstrumentedModule already
  // decides whether unused metadata is limited to the four known PIX
  // virtual-register kinds by revalidating identity and structurally
  // stripped copies of the module, so any diagnostic reaching this
  // function is significant.
  std::vector<std::string>
  GetSignificantValidationDiagnostics(const std::string &errors) {
    std::vector<std::string> result;
    std::stringstream errorStream(errors);
    std::string line;
    while (std::getline(errorStream, line)) {
      if (!line.empty() && line.back() == '\r') {
        line.pop_back();
      }
      if (line.empty() || line == "Validation failed.") {
        continue;
      }
      result.push_back(line);
    }
    return result;
  }

  // The pass/fail disposition that VerifyInstrumentedModuleIsValid acts on.
  // Exposed separately (rather than only inlined in
  // VerifyInstrumentedModuleIsValid) so control tests can assert on the
  // exact decision production validation makes, instead of on an internal
  // helper whose result might not reflect it.
  struct InstrumentedModuleDisposition {
    bool Valid;
    std::vector<std::string> Diagnostics; // significant diagnostics if !Valid
  };

  InstrumentedModuleDisposition
  GetInstrumentedModuleDisposition(IDxcBlob *pModule) {
    ValidationResult validation = ValidateInstrumentedModule(pModule);
    if (validation.Valid) {
      return {true, {}};
    }
    return {false, GetSignificantValidationDiagnostics(validation.Errors)};
  }

  // Asserts an instrumented module validates; logs and fails otherwise.
  void VerifyInstrumentedModuleIsValid(IDxcBlob *pModule,
                                       const char *description) {
    InstrumentedModuleDisposition disposition =
        GetInstrumentedModuleDisposition(pModule);
    if (disposition.Valid) {
      return;
    }

    std::string joined;
    if (disposition.Diagnostics.empty()) {
      joined = "(validator reported failure with no significant diagnostic "
               "text)";
    } else {
      for (std::string const &significantError : disposition.Diagnostics) {
        joined += significantError + "\n";
      }
    }
    WEX::Logging::Log::Error(WEX::Common::String().Format(
        L"Validation failed after %S:\n%S", description, joined.c_str()));
    VERIFY_FAIL();
  }

  CComPtr<IDxcBlob> FindModule(hlsl::DxilFourCC fourCC, IDxcBlob *pSource) {
    const UINT32 BC_C0DE = ((INT32)(INT8)'B' | (INT32)(INT8)'C' << 8 |
                            (INT32)0xDEC0 << 16); // BC0xc0de in big endian
    const char *pBitcode = nullptr;
    const hlsl::DxilPartHeader *pDxilPartHeader =
        (hlsl::DxilPartHeader *)
            pSource->GetBufferPointer(); // Initialize assuming that source is
                                         // starting with DXIL part

    if (BC_C0DE == *(UINT32 *)pSource->GetBufferPointer()) {
      return pSource;
    }
    if (hlsl::IsValidDxilContainer(
            (hlsl::DxilContainerHeader *)pSource->GetBufferPointer(),
            pSource->GetBufferSize())) {
      hlsl::DxilContainerHeader *pDxilContainerHeader =
          (hlsl::DxilContainerHeader *)pSource->GetBufferPointer();
      pDxilPartHeader =
          *std::find_if(begin(pDxilContainerHeader), end(pDxilContainerHeader),
                        hlsl::DxilPartIsType(fourCC));
    }
    if (fourCC == pDxilPartHeader->PartFourCC) {
      UINT32 pBlobSize;
      const hlsl::DxilProgramHeader *pDxilProgramHeader =
          (const hlsl::DxilProgramHeader *)(pDxilPartHeader + 1);
      hlsl::GetDxilProgramBitcode(pDxilProgramHeader, &pBitcode, &pBlobSize);
      UINT32 offset =
          (UINT32)(pBitcode - (const char *)pSource->GetBufferPointer());
      CComPtr<IDxcLibrary> library;
      IFT(m_dllSupport.CreateInstance(CLSID_DxcLibrary, &library));
      CComPtr<IDxcBlob> targetBlob;
      library->CreateBlobFromBlob(pSource, offset, pBlobSize, &targetBlob);
      return targetBlob;
    }
    return {};
  }

  void ReplaceDxilBlobPart(const void *originalShaderBytecode,
                           SIZE_T originalShaderLength, IDxcBlob *pNewDxilBlob,
                           IDxcBlob **ppNewShaderOut) {
    CComPtr<IDxcLibrary> pLibrary;
    IFT(m_dllSupport.CreateInstance(CLSID_DxcLibrary, &pLibrary));

    CComPtr<IDxcBlob> pNewContainer;

    // Use the container assembler to build a new container from the
    // recently-modified DXIL bitcode. This container will contain new copies of
    // things like input signature etc., which will supersede the ones from the
    // original compiled shader's container.
    {
      CComPtr<IDxcAssembler> pAssembler;
      IFT(m_dllSupport.CreateInstance(CLSID_DxcAssembler, &pAssembler));

      CComPtr<IDxcOperationResult> pAssembleResult;
      VERIFY_SUCCEEDED(
          pAssembler->AssembleToContainer(pNewDxilBlob, &pAssembleResult));

      CComPtr<IDxcBlobEncoding> pAssembleErrors;
      VERIFY_SUCCEEDED(pAssembleResult->GetErrorBuffer(&pAssembleErrors));

      if (pAssembleErrors && pAssembleErrors->GetBufferSize() != 0) {
        OutputDebugStringA(
            static_cast<LPCSTR>(pAssembleErrors->GetBufferPointer()));
        VERIFY_SUCCEEDED(E_FAIL);
      }

      VERIFY_SUCCEEDED(pAssembleResult->GetResult(&pNewContainer));
    }

    // Now copy over the blobs from the original container that won't have been
    // invalidated by changing the shader code itself, using the container
    // reflection API
    {
      // Wrap the original code in a container blob
      CComPtr<IDxcBlobEncoding> pContainer;
      VERIFY_SUCCEEDED(pLibrary->CreateBlobWithEncodingFromPinned(
          static_cast<LPBYTE>(const_cast<void *>(originalShaderBytecode)),
          static_cast<UINT32>(originalShaderLength), CP_ACP, &pContainer));

      CComPtr<IDxcContainerReflection> pReflection;
      IFT(m_dllSupport.CreateInstance(CLSID_DxcContainerReflection,
                                      &pReflection));

      // Load the reflector from the original shader
      VERIFY_SUCCEEDED(pReflection->Load(pContainer));

      UINT32 partIndex;

      if (SUCCEEDED(pReflection->FindFirstPartKind(hlsl::DFCC_PrivateData,
                                                   &partIndex))) {
        CComPtr<IDxcBlob> pPart;
        VERIFY_SUCCEEDED(pReflection->GetPartContent(partIndex, &pPart));

        CComPtr<IDxcContainerBuilder> pContainerBuilder;
        IFT(m_dllSupport.CreateInstance(CLSID_DxcContainerBuilder,
                                        &pContainerBuilder));

        VERIFY_SUCCEEDED(pContainerBuilder->Load(pNewContainer));

        VERIFY_SUCCEEDED(
            pContainerBuilder->AddPart(hlsl::DFCC_PrivateData, pPart));

        CComPtr<IDxcOperationResult> pBuildResult;

        VERIFY_SUCCEEDED(pContainerBuilder->SerializeContainer(&pBuildResult));

        CComPtr<IDxcBlobEncoding> pBuildErrors;
        VERIFY_SUCCEEDED(pBuildResult->GetErrorBuffer(&pBuildErrors));

        if (pBuildErrors && pBuildErrors->GetBufferSize() != 0) {
          OutputDebugStringA(
              reinterpret_cast<LPCSTR>(pBuildErrors->GetBufferPointer()));
          VERIFY_SUCCEEDED(E_FAIL);
        }

        VERIFY_SUCCEEDED(pBuildResult->GetResult(&pNewContainer));
      }
    }

    *ppNewShaderOut = pNewContainer.Detach();
  }

  void ValidateAccessTrackingMods(const char *hlsl, bool modsExpected);
  void LoadSubobjectsFromContainerIntoModule(IDxcBlob *container,
                                             DxilModule &DM);
  void VerifyGlobalRootSignaturesHaveToolsUAVs(
      DxilSubobjects *subObjects,
      const std::vector<std::string> &expectedRootSignatureNames,
      const std::vector<uint32_t> &expectedShaderRegisters);

  class ModuleAndHangersOn {
    std::unique_ptr<llvm::LLVMContext> llvmContext;
    std::unique_ptr<llvm::Module> llvmModule;
    DxilModule *dxilModule;

  public:
    // partKind selects which container part to parse when pBlob is a full
    // container (bare bitcode, the "assume a dxil part first" branch below,
    // ignores partKind entirely). Defaults to DFCC_ShaderDebugInfoDXIL,
    // preserving every existing caller's behavior; ValidateInstrumentedModule's
    // fallback pipeline passes DFCC_DXIL explicitly instead, so it always
    // parses the same canonical part RunValidator actually validated.
    ModuleAndHangersOn(IDxcBlob *pBlob,
                       hlsl::DxilFourCC partKind = DFCC_ShaderDebugInfoDXIL) {

      // Assume we were given a dxil part first:
      const DxilProgramHeader *pProgramHeader =
          reinterpret_cast<const DxilProgramHeader *>(
              pBlob->GetBufferPointer());
      uint32_t partSize = static_cast<uint32_t>(pBlob->GetBufferSize());
      // Check if we were given a valid dxil container instead:
      const DxilContainerHeader *pContainer = IsDxilContainerLike(
          pBlob->GetBufferPointer(), pBlob->GetBufferSize());
      if (pContainer != nullptr) {
        VERIFY_IS_TRUE(
            IsValidDxilContainer(pContainer, pBlob->GetBufferSize()));

        // Get Dxil part from container.
        DxilPartIterator it = std::find_if(begin(pContainer), end(pContainer),
                                           DxilPartIsType(partKind));
        VERIFY_IS_FALSE(it == end(pContainer));

        pProgramHeader =
            reinterpret_cast<const DxilProgramHeader *>(GetDxilPartData(*it));
        partSize = (*it)->PartSize;
      }

      VERIFY_IS_TRUE(IsValidDxilProgramHeader(pProgramHeader, partSize));

      // Get a pointer to the llvm bitcode.
      const char *pIL;
      uint32_t pILLength;
      GetDxilProgramBitcode(pProgramHeader, &pIL, &pILLength);

      // Parse llvm bitcode into a module.
      std::unique_ptr<llvm::MemoryBuffer> pBitcodeBuf(
          llvm::MemoryBuffer::getMemBuffer(llvm::StringRef(pIL, pILLength), "",
                                           false));

      llvmContext.reset(new llvm::LLVMContext);

      llvm::ErrorOr<std::unique_ptr<llvm::Module>> pModule(
          llvm::parseBitcodeFile(pBitcodeBuf->getMemBufferRef(), *llvmContext));
      if (std::error_code ec = pModule.getError()) {
        VERIFY_FAIL();
      }

      llvmModule = std::move(pModule.get());

      dxilModule = DxilModule::TryGetDxilModule(llvmModule.get());
    }

    DxilModule &GetDxilModule() { return *dxilModule; }
  };

  struct AggregateOffsetAndSize {
    unsigned countOfMembers;
    unsigned offset;
    unsigned size;
  };
  struct AllocaWrite {
    std::string memberName;
    uint32_t regBase;
    uint32_t regSize;
    uint64_t index;
  };
  struct TestableResults {
    std::vector<AggregateOffsetAndSize> OffsetAndSizes;
    std::vector<AllocaWrite> AllocaWrites;
  };

  TestableResults TestStructAnnotationCase(const char *hlsl,
                                           const wchar_t *optimizationLevel,
                                           bool validateCoverage = true,
                                           const wchar_t *profile = L"as_6_5");
  void ValidateAllocaWrite(std::vector<AllocaWrite> const &allocaWrites,
                           size_t index, const char *name);
  PassOutput RunShaderAccessTrackingPass(IDxcBlob *blob);
  CComPtr<IDxcBlob>
  RunDxilPIXAddTidToAmplificationShaderPayloadPass(IDxcBlob *blob);
  CComPtr<IDxcBlob> RunDxilPIXMeshShaderOutputPass(IDxcBlob *blob);
  CComPtr<IDxcBlob>
  RunDxilPIXDXRInvocationsLog(IDxcBlob *blob, unsigned maxNumEntriesInLog = 24);
  PassOutput
  RunDxilNonUniformResourceIndexInstrumentation(IDxcBlob *blob,
                                                std::string &outputText);
  void TestNuriCase(const char *source, const wchar_t *target,
                    uint32_t expectedResult);
  void TestPixUAVCase(char const *hlsl, wchar_t const *model,
                      wchar_t const *entry);
  std::string Disassemble(IDxcBlob *pProgram);
};

bool PixTest::InitSupport() {
  if (!m_dllSupport.IsEnabled()) {
    VERIFY_SUCCEEDED(m_dllSupport.Initialize());
    m_ver.Initialize(m_dllSupport);
  }
  return true;
}

static unsigned CountToolsUAVs(DxilModule &DM) {
  unsigned count = 0;
  for (auto const &uav : DM.GetUAVs()) {
    if (uav->GetSpaceID() == static_cast<uint32_t>(-2)) {
      count++;
    }
  }
  return count;
}

static int CountToolsUAVRecords(std::vector<std::string> const &lines) {
  int count = 0;
  for (std::string const &line : lines) {
    if (!line.empty() && line[0] == '!' &&
        line.find(", i32 -2, i32 ") != std::string::npos) {
      count++;
    }
  }
  return count;
}

static bool
HasDxrInvocationLogEntryCountCheck(std::vector<std::string> const &lines,
                                   unsigned expectedEntryCount) {
  // Reviewer 4.1: matching "icmp ult i32 %EntryIndexResult" and ", N"
  // anywhere in the line (previously two independent, unanchored find()
  // calls) lets a bound of 1 also match text containing 10 or 100, since
  // ", 1" is a substring of ", 10" and ", 100". Anchor the value
  // immediately after the known operand prefix, and require the decimal
  // literal to end exactly there. Reviewer follow-up: rejecting only a
  // following digit is not enough (e.g. "1x" would still match); the only
  // valid continuations of an LLVM IR operand's decimal literal are
  // end-of-line, whitespace (including a trailing CR before a "\r\n" line
  // ending), or a comma introducing an attached metadata reference (e.g.
  // ", !dbg !12"). Reject every other continuation, digit or not.
  const std::string prefix = "icmp ult i32 %EntryIndexResult, ";
  const std::string expectedValue = std::to_string(expectedEntryCount);
  for (std::string const &line : lines) {
    size_t prefixPos = line.find(prefix);
    if (prefixPos == std::string::npos) {
      continue;
    }
    size_t valuePos = prefixPos + prefix.size();
    if (line.compare(valuePos, expectedValue.size(), expectedValue) != 0) {
      continue;
    }
    size_t afterValuePos = valuePos + expectedValue.size();
    bool validContinuation = afterValuePos >= line.size();
    if (!validContinuation) {
      const unsigned char nextChar =
          static_cast<unsigned char>(line[afterValuePos]);
      validContinuation = nextChar == ',' || std::isspace(nextChar) != 0;
    }
    if (!validContinuation) {
      continue;
    }
    return true;
  }
  return false;
}

static bool
RootSignatureHasToolsUAV(const DxilVersionedRootSignatureDesc *rootSignature,
                         uint32_t shaderRegister) {
  switch (rootSignature->Version) {
  case DxilRootSignatureVersion::Version_1_0: {
    const DxilRootSignatureDesc &desc = rootSignature->Desc_1_0;
    for (uint32_t i = 0; i < desc.NumParameters; ++i) {
      const DxilRootParameter &param = desc.pParameters[i];
      if (param.ParameterType == DxilRootParameterType::UAV &&
          param.Descriptor.RegisterSpace == static_cast<uint32_t>(-2) &&
          param.Descriptor.ShaderRegister == shaderRegister) {
        return true;
      }
    }
    break;
  }
  case DxilRootSignatureVersion::Version_1_1: {
    const DxilRootSignatureDesc1 &desc = rootSignature->Desc_1_1;
    for (uint32_t i = 0; i < desc.NumParameters; ++i) {
      const DxilRootParameter1 &param = desc.pParameters[i];
      if (param.ParameterType == DxilRootParameterType::UAV &&
          param.Descriptor.RegisterSpace == static_cast<uint32_t>(-2) &&
          param.Descriptor.ShaderRegister == shaderRegister) {
        return true;
      }
    }
    break;
  }
  }
  return false;
}

void PixTest::LoadSubobjectsFromContainerIntoModule(IDxcBlob *container,
                                                    DxilModule &DM) {
  const char *blobContent =
      reinterpret_cast<const char *>(container->GetBufferPointer());
  const unsigned blobSize = container->GetBufferSize();
  const hlsl::DxilContainerHeader *containerHeader =
      hlsl::IsDxilContainerLike(blobContent, blobSize);
  VERIFY_ARE_NOT_EQUAL(containerHeader, nullptr);

  const hlsl::DxilPartHeader *partHeader =
      GetDxilPartByType(containerHeader, hlsl::DFCC_RuntimeData);
  VERIFY_ARE_NOT_EQUAL(partHeader, nullptr);

  hlsl::RDAT::DxilRuntimeData rdat(GetDxilPartData(partHeader),
                                   partHeader->PartSize);
  std::unique_ptr<DxilSubobjects> subObjects(new DxilSubobjects());
  VERIFY_IS_TRUE(LoadSubobjectsFromRDAT(*subObjects, rdat));
  DM.ResetSubobjects(subObjects.release());
}

void PixTest::VerifyGlobalRootSignaturesHaveToolsUAVs(
    DxilSubobjects *subObjects,
    const std::vector<std::string> &expectedRootSignatureNames,
    const std::vector<uint32_t> &expectedShaderRegisters) {
  VERIFY_IS_NOT_NULL(subObjects);

  std::map<std::string, bool> foundRootSignatures;
  for (const std::string &rootSignatureName : expectedRootSignatureNames) {
    foundRootSignatures[rootSignatureName] = false;
  }

  for (auto const &subObject : subObjects->GetSubobjects()) {
    if (subObject.second->GetKind() !=
        hlsl::DXIL::SubobjectKind::GlobalRootSignature) {
      continue;
    }

    const std::string subObjectName = subObject.first.str();
    if (foundRootSignatures.find(subObjectName) == foundRootSignatures.end()) {
      continue;
    }

    const void *data = nullptr;
    uint32_t size = 0;
    constexpr bool notALocalRS = false;
    VERIFY_IS_TRUE(
        subObject.second->GetRootSignature(notALocalRS, data, size, nullptr));

    DxilVersionedRootSignatureDesc const *rootSignature = nullptr;
    DeserializeRootSignature(data, size, &rootSignature);
    for (uint32_t expectedShaderRegister : expectedShaderRegisters) {
      VERIFY_IS_TRUE(
          RootSignatureHasToolsUAV(rootSignature, expectedShaderRegister));
    }
    DeleteRootSignature(rootSignature);
    foundRootSignatures[subObjectName] = true;
  }

  for (const std::pair<const std::string, bool> &foundRootSignature :
       foundRootSignatures) {
    VERIFY_IS_TRUE(foundRootSignature.second);
  }
}

void PixTest::TestPixUAVCase(char const *hlsl, wchar_t const *model,
                             wchar_t const *entry) {
  auto mod = Compile(m_dllSupport, hlsl, model, {}, entry);
  CComPtr<IDxcBlob> dxilPart = FindModule(DFCC_ShaderDebugInfoDXIL, mod);
  PassOutput passOutput = RunDebugPass(dxilPart);
  CComPtr<IDxcBlob> modifiedDxilContainer;
  ReplaceDxilBlobPart(mod->GetBufferPointer(), mod->GetBufferSize(),
                      passOutput.blob, &modifiedDxilContainer);

  ModuleAndHangersOn moduleEtc(modifiedDxilContainer);
  auto &compilerGeneratedUAV = moduleEtc.GetDxilModule().GetUAV(0);
  auto &pixDebugGeneratedUAV = moduleEtc.GetDxilModule().GetUAV(1);
  VERIFY_ARE_EQUAL(compilerGeneratedUAV.GetClass(),
                   pixDebugGeneratedUAV.GetClass());
  VERIFY_ARE_EQUAL(compilerGeneratedUAV.GetKind(),
                   pixDebugGeneratedUAV.GetKind());
  VERIFY_ARE_EQUAL(compilerGeneratedUAV.GetHLSLType(),
                   pixDebugGeneratedUAV.GetHLSLType());
  VERIFY_ARE_EQUAL(compilerGeneratedUAV.GetSampleCount(),
                   pixDebugGeneratedUAV.GetSampleCount());
  VERIFY_ARE_EQUAL(compilerGeneratedUAV.GetElementStride(),
                   pixDebugGeneratedUAV.GetElementStride());
  VERIFY_ARE_EQUAL(compilerGeneratedUAV.GetBaseAlignLog2(),
                   pixDebugGeneratedUAV.GetBaseAlignLog2());
  VERIFY_ARE_EQUAL(compilerGeneratedUAV.GetCompType(),
                   pixDebugGeneratedUAV.GetCompType());
  VERIFY_ARE_EQUAL(compilerGeneratedUAV.GetSamplerFeedbackType(),
                   pixDebugGeneratedUAV.GetSamplerFeedbackType());
  VERIFY_ARE_EQUAL(compilerGeneratedUAV.IsGloballyCoherent(),
                   pixDebugGeneratedUAV.IsGloballyCoherent());
  VERIFY_ARE_EQUAL(compilerGeneratedUAV.HasCounter(),
                   pixDebugGeneratedUAV.HasCounter());
  VERIFY_ARE_EQUAL(compilerGeneratedUAV.HasAtomic64Use(),
                   pixDebugGeneratedUAV.HasAtomic64Use());

  VERIFY_ARE_EQUAL(compilerGeneratedUAV.GetGlobalSymbol()->getType(),
                   pixDebugGeneratedUAV.GetGlobalSymbol()->getType());
}

TEST_F(PixTest, DebugUAV_CS_6_1) {
  const char *hlsl = R"(
RWByteAddressBuffer RawUAV : register(u0);
[numthreads(1, 1, 1)]
void CSMain()
{
    RawUAV.Store(0, RawUAV.Load(4));
}
)";
  TestPixUAVCase(hlsl, L"cs_6_1", L"CSMain");
}

TEST_F(PixTest, DebugUAV_CS_6_2) {
  const char *hlsl = R"(
RWByteAddressBuffer RawUAV : register(u0);
[numthreads(1, 1, 1)]
void CSMain()
{
    RawUAV.Store(0, RawUAV.Load(4));
}
)";
  // In 6.2, rawBufferLoad replaced bufferLoad for UAVs, but we don't
  // expect this test to notice the difference. We just test 6.2
  TestPixUAVCase(hlsl, L"cs_6_2", L"CSMain");
}

TEST_F(PixTest, DebugUAV_lib_6_3_through_6_8) {
  const char *hlsl = R"(
RWByteAddressBuffer RawUAV : register(u0);
struct [raypayload] Payload
{
  double a : read(caller, closesthit, anyhit) : write(caller, miss, closesthit);
};
[shader("miss")]
void Miss( inout Payload payload ) 
{ 
    RawUAV.Store(0, RawUAV.Load(4));
    payload.a = 4.2;
})";
  TestPixUAVCase(hlsl, L"lib_6_3", L"");
  TestPixUAVCase(hlsl, L"lib_6_4", L"");
  TestPixUAVCase(hlsl, L"lib_6_5", L"");

  if (m_ver.SkipDxilVersion(1, 6))
    return;
  TestPixUAVCase(hlsl, L"lib_6_6", L"");

  if (m_ver.SkipDxilVersion(1, 7))
    return;
  TestPixUAVCase(hlsl, L"lib_6_7", L"");

  if (m_ver.SkipDxilVersion(1, 8))
    return;
  TestPixUAVCase(hlsl, L"lib_6_8", L"");
}

TEST_F(PixTest, CompileDebugDisasmPDB) {
  const char *hlsl = R"(
    [RootSignature("")]
    float main(float pos : A) : SV_Target {
      float x = abs(pos);
      float y = sin(pos);
      float z = x + y;
      return z;
    }
  )";
  CComPtr<IDxcLibrary> pLib;
  VERIFY_SUCCEEDED(m_dllSupport.CreateInstance(CLSID_DxcLibrary, &pLib));

  CComPtr<IDxcCompiler> pCompiler;
  CComPtr<IDxcCompiler2> pCompiler2;

  CComPtr<IDxcOperationResult> pResult;
  CComPtr<IDxcBlobEncoding> pSource;
  CComPtr<IDxcBlob> pProgram;
  CComPtr<IDxcBlob> pPdbBlob;
  CComHeapPtr<WCHAR> pDebugName;

  VERIFY_SUCCEEDED(CreateCompiler(m_dllSupport, &pCompiler));
  VERIFY_SUCCEEDED(pCompiler.QueryInterface(&pCompiler2));
  CreateBlobFromText(m_dllSupport, hlsl, &pSource);
  LPCWSTR args[] = {L"/Zi", L"/Qembed_debug"};
  VERIFY_SUCCEEDED(pCompiler2->CompileWithDebug(
      pSource, L"source.hlsl", L"main", L"ps_6_0", args, _countof(args),
      nullptr, 0, nullptr, &pResult, &pDebugName, &pPdbBlob));
  VERIFY_SUCCEEDED(pResult->GetResult(&pProgram));

  // Test that disassembler can consume a PDB container
  CComPtr<IDxcBlobEncoding> pDisasm;
  VERIFY_SUCCEEDED(pCompiler->Disassemble(pPdbBlob, &pDisasm));
}

PassOutput PixTest::RunShaderAccessTrackingPass(IDxcBlob *blob) {
  CComPtr<IDxcOptimizer> pOptimizer;
  VERIFY_SUCCEEDED(
      m_dllSupport.CreateInstance(CLSID_DxcOptimizer, &pOptimizer));
  std::vector<LPCWSTR> Options;
  Options.push_back(L"-opt-mod-passes");
  Options.push_back(L"-hlsl-dxil-pix-shader-access-instrumentation,config=U0:0:"
                    L"10i0;U0:1:2i0;.0;0;0.");

  CComPtr<IDxcBlob> pOptimizedModule;
  CComPtr<IDxcBlobEncoding> pText;
  VERIFY_SUCCEEDED(pOptimizer->RunOptimizer(
      blob, Options.data(), Options.size(), &pOptimizedModule, &pText));

  CComPtr<IDxcAssembler> pAssembler;
  VERIFY_SUCCEEDED(
      m_dllSupport.CreateInstance(CLSID_DxcAssembler, &pAssembler));

  CComPtr<IDxcOperationResult> pAssembleResult;
  VERIFY_SUCCEEDED(
      pAssembler->AssembleToContainer(pOptimizedModule, &pAssembleResult));

  HRESULT hr;
  VERIFY_SUCCEEDED(pAssembleResult->GetStatus(&hr));
  VERIFY_SUCCEEDED(hr);

  CComPtr<IDxcBlob> pNewContainer;
  VERIFY_SUCCEEDED(pAssembleResult->GetResult(&pNewContainer));

  PassOutput ret;
  ret.blob = pNewContainer;
  std::string outputText = BlobToUtf8(pText);
  ret.lines = Tokenize(outputText.c_str(), "\n");

  return ret;
}

CComPtr<IDxcBlob> PixTest::RunDxilPIXMeshShaderOutputPass(IDxcBlob *blob) {
  CComPtr<IDxcBlob> dxil = FindModule(DFCC_ShaderDebugInfoDXIL, blob);
  CComPtr<IDxcOptimizer> pOptimizer;
  VERIFY_SUCCEEDED(
      m_dllSupport.CreateInstance(CLSID_DxcOptimizer, &pOptimizer));
  std::vector<LPCWSTR> Options;
  Options.push_back(L"-opt-mod-passes");
  Options.push_back(L"-hlsl-dxil-pix-meshshader-output-instrumentation,expand-"
                    L"payload=1,UAVSize=8192");

  CComPtr<IDxcBlob> pOptimizedModule;
  CComPtr<IDxcBlobEncoding> pText;
  VERIFY_SUCCEEDED(pOptimizer->RunOptimizer(
      dxil, Options.data(), Options.size(), &pOptimizedModule, &pText));

  std::string outputText;
  if (pText->GetBufferSize() != 0) {
    outputText = reinterpret_cast<const char *>(pText->GetBufferPointer());
  }

  return pOptimizedModule;
}

CComPtr<IDxcBlob>
PixTest::RunDxilPIXDXRInvocationsLog(IDxcBlob *blob,
                                     unsigned maxNumEntriesInLog) {

  CComPtr<IDxcBlob> dxil = FindModule(DFCC_ShaderDebugInfoDXIL, blob);
  CComPtr<IDxcOptimizer> pOptimizer;
  VERIFY_SUCCEEDED(
      m_dllSupport.CreateInstance(CLSID_DxcOptimizer, &pOptimizer));
  std::wstring logArg = L"-hlsl-dxil-pix-dxr-invocations-log,"
                        L"maxNumEntriesInLog=" +
                        std::to_wstring(maxNumEntriesInLog);
  std::vector<LPCWSTR> Options;
  Options.push_back(logArg.c_str());

  CComPtr<IDxcBlob> pOptimizedModule;
  CComPtr<IDxcBlobEncoding> pText;
  VERIFY_SUCCEEDED(pOptimizer->RunOptimizer(
      blob, Options.data(), Options.size(), &pOptimizedModule, &pText));

  std::string outputText;
  if (pText->GetBufferSize() != 0) {
    outputText = reinterpret_cast<const char *>(pText->GetBufferPointer());
  }

  return pOptimizedModule;
}

static const char *kSingleMissInvocationLogShader = R"x(
struct [raypayload] MyPayload
{
    float2 barycentrics : read(caller) : write(caller,anyhit);
    uint primitiveIndex : read(caller) : write(caller,anyhit);
};

[shader("miss")]
void MissOne(inout MyPayload payload)
{
    payload.primitiveIndex = 1;
}
)x";

PassOutput PixTest::RunDxilNonUniformResourceIndexInstrumentation(
    IDxcBlob *blob, std::string &outputText) {

  CComPtr<IDxcBlob> dxil = FindModule(DFCC_ShaderDebugInfoDXIL, blob);
  CComPtr<IDxcOptimizer> pOptimizer;
  VERIFY_SUCCEEDED(
      m_dllSupport.CreateInstance(CLSID_DxcOptimizer, &pOptimizer));
  std::array<LPCWSTR, 4> Options = {
      L"-opt-mod-passes", L"-dxil-dbg-value-to-dbg-declare",
      L"-dxil-annotate-with-virtual-regs",
      L"-hlsl-dxil-non-uniform-resource-index-instrumentation"};

  CComPtr<IDxcBlob> pOptimizedModule;
  CComPtr<IDxcBlobEncoding> pText;
  VERIFY_SUCCEEDED(pOptimizer->RunOptimizer(
      dxil, Options.data(), Options.size(), &pOptimizedModule, &pText));

  outputText = BlobToUtf8(pText);

  PassOutput result;
  result.blob = pOptimizedModule;
  result.lines = Tokenize(Disassemble(pOptimizedModule), "\n");
  return result;
}

CComPtr<IDxcBlob>
PixTest::RunDxilPIXAddTidToAmplificationShaderPayloadPass(IDxcBlob *blob) {
  CComPtr<IDxcBlob> dxil = FindModule(DFCC_ShaderDebugInfoDXIL, blob);
  CComPtr<IDxcOptimizer> pOptimizer;
  VERIFY_SUCCEEDED(
      m_dllSupport.CreateInstance(CLSID_DxcOptimizer, &pOptimizer));
  std::vector<LPCWSTR> Options;
  Options.push_back(L"-opt-mod-passes");
  Options.push_back(
      L"-hlsl-dxil-PIX-add-tid-to-as-payload,dispatchArgY=1,dispatchArgZ=2");

  CComPtr<IDxcBlob> pOptimizedModule;
  CComPtr<IDxcBlobEncoding> pText;
  VERIFY_SUCCEEDED(pOptimizer->RunOptimizer(
      dxil, Options.data(), Options.size(), &pOptimizedModule, &pText));

  return pOptimizedModule;
}

static bool HasDeclaration(const std::string &disassembly,
                           const std::string &functionName);
static std::string FindDeclarationLine(const std::string &disassembly,
                                       const std::string &functionName);
static bool HasDeclarationLine(const std::string &disassembly,
                               const std::string &declaration);

TEST_F(PixTest, AddToASPayload) {

  const char *hlsl = R"(
struct MyPayload
{
    float f1;
    float f2;
};

[numthreads(1, 1, 1)]
void ASMain(uint gid : SV_GroupID)
{
    MyPayload payload;
    payload.f1 = (float)gid / 4.f;
    payload.f2 = (float)gid * 4.f;
    DispatchMesh(1, 1, 1, payload);
}

struct PSInput
{
    float4 position : SV_POSITION;
};


[outputtopology("triangle")]
[numthreads(3,1,1)]
void MSMain(
    in payload MyPayload small,
    in uint tid : SV_GroupThreadID,
    in uint3 dtid : SV_DispatchThreadID,
    out vertices PSInput verts[3],
    out indices uint3 triangles[1])
{
    SetMeshOutputCounts(3, 1);
    verts[tid].position = float4(small.f1, small.f2, 0, 0);
    triangles[0] = uint3(0, 1, 2);
}

  )";

  auto as = Compile(m_dllSupport, hlsl, L"as_6_6", {}, L"ASMain");
  const std::string originalDispatchMeshDeclaration =
      FindDeclarationLine(Disassemble(as), "dx.op.dispatchMesh");
  VERIFY_IS_FALSE(originalDispatchMeshDeclaration.empty());

  CComPtr<IDxcBlob> asOutput =
      RunDxilPIXAddTidToAmplificationShaderPayloadPass(as);
  VERIFY_IS_FALSE(HasDeclarationLine(Disassemble(asOutput),
                                     originalDispatchMeshDeclaration));

  auto ms = Compile(m_dllSupport, hlsl, L"ms_6_6", {}, L"MSMain");
  const std::string originalGetMeshPayloadDeclaration =
      FindDeclarationLine(Disassemble(ms), "dx.op.getMeshPayload");
  VERIFY_IS_FALSE(originalGetMeshPayloadDeclaration.empty());

  CComPtr<IDxcBlob> msOutput = RunDxilPIXMeshShaderOutputPass(ms);
  const std::string meshDisassembly = Disassemble(msOutput);
  VERIFY_IS_FALSE(
      HasDeclarationLine(meshDisassembly, originalGetMeshPayloadDeclaration));
  VERIFY_IS_FALSE(
      HasDeclaration(meshDisassembly, "dx.op.storeVertexOutput.i32"));
  VERIFY_IS_FALSE(
      HasDeclaration(meshDisassembly, "dx.op.storeVertexOutput.i16"));
  VERIFY_IS_FALSE(
      HasDeclaration(meshDisassembly, "dx.op.storeVertexOutput.f16"));
}
unsigned FindOrAddVSInSignatureElementForInstanceOrVertexID(
    hlsl::DxilSignature &InputSignature, hlsl::DXIL::SemanticKind semanticKind);

TEST_F(PixTest, SignatureModification_Empty) {

  DxilSignature sig(DXIL::ShaderKind::Vertex, DXIL::SignatureKind::Input,
                    false);

  FindOrAddVSInSignatureElementForInstanceOrVertexID(
      sig, DXIL::SemanticKind::InstanceID);
  FindOrAddVSInSignatureElementForInstanceOrVertexID(
      sig, DXIL::SemanticKind::VertexID);

  VERIFY_ARE_EQUAL(2ull, sig.GetElements().size());
  VERIFY_ARE_EQUAL(sig.GetElement(0).GetKind(), DXIL::SemanticKind::InstanceID);
  VERIFY_ARE_EQUAL(sig.GetElement(0).GetCols(), 1u);
  VERIFY_ARE_EQUAL(sig.GetElement(0).GetRows(), 1u);
  VERIFY_ARE_EQUAL(sig.GetElement(0).GetStartCol(), 0);
  VERIFY_ARE_EQUAL(sig.GetElement(0).GetStartRow(), 0);
  VERIFY_ARE_EQUAL(sig.GetElement(1).GetKind(), DXIL::SemanticKind::VertexID);
  VERIFY_ARE_EQUAL(sig.GetElement(1).GetCols(), 1u);
  VERIFY_ARE_EQUAL(sig.GetElement(1).GetRows(), 1u);
  VERIFY_ARE_EQUAL(sig.GetElement(1).GetStartCol(), 0);
  VERIFY_ARE_EQUAL(sig.GetElement(1).GetStartRow(), 1);
}

TEST_F(PixTest, SignatureModification_VertexIdAlready) {

  DxilSignature sig(DXIL::ShaderKind::Vertex, DXIL::SignatureKind::Input,
                    false);

  auto AddedElement =
      llvm::make_unique<DxilSignatureElement>(DXIL::SigPointKind::VSIn);
  AddedElement->Initialize(
      Semantic::Get(DXIL::SemanticKind::VertexID)->GetName(),
      hlsl::CompType::getU32(), DXIL::InterpolationMode::Constant, 1, 1, 0, 0,
      0, {0});
  AddedElement->SetKind(DXIL::SemanticKind::VertexID);
  AddedElement->SetUsageMask(1);
  sig.AppendElement(std::move(AddedElement));

  FindOrAddVSInSignatureElementForInstanceOrVertexID(
      sig, DXIL::SemanticKind::InstanceID);
  FindOrAddVSInSignatureElementForInstanceOrVertexID(
      sig, DXIL::SemanticKind::VertexID);

  VERIFY_ARE_EQUAL(2ull, sig.GetElements().size());
  VERIFY_ARE_EQUAL(sig.GetElement(0).GetKind(), DXIL::SemanticKind::VertexID);
  VERIFY_ARE_EQUAL(sig.GetElement(0).GetCols(), 1u);
  VERIFY_ARE_EQUAL(sig.GetElement(0).GetRows(), 1u);
  VERIFY_ARE_EQUAL(sig.GetElement(0).GetStartCol(), 0);
  VERIFY_ARE_EQUAL(sig.GetElement(0).GetStartRow(), 0);
  VERIFY_ARE_EQUAL(sig.GetElement(1).GetKind(), DXIL::SemanticKind::InstanceID);
  VERIFY_ARE_EQUAL(sig.GetElement(1).GetCols(), 1u);
  VERIFY_ARE_EQUAL(sig.GetElement(1).GetRows(), 1u);
  VERIFY_ARE_EQUAL(sig.GetElement(1).GetStartCol(), 0);
  VERIFY_ARE_EQUAL(sig.GetElement(1).GetStartRow(), 1);
}

TEST_F(PixTest, SignatureModification_SomethingElseFirst) {

  DxilSignature sig(DXIL::ShaderKind::Vertex, DXIL::SignatureKind::Input,
                    false);

  auto AddedElement =
      llvm::make_unique<DxilSignatureElement>(DXIL::SigPointKind::VSIn);
  AddedElement->Initialize("One", hlsl::CompType::getU32(),
                           DXIL::InterpolationMode::Constant, 1, 6, 0, 0, 0,
                           {0});
  AddedElement->SetKind(DXIL::SemanticKind::Arbitrary);
  AddedElement->SetUsageMask(1);
  sig.AppendElement(std::move(AddedElement));

  FindOrAddVSInSignatureElementForInstanceOrVertexID(
      sig, DXIL::SemanticKind::InstanceID);
  FindOrAddVSInSignatureElementForInstanceOrVertexID(
      sig, DXIL::SemanticKind::VertexID);

  VERIFY_ARE_EQUAL(3ull, sig.GetElements().size());
  // Not gonna check the first one cuz that would just be grading our own
  // homework
  VERIFY_ARE_EQUAL(sig.GetElement(1).GetKind(), DXIL::SemanticKind::InstanceID);
  VERIFY_ARE_EQUAL(sig.GetElement(1).GetCols(), 1u);
  VERIFY_ARE_EQUAL(sig.GetElement(1).GetRows(), 1u);
  VERIFY_ARE_EQUAL(sig.GetElement(1).GetStartCol(), 0);
  VERIFY_ARE_EQUAL(sig.GetElement(1).GetStartRow(), 1);
  VERIFY_ARE_EQUAL(sig.GetElement(2).GetKind(), DXIL::SemanticKind::VertexID);
  VERIFY_ARE_EQUAL(sig.GetElement(2).GetCols(), 1u);
  VERIFY_ARE_EQUAL(sig.GetElement(2).GetRows(), 1u);
  VERIFY_ARE_EQUAL(sig.GetElement(2).GetStartCol(), 0);
  VERIFY_ARE_EQUAL(sig.GetElement(2).GetStartRow(), 2);
}

void PixTest::ValidateAccessTrackingMods(const char *hlsl, bool modsExpected) {
  auto code = Compile(m_dllSupport, hlsl, L"ps_6_6", {L"-Od"}, L"main");
  auto result = RunShaderAccessTrackingPass(code).lines;
  bool hasMods = true;
  for (auto const &line : result)
    if (line.find("NotModified") != std::string::npos)
      hasMods = false;
  VERIFY_ARE_EQUAL(modsExpected, hasMods);
}

TEST_F(PixTest, AccessTracking_ModificationReport_Nothing) {
  const char *hlsl = R"(
float main() : SV_Target 
{
  return 0;
}
)";
  ValidateAccessTrackingMods(hlsl, false);
}

TEST_F(PixTest, AccessTracking_ModificationReport_Read) {
  const char *hlsl = R"(
RWByteAddressBuffer g_texture;
float main() : SV_Target 
{
  return g_texture.Load(0);
}
)";
  ValidateAccessTrackingMods(hlsl, true);
}

TEST_F(PixTest, AccessTracking_ModificationReport_Write) {
  const char *hlsl = R"(
RWByteAddressBuffer g_texture;
float main() : SV_Target 
{
  g_texture.Store(0, 0);
  return 0;
}
)";
  ValidateAccessTrackingMods(hlsl, true);
}

TEST_F(PixTest, AccessTracking_ModificationReport_SM66) {
  const char *hlsl = R"(
float main() : SV_Target 
{
    RWByteAddressBuffer g_texture = ResourceDescriptorHeap[0];
    g_texture.Store(0, 0);
    return 0;
}
)";
  ValidateAccessTrackingMods(hlsl, true);
}

TEST_F(PixTest, AddToASGroupSharedPayload) {

  const char *hlsl = R"(
struct Contained
{
    uint j;
    float af[3];
};

struct Bigger
{
    half h;
    void Init() { h = 1.f; }
  Contained a[2];
};

struct MyPayload
{
    uint i;
    Bigger big[3];
};

groupshared MyPayload payload;

[numthreads(1, 1, 1)]
void main(uint gid : SV_GroupID)
{
  DispatchMesh(1, 1, 1, payload);
}

  )";

  auto as = Compile(m_dllSupport, hlsl, L"as_6_6", {L"-Od"}, L"main");
  RunDxilPIXAddTidToAmplificationShaderPayloadPass(as);
}

TEST_F(PixTest, AddToASGroupSharedPayload_MeshletCullSample) {

  const char *hlsl = R"(
struct MyPayload
{
    uint i[32];
};

groupshared MyPayload payload;

[numthreads(1, 1, 1)]
void main(uint gid : SV_GroupID)
{
  DispatchMesh(1, 1, 1, payload);
}

  )";

  auto as = Compile(m_dllSupport, hlsl, L"as_6_6", {L"-Od"}, L"main");
  RunDxilPIXAddTidToAmplificationShaderPayloadPass(as);
}
static llvm::DIType *PeelTypedefs(llvm::DIType *diTy) {
  using namespace llvm;
  const llvm::DITypeIdentifierMap EmptyMap;
  while (1) {
    DIDerivedType *diDerivedTy = dyn_cast<DIDerivedType>(diTy);
    if (!diDerivedTy)
      return diTy;

    switch (diTy->getTag()) {
    case dwarf::DW_TAG_member:
    case dwarf::DW_TAG_inheritance:
    case dwarf::DW_TAG_typedef:
    case dwarf::DW_TAG_reference_type:
    case dwarf::DW_TAG_const_type:
    case dwarf::DW_TAG_restrict_type:
      diTy = diDerivedTy->getBaseType().resolve(EmptyMap);
      break;
    default:
      return diTy;
    }
  }

  return diTy;
}

static unsigned GetDITypeSizeInBits(llvm::DIType *diTy) {
  return PeelTypedefs(diTy)->getSizeInBits();
}

static unsigned GetDITypeAlignmentInBits(llvm::DIType *diTy) {
  return PeelTypedefs(diTy)->getAlignInBits();
}

static bool FindStructMemberFromStore(llvm::StoreInst *S,
                                      std::string *OutMemberName) {
  using namespace llvm;
  Value *Ptr = S->getPointerOperand();
  AllocaInst *Alloca = nullptr;

  auto &DL = S->getModule()->getDataLayout();

  unsigned OffsetInAlloca = 0;
  while (Ptr) {
    if (auto AI = dyn_cast<AllocaInst>(Ptr)) {
      Alloca = AI;
      break;
    } else if (auto Gep = dyn_cast<GEPOperator>(Ptr)) {
      if (Gep->getNumIndices() < 2 || !Gep->hasAllConstantIndices() ||
          0 != cast<ConstantInt>(Gep->getOperand(1))->getLimitedValue()) {
        return false;
      }

      auto GepSrcPtr = Gep->getPointerOperand();
      Type *GepSrcPtrTy = GepSrcPtr->getType()->getPointerElementType();

      Type *PeelingType = GepSrcPtrTy;
      for (unsigned i = 1; i < Gep->getNumIndices(); i++) {
        uint64_t Idx =
            cast<ConstantInt>(Gep->getOperand(1 + i))->getLimitedValue();

        if (PeelingType->isStructTy()) {
          auto StructTy = cast<StructType>(PeelingType);
          unsigned Offset =
              DL.getStructLayout(StructTy)->getElementOffsetInBits(Idx);
          OffsetInAlloca += Offset;
          PeelingType = StructTy->getElementType(Idx);
        } else if (PeelingType->isVectorTy()) {
          OffsetInAlloca +=
              DL.getTypeSizeInBits(PeelingType->getVectorElementType()) * Idx;
          PeelingType = PeelingType->getVectorElementType();
        } else if (PeelingType->isArrayTy()) {
          OffsetInAlloca +=
              DL.getTypeSizeInBits(PeelingType->getArrayElementType()) * Idx;
          PeelingType = PeelingType->getArrayElementType();
        } else {
          return false;
        }
      }

      Ptr = GepSrcPtr;
    } else {
      return false;
    }
  }

  // If there's not exactly one dbg.* inst, give up for now.
  if (hlsl::dxilutil::mdv_user_empty(Alloca) ||
      std::next(hlsl::dxilutil::mdv_users_begin(Alloca)) !=
          hlsl::dxilutil::mdv_users_end(Alloca)) {
    return false;
  }

  auto DI = dyn_cast<DbgDeclareInst>(*hlsl::dxilutil::mdv_users_begin(Alloca));
  if (!DI)
    return false;

  DILocalVariable *diVar = DI->getVariable();
  DIExpression *diExpr = DI->getExpression();
  const llvm::DITypeIdentifierMap EmptyMap;
  DIType *diType = diVar->getType().resolve(EmptyMap);

  unsigned MemberOffset = OffsetInAlloca;
  if (diExpr->isBitPiece()) {
    MemberOffset += diExpr->getBitPieceOffset();
  }

  diType = PeelTypedefs(diType);
  if (!isa<DICompositeType>(diType))
    return false;

  unsigned OffsetInDI = 0;
  std::string MemberName;

  //=====================================================
  // Find the correct member based on size
  while (diType) {
    diType = PeelTypedefs(diType);
    if (DICompositeType *diCompType = dyn_cast<DICompositeType>(diType)) {
      if (diCompType->getTag() == dwarf::DW_TAG_structure_type ||
          diCompType->getTag() == dwarf::DW_TAG_class_type) {
        bool FoundCompositeMember = false;
        for (DINode *Elem : diCompType->getElements()) {
          auto diElemType = dyn_cast<DIType>(Elem);
          if (!diElemType)
            return false;

          StringRef CurMemberName;
          if (diElemType->getTag() == dwarf::DW_TAG_member) {
            CurMemberName = diElemType->getName();
          } else if (diElemType->getTag() == dwarf::DW_TAG_inheritance) {
          } else {
            return false;
          }

          unsigned CompositeMemberSize = GetDITypeSizeInBits(diElemType);
          unsigned CompositeMemberAlignment =
              GetDITypeAlignmentInBits(diElemType);

          assert(CompositeMemberAlignment);
          OffsetInDI =
              llvm::RoundUpToAlignment(OffsetInDI, CompositeMemberAlignment);

          if (OffsetInDI <= MemberOffset &&
              MemberOffset < OffsetInDI + CompositeMemberSize) {
            diType = diElemType;
            if (CurMemberName.size()) {
              if (MemberName.size())
                MemberName += ".";
              MemberName += CurMemberName;
            }
            FoundCompositeMember = true;
            break;
          }

          // TODO: How will we match up the padding?
          OffsetInDI += CompositeMemberSize;
        }

        if (!FoundCompositeMember)
          return false;
      }
      // For arrays, just flatten it for now.
      // TODO: multi-dimension array
      else if (diCompType->getTag() == dwarf::DW_TAG_array_type) {
        if (MemberOffset < OffsetInDI ||
            MemberOffset >= OffsetInDI + diCompType->getSizeInBits())
          return false;
        DIType *diArrayElemType = diCompType->getBaseType().resolve(EmptyMap);

        {
          unsigned CurSize = diCompType->getSizeInBits();
          unsigned CurOffset = MemberOffset - OffsetInDI;
          for (DINode *SubrangeMD : diCompType->getElements()) {
            DISubrange *Range = cast<DISubrange>(SubrangeMD);

            unsigned ElemSize = CurSize / Range->getCount();
            unsigned Idx = CurOffset / ElemSize;

            CurOffset -= ElemSize * Idx;
            CurSize = ElemSize;

            MemberName += "[";
            MemberName += std::to_string(Idx);
            MemberName += "]";
          }
        }

        unsigned ArrayElemSize = GetDITypeSizeInBits(diArrayElemType);
        unsigned FlattenedIdx = (MemberOffset - OffsetInDI) / ArrayElemSize;
        OffsetInDI += FlattenedIdx * ArrayElemSize;
        diType = diArrayElemType;
      } else {
        return false;
      }
    } else if (DIBasicType *diBasicType = dyn_cast<DIBasicType>(diType)) {
      if (OffsetInDI == MemberOffset) {
        *OutMemberName = MemberName;
        return true;
      }

      OffsetInDI += diBasicType->getSizeInBits();
      return false;
    } else {
      return false;
    }
  }

  return false;
}

std::string PixTest::Disassemble(IDxcBlob *pProgram) {
  CComPtr<IDxcCompiler> pCompiler;
  CComPtr<IDxcOperationResult> pResult;
  CComPtr<IDxcBlobEncoding> pSource;
  VERIFY_SUCCEEDED(CreateCompiler(m_dllSupport, &pCompiler));
  CComPtr<IDxcBlobEncoding> pDisassembly;
  VERIFY_SUCCEEDED(pCompiler->Disassemble(pProgram, &pDisassembly));
  return BlobToUtf8(pDisassembly);
}

// This function lives in lib\DxilPIXPasses\DxilAnnotateWithVirtualRegister.cpp
// Declared here so we can test it.
uint32_t CountStructMembers(llvm::Type const *pType);

PixTest::TestableResults PixTest::TestStructAnnotationCase(
    const char *hlsl, const wchar_t *optimizationLevel, bool validateCoverage,
    const wchar_t *profile) {
  CComPtr<IDxcBlob> pBlob =
      Compile(m_dllSupport, hlsl, profile,
              {optimizationLevel, L"-HV", L"2018", L"-enable-16bit-types"});

  CComPtr<IDxcBlob> pDxil = FindModule(DFCC_ShaderDebugInfoDXIL, pBlob);

  PassOutput passOutput = RunAnnotationPasses(m_dllSupport, pDxil);

  auto pAnnotated = passOutput.blob;

  CComPtr<IDxcBlob> pAnnotatedContainer;
  ReplaceDxilBlobPart(pBlob->GetBufferPointer(), pBlob->GetBufferSize(),
                      pAnnotated, &pAnnotatedContainer);

#if 0 // handy for debugging
  auto disTextW = Disassemble(pAnnotatedContainer);
#endif

  ModuleAndHangersOn moduleEtc(pAnnotatedContainer);
  PixTest::TestableResults ret;

  // For every dbg.declare, run the member iterator and record what it finds:
  auto entryPoints = moduleEtc.GetDxilModule().GetExportedFunctions();
  for (auto &entryFunction : entryPoints) {
    for (auto &block : entryFunction->getBasicBlockList()) {
      for (auto &instruction : block.getInstList()) {
        if (auto *dbgDeclare =
                llvm::dyn_cast<llvm::DbgDeclareInst>(&instruction)) {
          llvm::Value *Address = dbgDeclare->getAddress();
          auto *AddressAsAlloca = llvm::dyn_cast<llvm::AllocaInst>(Address);
          if (AddressAsAlloca != nullptr) {
            auto *Expression = dbgDeclare->getExpression();

            std::unique_ptr<dxil_debug_info::MemberIterator> iterator =
                dxil_debug_info::CreateMemberIterator(
                    dbgDeclare,
                    moduleEtc.GetDxilModule().GetModule()->getDataLayout(),
                    AddressAsAlloca, Expression);

            unsigned int startingBit = 0;
            unsigned int coveredBits = 0;
            unsigned int memberIndex = 0;
            unsigned int memberCount = 0;
            while (iterator->Next(&memberIndex)) {
              memberCount++;
              if (memberIndex == 0) {
                startingBit = iterator->OffsetInBits(memberIndex);
                coveredBits = iterator->SizeInBits(memberIndex);
              } else {
                coveredBits = std::max<unsigned int>(
                    coveredBits, iterator->OffsetInBits(memberIndex) +
                                     iterator->SizeInBits(memberIndex));
              }
            }

            AggregateOffsetAndSize OffsetAndSize = {};
            OffsetAndSize.countOfMembers = memberCount;
            OffsetAndSize.offset = startingBit;
            OffsetAndSize.size = coveredBits;
            ret.OffsetAndSizes.push_back(OffsetAndSize);

            // Use this independent count of number of struct members to test
            // the function that operates on the alloca type:
            llvm::Type *pAllocaTy =
                AddressAsAlloca->getType()->getElementType();
            if (auto *AT = llvm::dyn_cast<llvm::ArrayType>(pAllocaTy)) {
              // This is the case where a struct is passed to a function, and
              // in these tests there should be only one struct behind the
              // pointer.
              VERIFY_ARE_EQUAL(AT->getNumElements(), 1u);
              pAllocaTy = AT->getArrayElementType();
            }

            if (auto *ST = llvm::dyn_cast<llvm::StructType>(pAllocaTy)) {
              uint32_t countOfMembers = CountStructMembers(ST);
              // memberIndex might be greater, because the fragment iterator
              // also includes contained derived types as fragments, in
              // addition to the members of that contained derived types.
              // CountStructMembers only counts the leaf-node types.
              VERIFY_ARE_EQUAL(countOfMembers, memberCount);
            } else if (pAllocaTy->isFloatingPointTy() ||
                       pAllocaTy->isIntegerTy()) {
              // If there's only one member in the struct in the
              // pass-to-function (by pointer) case, then the underlying type
              // will have been reduced to the contained type.
              VERIFY_ARE_EQUAL(1u, memberCount);
            } else {
              VERIFY_IS_TRUE(false);
            }
          }
        }
      }
    }

    // The member iterator should find a solid run of bits that is exactly
    // covered by exactly one of the members found by the annotation pass:
    if (validateCoverage) {
      unsigned CurRegIdx = 0;
      for (AggregateOffsetAndSize const &cover :
           ret.OffsetAndSizes) // For each entry read from member iterators
                               // and dbg.declares
      {
        bool found = false;
        for (ValueLocation const &valueLocation :
             passOutput.valueLocations) // For each allocas and dxil values
        {
          if (CurRegIdx == (unsigned)valueLocation.base &&
              (unsigned)valueLocation.count == cover.countOfMembers) {
            VERIFY_IS_FALSE(found);
            found = true;
          }
        }
        VERIFY_IS_TRUE(found);
        CurRegIdx += cover.countOfMembers;
      }
    }

    // For every store operation to the struct alloca, check that the
    // annotation pass correctly determined which alloca
    for (auto &block : entryFunction->getBasicBlockList()) {
      for (auto &instruction : block.getInstList()) {
        if (auto *store = llvm::dyn_cast<llvm::StoreInst>(&instruction)) {

          AllocaWrite NewAllocaWrite = {};
          if (FindStructMemberFromStore(store, &NewAllocaWrite.memberName)) {
            llvm::Value *index;
            if (pix_dxil::PixAllocaRegWrite::FromInst(
                    store, &NewAllocaWrite.regBase, &NewAllocaWrite.regSize,
                    &index)) {
              auto *asInt = llvm::dyn_cast<llvm::ConstantInt>(index);
              NewAllocaWrite.index = asInt->getLimitedValue();
              ret.AllocaWrites.push_back(NewAllocaWrite);
            }
          }
        }
      }
    }
  }
  return ret;
}

void PixTest::ValidateAllocaWrite(std::vector<AllocaWrite> const &allocaWrites,
                                  size_t index, const char *name) {
  VERIFY_ARE_EQUAL(index,
                   allocaWrites[index].regBase + allocaWrites[index].index);
#ifndef NDEBUG
  // Compilation may add a prefix to the struct member name:
  VERIFY_IS_TRUE(
      0 == strncmp(name, allocaWrites[index].memberName.c_str(), strlen(name)));
#endif
}

struct OptimizationChoice {
  const wchar_t *Flag;
  bool IsOptimized;
};
static const OptimizationChoice OptimizationChoices[] = {
    {L"-Od", false},
    {L"-O1", true},
};

TEST_F(PixTest, PixStructAnnotation_Lib_DualRaygen) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;
    const char *hlsl = R"(

RaytracingAccelerationStructure Scene : register(t0, space0);
RWTexture2D<float4> RenderTarget : register(u0);

struct SceneConstantBuffer
{
    float4x4 projectionToWorld;
    float4 cameraPosition;
    float4 lightPosition;
    float4 lightAmbientColor;
    float4 lightDiffuseColor;
};

ConstantBuffer<SceneConstantBuffer> g_sceneCB : register(b0);

struct RayPayload
{
    float4 color;
};

inline void GenerateCameraRay(uint2 index, out float3 origin, out float3 direction)
{
    float2 xy = index + 0.5f; // center in the middle of the pixel.
    float2 screenPos = xy;// / DispatchRaysDimensions().xy * 2.0 - 1.0;

    // Invert Y for DirectX-style coordinates.
    screenPos.y = -screenPos.y;

    // Unproject the pixel coordinate into a ray.
    float4 world = /*mul(*/float4(screenPos, 0, 1)/*, g_sceneCB.projectionToWorld)*/;

    //world.xyz /= world.w;
    origin = world.xyz; //g_sceneCB.cameraPosition.xyz;
    direction = float3(1,0,0);//normalize(world.xyz - origin);
}

void RaygenCommon()
{
    float3 rayDir;
    float3 origin;
    
    // Generate a ray for a camera pixel corresponding to an index from the dispatched 2D grid.
    GenerateCameraRay(DispatchRaysIndex().xy, origin, rayDir);

    // Trace the ray.
    // Set the ray's extents.
    RayDesc ray;
    ray.Origin = origin;
    ray.Direction = rayDir;
    // Set TMin to a non-zero small value to avoid aliasing issues due to floating - point errors.
    // TMin should be kept small to prevent missing geometry at close contact areas.
    ray.TMin = 0.001;
    ray.TMax = 10000.0;
    RayPayload payload = { float4(0, 0, 0, 0) };
    TraceRay(Scene, RAY_FLAG_CULL_BACK_FACING_TRIANGLES, ~0, 0, 1, 0, ray, payload);

    // Write the raytraced color to the output texture.
   // RenderTarget[DispatchRaysIndex().xy] = payload.color;
}

[shader("raygeneration")]
void Raygen0()
{
    RaygenCommon();
}

[shader("raygeneration")]
void Raygen1()
{
    RaygenCommon();
}
)";

    // This is just a crash test until we decide what the right way forward
    CComPtr<IDxcBlob> pBlob =
        Compile(m_dllSupport, hlsl, L"lib_6_6", {optimization});
    CComPtr<IDxcBlob> pDxil = FindModule(DFCC_ShaderDebugInfoDXIL, pBlob);
    RunAnnotationPasses(m_dllSupport, pDxil);
  }
}

TEST_F(PixTest, PixStructAnnotation_Simple) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;
    const char *hlsl = R"(
struct smallPayload
{
    uint dummy;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.dummy = 42;
    DispatchMesh(1, 1, 1, p);
}
)";

    auto Testables = TestStructAnnotationCase(hlsl, optimization);

    if (!Testables.OffsetAndSizes.empty()) {
      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes.size());
      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[0].countOfMembers);
      VERIFY_ARE_EQUAL(0u, Testables.OffsetAndSizes[0].offset);
      VERIFY_ARE_EQUAL(32u, Testables.OffsetAndSizes[0].size);
    }

    VERIFY_ARE_EQUAL(1u, Testables.AllocaWrites.size());
    ValidateAllocaWrite(Testables.AllocaWrites, 0, "dummy");
  }
}

TEST_F(PixTest, PixStructAnnotation_CopiedStruct) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;
  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;

    const char *hlsl = R"(
struct smallPayload
{
    uint dummy;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.dummy = 42;
    smallPayload p2 = p;
    DispatchMesh(1, 1, 1, p2);
}
)";

    auto Testables = TestStructAnnotationCase(hlsl, optimization);

    // 2 in unoptimized case (one for each instance of smallPayload)
    // 1 in optimized case (cuz p2 aliases over p)
    VERIFY_IS_TRUE(Testables.OffsetAndSizes.size() >= 1);

    for (const auto &os : Testables.OffsetAndSizes) {
      VERIFY_ARE_EQUAL(1u, os.countOfMembers);
      VERIFY_ARE_EQUAL(0u, os.offset);
      VERIFY_ARE_EQUAL(32u, os.size);
    }

    VERIFY_ARE_EQUAL(1u, Testables.AllocaWrites.size());
  }
}

TEST_F(PixTest, PixStructAnnotation_MixedSizes) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;

    const char *hlsl = R"(
struct smallPayload
{
    bool b1;
    uint16_t sixteen;
    uint32_t thirtytwo;
    uint64_t sixtyfour;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.b1 = true;
    p.sixteen = 16;
    p.thirtytwo = 32;
    p.sixtyfour = 64;
    DispatchMesh(1, 1, 1, p);
}
)";

    auto Testables = TestStructAnnotationCase(hlsl, optimization);

    if (!choice.IsOptimized) {
      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes.size());
      VERIFY_ARE_EQUAL(4u, Testables.OffsetAndSizes[0].countOfMembers);
      VERIFY_ARE_EQUAL(0u, Testables.OffsetAndSizes[0].offset);
      // 8 bytes align for uint64_t:
      VERIFY_ARE_EQUAL(32u + 16u + 16u /*alignment for next field*/ + 32u +
                           32u /*alignment for max align*/ + 64u,
                       Testables.OffsetAndSizes[0].size);
    } else {
      VERIFY_ARE_EQUAL(4u, Testables.OffsetAndSizes.size());

      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[0].countOfMembers);
      VERIFY_ARE_EQUAL(0u, Testables.OffsetAndSizes[0].offset);
      VERIFY_ARE_EQUAL(32u, Testables.OffsetAndSizes[0].size);

      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[1].countOfMembers);
      VERIFY_ARE_EQUAL(32u, Testables.OffsetAndSizes[1].offset);
      VERIFY_ARE_EQUAL(16u, Testables.OffsetAndSizes[1].size);

      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[2].countOfMembers);
      VERIFY_ARE_EQUAL(32u + 32u, Testables.OffsetAndSizes[2].offset);
      VERIFY_ARE_EQUAL(32u, Testables.OffsetAndSizes[2].size);

      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[3].countOfMembers);
      VERIFY_ARE_EQUAL(32u + 32u + 32u + /*padding for alignment*/ 32u,
                       Testables.OffsetAndSizes[3].offset);
      VERIFY_ARE_EQUAL(64u, Testables.OffsetAndSizes[3].size);
    }

    VERIFY_ARE_EQUAL(4u, Testables.AllocaWrites.size());
    ValidateAllocaWrite(Testables.AllocaWrites, 0, "b1");
    ValidateAllocaWrite(Testables.AllocaWrites, 1, "sixteen");
    ValidateAllocaWrite(Testables.AllocaWrites, 2, "thirtytwo");
    ValidateAllocaWrite(Testables.AllocaWrites, 3, "sixtyfour");
  }
}

TEST_F(PixTest, PixStructAnnotation_StructWithinStruct) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;

    const char *hlsl = R"(

struct Contained
{
  uint32_t one;
  uint32_t two;
};

struct smallPayload
{
  uint32_t before;
  Contained contained;
  uint32_t after;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.before = 0xb4;
    p.contained.one = 1;
    p.contained.two = 2;
    p.after = 3;
    DispatchMesh(1, 1, 1, p);
}
)";

    auto Testables = TestStructAnnotationCase(hlsl, optimization);

    if (!choice.IsOptimized) {
      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes.size());
      VERIFY_ARE_EQUAL(4u, Testables.OffsetAndSizes[0].countOfMembers);
      VERIFY_ARE_EQUAL(0u, Testables.OffsetAndSizes[0].offset);
      VERIFY_ARE_EQUAL(4u * 32u, Testables.OffsetAndSizes[0].size);
    } else {
      VERIFY_ARE_EQUAL(4u, Testables.OffsetAndSizes.size());
      for (unsigned i = 0; i < 4; i++) {
        VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[i].countOfMembers);
        VERIFY_ARE_EQUAL(i * 32u, Testables.OffsetAndSizes[i].offset);
        VERIFY_ARE_EQUAL(32u, Testables.OffsetAndSizes[i].size);
      }
    }

    ValidateAllocaWrite(Testables.AllocaWrites, 0, "before");
    ValidateAllocaWrite(Testables.AllocaWrites, 1, "contained.one");
    ValidateAllocaWrite(Testables.AllocaWrites, 2, "contained.two");
    ValidateAllocaWrite(Testables.AllocaWrites, 3, "after");
  }
}

TEST_F(PixTest, PixStructAnnotation_1DArray) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;

    const char *hlsl = R"(
struct smallPayload
{
    uint32_t Array[2];
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.Array[0] = 250;
    p.Array[1] = 251;
    DispatchMesh(1, 1, 1, p);
}
)";

    auto Testables = TestStructAnnotationCase(hlsl, optimization);
    if (!choice.IsOptimized) {
      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes.size());
      VERIFY_ARE_EQUAL(2u, Testables.OffsetAndSizes[0].countOfMembers);
      VERIFY_ARE_EQUAL(0u, Testables.OffsetAndSizes[0].offset);
      VERIFY_ARE_EQUAL(2u * 32u, Testables.OffsetAndSizes[0].size);
    } else {
      VERIFY_ARE_EQUAL(2u, Testables.OffsetAndSizes.size());
      for (unsigned i = 0; i < 2; i++) {
        VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[i].countOfMembers);
        VERIFY_ARE_EQUAL(i * 32u, Testables.OffsetAndSizes[i].offset);
        VERIFY_ARE_EQUAL(32u, Testables.OffsetAndSizes[i].size);
      }
    }
    VERIFY_ARE_EQUAL(2u, Testables.AllocaWrites.size());

    int Idx = 0;
    ValidateAllocaWrite(Testables.AllocaWrites, Idx++, "Array[0]");
    ValidateAllocaWrite(Testables.AllocaWrites, Idx++, "Array[1]");
  }
}

TEST_F(PixTest, PixStructAnnotation_2DArray) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;
    const char *hlsl = R"(
struct smallPayload
{
    uint32_t TwoDArray[2][3];
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.TwoDArray[0][0] = 250;
    p.TwoDArray[0][1] = 251;
    p.TwoDArray[0][2] = 252;
    p.TwoDArray[1][0] = 253;
    p.TwoDArray[1][1] = 254;
    p.TwoDArray[1][2] = 255;
    DispatchMesh(1, 1, 1, p);
}
)";

    auto Testables = TestStructAnnotationCase(hlsl, optimization);
    if (!choice.IsOptimized) {
      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes.size());
      VERIFY_ARE_EQUAL(6u, Testables.OffsetAndSizes[0].countOfMembers);
      VERIFY_ARE_EQUAL(0u, Testables.OffsetAndSizes[0].offset);
      VERIFY_ARE_EQUAL(2u * 3u * 32u, Testables.OffsetAndSizes[0].size);
    } else {
      VERIFY_ARE_EQUAL(6u, Testables.OffsetAndSizes.size());
      for (unsigned i = 0; i < 6; i++) {
        VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[i].countOfMembers);
        VERIFY_ARE_EQUAL(i * 32u, Testables.OffsetAndSizes[i].offset);
        VERIFY_ARE_EQUAL(32u, Testables.OffsetAndSizes[i].size);
      }
    }
    VERIFY_ARE_EQUAL(6u, Testables.AllocaWrites.size());

    int Idx = 0;
    ValidateAllocaWrite(Testables.AllocaWrites, Idx++, "TwoDArray[0][0]");
    ValidateAllocaWrite(Testables.AllocaWrites, Idx++, "TwoDArray[0][1]");
    ValidateAllocaWrite(Testables.AllocaWrites, Idx++, "TwoDArray[0][2]");
    ValidateAllocaWrite(Testables.AllocaWrites, Idx++, "TwoDArray[1][0]");
    ValidateAllocaWrite(Testables.AllocaWrites, Idx++, "TwoDArray[1][1]");
    ValidateAllocaWrite(Testables.AllocaWrites, Idx++, "TwoDArray[1][2]");
  }
}

TEST_F(PixTest, PixStructAnnotation_EmbeddedArray) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;
    const char *hlsl = R"(

struct Contained
{
  uint32_t array[3];
};

struct smallPayload
{
  uint32_t before;
  Contained contained;
  uint32_t after;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.before = 0xb4;
    p.contained.array[0] = 0;
    p.contained.array[1] = 1;
    p.contained.array[2] = 2;
    p.after = 3;
    DispatchMesh(1, 1, 1, p);
}
)";

    auto Testables = TestStructAnnotationCase(hlsl, optimization);

    if (!choice.IsOptimized) {
      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes.size());
      VERIFY_ARE_EQUAL(5u, Testables.OffsetAndSizes[0].countOfMembers);
      VERIFY_ARE_EQUAL(0u, Testables.OffsetAndSizes[0].offset);
      VERIFY_ARE_EQUAL(5u * 32u, Testables.OffsetAndSizes[0].size);
    } else {
      VERIFY_ARE_EQUAL(5u, Testables.OffsetAndSizes.size());
      for (unsigned i = 0; i < 5; i++) {
        VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[i].countOfMembers);
        VERIFY_ARE_EQUAL(i * 32u, Testables.OffsetAndSizes[i].offset);
        VERIFY_ARE_EQUAL(32u, Testables.OffsetAndSizes[i].size);
      }
    }

    ValidateAllocaWrite(Testables.AllocaWrites, 0, "before");
    ValidateAllocaWrite(Testables.AllocaWrites, 1, "contained.array[0]");
    ValidateAllocaWrite(Testables.AllocaWrites, 2, "contained.array[1]");
    ValidateAllocaWrite(Testables.AllocaWrites, 3, "contained.array[2]");
    ValidateAllocaWrite(Testables.AllocaWrites, 4, "after");
  }
}

TEST_F(PixTest, PixStructAnnotation_FloatN) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;
    auto IsOptimized = choice.IsOptimized;
    const char *hlsl = R"(
struct smallPayload
{
    float2 f2;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.f2 = float2(1,2);
    DispatchMesh(1, 1, 1, p);
}
)";

    auto Testables = TestStructAnnotationCase(hlsl, optimization);

    if (IsOptimized) {
      VERIFY_ARE_EQUAL(2u, Testables.OffsetAndSizes.size());
      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[0].countOfMembers);
      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[1].countOfMembers);
      VERIFY_ARE_EQUAL(0u, Testables.OffsetAndSizes[0].offset);
      VERIFY_ARE_EQUAL(32u, Testables.OffsetAndSizes[0].size);
      VERIFY_ARE_EQUAL(32u, Testables.OffsetAndSizes[1].offset);
      VERIFY_ARE_EQUAL(32u, Testables.OffsetAndSizes[1].size);
    } else {
      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes.size());
      VERIFY_ARE_EQUAL(2u, Testables.OffsetAndSizes[0].countOfMembers);
      VERIFY_ARE_EQUAL(0u, Testables.OffsetAndSizes[0].offset);
      VERIFY_ARE_EQUAL(32u + 32u, Testables.OffsetAndSizes[0].size);
    }

    VERIFY_ARE_EQUAL(Testables.AllocaWrites.size(), 2u);
    ValidateAllocaWrite(Testables.AllocaWrites, 0, "f2.x");
    ValidateAllocaWrite(Testables.AllocaWrites, 1, "f2.y");
  }
}

TEST_F(PixTest, PixStructAnnotation_SequentialFloatN) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;
    const char *hlsl = R"(
struct smallPayload
{
    float3 color;
    float3 dir;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.color = float3(1,2,3);
    p.dir = float3(4,5,6);

    DispatchMesh(1, 1, 1, p);
}
)";

    auto Testables = TestStructAnnotationCase(hlsl, optimization);

    if (choice.IsOptimized) {
      VERIFY_ARE_EQUAL(6u, Testables.OffsetAndSizes.size());
      for (unsigned i = 0; i < 6; i++) {
        VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[i].countOfMembers);
        VERIFY_ARE_EQUAL(i * 32u, Testables.OffsetAndSizes[i].offset);
        VERIFY_ARE_EQUAL(32u, Testables.OffsetAndSizes[i].size);
      }
    } else {
      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes.size());
      VERIFY_ARE_EQUAL(6u, Testables.OffsetAndSizes[0].countOfMembers);
      VERIFY_ARE_EQUAL(0u, Testables.OffsetAndSizes[0].offset);
      VERIFY_ARE_EQUAL(32u * 6u, Testables.OffsetAndSizes[0].size);
    }

    VERIFY_ARE_EQUAL(6u, Testables.AllocaWrites.size());
    ValidateAllocaWrite(Testables.AllocaWrites, 0, "color.x");
    ValidateAllocaWrite(Testables.AllocaWrites, 1, "color.y");
    ValidateAllocaWrite(Testables.AllocaWrites, 2, "color.z");
    ValidateAllocaWrite(Testables.AllocaWrites, 3, "dir.x");
    ValidateAllocaWrite(Testables.AllocaWrites, 4, "dir.y");
    ValidateAllocaWrite(Testables.AllocaWrites, 5, "dir.z");
  }
}

TEST_F(PixTest, PixStructAnnotation_EmbeddedFloatN) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;
    const char *hlsl = R"(

struct Embedded
{
    float2 f2;
};

struct smallPayload
{
  uint32_t i32;
  Embedded e;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.i32 = 32;
    p.e.f2 = float2(1,2);
    DispatchMesh(1, 1, 1, p);
}
)";

    auto Testables = TestStructAnnotationCase(hlsl, optimization);

    if (choice.IsOptimized) {
      VERIFY_ARE_EQUAL(3u, Testables.OffsetAndSizes.size());
      for (unsigned i = 0; i < 3; i++) {
        VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[i].countOfMembers);
        VERIFY_ARE_EQUAL(i * 32u, Testables.OffsetAndSizes[i].offset);
        VERIFY_ARE_EQUAL(32u, Testables.OffsetAndSizes[i].size);
      }
    } else {
      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes.size());
      VERIFY_ARE_EQUAL(3u, Testables.OffsetAndSizes[0].countOfMembers);
      VERIFY_ARE_EQUAL(0u, Testables.OffsetAndSizes[0].offset);
      VERIFY_ARE_EQUAL(32u * 3u, Testables.OffsetAndSizes[0].size);
    }

    VERIFY_ARE_EQUAL(3u, Testables.AllocaWrites.size());
    ValidateAllocaWrite(Testables.AllocaWrites, 0, "i32");
    ValidateAllocaWrite(Testables.AllocaWrites, 1, "e.f2.x");
    ValidateAllocaWrite(Testables.AllocaWrites, 2, "e.f2.y");
  }
}

TEST_F(PixTest, PixStructAnnotation_Matrix) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;
    const char *hlsl = R"(
struct smallPayload
{
  float4x4 mat;
};


[numthreads(1, 1, 1)]
void main()
{
  smallPayload p;
  p.mat = float4x4( 1,2,3,4, 5,6,7,8, 9,10,11,12, 13,14,15, 16);
  DispatchMesh(1, 1, 1, p);
}
)";

    auto Testables = TestStructAnnotationCase(hlsl, optimization);
    // Can't test member iterator until dbg.declare instructions are emitted
    // when structs contain pointers-to-pointers
    VERIFY_ARE_EQUAL(16u, Testables.AllocaWrites.size());
    for (int i = 0; i < 4; ++i) {
      for (int j = 0; j < 4; ++j) {
        std::string expected = std::string("mat._") + std::to_string(i + 1) +
                               std::to_string(j + 1);
        ValidateAllocaWrite(Testables.AllocaWrites, i * 4 + j,
                            expected.c_str());
      }
    }
  }
}

TEST_F(PixTest, PixStructAnnotation_MemberFunction) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;
    const char *hlsl = R"(

RWStructuredBuffer<float> floatRWUAV: register(u0);

struct smallPayload
{
    int i;
};

float2 signNotZero(float2 v)
{
 return (v > 0.0f ? float(1).xx : float(-1).xx);
}

float2 unpackUnorm2(uint packed)
{
 return (1.0 / 65535.0) * float2((packed >> 16) & 0xffff, packed & 0xffff);
}

float3 unpackOctahedralSnorm(float2 e)
{
 float3 v = float3(e.xy, 1.0f - abs(e.x) - abs(e.y));
 if (v.z < 0.0f) v.xy = (1.0f - abs(v.yx)) * signNotZero(v.xy);
 return normalize(v);
}

float3 unpackOctahedralUnorm(float2 e)
{
 return unpackOctahedralSnorm(e * 2.0f - 1.0f);
}

float2 unpackHalf2(uint packed)
{
 return float2(f16tof32(packed >> 16), f16tof32(packed & 0xffff));
}

struct Gbuffer
{
	float3 worldNormal;
	float3 objectNormal; //offset:12
	float linearZ; //24
	float prevLinearZ; //28
	float fwidthLinearZ; //32
	float fwidthObjectNormal; //36
	uint materialType; //40
	uint2 materialParams0; //44
	uint4 materialParams1; //52  <--------- this is the variable that's being covered twice (52*8 = 416 416)
	uint instanceId;  //68  <------- and there's one dword left over, as expected
	void load(int2 pixelPos, Texture2DArray<uint4> gbTex)
	{
	uint4 data0 = gbTex.Load(int4(pixelPos, 0, 0));
	uint4 data1 = gbTex.Load(int4(pixelPos, 1, 0));
	uint4 data2 = gbTex.Load(int4(pixelPos, 2, 0));
	worldNormal = unpackOctahedralUnorm(unpackUnorm2(data0.x));
	linearZ = f16tof32((data0.y >> 8) & 0xffff);
	materialType = (data0.y & 0xff);
	materialParams0 = data0.zw;
	materialParams1 = data1.xyzw;
	instanceId = data2.x;
	prevLinearZ = asfloat(data2.y);
	objectNormal = unpackOctahedralUnorm(unpackUnorm2(data2.z));
	float2 fwidth = unpackHalf2(data2.w);
	fwidthLinearZ = fwidth.x;
	fwidthObjectNormal = fwidth.y;
	}
};

Gbuffer loadGbuffer(int2 pixelPos, Texture2DArray<uint4> gbTex)
{
	Gbuffer output;
	output.load(pixelPos, gbTex);
	return output;
}

Texture2DArray<uint4> g_gbuffer : register(t0, space0);

[numthreads(1, 1, 1)]
void main()
{	
	const Gbuffer gbuffer = loadGbuffer(int2(0,0), g_gbuffer);
    smallPayload p;
    p.i = gbuffer.materialParams1.x + gbuffer.materialParams1.y + gbuffer.materialParams1.z + gbuffer.materialParams1.w;
    DispatchMesh(1, 1, 1, p);
}


)";
    auto Testables = TestStructAnnotationCase(hlsl, optimization, true);

    // TODO: Make 'this' work

    // Can't validate # of writes: rel and dbg are different
    // VERIFY_ARE_EQUAL(43, Testables.AllocaWrites.size());

    // Can't test individual writes until struct member names are returned:
    // for (int i = 0; i < 51; ++i)
    //{
    //  ValidateAllocaWrite(Testables.AllocaWrites, i, "");
    //}
  }
}

TEST_F(PixTest, PixStructAnnotation_BigMess) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;

    const char *hlsl = R"(

struct BigStruct
{
    uint64_t bigInt;
    double bigDouble;
};

struct EmbeddedStruct
{
    uint32_t OneInt;
    uint32_t TwoDArray[2][2];
};

struct smallPayload
{
    uint dummy;
    uint vertexCount;
    uint primitiveCount;
    EmbeddedStruct embeddedStruct;
#ifdef PAYLOAD_MATRICES
    float4x4 mat;
#endif
    uint64_t bigOne;
    half littleOne;
    BigStruct bigStruct[2];
    uint lastCheck;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    // Adding enough instructions to make the shader interesting to debug:
    p.dummy = 42;
    p.vertexCount = 3;
    p.primitiveCount = 1;
    p.embeddedStruct.OneInt = 123;
    p.embeddedStruct.TwoDArray[0][0] = 252;
    p.embeddedStruct.TwoDArray[0][1] = 253;
    p.embeddedStruct.TwoDArray[1][0] = 254;
    p.embeddedStruct.TwoDArray[1][1] = 255;
#ifdef PAYLOAD_MATRICES
    p.mat = float4x4( 1,2,3,4, 5,6,7,8, 9,10,11,12, 13,14,15, 16);
#endif
    p.bigOne = 123456789;
    p.littleOne = 1.0;
    p.bigStruct[0].bigInt = 10;
    p.bigStruct[0].bigDouble = 2.0;
    p.bigStruct[1].bigInt = 20;
    p.bigStruct[1].bigDouble = 4.0;
    p.lastCheck = 27;
    DispatchMesh(1, 1, 1, p);
}
)";

    auto Testables = TestStructAnnotationCase(hlsl, optimization);
    if (!choice.IsOptimized) {
      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes.size());
      VERIFY_ARE_EQUAL(15u, Testables.OffsetAndSizes[0].countOfMembers);
      VERIFY_ARE_EQUAL(0u, Testables.OffsetAndSizes[0].offset);
      constexpr uint32_t BigStructBitSize = 64 * 2;
      constexpr uint32_t EmbeddedStructBitSize = 32 * 5;
      VERIFY_ARE_EQUAL(3u * 32u + EmbeddedStructBitSize + 64u + 16u +
                           16u /*alignment for next field*/ +
                           BigStructBitSize * 2u + 32u +
                           32u /*align to max align*/,
                       Testables.OffsetAndSizes[0].size);
    } else {
      VERIFY_ARE_EQUAL(15u, Testables.OffsetAndSizes.size());

      // First 8 members
      for (unsigned i = 0; i < 8; i++) {
        VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[i].countOfMembers);
        VERIFY_ARE_EQUAL(i * 32u, Testables.OffsetAndSizes[i].offset);
        VERIFY_ARE_EQUAL(32u, Testables.OffsetAndSizes[i].size);
      }

      // bigOne
      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[8].countOfMembers);
      VERIFY_ARE_EQUAL(256u, Testables.OffsetAndSizes[8].offset);
      VERIFY_ARE_EQUAL(64u, Testables.OffsetAndSizes[8].size);

      // littleOne
      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[9].countOfMembers);
      VERIFY_ARE_EQUAL(320u, Testables.OffsetAndSizes[9].offset);
      VERIFY_ARE_EQUAL(16u, Testables.OffsetAndSizes[9].size);

      // Each member of BigStruct[2]
      for (unsigned i = 0; i < 4; i++) {
        int idx = i + 10;
        VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[idx].countOfMembers);
        VERIFY_ARE_EQUAL(384 + i * 64u, Testables.OffsetAndSizes[idx].offset);
        VERIFY_ARE_EQUAL(64u, Testables.OffsetAndSizes[idx].size);
      }

      VERIFY_ARE_EQUAL(1u, Testables.OffsetAndSizes[14].countOfMembers);
      VERIFY_ARE_EQUAL(640u, Testables.OffsetAndSizes[14].offset);
      VERIFY_ARE_EQUAL(32u, Testables.OffsetAndSizes[14].size);
    }

    VERIFY_ARE_EQUAL(15u, Testables.AllocaWrites.size());

    size_t Index = 0;
    ValidateAllocaWrite(Testables.AllocaWrites, Index++, "dummy");
    ValidateAllocaWrite(Testables.AllocaWrites, Index++, "vertexCount");
    ValidateAllocaWrite(Testables.AllocaWrites, Index++, "primitiveCount");
    ValidateAllocaWrite(Testables.AllocaWrites, Index++,
                        "embeddedStruct.OneInt");
    ValidateAllocaWrite(Testables.AllocaWrites, Index++,
                        "embeddedStruct.TwoDArray[0][0]");
    ValidateAllocaWrite(Testables.AllocaWrites, Index++,
                        "embeddedStruct.TwoDArray[0][1]");
    ValidateAllocaWrite(Testables.AllocaWrites, Index++,
                        "embeddedStruct.TwoDArray[1][0]");
    ValidateAllocaWrite(Testables.AllocaWrites, Index++,
                        "embeddedStruct.TwoDArray[1][1]");
    ValidateAllocaWrite(Testables.AllocaWrites, Index++, "bigOne");
    ValidateAllocaWrite(Testables.AllocaWrites, Index++, "littleOne");
    ValidateAllocaWrite(Testables.AllocaWrites, Index++, "bigStruct[0].bigInt");
    ValidateAllocaWrite(Testables.AllocaWrites, Index++,
                        "bigStruct[0].bigDouble");
    ValidateAllocaWrite(Testables.AllocaWrites, Index++, "bigStruct[1].bigInt");
    ValidateAllocaWrite(Testables.AllocaWrites, Index++,
                        "bigStruct[1].bigDouble");
    ValidateAllocaWrite(Testables.AllocaWrites, Index++, "lastCheck");
  }
}

TEST_F(PixTest, PixStructAnnotation_AlignedFloat4Arrays) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;

    const char *hlsl = R"(

struct LinearSHSampleData
{
	float4 linearTerms[3];
	float4 hdrColorAO;
	float4 visibilitySH;
} g_lhSampleData;

struct smallPayload
{
    LinearSHSampleData lhSampleData;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.lhSampleData.linearTerms[0].x = g_lhSampleData.linearTerms[0].x;
    DispatchMesh(1, 1, 1, p);
}
)";

    auto Testables = TestStructAnnotationCase(hlsl, optimization);
    // Can't test offsets and sizes until dbg.declare instructions are emitted
    // when floatn is used
    // (https://github.com/microsoft/DirectXShaderCompiler/issues/2920)
    // VERIFY_ARE_EQUAL(20, Testables.AllocaWrites.size());
  }
}

TEST_F(PixTest, PixStructAnnotation_Inheritance) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;

    const char *hlsl = R"(
struct Base
{
    float floatValue;
};
typedef Base BaseTypedef;

struct Derived : BaseTypedef
{
	int intValue;
};

[numthreads(1, 1, 1)]
void main()
{
    Derived p;
    p.floatValue = 1.;
    p.intValue = 2;
    DispatchMesh(1, 1, 1, p);
}
)";

    auto Testables = TestStructAnnotationCase(hlsl, optimization);

    // Can't test offsets and sizes until dbg.declare instructions are emitted
    // when floatn is used
    // (https://github.com/microsoft/DirectXShaderCompiler/issues/2920)
    // VERIFY_ARE_EQUAL(20, Testables.AllocaWrites.size());
  }
}

TEST_F(PixTest, PixStructAnnotation_ResourceAsMember) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;

    const char *hlsl = R"(

Buffer g_texture;

struct smallPayload
{
    float value;
};

struct WithEmbeddedObject
{
	Buffer texture;
};

void DispatchIt(WithEmbeddedObject eo)
{
    smallPayload p;
    p.value = eo.texture.Load(0);
    DispatchMesh(1, 1, 1, p);
}

[numthreads(1, 1, 1)]
void main()
{
    WithEmbeddedObject eo;
    eo.texture = g_texture;
    DispatchIt(eo);
}
)";

    auto Testables = TestStructAnnotationCase(hlsl, optimization);
    // Can't test offsets and sizes until dbg.declare instructions are emitted
    // when floatn is used
    // (https://github.com/microsoft/DirectXShaderCompiler/issues/2920)
    // VERIFY_ARE_EQUAL(20, Testables.AllocaWrites.size());
  }
}

TEST_F(PixTest, PixStructAnnotation_WheresMyDbgValue) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;

    const char *hlsl = R"(

struct smallPayload
{
    float f1;
    float2 f2;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.f1 = 1;
    p.f2 = float2(2,3);
    DispatchMesh(1, 1, 1, p);
}
)";

    auto Testables = TestStructAnnotationCase(hlsl, optimization);
    // Can't test offsets and sizes until dbg.declare instructions are emitted
    // when floatn is used
    // (https://github.com/microsoft/DirectXShaderCompiler/issues/2920)
    VERIFY_ARE_EQUAL(3u, Testables.AllocaWrites.size());
  }
}

TEST_F(PixTest, VirtualRegisters_InstructionCounts) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  for (auto choice : OptimizationChoices) {
    auto optimization = choice.Flag;
    const char *hlsl = R"(

RaytracingAccelerationStructure Scene : register(t0, space0);
RWTexture2D<float4> RenderTarget : register(u0);

struct SceneConstantBuffer
{
    float4x4 projectionToWorld;
    float4 cameraPosition;
    float4 lightPosition;
    float4 lightAmbientColor;
    float4 lightDiffuseColor;
};

ConstantBuffer<SceneConstantBuffer> g_sceneCB : register(b0);

struct RayPayload
{
    float4 color;
};

inline void GenerateCameraRay(uint2 index, out float3 origin, out float3 direction)
{
    float2 xy = index + 0.5f; // center in the middle of the pixel.
    float2 screenPos = xy;// / DispatchRaysDimensions().xy * 2.0 - 1.0;

    // Invert Y for DirectX-style coordinates.
    screenPos.y = -screenPos.y;

    // Unproject the pixel coordinate into a ray.
    float4 world = /*mul(*/float4(screenPos, 0, 1)/*, g_sceneCB.projectionToWorld)*/;

    //world.xyz /= world.w;
    origin = world.xyz; //g_sceneCB.cameraPosition.xyz;
    direction = float3(1,0,0);//normalize(world.xyz - origin);
}

void RaygenCommon()
{
    float3 rayDir;
    float3 origin;
    
    // Generate a ray for a camera pixel corresponding to an index from the dispatched 2D grid.
    GenerateCameraRay(DispatchRaysIndex().xy, origin, rayDir);

    // Trace the ray.
    // Set the ray's extents.
    RayDesc ray;
    ray.Origin = origin;
    ray.Direction = rayDir;
    // Set TMin to a non-zero small value to avoid aliasing issues due to floating - point errors.
    // TMin should be kept small to prevent missing geometry at close contact areas.
    ray.TMin = 0.001;
    ray.TMax = 10000.0;
    RayPayload payload = { float4(0, 0, 0, 0) };
    TraceRay(Scene, RAY_FLAG_CULL_BACK_FACING_TRIANGLES, ~0, 0, 1, 0, ray, payload);

    // Write the raytraced color to the output texture.
   // RenderTarget[DispatchRaysIndex().xy] = payload.color;
}

[shader("raygeneration")]
void Raygen0()
{
    RaygenCommon();
}

[shader("raygeneration")]
void Raygen1()
{
    RaygenCommon();
}

typedef BuiltInTriangleIntersectionAttributes MyAttributes;

[shader("closesthit")]
void InnerClosestHitShader(inout RayPayload payload, in MyAttributes attr)
{
    payload.color = float4(0,1,0,0);
}


[shader("miss")]
void MyMissShader(inout RayPayload payload)
{
    payload.color = float4(1, 0, 0, 0);
})";

    CComPtr<IDxcBlob> pBlob =
        Compile(m_dllSupport, hlsl, L"lib_6_6", {optimization});
    CComPtr<IDxcBlob> pDxil = FindModule(DFCC_ShaderDebugInfoDXIL, pBlob);
    auto outputLines = RunAnnotationPasses(m_dllSupport, pDxil).lines;

    const char instructionRangeLabel[] = "InstructionRange:";

    // The numbering pass should have counted  instructions for each
    // "interesting" (to PIX) function and output its start and (end+1)
    // instruction ordinal. End should always be a reasonable number of
    // instructions (>10) and end should always be higher than start, and all
    // four functions above should be represented.
    int countOfInstructionRangeLines = 0;
    for (auto const &line : outputLines) {
      auto tokens = Tokenize(line, " ");
      if (tokens.size() >= 4) {
        if (tokens[0] == instructionRangeLabel) {
          countOfInstructionRangeLines++;
          int instructionStart = atoi(tokens[1].c_str());
          int instructionEnd = atoi(tokens[2].c_str());
          VERIFY_IS_TRUE(instructionEnd > 10);
          VERIFY_IS_TRUE(instructionEnd > instructionStart);
          auto found1 = tokens[3].find("Raygen0@@YAXXZ") != std::string::npos;
          auto found2 = tokens[3].find("Raygen1@@YAXXZ") != std::string::npos;
          auto foundClosest =
              tokens[3].find("InnerClosestHit") != std::string::npos;
          auto foundMiss = tokens[3].find("MyMiss") != std::string::npos;
          VERIFY_IS_TRUE(found1 || found2 || foundClosest || foundMiss);
        }
      }
    }
    VERIFY_ARE_EQUAL(4, countOfInstructionRangeLines);

    // Non-library target:
    const char *PixelShader = R"(
    [RootSignature("")]
    float main(float pos : A) : SV_Target {
      float x = abs(pos);
      float y = sin(pos);
      float z = x + y;
      return z;
    }
  )";
    pBlob = Compile(m_dllSupport, PixelShader, L"ps_6_6", {optimization});
    pDxil = FindModule(DFCC_ShaderDebugInfoDXIL, pBlob);
    outputLines = RunAnnotationPasses(m_dllSupport, pDxil).lines;

    countOfInstructionRangeLines = 0;
    for (auto const &line : outputLines) {
      auto tokens = Tokenize(line, " ");
      if (tokens.size() >= 4) {
        if (tokens[0] == instructionRangeLabel) {
          countOfInstructionRangeLines++;
          int instructionStart = atoi(tokens[1].c_str());
          int instructionEnd = atoi(tokens[2].c_str());
          VERIFY_IS_TRUE(instructionStart == 0);
          VERIFY_IS_TRUE(instructionEnd > 10);
          VERIFY_IS_TRUE(instructionEnd > instructionStart);
          auto foundMain = tokens[3].find("main") != std::string::npos;
          VERIFY_IS_TRUE(foundMain);
        }
      }
    }
    VERIFY_ARE_EQUAL(1, countOfInstructionRangeLines);

    // Now check that the initial value parameter works:
    const int startingInstructionOrdinal = 1234;
    outputLines =
        RunAnnotationPasses(m_dllSupport, pDxil, startingInstructionOrdinal)
            .lines;

    countOfInstructionRangeLines = 0;
    for (auto const &line : outputLines) {
      auto tokens = Tokenize(line, " ");
      if (tokens.size() >= 4) {
        if (tokens[0] == instructionRangeLabel) {
          countOfInstructionRangeLines++;
          int instructionStart = atoi(tokens[1].c_str());
          int instructionEnd = atoi(tokens[2].c_str());
          VERIFY_IS_TRUE(instructionStart == startingInstructionOrdinal);
          VERIFY_IS_TRUE(instructionEnd > instructionStart);
          auto foundMain = tokens[3].find("main") != std::string::npos;
          VERIFY_IS_TRUE(foundMain);
        }
      }
    }
    VERIFY_ARE_EQUAL(1, countOfInstructionRangeLines);
  }
}

TEST_F(PixTest, VirtualRegisters_AlignedOffsets) {
  if (m_ver.SkipDxilVersion(1, 5))
    return;

  {
    const char *hlsl = R"(
cbuffer cbEveryFrame : register(b0)
{
    int i32;
    float f32;
};

struct VS_OUTPUT_ENV
{
    float4 Pos        : SV_Position;
    float2 Tex        : TEXCOORD0;
};

float4 main(VS_OUTPUT_ENV input) : SV_Target
{
    // (BTW we load from i32 and f32 (which are resident in a cb) so that these local variables aren't optimized away)
    bool i1 = i32 != 0;
    min16uint u16 = (min16uint)(i32 / 4);
    min16int s16 = (min16int)(i32/4) * -1; // signed s16 gets -8
    min12int s12 = (min12int)(i32/8) * -1; // signed s12 gets -4
    half h = (half) f32 / 2.f; // f32 is initialized to 32.0 in8he CB, so the 16-bit type now has "16.0" in it
    min16float mf16 = (min16float) f32 / -2.f;
    min10float mf10 = (min10float) f32 / -4.f;
    return float4((float)(i1 + u16) / 2.f, (float)(s16 + s12) / -128.f, h / 128.f, mf16 / 128.f + mf10 / 256.f);
}
)";

    // This is little more than a crash test, designed to exercise a previously
    // over-active assert..
    std::vector<std::pair<const wchar_t *, std::vector<const wchar_t *>>>
        argSets = {
            {L"ps_6_0", {L"-Od"}},
            {L"ps_6_2", {L"-Od", L"-HV", L"2018", L"-enable-16bit-types"}}};
    for (auto const &args : argSets) {

      CComPtr<IDxcBlob> pBlob =
          Compile(m_dllSupport, hlsl, args.first, args.second);
      CComPtr<IDxcBlob> pDxil = FindModule(DFCC_ShaderDebugInfoDXIL, pBlob);
      RunAnnotationPasses(m_dllSupport, pDxil);
    }
  }
}

static void VerifyOperationSucceeded(IDxcOperationResult *pResult) {
  HRESULT result;
  VERIFY_SUCCEEDED(pResult->GetStatus(&result));
  if (FAILED(result)) {
    CComPtr<IDxcBlobEncoding> pErrors;
    VERIFY_SUCCEEDED(pResult->GetErrorBuffer(&pErrors));
    CA2W errorsWide(BlobToUtf8(pErrors).c_str());
    WEX::Logging::Log::Comment(errorsWide);
  }
  VERIFY_SUCCEEDED(result);
}

TEST_F(PixTest, RootSignatureUpgrade_SubObjects) {

  const char *source = R"x(
GlobalRootSignature so_GlobalRootSignature =
{
	"RootConstants(num32BitConstants=1, b8), "
};

StateObjectConfig so_StateObjectConfig = 
{ 
    STATE_OBJECT_FLAGS_ALLOW_LOCAL_DEPENDENCIES_ON_EXTERNAL_DEFINITONS
};

LocalRootSignature so_LocalRootSignature1 = 
{
	"RootConstants(num32BitConstants=3, b2), "
	"UAV(u6),RootFlags(LOCAL_ROOT_SIGNATURE)" 
};

LocalRootSignature so_LocalRootSignature2 = 
{
	"RootConstants(num32BitConstants=3, b2), "
	"UAV(u8, flags=DATA_STATIC), " 
	"RootFlags(LOCAL_ROOT_SIGNATURE)"
};

RaytracingShaderConfig  so_RaytracingShaderConfig =
{
    128, // max payload size
    32   // max attribute size
};

RaytracingPipelineConfig so_RaytracingPipelineConfig =
{
    2 // max trace recursion depth
};

TriangleHitGroup MyHitGroup =
{
    "MyAnyHit",       // AnyHit
    "MyClosestHit",   // ClosestHit
};

SubobjectToExportsAssociation so_Association1 =
{
	"so_LocalRootSignature1", // subobject name
	"MyRayGen"                // export association 
};

SubobjectToExportsAssociation so_Association2 =
{
	"so_LocalRootSignature2", // subobject name
	"MyAnyHit"                // export association 
};

struct MyPayload
{
    float4 color;
};

[shader("raygeneration")]
void MyRayGen()
{
}

[shader("closesthit")]
void MyClosestHit(inout MyPayload payload, in BuiltInTriangleIntersectionAttributes attr)
{  
}

[shader("anyhit")]
void MyAnyHit(inout MyPayload payload, in BuiltInTriangleIntersectionAttributes attr)
{
}

[shader("miss")]
void MyMiss(inout MyPayload payload)
{
}

)x";

  CComPtr<IDxcCompiler> pCompiler;
  VERIFY_SUCCEEDED(m_dllSupport.CreateInstance(CLSID_DxcCompiler, &pCompiler));

  CComPtr<IDxcBlobEncoding> pSource;
  Utf8ToBlob(m_dllSupport, source, &pSource);

  CComPtr<IDxcOperationResult> pResult;
  VERIFY_SUCCEEDED(pCompiler->Compile(pSource, L"source.hlsl", L"", L"lib_6_6",
                                      nullptr, 0, nullptr, 0, nullptr,
                                      &pResult));
  VerifyOperationSucceeded(pResult);
  CComPtr<IDxcBlob> compiled;
  VERIFY_SUCCEEDED(pResult->GetResult(&compiled));

  auto optimizedContainer = RunShaderAccessTrackingPass(compiled).blob;

  const char *pBlobContent =
      reinterpret_cast<const char *>(optimizedContainer->GetBufferPointer());
  unsigned blobSize = optimizedContainer->GetBufferSize();
  const hlsl::DxilContainerHeader *pContainerHeader =
      hlsl::IsDxilContainerLike(pBlobContent, blobSize);

  const hlsl::DxilPartHeader *pPartHeader =
      GetDxilPartByType(pContainerHeader, hlsl::DFCC_RuntimeData);
  VERIFY_ARE_NOT_EQUAL(pPartHeader, nullptr);

  hlsl::RDAT::DxilRuntimeData rdat(GetDxilPartData(pPartHeader),
                                   pPartHeader->PartSize);

  auto const subObjectTableReader = rdat.GetSubobjectTable();

  // There are 9 subobjects in the HLSL above:
  VERIFY_ARE_EQUAL(subObjectTableReader.Count(), 9u);

  bool foundGlobalRS = false;
  for (uint32_t i = 0; i < subObjectTableReader.Count(); ++i) {
    auto subObject = subObjectTableReader[i];
    hlsl::DXIL::SubobjectKind subobjectKind = subObject.getKind();
    switch (subobjectKind) {
    case hlsl::DXIL::SubobjectKind::GlobalRootSignature: {
      foundGlobalRS = true;
      VERIFY_IS_TRUE(0 ==
                     strcmp(subObject.getName(), "so_GlobalRootSignature"));

      auto rootSigReader = subObject.getRootSignature();
      DxilVersionedRootSignatureDesc const *rootSignature = nullptr;
      DeserializeRootSignature(rootSigReader.getData(),
                               rootSigReader.sizeData(), &rootSignature);
      VERIFY_ARE_EQUAL(rootSignature->Version,
                       DxilRootSignatureVersion::Version_1_1);
      VERIFY_ARE_EQUAL(rootSignature->Desc_1_1.NumParameters, 2u);
      VERIFY_ARE_EQUAL(rootSignature->Desc_1_1.pParameters[1].ParameterType,
                       DxilRootParameterType::UAV);
      VERIFY_ARE_EQUAL(rootSignature->Desc_1_1.pParameters[1].ShaderVisibility,
                       DxilShaderVisibility::All);
      VERIFY_ARE_EQUAL(
          rootSignature->Desc_1_1.pParameters[1].Descriptor.RegisterSpace,
          static_cast<uint32_t>(-2));
      VERIFY_ARE_EQUAL(
          rootSignature->Desc_1_1.pParameters[1].Descriptor.ShaderRegister, 0u);
      DeleteRootSignature(rootSignature);
      break;
    }
    }
  }
  VERIFY_IS_TRUE(foundGlobalRS);
}

TEST_F(PixTest, RootSignatureUpgrade_Annotation) {

  const char *dynamicTextureAccess = R"x(
Texture1D<float4> tex[5] : register(t3);
SamplerState SS[3] : register(s2);

[RootSignature("DescriptorTable(SRV(t3, numDescriptors=5)),\
                DescriptorTable(Sampler(s2, numDescriptors=3))")]
float4 main(int i : A, float j : B) : SV_TARGET
{
  float4 r = tex[i].Sample(SS[i], i);
  return r;
}
  )x";

  auto compiled = Compile(m_dllSupport, dynamicTextureAccess, L"ps_6_6");
  auto pOptimizedContainer = RunShaderAccessTrackingPass(compiled).blob;

  const char *pBlobContent =
      reinterpret_cast<const char *>(pOptimizedContainer->GetBufferPointer());
  unsigned blobSize = pOptimizedContainer->GetBufferSize();
  const hlsl::DxilContainerHeader *pContainerHeader =
      hlsl::IsDxilContainerLike(pBlobContent, blobSize);

  const hlsl::DxilPartHeader *pPartHeader =
      GetDxilPartByType(pContainerHeader, hlsl::DFCC_RootSignature);
  VERIFY_ARE_NOT_EQUAL(pPartHeader, nullptr);

  hlsl::RootSignatureHandle RSH;
  RSH.LoadSerialized((const uint8_t *)GetDxilPartData(pPartHeader),
                     pPartHeader->PartSize);

  RSH.Deserialize();

  auto const *desc = RSH.GetDesc();

  bool foundGlobalRS = false;

  VERIFY_ARE_EQUAL(desc->Version, hlsl::DxilRootSignatureVersion::Version_1_1);
  VERIFY_ARE_EQUAL(desc->Desc_1_1.NumParameters, 3u);
  for (unsigned int i = 0; i < desc->Desc_1_1.NumParameters; ++i) {
    hlsl::DxilRootParameter1 const *param = desc->Desc_1_1.pParameters + i;
    switch (param->ParameterType) {
    case hlsl::DxilRootParameterType::UAV:
      VERIFY_ARE_EQUAL(param->Descriptor.RegisterSpace,
                       static_cast<uint32_t>(-2));
      VERIFY_ARE_EQUAL(param->Descriptor.ShaderRegister, 0u);
      foundGlobalRS = true;
      break;
    }
  }

  VERIFY_IS_TRUE(foundGlobalRS);
}

TEST_F(PixTest, ToolsUav_TwoPixPassesShareOneResource) {
  const char *source = R"x(
RWByteAddressBuffer output : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    output.Store(4 * tid.x, tid.x);
})x";

  CComPtr<IDxcBlob> compiled =
      Compile(m_dllSupport, source, L"cs_6_2", {L"-Od"});
  PassOutput debugOutput = RunDebugPass(compiled);
  PassOutput accessOutput = RunShaderAccessTrackingPass(debugOutput.blob);

  ModuleAndHangersOn moduleEtc(accessOutput.blob);
  VERIFY_ARE_EQUAL(1u, CountToolsUAVs(moduleEtc.GetDxilModule()));
  VerifyInstrumentedModuleIsValid(
      accessOutput.blob,
      "debug instrumentation followed by shader access tracking");
}

TEST_F(PixTest, ToolsUav_LibraryWithTwoEntryPointsCreatesOnePair) {
  const char *source = R"x(
struct [raypayload] MyPayload
{
    float2 barycentrics : read(caller) : write(caller,anyhit);
    uint primitiveIndex : read(caller) : write(caller,anyhit);
};

[shader("miss")]
void MissOne(inout MyPayload payload)
{
    payload.primitiveIndex = 1;
}

[shader("miss")]
void MissTwo(inout MyPayload payload)
{
    payload.primitiveIndex = 2;
}
)x";

  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"lib_6_6", {});
  CComPtr<IDxcBlob> output = RunDxilPIXDXRInvocationsLog(compiled);

  std::vector<std::string> lines = Tokenize(Disassemble(output), "\n");
  VERIFY_ARE_EQUAL(2, CountToolsUAVRecords(lines));
}

TEST_F(PixTest, ToolsUav_ExtendsEveryGlobalRootSignatureSubobject) {
  const char *source = R"x(
GlobalRootSignature firstRootSignature = {"CBV(b0)"};
GlobalRootSignature secondRootSignature = {"SRV(t0)"};

SubobjectToExportsAssociation firstAssociation =
{
    "firstRootSignature",
    "MyClosestHit"
};

SubobjectToExportsAssociation secondAssociation =
{
    "secondRootSignature",
    "MyMiss"
};

struct MyPayload
{
    float4 color;
};

[shader("raygeneration")]
void MyRayGen()
{
}

[shader("closesthit")]
void MyClosestHit(inout MyPayload payload,
                  in BuiltInTriangleIntersectionAttributes attr)
{
}

[shader("miss")]
void MyMiss(inout MyPayload payload)
{
}
)x";

  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"lib_6_6", {});
  ModuleAndHangersOn moduleEtc(compiled);
  DxilModule &DM = moduleEtc.GetDxilModule();
  LoadSubobjectsFromContainerIntoModule(compiled, DM);
  PIXPassHelpers::CreateGlobalUAVResource(DM, 0, "PIX_CountUAV_Handle");
  PIXPassHelpers::CreateGlobalUAVResource(DM, 1, "PIX_LogUAV_Handle");

  VerifyGlobalRootSignaturesHaveToolsUAVs(
      DM.GetSubobjects(), {"firstRootSignature", "secondRootSignature"},
      {0, 1});
}

TEST_F(PixTest, DebugInstrumentation_RawBufferShaderFlagDeclared) {
  const char *source = R"x(
[numthreads(1, 1, 1)]
void main(uint threadId : SV_DispatchThreadID)
{
})x";

  CComPtr<IDxcBlob> compiled =
      Compile(m_dllSupport, source, L"cs_6_2", {L"-Od"});
  PassOutput output = RunDebugPass(compiled);
  std::vector<std::string> lines = Tokenize(Disassemble(output.blob), "\n");

  constexpr uint64_t EnableRawAndStructuredBuffers = 0x10;
  bool foundShaderFlags = false;
  uint64_t shaderFlags = 0;
  const std::string tagPrefix = "!{i32 0, i64 ";
  for (std::string const &line : lines) {
    std::string::size_type const tagStart = line.find(tagPrefix);
    if (tagStart == std::string::npos) {
      continue;
    }
    shaderFlags =
        strtoull(line.c_str() + tagStart + tagPrefix.length(), nullptr, 10);
    foundShaderFlags = true;
    break;
  }

  VERIFY_IS_TRUE(foundShaderFlags);
  VERIFY_ARE_EQUAL(EnableRawAndStructuredBuffers,
                   shaderFlags & EnableRawAndStructuredBuffers);
  VerifyInstrumentedModuleIsValid(output.blob,
                                  "debug instrumentation shader flags");
}

TEST_F(PixTest, ToolsUav_RootSignatureSerializationFailurePreservesSignature) {
  const char *source = R"x(
[numthreads(1, 1, 1)]
void main()
{
})x";

  DxilDescriptorRange range = {};
  range.RangeType = DxilDescriptorRangeType::UAV;
  range.NumDescriptors = 1;
  range.BaseShaderRegister = 0;
  range.RegisterSpace = static_cast<uint32_t>(-2);
  range.OffsetInDescriptorsFromTableStart = DxilDescriptorRangeOffsetAppend;

  DxilRootParameter parameter = {};
  parameter.ParameterType = DxilRootParameterType::DescriptorTable;
  parameter.DescriptorTable.NumDescriptorRanges = 1;
  parameter.DescriptorTable.pDescriptorRanges = &range;
  parameter.ShaderVisibility = DxilShaderVisibility::All;

  DxilVersionedRootSignatureDesc rootSignature = {};
  rootSignature.Version = DxilRootSignatureVersion::Version_1_0;
  rootSignature.Desc_1_0.NumParameters = 1;
  rootSignature.Desc_1_0.pParameters = &parameter;
  rootSignature.Desc_1_0.Flags = DxilRootSignatureFlags::None;

  CComPtr<IDxcBlob> serializedRootSignature;
  CComPtr<IDxcBlobEncoding> errorBlob;
  SerializeRootSignature(&rootSignature, &serializedRootSignature, &errorBlob,
                         true);
  VERIFY_IS_NOT_NULL(serializedRootSignature);

  const uint8_t *serializedData =
      static_cast<const uint8_t *>(serializedRootSignature->GetBufferPointer());
  std::vector<uint8_t> originalRootSignature(
      serializedData,
      serializedData + serializedRootSignature->GetBufferSize());

  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"cs_6_0", {});
  ModuleAndHangersOn moduleEtc(compiled);
  DxilModule &DM = moduleEtc.GetDxilModule();
  DM.ResetSerializedRootSignature(originalRootSignature);

  std::unique_ptr<DxilSubobjects> subObjects(new DxilSubobjects());
  constexpr bool notALocalRootSignature = false;
  subObjects->CreateRootSignature(
      "testRootSignature", notALocalRootSignature, originalRootSignature.data(),
      static_cast<uint32_t>(originalRootSignature.size()));
  DM.ResetSubobjects(subObjects.release());

  // The pre-existing descriptor-table UAV range already occupies register
  // 0 in the tools-reserved space; adding a second, root-descriptor-based
  // UAV at the same register+space produces a signature the serializer
  // rejects. This must fail closed (throw, add nothing) rather than
  // silently continue instrumentation with a partially-updated or
  // corrupted signature.
  bool caught = false;
  try {
    PIXPassHelpers::CreateGlobalUAVResource(DM, 0, "PIX_TestUAV");
  } catch (hlsl::Exception const &) {
    caught = true;
  }
  VERIFY_IS_TRUE(caught);

  const std::vector<uint8_t> &actualRootSignature =
      DM.GetSerializedRootSignature();
  VERIFY_ARE_EQUAL(originalRootSignature.size(), actualRootSignature.size());
  VERIFY_IS_TRUE(std::equal(originalRootSignature.begin(),
                            originalRootSignature.end(),
                            actualRootSignature.begin()));

  bool foundRootSignature = false;
  for (auto const &subObject : DM.GetSubobjects()->GetSubobjects()) {
    if (subObject.first != "testRootSignature") {
      continue;
    }

    const void *data = nullptr;
    uint32_t size = 0;
    VERIFY_IS_TRUE(subObject.second->GetRootSignature(notALocalRootSignature,
                                                      data, size, nullptr));
    VERIFY_ARE_EQUAL(originalRootSignature.size(), static_cast<size_t>(size));
    VERIFY_IS_TRUE(std::equal(originalRootSignature.begin(),
                              originalRootSignature.end(),
                              static_cast<const uint8_t *>(data)));
    foundRootSignature = true;
  }
  VERIFY_IS_TRUE(foundRootSignature);

  // No UAV resource was created either: the whole request was rejected
  // atomically, not partially applied.
  VERIFY_ARE_EQUAL(size_t(0), DM.GetUAVs().size());
}

// Reviewer item 2.1: when a version 1.1 root signature already holds the
// requested tools UAV, ExtendRootSig returns without appending a new
// parameter. The caller must then leave the existing last parameter's
// flags untouched; only a genuinely appended parameter gets flags None.
TEST_F(PixTest,
       ToolsUav_PreservesUnrelatedRootDescriptorFlagsWhenAlreadyPresent) {
  const char *source = R"x(
[numthreads(1, 1, 1)]
void main()
{
})x";

  constexpr uint32_t ToolsUAVRegisterSpace = static_cast<uint32_t>(-2);
  constexpr uint32_t ExistingToolsUAVRegister = 0;
  constexpr uint32_t NewToolsUAVRegister = 1;

  // Parameter 0: the tools UAV already present at the well-known space.
  // Parameter 1: an unrelated root descriptor whose flags are not None;
  // ExtendRootSig's early return must leave this parameter's flags alone.
  DxilRootParameter1 parameters[2] = {};
  parameters[0].ParameterType = DxilRootParameterType::UAV;
  parameters[0].Descriptor.ShaderRegister = ExistingToolsUAVRegister;
  parameters[0].Descriptor.RegisterSpace = ToolsUAVRegisterSpace;
  parameters[0].Descriptor.Flags = DxilRootDescriptorFlags::None;
  parameters[0].ShaderVisibility = DxilShaderVisibility::All;

  parameters[1].ParameterType = DxilRootParameterType::UAV;
  parameters[1].Descriptor.ShaderRegister = 5;
  parameters[1].Descriptor.RegisterSpace = 0;
  parameters[1].Descriptor.Flags = DxilRootDescriptorFlags::DataStatic;
  parameters[1].ShaderVisibility = DxilShaderVisibility::All;

  DxilVersionedRootSignatureDesc rootSignature = {};
  rootSignature.Version = DxilRootSignatureVersion::Version_1_1;
  rootSignature.Desc_1_1.NumParameters = 2;
  rootSignature.Desc_1_1.pParameters = parameters;
  rootSignature.Desc_1_1.Flags = DxilRootSignatureFlags::None;

  CComPtr<IDxcBlob> serializedRootSignature;
  CComPtr<IDxcBlobEncoding> errorBlob;
  SerializeRootSignature(&rootSignature, &serializedRootSignature, &errorBlob,
                         true);
  VERIFY_IS_NOT_NULL(serializedRootSignature);

  std::vector<uint8_t> originalRootSignature(
      static_cast<const uint8_t *>(serializedRootSignature->GetBufferPointer()),
      static_cast<const uint8_t *>(
          serializedRootSignature->GetBufferPointer()) +
          serializedRootSignature->GetBufferSize());

  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"cs_6_0", {});
  ModuleAndHangersOn moduleEtc(compiled);
  DxilModule &DM = moduleEtc.GetDxilModule();
  DM.ResetSerializedRootSignature(originalRootSignature);

  // Requesting the tools UAV register that is already present must not
  // append a parameter, and must not touch parameter 1's flags.
  PIXPassHelpers::CreateGlobalUAVResource(DM, ExistingToolsUAVRegister,
                                          "PIX_ExistingToolsUAV");

  {
    const std::vector<uint8_t> &afterFirstCall =
        DM.GetSerializedRootSignature();
    DxilVersionedRootSignature deserialized;
    DeserializeRootSignature(afterFirstCall.data(),
                             static_cast<uint32_t>(afterFirstCall.size()),
                             deserialized.get_address_of());
    VERIFY_ARE_EQUAL(2u, deserialized->Desc_1_1.NumParameters);
    VERIFY_IS_TRUE(deserialized->Desc_1_1.pParameters[1].Descriptor.Flags ==
                   DxilRootDescriptorFlags::DataStatic);
  }

  // A genuinely new tools UAV register must still append a parameter, and
  // that new parameter (not the unrelated one) gets flags None.
  PIXPassHelpers::CreateGlobalUAVResource(DM, NewToolsUAVRegister,
                                          "PIX_NewToolsUAV");

  {
    const std::vector<uint8_t> &afterSecondCall =
        DM.GetSerializedRootSignature();
    DxilVersionedRootSignature deserialized;
    DeserializeRootSignature(afterSecondCall.data(),
                             static_cast<uint32_t>(afterSecondCall.size()),
                             deserialized.get_address_of());
    VERIFY_ARE_EQUAL(3u, deserialized->Desc_1_1.NumParameters);
    VERIFY_IS_TRUE(deserialized->Desc_1_1.pParameters[1].Descriptor.Flags ==
                   DxilRootDescriptorFlags::DataStatic);
    VERIFY_IS_TRUE(deserialized->Desc_1_1.pParameters[2].Descriptor.Flags ==
                   DxilRootDescriptorFlags::None);
  }
}

// Builds a serialized v1.0 root signature whose only parameter is a root
// constant costing exactly fillerDwords DWORDs (Num32BitValues), so tests
// can construct a signature at a precise D3D12 budget position before
// adding tools UAVs (each a 2-DWORD root descriptor).
static std::vector<uint8_t>
BuildFillerRootSignatureBytes(uint32_t fillerDwords) {
  DxilRootParameter parameter = {};
  parameter.ParameterType = DxilRootParameterType::Constants32Bit;
  parameter.Constants.ShaderRegister = 0;
  parameter.Constants.RegisterSpace = 0;
  parameter.Constants.Num32BitValues = fillerDwords;
  parameter.ShaderVisibility = DxilShaderVisibility::All;

  DxilVersionedRootSignatureDesc rootSignature = {};
  rootSignature.Version = DxilRootSignatureVersion::Version_1_0;
  rootSignature.Desc_1_0.NumParameters = 1;
  rootSignature.Desc_1_0.pParameters = &parameter;
  rootSignature.Desc_1_0.Flags = DxilRootSignatureFlags::None;

  CComPtr<IDxcBlob> serialized;
  CComPtr<IDxcBlobEncoding> errorBlob;
  SerializeRootSignature(&rootSignature, &serialized, &errorBlob, true);
  VERIFY_IS_NOT_NULL(serialized);

  return std::vector<uint8_t>(
      static_cast<const uint8_t *>(serialized->GetBufferPointer()),
      static_cast<const uint8_t *>(serialized->GetBufferPointer()) +
          serialized->GetBufferSize());
}

// Builds a serialized v1.0 root signature that actually covers a shader
// declaring RWByteAddressBuffer u0 (a root UAV descriptor for register 0,
// space 0 -- 2 DWORDs), plus a root constant costing exactly fillerDwords
// DWORDs. Unlike BuildFillerRootSignatureBytes, this is safe to embed as
// a real DFCC_RootSignature container part: DxcContainerBuilder validates
// (DxcValidatorFlags_RootSignatureOnly) any container it adds a root
// signature part to, and that validation requires the signature to cover
// every resource the shader actually binds.
static std::vector<uint8_t>
BuildRootSignatureCoveringU0Bytes(uint32_t fillerDwords) {
  DxilRootParameter parameters[2] = {};
  parameters[0].ParameterType = DxilRootParameterType::UAV;
  parameters[0].Descriptor.ShaderRegister = 0;
  parameters[0].Descriptor.RegisterSpace = 0;
  parameters[0].ShaderVisibility = DxilShaderVisibility::All;

  parameters[1].ParameterType = DxilRootParameterType::Constants32Bit;
  parameters[1].Constants.ShaderRegister = 0;
  parameters[1].Constants.RegisterSpace = 1;
  parameters[1].Constants.Num32BitValues = fillerDwords;
  parameters[1].ShaderVisibility = DxilShaderVisibility::All;

  DxilVersionedRootSignatureDesc rootSignature = {};
  rootSignature.Version = DxilRootSignatureVersion::Version_1_0;
  rootSignature.Desc_1_0.NumParameters = 2;
  rootSignature.Desc_1_0.pParameters = parameters;
  rootSignature.Desc_1_0.Flags = DxilRootSignatureFlags::None;

  CComPtr<IDxcBlob> serialized;
  CComPtr<IDxcBlobEncoding> errorBlob;
  SerializeRootSignature(&rootSignature, &serialized, &errorBlob, true);
  VERIFY_IS_NOT_NULL(serialized);

  return std::vector<uint8_t>(
      static_cast<const uint8_t *>(serialized->GetBufferPointer()),
      static_cast<const uint8_t *>(serialized->GetBufferPointer()) +
          serialized->GetBufferSize());
}

// One-UAV request: filler at 62 DWORDs + one 2-DWORD UAV = exactly 64,
// the D3D12 budget limit. Must succeed.
TEST_F(PixTest, ToolsUav_BudgetOneUAVSucceedsAtExactly64Dwords) {
  const char *source = R"x(
[numthreads(1, 1, 1)]
void main()
{})x";

  std::vector<uint8_t> original = BuildFillerRootSignatureBytes(62);
  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"cs_6_0", {});
  ModuleAndHangersOn moduleEtc(compiled);
  DxilModule &DM = moduleEtc.GetDxilModule();
  DM.ResetSerializedRootSignature(original);

  PIXPassHelpers::CreateGlobalUAVResource(DM, 0, "PIX_TestUAV");

  VERIFY_ARE_EQUAL(size_t(1), DM.GetUAVs().size());
  const std::vector<uint8_t> &updated = DM.GetSerializedRootSignature();
  DxilVersionedRootSignature deserialized;
  DeserializeRootSignature(updated.data(),
                           static_cast<uint32_t>(updated.size()),
                           deserialized.get_address_of());
  VERIFY_ARE_EQUAL(2u, deserialized->Desc_1_0.NumParameters);
}

// One-UAV request: filler already at 64 DWORDs; adding a 2-DWORD UAV would
// reach 66, over budget. Must reject atomically: exception thrown, root
// signature byte-identical to the original, no UAV resource created.
TEST_F(PixTest, ToolsUav_BudgetOneUAVRejectsWhenAlreadyAt64Dwords) {
  const char *source = R"x(
[numthreads(1, 1, 1)]
void main()
{})x";

  std::vector<uint8_t> original = BuildFillerRootSignatureBytes(64);
  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"cs_6_0", {});
  ModuleAndHangersOn moduleEtc(compiled);
  DxilModule &DM = moduleEtc.GetDxilModule();
  DM.ResetSerializedRootSignature(original);

  bool caught = false;
  try {
    PIXPassHelpers::CreateGlobalUAVResource(DM, 0, "PIX_TestUAV");
  } catch (hlsl::Exception const &) {
    caught = true;
  }
  VERIFY_IS_TRUE(caught);

  VERIFY_ARE_EQUAL(size_t(0), DM.GetUAVs().size());
  const std::vector<uint8_t> &actual = DM.GetSerializedRootSignature();
  VERIFY_ARE_EQUAL(original.size(), actual.size());
  VERIFY_IS_TRUE(std::equal(original.begin(), original.end(), actual.begin()));
}

// Boundary check distinct from the exactly-64 case above: filler at 63
// DWORDs (one short of the limit) plus one 2-DWORD UAV reaches 65 -- one
// over budget, not merely at it. Must still reject atomically.
TEST_F(PixTest, ToolsUav_BudgetOneUAVRejectsAt63PlusTwoDwords) {
  const char *source = R"x(
[numthreads(1, 1, 1)]
void main()
{})x";

  std::vector<uint8_t> original = BuildFillerRootSignatureBytes(63);
  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"cs_6_0", {});
  ModuleAndHangersOn moduleEtc(compiled);
  DxilModule &DM = moduleEtc.GetDxilModule();
  DM.ResetSerializedRootSignature(original);

  bool caught = false;
  try {
    PIXPassHelpers::CreateGlobalUAVResource(DM, 0, "PIX_TestUAV");
  } catch (hlsl::Exception const &) {
    caught = true;
  }
  VERIFY_IS_TRUE(caught);

  VERIFY_ARE_EQUAL(size_t(0), DM.GetUAVs().size());
  const std::vector<uint8_t> &actual = DM.GetSerializedRootSignature();
  VERIFY_ARE_EQUAL(original.size(), actual.size());
  VERIFY_IS_TRUE(std::equal(original.begin(), original.end(), actual.begin()));
}

// Two-UAV batch request (the DXR invocation log's own pattern): filler at
// 60 DWORDs + two 2-DWORD UAVs = exactly 64. Must succeed, and both
// registers must be reserved together.
TEST_F(PixTest, ToolsUav_BudgetTwoUAVsSucceedsAtExactly64Dwords) {
  const char *source = R"x(
[numthreads(1, 1, 1)]
void main()
{})x";

  std::vector<uint8_t> original = BuildFillerRootSignatureBytes(60);
  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"cs_6_0", {});
  ModuleAndHangersOn moduleEtc(compiled);
  DxilModule &DM = moduleEtc.GetDxilModule();
  DM.ResetSerializedRootSignature(original);

  llvm::IRBuilder<> Builder(
      dxilutil::FirstNonAllocaInsertionPt(DM.GetEntryFunction()));
  std::vector<llvm::CallInst *> handles =
      PIXPassHelpers::CreateUAVsOnceForModule(
          DM, Builder, {{0u, "PIX_CountUAV_Handle"}, {1u, "PIX_UAV_Handle"}});
  VERIFY_ARE_EQUAL(size_t(2), handles.size());
  VERIFY_IS_NOT_NULL(handles[0]);
  VERIFY_IS_NOT_NULL(handles[1]);

  VERIFY_ARE_EQUAL(size_t(2), DM.GetUAVs().size());
  const std::vector<uint8_t> &updated = DM.GetSerializedRootSignature();
  DxilVersionedRootSignature deserialized;
  DeserializeRootSignature(updated.data(),
                           static_cast<uint32_t>(updated.size()),
                           deserialized.get_address_of());
  VERIFY_ARE_EQUAL(3u, deserialized->Desc_1_0.NumParameters);
}

// Two-UAV batch request: filler at 62 DWORDs + two 2-DWORD UAVs = 66, over
// budget. Must reject the *entire batch* atomically: neither register is
// added, and no UAV resource is created for either one -- proving the
// two-UAV caller cannot end up with only one of its two registers
// reserved.
TEST_F(PixTest, ToolsUav_BudgetTwoUAVsRejectsAtomically) {
  const char *source = R"x(
[numthreads(1, 1, 1)]
void main()
{})x";

  std::vector<uint8_t> original = BuildFillerRootSignatureBytes(62);
  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"cs_6_0", {});
  ModuleAndHangersOn moduleEtc(compiled);
  DxilModule &DM = moduleEtc.GetDxilModule();
  DM.ResetSerializedRootSignature(original);

  llvm::IRBuilder<> Builder(
      dxilutil::FirstNonAllocaInsertionPt(DM.GetEntryFunction()));
  bool caught = false;
  try {
    PIXPassHelpers::CreateUAVsOnceForModule(
        DM, Builder, {{0u, "PIX_CountUAV_Handle"}, {1u, "PIX_UAV_Handle"}});
  } catch (hlsl::Exception const &) {
    caught = true;
  }
  VERIFY_IS_TRUE(caught);

  VERIFY_ARE_EQUAL(size_t(0), DM.GetUAVs().size());
  const std::vector<uint8_t> &actual = DM.GetSerializedRootSignature();
  VERIFY_ARE_EQUAL(original.size(), actual.size());
  VERIFY_IS_TRUE(std::equal(original.begin(), original.end(), actual.begin()));
}

// With two DXR GlobalRootSignature subobjects, one that has room and one
// already at the 64-DWORD budget, a request must reject atomically:
// neither subobject is replaced (not even the one with room), and no UAV
// resource is created. This is the "one unextendable signature blocks
// everything" transactional requirement across multiple root signatures.
TEST_F(PixTest,
       ToolsUav_BudgetRejectionAcrossMultipleGlobalRootSignaturesIsAtomic) {
  const char *source = R"x(
[shader("raygeneration")]
void RayGen()
{
})x";

  std::vector<uint8_t> extendable = BuildFillerRootSignatureBytes(0);
  std::vector<uint8_t> unextendable = BuildFillerRootSignatureBytes(64);

  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"lib_6_6", {});
  ModuleAndHangersOn moduleEtc(compiled);
  DxilModule &DM = moduleEtc.GetDxilModule();

  std::unique_ptr<DxilSubobjects> subObjects(new DxilSubobjects());
  constexpr bool notALocalRootSignature = false;
  subObjects->CreateRootSignature("extendableRootSignature",
                                  notALocalRootSignature, extendable.data(),
                                  static_cast<uint32_t>(extendable.size()));
  subObjects->CreateRootSignature("unextendableRootSignature",
                                  notALocalRootSignature, unextendable.data(),
                                  static_cast<uint32_t>(unextendable.size()));
  DM.ResetSubobjects(subObjects.release());

  bool caught = false;
  try {
    PIXPassHelpers::CreateGlobalUAVResource(DM, 0, "PIX_TestUAV");
  } catch (hlsl::Exception const &) {
    caught = true;
  }
  VERIFY_IS_TRUE(caught);

  VERIFY_ARE_EQUAL(size_t(0), DM.GetUAVs().size());

  std::map<std::string, std::vector<uint8_t> const *> expectedByName{
      {"extendableRootSignature", &extendable},
      {"unextendableRootSignature", &unextendable},
  };
  int checkedCount = 0;
  for (auto const &subObject : DM.GetSubobjects()->GetSubobjects()) {
    std::map<std::string, std::vector<uint8_t> const *>::iterator it =
        expectedByName.find(subObject.first.str());
    if (it == expectedByName.end()) {
      continue;
    }
    const void *data = nullptr;
    uint32_t size = 0;
    VERIFY_IS_TRUE(subObject.second->GetRootSignature(notALocalRootSignature,
                                                      data, size, nullptr));
    std::vector<uint8_t> const &expected = *it->second;
    VERIFY_ARE_EQUAL(expected.size(), static_cast<size_t>(size));
    VERIFY_IS_TRUE(std::equal(expected.begin(), expected.end(),
                              static_cast<const uint8_t *>(data)));
    ++checkedCount;
  }
  VERIFY_ARE_EQUAL(2, checkedCount);
}

// A batch request containing two entries for the SAME not-yet-existing
// register (no pre-existing root signature) must be deduplicated before
// any planning or commit: exactly one resource is created (named for the
// first request), one root-signature reservation is made, and BOTH
// result entries resolve to that single resource so a caller can still
// create a per-request handle for each original index.
TEST_F(PixTest, ToolsUav_DuplicateNewRequestsNoRootSignatureAreDeduped) {
  const char *source = R"x(
[numthreads(1, 1, 1)]
void main()
{})x";

  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"cs_6_0", {});
  ModuleAndHangersOn moduleEtc(compiled);
  DxilModule &DM = moduleEtc.GetDxilModule();

  std::vector<hlsl::DxilResource *> results =
      PIXPassHelpers::CreateGlobalUAVResources(
          DM, {{0u, "PIX_First"}, {0u, "PIX_Second"}});

  VERIFY_ARE_EQUAL(size_t(2), results.size());
  VERIFY_IS_NOT_NULL(results[0]);
  VERIFY_IS_NOT_NULL(results[1]);
  VERIFY_ARE_EQUAL(size_t(1), DM.GetUAVs().size());
  VERIFY_IS_TRUE(results[0] == results[1]);
  VERIFY_ARE_EQUAL(std::string("PIX_First"), results[0]->GetGlobalName());
}

// Same duplicate-register scenario, but with a pre-existing root
// signature that has room for exactly one 2-DWORD UAV descriptor (not
// two). Deduplication must happen before the root-signature reservation
// is planned, so this succeeds with a single reservation; without
// dedup, planning would (incorrectly) request space for two registers
// and exceed the budget.
TEST_F(PixTest, ToolsUav_DuplicateNewRequestsWithRootSignatureAreDeduped) {
  const char *source = R"x(
[numthreads(1, 1, 1)]
void main()
{})x";

  std::vector<uint8_t> original = BuildFillerRootSignatureBytes(62);
  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"cs_6_0", {});
  ModuleAndHangersOn moduleEtc(compiled);
  DxilModule &DM = moduleEtc.GetDxilModule();
  DM.ResetSerializedRootSignature(original);

  std::vector<hlsl::DxilResource *> results =
      PIXPassHelpers::CreateGlobalUAVResources(
          DM, {{0u, "PIX_First"}, {0u, "PIX_Second"}});

  VERIFY_ARE_EQUAL(size_t(2), results.size());
  VERIFY_IS_TRUE(results[0] == results[1]);
  VERIFY_ARE_EQUAL(size_t(1), DM.GetUAVs().size());

  const std::vector<uint8_t> &updated = DM.GetSerializedRootSignature();
  DxilVersionedRootSignature deserialized;
  DeserializeRootSignature(updated.data(),
                           static_cast<uint32_t>(updated.size()),
                           deserialized.get_address_of());
  VERIFY_ARE_EQUAL(2u, deserialized->Desc_1_0.NumParameters);
}

// Duplicate requests for a register that ALREADY has a tools UAV
// resource must be fully idempotent: no new resource, no new
// root-signature reservation, and both requests resolve to the
// pre-existing resource.
TEST_F(PixTest, ToolsUav_DuplicateRequestsForExistingResourceAreIdempotent) {
  const char *source = R"x(
[numthreads(1, 1, 1)]
void main()
{})x";

  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"cs_6_0", {});
  ModuleAndHangersOn moduleEtc(compiled);
  DxilModule &DM = moduleEtc.GetDxilModule();

  hlsl::DxilResource *existing =
      PIXPassHelpers::CreateGlobalUAVResource(DM, 0, "PIX_Existing");
  VERIFY_ARE_EQUAL(size_t(1), DM.GetUAVs().size());
  const std::vector<uint8_t> afterFirst = DM.GetSerializedRootSignature();

  std::vector<hlsl::DxilResource *> results =
      PIXPassHelpers::CreateGlobalUAVResources(
          DM, {{0u, "PIX_Dup1"}, {0u, "PIX_Dup2"}});

  VERIFY_ARE_EQUAL(size_t(2), results.size());
  VERIFY_IS_TRUE(results[0] == existing);
  VERIFY_IS_TRUE(results[1] == existing);
  VERIFY_ARE_EQUAL(size_t(1), DM.GetUAVs().size());

  const std::vector<uint8_t> &afterSecond = DM.GetSerializedRootSignature();
  VERIFY_ARE_EQUAL(afterFirst.size(), afterSecond.size());
  VERIFY_IS_TRUE(
      std::equal(afterFirst.begin(), afterFirst.end(), afterSecond.begin()));
}

// A real optimizer-pass rejection control (not an assert-success test
// helper): compiles a full container, embeds a crafted root signature as
// a DFCC_RootSignature container part, then calls
// IDxcOptimizer::RunOptimizer directly -- the same entry point
// RunShaderAccessTrackingPass wraps internally -- capturing its HRESULT
// explicitly instead of asserting success. At exactly 64 DWORDs after
// the pass's one tools UAV, the pass must succeed; one DWORD over
// budget, RunOptimizer must fail closed with no output module, proving
// the budget check is enforced on the real optimizer-pass path
// (DxcOptimizer::RunOptimizer catches the thrown hlsl::Exception via
// CATCH_CPP_RETURN_HRESULT and returns its HRESULT), not merely
// observable via PixPassHelpers unit tests.
TEST_F(PixTest, ToolsUav_OptimizerPassRejectsOverBudgetRootSignature) {
  const char *source = R"x(
RWByteAddressBuffer output : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    output.Store(4 * tid.x, tid.x);
})x";

  CComPtr<IDxcBlob> compiled =
      Compile(m_dllSupport, source, L"cs_6_2", {L"-Od"});

  CComPtr<IDxcOptimizer> pOptimizer;
  VERIFY_SUCCEEDED(
      m_dllSupport.CreateInstance(CLSID_DxcOptimizer, &pOptimizer));
  std::vector<LPCWSTR> Options;
  Options.push_back(L"-opt-mod-passes");
  Options.push_back(L"-hlsl-dxil-pix-shader-access-instrumentation,config=U0:0:"
                    L"10i0;U0:1:2i0;.0;0;0.");

  // At-budget case: u0 coverage (2 DWORDs) + filler at 60 DWORDs + the
  // pass's one 2-DWORD tools UAV = exactly 64. Must succeed.
  {
    std::vector<uint8_t> atBudget = BuildRootSignatureCoveringU0Bytes(60);
    CComPtr<IDxcBlob> container = AddRootSignaturePart(compiled, atBudget);

    CComPtr<IDxcBlob> pOutputModule;
    CComPtr<IDxcBlobEncoding> pText;
    HRESULT hr = pOptimizer->RunOptimizer(container, Options.data(),
                                          static_cast<UINT32>(Options.size()),
                                          &pOutputModule, &pText);
    VERIFY_SUCCEEDED(hr);
    VERIFY_IS_TRUE(pOutputModule.p != nullptr);
  }

  // Over-budget case: u0 coverage (2 DWORDs) + filler at 61 DWORDs + the
  // pass's one 2-DWORD tools UAV = 65, one over budget. RunOptimizer must
  // fail closed: a failure HRESULT and no usable output module, with the
  // caller's input container untouched.
  {
    std::vector<uint8_t> overBudget = BuildRootSignatureCoveringU0Bytes(61);
    CComPtr<IDxcBlob> container = AddRootSignaturePart(compiled, overBudget);
    std::vector<uint8_t> originalBytes(
        static_cast<const uint8_t *>(container->GetBufferPointer()),
        static_cast<const uint8_t *>(container->GetBufferPointer()) +
            container->GetBufferSize());

    CComPtr<IDxcBlob> pOutputModule;
    CComPtr<IDxcBlobEncoding> pText;
    HRESULT hr = pOptimizer->RunOptimizer(container, Options.data(),
                                          static_cast<UINT32>(Options.size()),
                                          &pOutputModule, &pText);
    VERIFY_FAILED(hr);
    VERIFY_IS_TRUE(pOutputModule.p == nullptr);

    VERIFY_ARE_EQUAL(originalBytes.size(),
                     static_cast<size_t>(container->GetBufferSize()));
    VERIFY_IS_TRUE(std::equal(
        originalBytes.begin(), originalBytes.end(),
        static_cast<const uint8_t *>(container->GetBufferPointer())));
  }
}

static bool HasUnusedDeclaration(std::vector<std::string> const &lines,
                                 std::string const &functionName) {
  bool declared = false;
  for (std::string const &line : lines) {
    if (line.find("declare") != std::string::npos &&
        line.find(functionName) != std::string::npos) {
      declared = true;
    }
    if (line.find("call") != std::string::npos &&
        line.find(functionName) != std::string::npos) {
      return false;
    }
  }
  return declared;
}

static bool HasDeclaration(const std::string &disassembly,
                           const std::string &functionName) {
  for (const std::string &line : Tokenize(disassembly, "\n")) {
    if (line.find("declare") != std::string::npos &&
        line.find(functionName) != std::string::npos) {
      return true;
    }
  }
  return false;
}

static std::string FindDeclarationLine(const std::string &disassembly,
                                       const std::string &functionName) {
  for (const std::string &line : Tokenize(disassembly, "\n")) {
    if (line.find("declare") != std::string::npos &&
        line.find(functionName) != std::string::npos) {
      return line;
    }
  }
  return {};
}

static bool HasDeclarationLine(const std::string &disassembly,
                               const std::string &declaration) {
  for (const std::string &line : Tokenize(disassembly, "\n")) {
    if (line == declaration) {
      return true;
    }
  }
  return false;
}

TEST_F(PixTest, ConstantColor_UnusedIntOverloadIsErased) {
  const char *source = R"x(
float4 main() : SV_Target
{
    return float4(1, 2, 3, 4);
})x";

  CComPtr<IDxcBlob> compiled =
      Compile(m_dllSupport, source, L"ps_6_0", {L"-Od"});
  SinglePassOutput output =
      RunSinglePass(compiled, L"-hlsl-dxil-constantColor");

  VERIFY_IS_FALSE(HasUnusedDeclaration(output.Lines, "dx.op.storeOutput.i32"));
  VerifyInstrumentedModuleIsValid(output.Module,
                                  "constant-colour substitution");
}

TEST_F(PixTest, ConstantColor_NoTargetOverloadsAreErased) {
  const char *source = R"x(
[numthreads(1, 1, 1)]
void main()
{
})x";

  CComPtr<IDxcBlob> compiled =
      Compile(m_dllSupport, source, L"cs_6_0", {L"-Od"});
  SinglePassOutput output =
      RunSinglePass(compiled, L"-hlsl-dxil-constantColor");
  const std::string disassembly = Disassemble(output.Module);

  VerifyInstrumentedModuleIsValid(
      output.Module, "constant-colour substitution with no target");
  VERIFY_IS_FALSE(HasDeclaration(disassembly, "dx.op.storeOutput.f32"));
  VERIFY_IS_FALSE(HasDeclaration(disassembly, "dx.op.storeOutput.i32"));
}

TEST_F(PixTest, RemoveDiscards_UnusedDiscardOverloadIsErased) {
  const char *source = R"x(
float4 main() : SV_Target
{
    return float4(1, 2, 3, 4);
})x";

  CComPtr<IDxcBlob> compiled =
      Compile(m_dllSupport, source, L"ps_6_0", {L"-Od"});
  SinglePassOutput output =
      RunSinglePass(compiled, L"-hlsl-dxil-remove-discards");

  VERIFY_IS_FALSE(HasUnusedDeclaration(output.Lines, "dx.op.discard"));
  VerifyInstrumentedModuleIsValid(output.Module,
                                  "discard removal with no discard");
}

TEST_F(PixTest, OperationCacheCleanup_RemovesErasedFunctions) {
  const char *source = R"x(
float4 main() : SV_Target
{
    return float4(1, 2, 3, 4);
})x";

  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"ps_6_0", {});
  ModuleAndHangersOn moduleEtc(compiled);
  DxilModule &DM = moduleEtc.GetDxilModule();
  OP *HlslOP = DM.GetOP();
  llvm::Function *discard =
      HlslOP->GetOpFunc(DXIL::OpCode::Discard,
                        llvm::Type::getVoidTy(DM.GetModule()->getContext()));

  VERIFY_ARE_EQUAL(1u,
                   static_cast<unsigned>(
                       HlslOP->GetOpFuncList(DXIL::OpCode::Discard).size()));
  PIXPassHelpers::EraseIfUnused(DM, discard);
  VERIFY_ARE_EQUAL(0u,
                   static_cast<unsigned>(
                       HlslOP->GetOpFuncList(DXIL::OpCode::Discard).size()));

  llvm::Function *recreated =
      HlslOP->GetOpFunc(DXIL::OpCode::Discard,
                        llvm::Type::getVoidTy(DM.GetModule()->getContext()));
  VERIFY_IS_NOT_NULL(recreated);
  PIXPassHelpers::EraseIfUnused(DM, recreated);
}

TEST_F(PixTest, DynamicResourceCleanup_VisitorStopsEarly) {
  const char *source = R"x(
Texture2D<float4> textures[] : register(t0);

float4 main(float2 uv : TEXCOORD0) : SV_Target
{
    return textures[(uint)uv.x].Load(int3(0, 0, 0));
})x";

  CComPtr<IDxcBlob> compiled =
      Compile(m_dllSupport, source, L"ps_6_0", {L"-Od"});
  ModuleAndHangersOn moduleEtc(compiled);
  DxilModule &DM = moduleEtc.GetDxilModule();
  bool visitorCalled = false;
  PIXPassHelpers::ForEachDynamicallyIndexedResource(
      DM, [&visitorCalled](bool, llvm::Instruction *, llvm::Value *) {
        visitorCalled = true;
        return false;
      });

  VERIFY_IS_TRUE(visitorCalled);
  OP *HlslOP = DM.GetOP();
  VERIFY_ARE_EQUAL(
      0u,
      static_cast<unsigned>(
          HlslOP->GetOpFuncList(DXIL::OpCode::CreateHandleFromBinding).size()));
  VERIFY_ARE_EQUAL(
      0u,
      static_cast<unsigned>(
          HlslOP->GetOpFuncList(DXIL::OpCode::CreateHandleFromHeap).size()));
}

TEST_F(PixTest, DxilPIXDXRInvocationsLog_SanityTest) {

  const char *source = R"x(
struct MyPayload
{
    float4 color;
};

[shader("raygeneration")]
void MyRayGen()
{
}

[shader("closesthit")]
void MyClosestHit(inout MyPayload payload, in BuiltInTriangleIntersectionAttributes attr)
{
}

[shader("anyhit")]
void MyAnyHit(inout MyPayload payload, in BuiltInTriangleIntersectionAttributes attr)
{
}

[shader("miss")]
void MyMiss(inout MyPayload payload)
{
}

)x";

  auto compiledLib = Compile(m_dllSupport, source, L"lib_6_6", {});
  RunDxilPIXDXRInvocationsLog(compiledLib);
}

TEST_F(PixTest, DxilPIXDXRInvocationsLog_EmbeddedRootSigs) {

  const char *source = R"x(

GlobalRootSignature grs = {"CBV(b0)"};
struct MyPayload
{
    float4 color;
};

[shader("raygeneration")]
void MyRayGen()
{
}

[shader("closesthit")]
void MyClosestHit(inout MyPayload payload, in BuiltInTriangleIntersectionAttributes attr)
{
}

[shader("anyhit")]
void MyAnyHit(inout MyPayload payload, in BuiltInTriangleIntersectionAttributes attr)
{
}

[shader("miss")]
void MyMiss(inout MyPayload payload)
{
}

)x";

  auto compiledLib = Compile(m_dllSupport, source, L"lib_6_3",
                             {L"-Qstrip_reflect"}, L"RootSig");
  RunDxilPIXDXRInvocationsLog(compiledLib);
}

TEST_F(PixTest, DxilPIXDXRInvocationsLog_ZeroCapacityEmitsNothing) {
  CComPtr<IDxcBlob> compiledLib =
      Compile(m_dllSupport, kSingleMissInvocationLogShader, L"lib_6_6", {});

  CComPtr<IDxcBlob> oneEntryOutput =
      RunDxilPIXDXRInvocationsLog(compiledLib, 1);
  std::vector<std::string> oneEntryLines =
      Tokenize(Disassemble(oneEntryOutput), "\n");
  VERIFY_ARE_EQUAL(2, CountToolsUAVRecords(oneEntryLines));

  CComPtr<IDxcBlob> zeroEntryOutput =
      RunDxilPIXDXRInvocationsLog(compiledLib, 0);
  std::vector<std::string> zeroEntryLines =
      Tokenize(Disassemble(zeroEntryOutput), "\n");
  VERIFY_ARE_EQUAL(0, CountToolsUAVRecords(zeroEntryLines));
}

TEST_F(PixTest, DxilPIXDXRInvocationsLog_OneEntryUsesEntryCountBound) {
  CComPtr<IDxcBlob> compiledLib =
      Compile(m_dllSupport, kSingleMissInvocationLogShader, L"lib_6_6", {});
  CComPtr<IDxcBlob> output = RunDxilPIXDXRInvocationsLog(compiledLib, 1);
  std::vector<std::string> lines = Tokenize(Disassemble(output), "\n");

  VERIFY_IS_TRUE(HasDxrInvocationLogEntryCountCheck(lines, 1));
}

TEST_F(PixTest, DxilPIXDXRInvocationsLog_ExactCapacityUsesEntryCountBound) {
  CComPtr<IDxcBlob> compiledLib =
      Compile(m_dllSupport, kSingleMissInvocationLogShader, L"lib_6_6", {});
  CComPtr<IDxcBlob> output = RunDxilPIXDXRInvocationsLog(compiledLib, 24);
  std::vector<std::string> lines = Tokenize(Disassemble(output), "\n");

  VERIFY_IS_TRUE(HasDxrInvocationLogEntryCountCheck(lines, 24));
}

TEST_F(PixTest, DxilPIXDXRInvocationsLog_OverflowGuardValidates) {
  CComPtr<IDxcBlob> compiledLib =
      Compile(m_dllSupport, kSingleMissInvocationLogShader, L"lib_6_6", {});
  CComPtr<IDxcBlob> output = RunDxilPIXDXRInvocationsLog(compiledLib, 1);
  std::string disassembly = Disassemble(output);

  VERIFY_IS_TRUE(disassembly.find("@dx.op.binary.i32") == std::string::npos);
  VerifyInstrumentedModuleIsValid(output, "DXR invocations log overflow guard");
}

// Reviewer item 4.1: directly test HasDxrInvocationLogEntryCountCheck's
// value-boundary behavior with synthetic lines, independent of what the
// production pass actually emits, per the reviewer's exact example (an
// expected bound of 1 must not match text containing 10 or 100).
TEST_F(
    PixTest,
    DxilPIXDXRInvocationsLog_EntryCountCheckRejectsLongerBoundWithSamePrefix) {
  const std::vector<std::string> longerBoundLines = {
      "  %x = icmp ult i32 %EntryIndexResult, 100"};
  VERIFY_IS_FALSE(HasDxrInvocationLogEntryCountCheck(longerBoundLines, 1));

  // Reviewer follow-up: a following digit is not the only bad continuation;
  // any non-delimiter character (e.g. a letter, forming a different token
  // like a register name) must also be rejected.
  const std::vector<std::string> letterContinuationLines = {
      "  %x = icmp ult i32 %EntryIndexResult, 1x"};
  VERIFY_IS_FALSE(
      HasDxrInvocationLogEntryCountCheck(letterContinuationLines, 1));

  // Punctuation that is not the metadata-attachment comma must also be
  // rejected (e.g. a stray closing paren from a different construct).
  const std::vector<std::string> punctuationContinuationLines = {
      "  %x = icmp ult i32 %EntryIndexResult, 1)"};
  VERIFY_IS_FALSE(
      HasDxrInvocationLogEntryCountCheck(punctuationContinuationLines, 1));

  const std::vector<std::string> matchingOneLines = {
      "  %x = icmp ult i32 %EntryIndexResult, 1"};
  VERIFY_IS_TRUE(HasDxrInvocationLogEntryCountCheck(matchingOneLines, 1));

  const std::vector<std::string> matching24Lines = {
      "  %x = icmp ult i32 %EntryIndexResult, 24"};
  VERIFY_IS_TRUE(HasDxrInvocationLogEntryCountCheck(matching24Lines, 24));

  // A trailing CR (as if the line still carried a "\r\n" ending after
  // Tokenize split only on "\n") is whitespace and must still be accepted.
  const std::vector<std::string> crlfLines = {
      "  %x = icmp ult i32 %EntryIndexResult, 1\r"};
  VERIFY_IS_TRUE(HasDxrInvocationLogEntryCountCheck(crlfLines, 1));

  // A comma introducing an attached metadata reference (e.g. "!dbg") is a
  // valid continuation of the operand and must still be accepted.
  const std::vector<std::string> metadataAttachedLines = {
      "  %x = icmp ult i32 %EntryIndexResult, 1, !dbg !12"};
  VERIFY_IS_TRUE(HasDxrInvocationLogEntryCountCheck(metadataAttachedLines, 1));
}

uint32_t NuriGetWaveInstructionCount(const std::vector<std::string> &lines) {
  // This is the instruction we'll insert into the shader if we detect dynamic
  // resource indexing
  const char *const waveActiveAllEqual = "call i1 @dx.op.waveActiveAllEqual";

  uint32_t instCount = 0;
  for (const std::string &line : lines) {
    instCount += line.find(waveActiveAllEqual) != std::string::npos;
  }
  return instCount;
}

void PixTest::TestNuriCase(const char *source, const wchar_t *target,
                           uint32_t expectedResult) {

  for (const OptimizationChoice &choice : OptimizationChoices) {
    const std::vector<LPCWSTR> compilationOptions = {choice.Flag};

    CComPtr<IDxcBlob> compiledLib =
        Compile(m_dllSupport, source, target, compilationOptions);

    std::string outputText;
    PassOutput output =
        RunDxilNonUniformResourceIndexInstrumentation(compiledLib, outputText);
    const std::vector<std::string> &dxilLines = output.lines;

    VERIFY_ARE_EQUAL(NuriGetWaveInstructionCount(dxilLines), expectedResult);

    bool foundDynamicIndexingNoNuri = false;
    const std::vector<std::string> outputTextLines = Tokenize(outputText, "\n");
    for (const std::string &line : outputTextLines) {
      if (line.find("FoundDynamicIndexingNoNuri") != std::string::npos) {
        foundDynamicIndexingNoNuri = true;
        break;
      }
    }

    VERIFY_ARE_EQUAL((expectedResult != 0), foundDynamicIndexingNoNuri);
  }
}

TEST_F(PixTest, NonUniformResourceIndex_Resource) {

  const char *source = R"x(
Texture2D tex[] : register(t0);
float4 main(float2 uv : TEXCOORD0) : SV_TARGET
{
    uint index = uv.x * uv.y;
    return tex[index].Load(int3(0, 0, 0));
})x";

  const char *sourceWithNuri = R"x(
Texture2D tex[] : register(t0);
float4 main(float2 uv : TEXCOORD0) : SV_TARGET
{
    uint i = uv.x * uv.y;
    return tex[NonUniformResourceIndex(i)].Load(int3(0, 0, 0));
})x";

  TestNuriCase(source, L"ps_6_0", 1);
  TestNuriCase(sourceWithNuri, L"ps_6_0", 0);

  if (m_ver.SkipDxilVersion(1, 6)) {
    return;
  }

  TestNuriCase(source, L"ps_6_6", 1);
  TestNuriCase(sourceWithNuri, L"ps_6_6", 0);
}

// Reviewer item 3.1 (C++ coverage):
// NonUniformResourceIndexNoInstructionNumbers.hlsl can directly check that the
// tools UAV is not created (CHECK-NOT: PixUAVResource), but it cannot observe
// root signature content: %dxc's FileCheck substitution disassembles the
// fully-serialized container, by which point the root signature is already a
// separate container part and not IR metadata, so %opt never sees it regardless
// of the pass's behavior. Prove the root-signature guarantee here instead.
//
// Root signature bytes live only as a transient DxilModule field
// (DxilModule::m_SerializedRootSignature): DxilContainerAssembler moves them
// into a separate container part during final serialization, so neither a
// freshly compiled container nor a bitcode-only blob round-tripped through
// IDxcOptimizer ever carries them (confirmed empirically: both come back
// empty). RunDxilNonUniformResourceIndexInstrumentation also cannot be reused
// as-is: its Options list always includes -dxil-annotate-with-virtual-regs,
// which assigns instruction numbers to every createHandle call and so
// defeats the missing-instruction-number scenario this test targets.
//
// Reuse the same in-place pattern ToolsUav_RootSignatureSerializationFailure-
// PreservesSignature already established for this exact constraint: load the
// compiled module once, seed the root signature directly via
// DxilModule::ResetSerializedRootSignature, and invoke the pass's production
// logic directly (createDxilNonUniformResourceIndexInstrumentationPass()'s
// ModulePass::runOnModule; this pass declares no analysis dependencies, so
// no PassManager scaffolding is required) instead of a blob-in/blob-out
// IDxcOptimizer round trip.
TEST_F(PixTest,
       NonUniformResourceIndex_MissingInstructionNumberPreservesRootSignature) {
  const char *source = R"x(
Texture2D tex[8] : register(t0);

float4 main(float2 uv : TEXCOORD0) : SV_TARGET
{
    uint index = uv.x * uv.y;
    return tex[index].Load(int3(0, 0, 0));
})x";

  // A known, non-empty root signature compatible with the shader (matches
  // the reviewer's example).
  DxilDescriptorRange range = {};
  range.RangeType = DxilDescriptorRangeType::SRV;
  range.NumDescriptors = 8;
  range.BaseShaderRegister = 0;
  range.RegisterSpace = 0;
  range.OffsetInDescriptorsFromTableStart = DxilDescriptorRangeOffsetAppend;

  DxilRootParameter parameter = {};
  parameter.ParameterType = DxilRootParameterType::DescriptorTable;
  parameter.DescriptorTable.NumDescriptorRanges = 1;
  parameter.DescriptorTable.pDescriptorRanges = &range;
  parameter.ShaderVisibility = DxilShaderVisibility::All;

  DxilVersionedRootSignatureDesc rootSignature = {};
  rootSignature.Version = DxilRootSignatureVersion::Version_1_0;
  rootSignature.Desc_1_0.NumParameters = 1;
  rootSignature.Desc_1_0.pParameters = &parameter;
  rootSignature.Desc_1_0.Flags = DxilRootSignatureFlags::None;

  // REC-2: RegisterSpace 0 is an ordinary application-visible space, not
  // one of the system-reserved spaces DxilRootSignatureValidator gates on
  // (DxilSystemReservedRegisterSpaceValuesStart..End, e.g. the -2 tools
  // space used elsewhere in this file); bAllowReservedRegisterSpace=false
  // is therefore semantically correct here (unlike
  // ToolsUav_RootSignatureSerializationFailurePreservesSignature, which
  // seeds a genuinely reserved space and needs true).
  CComPtr<IDxcBlob> serializedRootSignature;
  CComPtr<IDxcBlobEncoding> errorBlob;
  SerializeRootSignature(&rootSignature, &serializedRootSignature, &errorBlob,
                         false);
  VERIFY_IS_NOT_NULL(serializedRootSignature);

  const uint8_t *serializedData =
      static_cast<const uint8_t *>(serializedRootSignature->GetBufferPointer());
  std::vector<uint8_t> originalRootSignature(
      serializedData,
      serializedData + serializedRootSignature->GetBufferSize());

  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"ps_6_0", {});
  ModuleAndHangersOn moduleEtc(compiled);
  DxilModule &DM = moduleEtc.GetDxilModule();
  DM.ResetSerializedRootSignature(originalRootSignature);

  std::unique_ptr<llvm::ModulePass> pass(
      llvm::createDxilNonUniformResourceIndexInstrumentationPass());
  // REC-1: attach a report stream so the pass's diagnostic text is
  // observable, and require it actually reports the missing-instruction-
  // number condition. Without this, the test could pass vacuously if a
  // future change caused the pass to silently skip the handle for an
  // unrelated reason (e.g. failing to find it at all) rather than
  // correctly detecting the missing precondition.
  std::string report;
  llvm::raw_string_ostream ReportStream(report);
  pass->setOSOverride(&ReportStream);

  // No annotation prepass ran, so no createHandle carries an instruction
  // number: this exercises the same missing-precondition path as the
  // .hlsl test.
  pass->runOnModule(*DM.GetModule());
  ReportStream.flush();
  VERIFY_IS_TRUE(report.find("NuriNotInstrumentedMissingInstructionNumber") !=
                 std::string::npos);

  // Root-signature check first: CreateGlobalUAVResource (which the pass
  // would call if it wrongly instrumented this handle) also appends a UAV
  // parameter to any present root signature via
  // AddUAVToShaderAttributeRootSignature, so this assertion is the one
  // that specifically catches a regression on this path, not just the
  // UAV-count check below.
  const std::vector<uint8_t> &actualRootSignature =
      DM.GetSerializedRootSignature();
  VERIFY_ARE_EQUAL(originalRootSignature.size(), actualRootSignature.size());
  VERIFY_IS_TRUE(std::equal(originalRootSignature.begin(),
                            originalRootSignature.end(),
                            actualRootSignature.begin()));

  VERIFY_ARE_EQUAL(0u, CountToolsUAVs(DM));
}

TEST_F(PixTest, NonUniformResourceIndex_QualifiedCleanupValidates) {
  if (m_ver.SkipDxilVersion(1, 6)) {
    return;
  }

  const char *source = R"x(
Texture2D<float4> textures[] : register(t0);

float4 main(float2 uv : TEXCOORD0) : SV_Target
{
    uint index = (uint)uv.x;
    return textures[NonUniformResourceIndex(index)].Load(int3(0, 0, 0));
})x";

  CComPtr<IDxcBlob> compiled =
      Compile(m_dllSupport, source, L"ps_6_6", {L"-Od"});
  std::string outputText;
  PassOutput output =
      RunDxilNonUniformResourceIndexInstrumentation(compiled, outputText);
  const std::string disassembly = Disassemble(output.blob);

  VerifyInstrumentedModuleIsValid(
      output.blob, "qualified non-uniform resource index instrumentation");
  VERIFY_ARE_EQUAL(0u, NuriGetWaveInstructionCount(output.lines));
  VERIFY_IS_FALSE(HasDeclaration(disassembly, "dx.op.waveActiveAllEqual.i32"));
  VERIFY_IS_FALSE(HasDeclaration(disassembly, "dx.op.atomicBinOp.i32"));
}

TEST_F(PixTest, NonUniformResourceIndex_DescriptorHeap) {

  if (m_ver.SkipDxilVersion(1, 6)) {
    return;
  }

  const char *source = R"x(
Texture2D tex[] : register(t0);
float4 main(float2 uv : TEXCOORD0) : SV_TARGET
{
    uint i = uv.x + uv.y;
    Texture2D<float4> dynResTex = 
        ResourceDescriptorHeap[i];
    SamplerState dynResSampler = 
        SamplerDescriptorHeap[i];
    return dynResTex.Sample(dynResSampler, uv);
})x";

  const char *sourceWithNuri = R"x(
Texture2D tex[] : register(t0);
float4 main(float2 uv : TEXCOORD0) : SV_TARGET
{
    uint i = uv.x + uv.y;
    Texture2D<float4> dynResTex = 
        ResourceDescriptorHeap[NonUniformResourceIndex(i)];
    SamplerState dynResSampler = 
        SamplerDescriptorHeap[NonUniformResourceIndex(i)];
    return dynResTex.Sample(dynResSampler, uv);
})x";

  TestNuriCase(source, L"ps_6_6", 2);
  TestNuriCase(sourceWithNuri, L"ps_6_6", 0);
}

TEST_F(PixTest, NonUniformResourceIndex_Raytracing) {

  if (m_ver.SkipDxilVersion(1, 5)) {
    return;
  }

  const char *source = R"x(
RWTexture2D<float4> RT[] : register(u0);

[noinline]
void FuncNoInline(uint index)
{
    float2 rayIndex = DispatchRaysIndex().xy;
    uint i = index + rayIndex.x * rayIndex.y;
    float4 c = float4(0.5, 0.5, 0.5, 0);
    RT[i][rayIndex.xy] += c;
}

void Func(uint index)
{
    float2 rayIndex = DispatchRaysIndex().xy;
    uint i = index + rayIndex.y;
    float4 c = float4(0, 1, 0, 0);
    RT[i][rayIndex.xy] += c;
}

[shader("raygeneration")]
void Main()
{
    float2 rayIndex = DispatchRaysIndex().xy;

    uint i1 = rayIndex.x;
    float4 c1 = float4(1, 0, 1, 1);
    RT[i1][rayIndex.xy] += c1;

    uint i2 = rayIndex.x * rayIndex.y * 0.25;
    float4 c2 = float4(0.25, 0, 0.25, 0);
    RT[i2][rayIndex.xy] += c2;

    Func(i1);
    FuncNoInline(i2);
})x";

  const char *sourceWithNuri = R"x(
RWTexture2D<float4> RT[] : register(u0);

[noinline]
void FuncNoInline(uint index)
{
    float2 rayIndex = DispatchRaysIndex().xy;
    uint i = index + rayIndex.x * rayIndex.y;
    float4 c = float4(0.5, 0.5, 0.5, 0);
    RT[NonUniformResourceIndex(i)][rayIndex.xy] += c;
}

void Func(uint index)
{
    float2 rayIndex = DispatchRaysIndex().xy;
    uint i = index + rayIndex.y;
    float4 c = float4(0, 1, 0, 0);
    RT[NonUniformResourceIndex(i)][rayIndex.xy] += c;
}

[shader("raygeneration")]
void Main()
{
    float2 rayIndex = DispatchRaysIndex().xy;

    uint i1 = rayIndex.x;
    float4 c1 = float4(1, 0, 1, 1);
    RT[NonUniformResourceIndex(i1)][rayIndex.xy] += c1;

    uint i2 = rayIndex.x * rayIndex.y * 0.25;
    float4 c2 = float4(0.25, 0, 0.25, 0);
    RT[NonUniformResourceIndex(i2)][rayIndex.xy] += c2;

    Func(i1);
    FuncNoInline(i2);
})x";

  TestNuriCase(source, L"lib_6_5", 4);
  TestNuriCase(sourceWithNuri, L"lib_6_5", 0);
}

TEST_F(PixTest, DebugInstrumentation_TextOutput) {

  const char *source = R"x(
float4 main() : SV_Target {
    return float4(0,0,0,0);
})x";

  auto compiled = Compile(m_dllSupport, source, L"ps_6_0", {});
  auto output = RunDebugPass(compiled, 8 /*ludicrously low UAV size limit*/);
  bool foundStaticOverflow = false;
  bool foundCounterOffset = false;
  bool foundThreshold = false;
  for (auto const &line : output.lines) {
    if (line.find("StaticOverflow:12") != std::string::npos)
      foundStaticOverflow = true;
    if (line.find("InterestingCounterOffset:3") != std::string::npos)
      foundCounterOffset = true;
    if (line.find("OverflowThreshold:1") != std::string::npos)
      foundThreshold = true;
  }
  VERIFY_IS_TRUE(foundStaticOverflow);
}

TEST_F(PixTest, DebugInstrumentation_BlockReport) {

  const char *source = R"x(
RWStructuredBuffer<int> UAV: register(u0);
float4 main() : SV_Target {
    // basic int variable
    int v = UAV[0];
    if(v == 0)
        UAV[1] = v;
    else
        UAV[2] = v;
    // float with indexed alloca
    float f[2];
    f[0] = UAV[4];
    f[1] = UAV[5];
    if(v == 2)
        f[0] = v;
    else
        f[1] = v;
    float farray2[2];
    farray2[0] = UAV[4];
    farray2[1] = UAV[5];
    if(v == 4)
        farray2[0] = v;
    else
        farray2[1] = v;
    double d = UAV[8];
    int64_t i64 = UAV[9];
    return float4(d,i64,0,0);
})x";

  auto compiled = Compile(m_dllSupport, source, L"ps_6_0", {L"-Od"});
  auto output = RunDebugPass(compiled);
  bool foundBlock = false;
  bool foundRet = false;
  bool foundUnnumberedVoidProllyADXNothing = false;
  bool found32BitAssignment = false;
  bool foundFloatAssignment = false;
  bool foundDoubleAssignment = false;
  bool found64BitAssignment = false;
  bool found32BitAllocaStore = false;
  for (auto const &line : output.lines) {
    if (line.find("Block#") != std::string::npos) {
      if (line.find("r,0,r;") != std::string::npos)
        foundRet = true;
      if (line.find("v,0,v;") != std::string::npos)
        foundUnnumberedVoidProllyADXNothing = true;
      if (line.find("3,3,a;") != std::string::npos)
        found32BitAssignment = true;
      if (line.find("d,13,a;") != std::string::npos)
        foundDoubleAssignment = true;
      if (line.find("f,19,a;") != std::string::npos)
        foundFloatAssignment = true;
      if (line.find("6,16,a;") != std::string::npos)
        found64BitAssignment = true;
      if (line.find("3,3,s,2+0;") != std::string::npos)
        found32BitAllocaStore = true;
      foundBlock = true;
    }
  }
  VERIFY_IS_TRUE(foundBlock);
  VERIFY_IS_TRUE(foundRet);
  VERIFY_IS_TRUE(foundUnnumberedVoidProllyADXNothing);
  VERIFY_IS_TRUE(found32BitAssignment);
  VERIFY_IS_TRUE(found64BitAssignment);
  VERIFY_IS_TRUE(foundFloatAssignment);
  VERIFY_IS_TRUE(foundDoubleAssignment);
  VERIFY_IS_TRUE(found32BitAllocaStore);
}

std::string ExtractBracedSubstring(std::string const &line) {
  auto open = line.find('{');
  auto close = line.find('}');
  if (open != std::string::npos && close != std::string::npos &&
      open + 1 < close) {
    return line.substr(open + 1, close - open - 1);
  }
  return {};
}

int ExtractMetaInt32Value(std::string const &token) {
  auto findi32 = token.find("i32 ");
  if (findi32 != std::string_view::npos) {
    return atoi(
        std::string(token.data() + findi32 + 4, token.length() - (findi32 + 4))
            .c_str());
  }
  return -1;
}

std::vector<std::string> Split(std::string str, char delimeter) {
  std::vector<std::string> lines;

  auto const *p = str.data();
  auto const *justPastPreviousDelimiter = p;
  while (p < str.data() + str.length()) {
    if (*p == delimeter) {
      lines.emplace_back(std::string(justPastPreviousDelimiter,
                                     p - justPastPreviousDelimiter));
      justPastPreviousDelimiter = p + 1;
      p = justPastPreviousDelimiter;
    } else {
      p++;
    }
  }

  lines.emplace_back(
      std::string(justPastPreviousDelimiter, p - justPastPreviousDelimiter));

  return lines;
}

struct MetadataAllocaDefinition {
  int base;
  int count;
};
using AllocaDefinitions = std::map<int, MetadataAllocaDefinition>;
struct MetadataAllocaWrite {
  int allocaDefMetadataKey;
  int offset;
  int size;
};
using AllocaWrites = std::map<int, MetadataAllocaWrite>;

struct AllocaMetadata {
  AllocaDefinitions allocaDefinitions;
  AllocaWrites allocaWrites;
  std::vector<int> allocaWritesMetaKeys;
};

AllocaMetadata
FindAllocaRelatedMetadata(std::vector<std::string> const &lines) {

  const char *allocaMetaDataAssignment = "= !{i32 1, ";
  const char *allocaRegWRiteAssignment = "= !{i32 2, !";
  const char *allocaRegWriteTag = "!pix-alloca-reg-write !";

  AllocaMetadata ret;
  for (auto const &line : lines) {
    if (line[0] == '!') {
      auto key = atoi(std::string(line.data() + 1, line.length() - 1).c_str());
      if (key != -1) {
        if (line.find(allocaMetaDataAssignment) != std::string::npos) {
          std::string bitInBraces = ExtractBracedSubstring(line);
          if (bitInBraces != "") {
            auto tokens = Split(bitInBraces, ',');
            if (tokens.size() == 3) {
              auto value0 = ExtractMetaInt32Value(tokens[1]);
              auto value1 = ExtractMetaInt32Value(tokens[2]);
              if (value0 != -1 && value1 != -1) {
                MetadataAllocaDefinition def;
                def.base = value0;
                def.count = value1;
                ret.allocaDefinitions[key] = def;
              }
            }
          }
        } else if (line.find(allocaRegWRiteAssignment) != std::string::npos) {
          std::string bitInBraces = ExtractBracedSubstring(line);
          if (bitInBraces != "") {
            auto tokens = Split(bitInBraces, ',');
            if (tokens.size() == 4 && tokens[1][1] == '!') {
              auto allocaKey = atoi(tokens[1].c_str() + 2);
              auto value0 = ExtractMetaInt32Value(tokens[2]);
              auto value1 = ExtractMetaInt32Value(tokens[3]);
              if (value0 != -1 && value1 != -1) {
                MetadataAllocaWrite aw;
                aw.allocaDefMetadataKey = allocaKey;
                aw.size = value0;
                aw.offset = value1;
                ret.allocaWrites[key] = aw;
              }
            }
          }
        }
      }
    } else {
      auto findAw = line.find(allocaRegWriteTag);
      if (findAw != std::string::npos) {
        ret.allocaWritesMetaKeys.push_back(
            atoi(line.c_str() + findAw + strlen(allocaRegWriteTag)));
      }
    }
  }
  return ret;
}

TEST_F(PixTest, DebugInstrumentation_VectorAllocaWrite_Structs) {
  const char *source = R"x(
RaytracingAccelerationStructure Scene : register(t0, space0);
struct RayPayload
{
    float4 color;
};
RWStructuredBuffer<float> UAV: register(u0);
[shader("raygeneration")]
void RaygenInternalName()
{
    RayDesc ray;
    ray.Origin = float3(UAV[0], UAV[1],UAV[3]);
    ray.Direction = float3(4.4,5.5,6.6);
    ray.TMin = 0.001;
    ray.TMax = 10000.0;
    RayPayload payload = { float4(0, 1, 0, 1) };
    TraceRay(Scene, RAY_FLAG_CULL_BACK_FACING_TRIANGLES, ~0, 0, 1, 0, ray, payload);
})x";

  auto compiled = Compile(m_dllSupport, source, L"lib_6_6", {L"-Od"});
  auto output = RunDebugPass(compiled);
  auto disassembly = Disassemble(output.blob);
  auto lines = Split(disassembly, '\n');
  auto metaDataKeyToValue = FindAllocaRelatedMetadata(lines);
  // To validate that the RayDesc and RayPayload instances were fully covered,
  // check that there are alloca writes that cover all of them. RayPayload
  // has four elements, and RayDesc has eight.
  std::array<bool, 4> RayPayloadElementCoverage;

  for (auto const &write : metaDataKeyToValue.allocaWrites) {
    // the whole point of the changes with this test is to separate vector
    // writes into individual elements:
    VERIFY_ARE_EQUAL(1, write.second.size);
    auto findAlloca = metaDataKeyToValue.allocaDefinitions.find(
        write.second.allocaDefMetadataKey);
    if (findAlloca != metaDataKeyToValue.allocaDefinitions.end()) {
      if (findAlloca->second.count == 4) {
        RayPayloadElementCoverage[write.second.offset] = true;
      }
    }
  }
  // Check that coverage for every element was emitted:
  for (auto const &b : RayPayloadElementCoverage)
    VERIFY_IS_TRUE(b);
}

TEST_F(PixTest, DebugBreakInstrumentation_Basic) {
  if (m_ver.SkipDxilVersion(1, 10))
    return;

  const char *source = R"x(
[numthreads(1, 1, 1)]
void main() {
    DebugBreak();
})x";

  auto compiled = Compile(m_dllSupport, source, L"cs_6_10", {});
  auto output = RunDebugBreakPass(compiled);
  bool foundDebugBreak = false;
  for (auto const &line : output.lines) {
    if (line.find("FoundDebugBreak") != std::string::npos)
      foundDebugBreak = true;
  }
  VERIFY_IS_TRUE(foundDebugBreak);
}

TEST_F(PixTest, DebugBreakInstrumentation_NoDebugBreak) {
  if (m_ver.SkipDxilVersion(1, 10))
    return;

  const char *source = R"x(
[numthreads(1, 1, 1)]
void main() {
})x";

  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"cs_6_10", {});
  auto output = RunDebugBreakPass(compiled);
  bool foundDebugBreak = false;
  for (auto const &line : output.lines) {
    if (line.find("FoundDebugBreak") != std::string::npos)
      foundDebugBreak = true;
  }
  VERIFY_IS_FALSE(foundDebugBreak);
  VerifyInstrumentedModuleIsValid(output.blob,
                                  "debug-break instrumentation with no call");
}

TEST_F(PixTest, DebugBreakInstrumentation_Multiple) {
  if (m_ver.SkipDxilVersion(1, 10))
    return;

  const char *source = R"x(
RWByteAddressBuffer buf : register(u0);
[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
    if (tid.x == 0)
        DebugBreak();
    buf.Store(0, tid.x);
    if (tid.x == 1)
        DebugBreak();
})x";

  auto compiled = Compile(m_dllSupport, source, L"cs_6_10", {});
  auto output = RunDebugBreakPass(compiled);
  bool foundDebugBreak = false;
  for (auto const &line : output.lines) {
    if (line.find("FoundDebugBreak") != std::string::npos)
      foundDebugBreak = true;
  }
  VERIFY_IS_TRUE(foundDebugBreak);

  // Verify the disassembly contains the expected AtomicBinOp calls
  // and no remaining DebugBreak calls
  auto disassembly = Disassemble(output.blob);
  VERIFY_IS_TRUE(disassembly.find("dx.op.debugBreak") == std::string::npos);

  // Count the number of DebugBreakBitSet calls to verify both
  // DebugBreak() calls were instrumented
  int debugBreakBitSetCount = 0;
  std::string::size_type pos = 0;
  while ((pos = disassembly.find("DebugBreakBitSet", pos)) !=
         std::string::npos) {
    debugBreakBitSetCount++;
    pos += strlen("DebugBreakBitSet");
  }
  VERIFY_ARE_EQUAL(debugBreakBitSetCount, 2);
}

///////////////////////////////////////////////////////////////////////////////
// Control tests for the PIX pass validation harness
// (ValidateInstrumentedModule / VerifyInstrumentedModuleIsValid).
//
// Both tests instrument the same trivial pixel shader with the
// virtual-register annotation pass, so the valid and invalid cases are
// directly comparable.

TEST_F(PixTest, Validation_ControlValidModulePasses) {
  const char *source = R"x(
float main() : SV_Target
{
    return 0;
})x";

  // Virtual-register annotation adds metadata that DXIL does not consume;
  // ValidateInstrumentedModule excuses only the four known PIX kinds.
  CComPtr<IDxcBlob> compiled =
      Compile(m_dllSupport, source, L"ps_6_0", {L"-Od"});
  SinglePassOutput output =
      RunSinglePass(compiled, L"-dxil-annotate-with-virtual-regs");
  VerifyInstrumentedModuleIsValid(
      output.Module,
      "virtual-register annotation of a trivial pixel shader (validation "
      "harness control)");
}

// Control for the fast path in ValidateInstrumentedModule: a module with no
// unused metadata at all validates on the first, direct attempt, without
// ever exercising the clone/strip machinery.
TEST_F(PixTest, Validation_ControlAlreadyValidModuleFastPath) {
  const char *source = R"x(
float main() : SV_Target
{
    return 0;
})x";

  // No PIX pass runs here, so there is no unused virtual-register
  // metadata; a plain compiled shader validates directly.
  CComPtr<IDxcBlob> compiled =
      Compile(m_dllSupport, source, L"ps_6_0", {L"-Od"});
  VerifyInstrumentedModuleIsValid(compiled,
                                  "plain compiled pixel shader, no PIX pass "
                                  "(direct-valid fast-path control)");
}

TEST_F(PixTest, Validation_ControlInvalidModuleFails) {
  const char *source = R"x(
float main() : SV_Target
{
    return 0;
})x";

  // Same shader and pass as Validation_ControlValidModulePasses; only the
  // corruption below differs.
  CComPtr<IDxcBlob> compiled =
      Compile(m_dllSupport, source, L"ps_6_0", {L"-Od"});
  SinglePassOutput output =
      RunSinglePass(compiled, L"-dxil-annotate-with-virtual-regs");

  // Confirm the baseline validates before corrupting it, so the failure
  // below is caused by the corruption and nothing else.
  VerifyInstrumentedModuleIsValid(
      output.Module,
      "virtual-register annotation of a trivial pixel shader, uncorrupted "
      "baseline (validation harness control)");

  // Mislabel the shader stage. The validator must reject this regardless
  // of the known PIX metadata kinds. This corruption also survives
  // ValidateInstrumentedModule's clone/serialize/reassemble round trip
  // unchanged, so it exercises the identity-clone gate: the identity clone
  // must still fail (proving reassembly alone did not mask the defect)
  // before the stripped clone is even attempted, and the stripped clone
  // must still fail too, since the defect is not metadata.
  std::string disassembly = Disassemble(output.Module);
  const std::string shaderKindTag = "!\"ps\",";
  std::string::size_type tagPosition = disassembly.find(shaderKindTag);
  VERIFY_IS_TRUE(tagPosition != std::string::npos);
  disassembly.replace(tagPosition, shaderKindTag.size(), "!\"vs\",");

  CComPtr<IDxcBlobEncoding> pDisassemblyBlob;
  CreateBlobFromText(m_dllSupport, disassembly.c_str(), &pDisassemblyBlob);

  CComPtr<IDxcAssembler> pAssembler;
  VERIFY_SUCCEEDED(
      m_dllSupport.CreateInstance(CLSID_DxcAssembler, &pAssembler));
  CComPtr<IDxcOperationResult> pAssembleResult;
  VERIFY_SUCCEEDED(
      pAssembler->AssembleToContainer(pDisassemblyBlob, &pAssembleResult));
  HRESULT assembleStatus;
  VERIFY_SUCCEEDED(pAssembleResult->GetStatus(&assembleStatus));
  VERIFY_SUCCEEDED(assembleStatus);
  CComPtr<IDxcBlob> pCorruptedContainer;
  VERIFY_SUCCEEDED(pAssembleResult->GetResult(&pCorruptedContainer));

  // Snapshot the caller's container bytes so we can confirm below that
  // neither the identity clone nor ValidateInstrumentedModule mutates it
  // in place. This is a container-shaped input (unlike
  // Validation_ControlNonPixUnusedMetadataIsRejected's bare-bitcode
  // input), so it exercises the NormalizeToContainer pass-through path.
  std::vector<uint8_t> originalContainerBytes(
      static_cast<const uint8_t *>(pCorruptedContainer->GetBufferPointer()),
      static_cast<const uint8_t *>(pCorruptedContainer->GetBufferPointer()) +
          pCorruptedContainer->GetBufferSize());

  // Lock down the identity-clone premise directly, not just the overall
  // disposition: the shader-kind corruption must still fail validation
  // after the very same clone/serialize/reassemble round trip
  // ValidateInstrumentedModule's identity-clone gate performs (a no-op
  // mutation). The overall disposition below would also read as invalid
  // if this premise silently broke and the gate fell back to the original
  // failure for the wrong reason, so assert on the identity clone itself.
  CComPtr<IDxcBlob> identityClone =
      CloneModuleAndMutate(pCorruptedContainer, [](llvm::Module &) {});
  VERIFY_IS_FALSE(RunValidator(identityClone).Valid);

  ValidationResult validation = ValidateInstrumentedModule(pCorruptedContainer);
  VERIFY_IS_FALSE(validation.Valid);

  // The caller's container must be untouched by either call above.
  VERIFY_ARE_EQUAL(originalContainerBytes.size(),
                   static_cast<size_t>(pCorruptedContainer->GetBufferSize()));
  VERIFY_IS_TRUE(memcmp(originalContainerBytes.data(),
                        pCorruptedContainer->GetBufferPointer(),
                        originalContainerBytes.size()) == 0);

  // Confirm the corruption produces a real diagnostic, not just the known
  // PIX metadata kinds.
  std::vector<std::string> diagnostics =
      GetSignificantValidationDiagnostics(validation.Errors);
  VERIFY_IS_FALSE(diagnostics.empty());
}

// Control test for item 1.1: the validation harness must reject unused
// metadata that is not one of the four known PIX virtual-register kinds,
// even though the validator's own diagnostic text cannot name the kind (it
// prints only the metadata node's own operands). ValidateInstrumentedModule
// tells the two apart structurally, by revalidating a copy with only the
// known PIX kinds removed.
TEST_F(PixTest, Validation_ControlNonPixUnusedMetadataIsRejected) {
  const char *source = R"x(
float main() : SV_Target
{
    return 0;
})x";

  CComPtr<IDxcBlob> compiled =
      Compile(m_dllSupport, source, L"ps_6_0", {L"-Od"});
  SinglePassOutput output =
      RunSinglePass(compiled, L"-dxil-annotate-with-virtual-regs");

  // Confirm the baseline (only known PIX metadata unused) validates.
  VerifyInstrumentedModuleIsValid(
      output.Module,
      "virtual-register annotation of a trivial pixel shader, uncorrupted "
      "baseline (non-PIX metadata control)");

  // Snapshot the caller's original blob so we can confirm below that
  // CloneModuleAndMutate never mutates it in place.
  std::vector<uint8_t> originalBytes(
      static_cast<const uint8_t *>(output.Module->GetBufferPointer()),
      static_cast<const uint8_t *>(output.Module->GetBufferPointer()) +
          output.Module->GetBufferSize());

  // Attach an unused metadata kind that is not one of the four known PIX
  // kinds. The validator's generic "all metadata must be used" diagnostic
  // cannot distinguish it from a real PIX kind by text, so this must be
  // rejected only because ValidateInstrumentedModule excuses solely the
  // four known kinds.
  CComPtr<IDxcBlob> withForeignMetadata =
      CloneModuleAndMutate(output.Module, [](llvm::Module &M) {
        llvm::Function *entry = nullptr;
        for (llvm::Function &F : M) {
          if (!F.isDeclaration()) {
            entry = &F;
            break;
          }
        }
        VERIFY_IS_NOT_NULL(entry);
        llvm::Instruction *firstInst =
            &*entry->getEntryBlock().getFirstInsertionPt();
        llvm::MDNode *marker = llvm::MDNode::get(
            M.getContext(),
            llvm::MDString::get(M.getContext(), "not-a-known-pix-kind"));
        firstInst->setMetadata(
            M.getContext().getMDKindID("pixtest-non-pix-marker"), marker);
      });

  // The caller's blob (output.Module) must be untouched by the clone.
  VERIFY_ARE_EQUAL(originalBytes.size(),
                   static_cast<size_t>(output.Module->GetBufferSize()));
  VERIFY_IS_TRUE(memcmp(originalBytes.data(), output.Module->GetBufferPointer(),
                        originalBytes.size()) == 0);

  // Go through the same disposition helper VerifyInstrumentedModuleIsValid
  // uses, not just ValidateInstrumentedModule's raw result: the raw
  // validator fails identically for known and unknown metadata kinds, so
  // asserting on it alone would pass even if a blanket text-based
  // "all metadata must be used" exception were still in force downstream.
  // This must fail specifically because the foreign kind is not permitted
  // after PIX-specific handling.
  InstrumentedModuleDisposition disposition =
      GetInstrumentedModuleDisposition(withForeignMetadata);
  VERIFY_IS_FALSE(disposition.Valid);
  VERIFY_IS_FALSE(disposition.Diagnostics.empty());
}

// Tests that GetSignificantValidationDiagnostics only filters the
// "Validation failed." boilerplate and blank lines; every other line,
// including an "all metadata must be used" line, is significant. The
// known-PIX-kind exception happens structurally in
// ValidateInstrumentedModule, not here.
TEST_F(PixTest, Validation_ControlBoilerplateOnlyFailureIsRejected) {
  // Boilerplate only: no significant diagnostic.
  std::vector<std::string> boilerplateOnly =
      GetSignificantValidationDiagnostics("Validation failed.\n");
  VERIFY_IS_TRUE(boilerplateOnly.empty());

  // A metadata diagnostic alone is significant at this layer: the
  // known-PIX-kind exception is no longer decided by text. Assert the
  // exact retained line, not just non-emptiness, so a regression that
  // re-filters this specific line is caught. This is the validator's
  // actual Meta.Used rule text (see hctdb.py's "Meta.Used" rule).
  const std::string metadataLine = "All metadata must be used by dxil.";
  std::vector<std::string> metadataDiagnosticOnly =
      GetSignificantValidationDiagnostics("Validation failed.\n" +
                                          metadataLine + "\n");
  VERIFY_ARE_EQUAL(size_t(1), metadataDiagnosticOnly.size());
  VERIFY_IS_TRUE(metadataLine == metadataDiagnosticOnly[0]);

  // A real diagnostic alongside the metadata diagnostic: assert both exact
  // lines survive, in order. A blanket text-based exception would drop the
  // metadata line and leave only the real one (size 1, not 2); checking
  // only non-emptiness would not catch that regression.
  const std::string realLine = "Some real validator diagnostic.";
  std::vector<std::string> realDiagnostic = GetSignificantValidationDiagnostics(
      "Validation failed.\n" + metadataLine + "\n" + realLine + "\n");
  VERIFY_ARE_EQUAL(size_t(2), realDiagnostic.size());
  VERIFY_IS_TRUE(metadataLine == realDiagnostic[0]);
  VERIFY_IS_TRUE(realLine == realDiagnostic[1]);
}

// Directly tests DiagnosticsArePreserved with synthetic duplicate and
// missing cases, without depending on real assembler/validator behavior
// to reproduce a genuine reassembly-masks-a-defect scenario (impractical
// to fabricate safely). This is the multiset-containment check
// ValidateInstrumentedModule uses to prove the identity clone did not
// silently drop or alter an original diagnostic before trusting the
// stripped clone's result.
TEST_F(PixTest, Validation_ControlDiagnosticsArePreservedHelper) {
  // Exact match: preserved.
  VERIFY_IS_TRUE(DiagnosticsArePreserved({"A", "B"}, {"A", "B"}));

  // Available is a superset: still preserved.
  VERIFY_IS_TRUE(DiagnosticsArePreserved({"A", "B"}, {"A", "B", "C"}));

  // A required diagnostic is missing entirely: not preserved.
  VERIFY_IS_FALSE(DiagnosticsArePreserved({"A", "B"}, {"A"}));

  // Duplicate required diagnostic, but only one copy available: multiset
  // containment must fail, not just "is A present at all".
  VERIFY_IS_FALSE(DiagnosticsArePreserved({"A", "A"}, {"A"}));

  // Duplicate required diagnostic with matching duplicate available: this
  // is the case a naive set-based (non-multiset) check would wrongly
  // treat the same as the single-copy case above.
  VERIFY_IS_TRUE(DiagnosticsArePreserved({"A", "A"}, {"A", "A"}));

  // Order must not matter.
  VERIFY_IS_TRUE(DiagnosticsArePreserved({"B", "A"}, {"A", "B"}));

  // Nothing required: trivially preserved, even against an empty pool. This
  // vacuous-truth case is exactly why ValidateInstrumentedModule must check
  // directDiagnostics.empty() and fail closed *before* ever calling this
  // helper with an empty `required` list: an original failure with no
  // significant diagnostic would otherwise let this "succeed" regardless
  // of what the identity clone reports.
  VERIFY_IS_TRUE(DiagnosticsArePreserved({}, {}));
  VERIFY_IS_TRUE(DiagnosticsArePreserved({}, {"A"}));

  // Something required against an empty pool: not preserved.
  VERIFY_IS_FALSE(DiagnosticsArePreserved({"A"}, {}));
}

// Control test for item 1's canonical-part fix: the metadata-strip fallback
// must parse/clone/strip the same canonical DFCC_DXIL part RunValidator's
// "direct" validation targets, not the debug-info-carrying
// DFCC_ShaderDebugInfoDXIL part. A container whose canonical part has a
// genuine, non-PIX defect and whose debug-info part has only known PIX
// metadata must still be rejected: stripping known PIX metadata from the
// wrong (debug-info) part can never repair the canonical part's real
// defect. The validator's "All metadata must be used by dxil." diagnostic
// is identical regardless of the unused metadata's kind or content (see
// Validation_ControlBoilerplateOnlyFailureIsRejected), so both parts
// naturally produce colliding diagnostic text -- proving text alone cannot
// be relied on to detect this divergence, only parsing the correct part
// can.
TEST_F(PixTest, Validation_ControlCanonicalPartMetadataDivergenceIsRejected) {
  const char *source = R"x(
float main() : SV_Target
{
    return 0;
})x";

  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"ps_6_0", {});
  VerifyInstrumentedModuleIsValid(
      compiled, "uncorrupted baseline (canonical-part divergence control)");

  // Snapshot the caller's original container so we can confirm below that
  // none of the construction or validation below mutates it in place.
  std::vector<uint8_t> originalBytes(
      static_cast<const uint8_t *>(compiled->GetBufferPointer()),
      static_cast<const uint8_t *>(compiled->GetBufferPointer()) +
          compiled->GetBufferSize());

  auto attachForeignMetadata = [](llvm::Module &M) {
    llvm::Function *entry = nullptr;
    for (llvm::Function &F : M) {
      if (!F.isDeclaration()) {
        entry = &F;
        break;
      }
    }
    VERIFY_IS_NOT_NULL(entry);
    llvm::Instruction *firstInst =
        &*entry->getEntryBlock().getFirstInsertionPt();
    llvm::MDNode *marker = llvm::MDNode::get(
        M.getContext(),
        llvm::MDString::get(M.getContext(), "canonical-divergence-marker"));
    firstInst->setMetadata(
        M.getContext().getMDKindID("pixtest-canonical-divergence-marker"),
        marker);
  };
  auto attachKnownPixMetadata = [](llvm::Module &M) {
    llvm::Function *entry = nullptr;
    for (llvm::Function &F : M) {
      if (!F.isDeclaration()) {
        entry = &F;
        break;
      }
    }
    VERIFY_IS_NOT_NULL(entry);
    llvm::Instruction *firstInst =
        &*entry->getEntryBlock().getFirstInsertionPt();
    // Same MDNode shape as the foreign marker above; only the metadata kind
    // name differs (one of the four known PIX kinds here, an arbitrary
    // foreign name above). The validator's diagnostic text depends on
    // neither, so both variants collide on the same generic message.
    llvm::MDNode *marker = llvm::MDNode::get(
        M.getContext(),
        llvm::MDString::get(M.getContext(), "canonical-divergence-marker"));
    firstInst->setMetadata(llvm::StringRef(pix_dxil::PixDxilInstNum::MDName),
                           marker);
  };

  // Build two independently-mutated containers from the same clean
  // baseline: one with only a foreign (non-PIX) unused metadata kind, one
  // with only a known PIX kind, sharing identical MDNode content so their
  // "All metadata must be used by dxil." diagnostics collide exactly.
  // Deliberately parse the default (debug-info-carrying) part here, not
  // DFCC_DXIL: retaining debug info is what makes WrapInNewContainer's
  // re-serialization produce *both* a DFCC_DXIL and a DFCC_ShaderDebugInfoDXIL
  // part below (see SerializeDxilContainerForModule), which this test needs
  // in order to combine them into a deliberately divergent pair. This is
  // orthogonal to the production fix, which is about which part
  // ValidateInstrumentedModule's own internal clones read, not about how
  // this test constructs its fixtures.
  CComPtr<IDxcBlob> withForeignMetadata =
      CloneModuleAndMutate(compiled, attachForeignMetadata);
  CComPtr<IDxcBlob> withKnownPixMetadata =
      CloneModuleAndMutate(compiled, attachKnownPixMetadata);

  VERIFY_IS_FALSE(RunValidator(withForeignMetadata).Valid);
  VERIFY_IS_FALSE(RunValidator(withKnownPixMetadata).Valid);

  CComPtr<IDxcBlob> knownPixDxilPart =
      ExtractPartContent(DFCC_DXIL, withKnownPixMetadata);

  // The divergent container: canonical DFCC_DXIL carries the foreign,
  // non-excusable defect (withForeignMetadata's own, untouched); its
  // DFCC_ShaderDebugInfoDXIL part is replaced with the known-PIX-only
  // content that stripping can repair. Only the canonical part's defect is
  // real; ValidateInstrumentedModule must reject based on it.
  CComPtr<IDxcBlob> divergentContainer = BuildContainerWithDivergentIldbPart(
      withForeignMetadata, knownPixDxilPart);

  // The identity-clone gate itself must now see the same defect direct
  // validation does, since both derive from the same canonical part.
  CComPtr<IDxcBlob> identityClone = CloneModuleAndMutate(
      divergentContainer, [](llvm::Module &) {}, DFCC_DXIL);
  VERIFY_IS_FALSE(RunValidator(identityClone).Valid);

  ValidationResult validation = ValidateInstrumentedModule(divergentContainer);
  VERIFY_IS_FALSE(validation.Valid);
  std::vector<std::string> diagnostics =
      GetSignificantValidationDiagnostics(validation.Errors);
  VERIFY_IS_FALSE(diagnostics.empty());

  // The caller's original container must be untouched throughout.
  VERIFY_ARE_EQUAL(originalBytes.size(),
                   static_cast<size_t>(compiled->GetBufferSize()));
  VERIFY_IS_TRUE(memcmp(originalBytes.data(), compiled->GetBufferPointer(),
                        originalBytes.size()) == 0);
}

// Positive control paired with the divergence test above: when both the
// canonical part and the debug-info part agree (the normal case, since
// WrapInNewContainer re-derives both from the same mutated bitcode), a
// module with only known PIX metadata still validates after the fix.
TEST_F(PixTest, Validation_ControlCanonicalKnownPixMetadataIsAccepted) {
  const char *source = R"x(
float main() : SV_Target
{
    return 0;
})x";

  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"ps_6_0", {});
  CComPtr<IDxcBlob> withKnownPixMetadata = CloneModuleAndMutate(
      compiled,
      [](llvm::Module &M) {
        llvm::Function *entry = nullptr;
        for (llvm::Function &F : M) {
          if (!F.isDeclaration()) {
            entry = &F;
            break;
          }
        }
        VERIFY_IS_NOT_NULL(entry);
        llvm::Instruction *firstInst =
            &*entry->getEntryBlock().getFirstInsertionPt();
        pix_dxil::PixDxilInstNum::AddMD(M.getContext(), firstInst, 0);
      },
      DFCC_DXIL);

  VerifyInstrumentedModuleIsValid(
      withKnownPixMetadata,
      "canonical part with only known PIX metadata (should be excused)");
}

// A canonical part carrying both a foreign kind and a known PIX kind
// together must still be rejected: stripping only the known kinds cannot
// repair the foreign one. Proves the fix does not over-excuse merely
// because *some* of the unused metadata happens to be a known PIX kind.
TEST_F(PixTest, Validation_ControlCanonicalMixedForeignMetadataIsRejected) {
  const char *source = R"x(
float main() : SV_Target
{
    return 0;
})x";

  CComPtr<IDxcBlob> compiled = Compile(m_dllSupport, source, L"ps_6_0", {});
  CComPtr<IDxcBlob> withMixedMetadata = CloneModuleAndMutate(
      compiled,
      [](llvm::Module &M) {
        llvm::Function *entry = nullptr;
        for (llvm::Function &F : M) {
          if (!F.isDeclaration()) {
            entry = &F;
            break;
          }
        }
        VERIFY_IS_NOT_NULL(entry);
        llvm::Instruction *firstInst =
            &*entry->getEntryBlock().getFirstInsertionPt();
        pix_dxil::PixDxilInstNum::AddMD(M.getContext(), firstInst, 0);
        llvm::MDNode *marker = llvm::MDNode::get(
            M.getContext(),
            llvm::MDString::get(M.getContext(), "mixed-marker"));
        firstInst->setMetadata(
            M.getContext().getMDKindID("pixtest-mixed-foreign-marker"), marker);
      },
      DFCC_DXIL);

  InstrumentedModuleDisposition disposition =
      GetInstrumentedModuleDisposition(withMixedMetadata);
  VERIFY_IS_FALSE(disposition.Valid);
  VERIFY_IS_FALSE(disposition.Diagnostics.empty());
}

TEST_F(PixTest, Validation_NonUniformResourceIndex_WaveOpsFlag) {
  const char *source = R"x(
Texture2D textures[]  : register(t0);
SamplerState samp     : register(s0);

cbuffer Constants : register(b0)
{
    uint index;
};

float4 main(float4 pos : SV_Position) : SV_Target
{
    return textures[index].Sample(samp, pos.xy);
})x";

  // This index is dynamic and unmarked, so the pass instruments it; an
  // index already marked NonUniformResourceIndex would be skipped.
  // Instrumentation inserts WaveActiveAllEqual, which requires the WaveOps
  // shader flag.
  CComPtr<IDxcBlob> compiled =
      Compile(m_dllSupport, source, L"ps_6_6", {L"-Od"});
  CComPtr<IDxcBlob> dxil = FindModule(DFCC_ShaderDebugInfoDXIL, compiled);

  CComPtr<IDxcOptimizer> pOptimizer;
  VERIFY_SUCCEEDED(
      m_dllSupport.CreateInstance(CLSID_DxcOptimizer, &pOptimizer));
  std::array<LPCWSTR, 4> Options = {
      L"-opt-mod-passes", L"-dxil-dbg-value-to-dbg-declare",
      L"-dxil-annotate-with-virtual-regs",
      L"-hlsl-dxil-non-uniform-resource-index-instrumentation"};

  CComPtr<IDxcBlob> pOptimizedModule;
  CComPtr<IDxcBlobEncoding> pText;
  VERIFY_SUCCEEDED(pOptimizer->RunOptimizer(
      dxil, Options.data(), Options.size(), &pOptimizedModule, &pText));

  VerifyInstrumentedModuleIsValid(pOptimizedModule,
                                  "non-uniform resource index instrumentation");

  VERIFY_ARE_NOT_EQUAL(
      std::string::npos,
      Disassemble(pOptimizedModule).find("dx.op.waveActiveAllEqual"));
}
