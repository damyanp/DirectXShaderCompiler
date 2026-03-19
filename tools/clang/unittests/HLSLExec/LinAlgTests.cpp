///////////////////////////////////////////////////////////////////////////////
//                                                                           //
// LinAlgTests.cpp                                                           //
// Copyright (C) Microsoft Corporation. All rights reserved.                 //
// This file is distributed under the University of Illinois Open Source     //
// License. See LICENSE.TXT for details.                                     //
//                                                                           //
// Execution tests for dx::linalg builtins (Proposal 0035, SM 6.10).        //
//                                                                           //
// Unlike older execution tests, these tests define shader source and        //
// resources entirely in C++ — no ShaderOpArith.xml entries required.        //
// ShaderOp objects are constructed programmatically and passed to the       //
// existing RunShaderOpTestAfterParse infrastructure.                        //
//                                                                           //
// Each test always compiles its shader via the DXC API to validate the      //
// HLSL, then skips GPU dispatch if no SM 6.10 device is available.          //
//                                                                           //
///////////////////////////////////////////////////////////////////////////////

// We need to keep & fix these warnings to integrate smoothly with HLK
#pragma warning(error : 4100 4242 4244 4267 4701 4389 4018)

#ifndef NOMINMAX
#define NOMINMAX 1
#endif

#define INLINE_TEST_METHOD_MARKUP
#include <WexTestClass.h>

#include "ShaderOpTest.h"
#include "dxc/Support/Global.h"
#include "dxc/Support/dxcapi.use.h"

#include "HlslTestUtils.h"

#include "HlslExecTestUtils.h"

#include <optional>
#include <sstream>
#include <string>
#include <vector>

namespace LinAlg {

// ===========================================================================
// DXIL component type constants
// ===========================================================================
enum ComponentType {
  CT_I16 = 2,
  CT_U16 = 3,
  CT_I32 = 4,
  CT_U32 = 5,
  CT_I64 = 6,
  CT_U64 = 7,
  CT_F16 = 8,
  CT_F32 = 9,
  CT_F64 = 10,
};

enum MatrixUse { MU_A = 0, MU_B = 1, MU_Accumulator = 2 };

enum MatrixScope { MS_Thread = 0, MS_Wave = 1, MS_ThreadGroup = 2 };

enum MatrixLayout {
  ML_RowMajor = 0,
  ML_ColMajor = 1,
  ML_MulOptimal = 2,
  ML_OuterProductOptimal = 3,
};

// ===========================================================================
// ShaderOp construction helpers
//
// These build st::ShaderOp objects programmatically so that tests are
// fully self-contained in this file — no XML required.
// ===========================================================================

// Create a ShaderOp for a compute shader dispatch.
static std::unique_ptr<st::ShaderOp>
createComputeOp(const char *Source, const char *Target, const char *RootSig,
                const char *Args = nullptr, UINT DispatchX = 1,
                UINT DispatchY = 1, UINT DispatchZ = 1) {
  auto Op = std::make_unique<st::ShaderOp>();
  LPCSTR CSName = Op->Strings.insert("CS");
  Op->Name = CSName;
  Op->CS = CSName;
  Op->RootSignature = Op->Strings.insert(RootSig);
  Op->DispatchX = DispatchX;
  Op->DispatchY = DispatchY;
  Op->DispatchZ = DispatchZ;
  Op->UseWarpDevice = true;

  st::ShaderOpShader Shader = {};
  Shader.Name = CSName;
  Shader.Target = Op->Strings.insert(Target);
  Shader.EntryPoint = Op->Strings.insert("main");
  Shader.Text = Op->Strings.insert(Source);
  Shader.Arguments = Args ? Op->Strings.insert(Args) : nullptr;
  Shader.Compiled = FALSE;
  Shader.Callback = FALSE;
  Op->Shaders.push_back(Shader);

  return Op;
}

// Add a UAV buffer resource to a ShaderOp.
static void addUAVBuffer(st::ShaderOp *Op, const char *Name, UINT64 Width,
                         bool ReadBack, const char *Init = "zero") {
  st::ShaderOpResource Res = {};
  Res.Name = Op->Strings.insert(Name);
  Res.Init = Op->Strings.insert(Init);
  Res.ReadBack = ReadBack ? TRUE : FALSE;

  Res.HeapProperties.Type = D3D12_HEAP_TYPE_DEFAULT;
  Res.HeapFlags = D3D12_HEAP_FLAG_NONE;
  Res.Desc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER;
  Res.Desc.Width = Width;
  Res.Desc.Height = 1;
  Res.Desc.DepthOrArraySize = 1;
  Res.Desc.MipLevels = 1;
  Res.Desc.SampleDesc.Count = 1;
  Res.Desc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
  Res.Desc.Flags = D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS;
  Res.InitialResourceState = D3D12_RESOURCE_STATE_COPY_DEST;
  Res.TransitionTo = D3D12_RESOURCE_STATE_UNORDERED_ACCESS;

  Op->Resources.push_back(Res);
}

// Bind a resource to a root UAV parameter by index.
static void addRootUAV(st::ShaderOp *Op, UINT Index, const char *ResName) {
  st::ShaderOpRootValue RV = {};
  RV.ResName = Op->Strings.insert(ResName);
  RV.HeapName = nullptr;
  RV.Index = Index;
  Op->RootValues.push_back(RV);
}

// Run a programmatically-built ShaderOp and return the result.
static std::shared_ptr<st::ShaderOpTestResult>
runShaderOp(ID3D12Device *Device, dxc::SpecificDllLoader &DxcSupport,
            std::unique_ptr<st::ShaderOp> Op,
            st::ShaderOpTest::TInitCallbackFn InitCallback = nullptr) {
  auto OpSet = std::make_shared<st::ShaderOpSet>();
  OpSet->ShaderOps.push_back(std::move(Op));

  return st::RunShaderOpTestAfterParse(Device, DxcSupport, nullptr,
                                       std::move(InitCallback),
                                       std::move(OpSet));
}

// ===========================================================================
// Shader compilation helper
//
// Compiles an HLSL shader using the DXC API to verify it is well-formed.
// This runs without a D3D12 device, so it works even when no SM 6.10
// hardware is available. Fails the test (via VERIFY) on compile error.
// ===========================================================================

static void compileShader(dxc::SpecificDllLoader &DxcSupport,
                          const char *Source, const char *Target,
                          const std::string &Args) {
  CComPtr<IDxcCompiler3> Compiler;
  VERIFY_SUCCEEDED(DxcSupport.CreateInstance(CLSID_DxcCompiler, &Compiler));

  CComPtr<IDxcUtils> Utils;
  VERIFY_SUCCEEDED(DxcSupport.CreateInstance(CLSID_DxcUtils, &Utils));

  CComPtr<IDxcBlobEncoding> SourceBlob;
  VERIFY_SUCCEEDED(Utils->CreateBlobFromPinned(
      Source, static_cast<UINT32>(strlen(Source)), DXC_CP_UTF8, &SourceBlob));

  // Build wide-string argument list: -T <target> -E main <extra args>.
  std::vector<std::wstring> WArgStorage;
  WArgStorage.push_back(L"-T");
  WArgStorage.push_back(std::wstring(Target, Target + strlen(Target)));
  WArgStorage.push_back(L"-E");
  WArgStorage.push_back(L"main");

  // Tokenize the additional arguments string.
  std::istringstream SS(Args);
  std::string Tok;
  while (SS >> Tok)
    WArgStorage.push_back(std::wstring(Tok.begin(), Tok.end()));

  std::vector<LPCWSTR> WArgPtrs;
  for (const auto &A : WArgStorage)
    WArgPtrs.push_back(A.c_str());

  DxcBuffer Buf = {};
  Buf.Ptr = SourceBlob->GetBufferPointer();
  Buf.Size = SourceBlob->GetBufferSize();
  Buf.Encoding = DXC_CP_UTF8;

  CComPtr<IDxcResult> Result;
  VERIFY_SUCCEEDED(Compiler->Compile(&Buf, WArgPtrs.data(),
                                     static_cast<UINT32>(WArgPtrs.size()),
                                     nullptr, IID_PPV_ARGS(&Result)));

  HRESULT HR;
  VERIFY_SUCCEEDED(Result->GetStatus(&HR));

  if (FAILED(HR)) {
    CComPtr<IDxcBlobUtf8> Errors;
    Result->GetOutput(DXC_OUT_ERRORS, IID_PPV_ARGS(&Errors), nullptr);
    if (Errors && Errors->GetStringLength() > 0)
      hlsl_test::LogErrorFmt(L"Shader compilation failed:\n%S",
                             Errors->GetStringPointer());
    VERIFY_SUCCEEDED(HR);
  }
}

// ===========================================================================
// Compiler arguments builder
// ===========================================================================

static std::string
buildCompilerArgs(int CompType, int M, int N, int Use, int Scope, int Stride,
                  int Layout, int NumThreads, bool Enable16Bit = false,
                  const char *ExtraDefines = nullptr) {
  std::stringstream SS;
  SS << "-HV 202x";
  SS << " -DCOMP_TYPE=" << CompType;
  SS << " -DM_DIM=" << M;
  SS << " -DN_DIM=" << N;
  SS << " -DUSE=" << Use;
  SS << " -DSCOPE=" << Scope;
  SS << " -DSTRIDE=" << Stride;
  SS << " -DLAYOUT=" << Layout;
  SS << " -DNUMTHREADS=" << NumThreads;
  if (Enable16Bit)
    SS << " -enable-16bit-types";
  if (ExtraDefines)
    SS << " " << ExtraDefines;
  return SS.str();
}

// ===========================================================================
// Verification helpers
// ===========================================================================

static bool verifyFloatBuffer(const void *Actual, const float *Expected,
                              size_t Count, bool Verbose,
                              float Tolerance = 0.0f) {
  const float *ActualFloats = static_cast<const float *>(Actual);
  bool Success = true;
  for (size_t I = 0; I < Count; I++) {
    float Diff = ActualFloats[I] - Expected[I];
    if (Diff < 0)
      Diff = -Diff;
    if (Diff > Tolerance) {
      hlsl_test::LogErrorFmt(L"Mismatch at index %zu: actual=%f, expected=%f",
                             I, static_cast<double>(ActualFloats[I]),
                             static_cast<double>(Expected[I]));
      Success = false;
    } else if (Verbose) {
      hlsl_test::LogCommentFmt(L"  [%zu] actual=%f, expected=%f (OK)", I,
                               static_cast<double>(ActualFloats[I]),
                               static_cast<double>(Expected[I]));
    }
  }
  return Success;
}

static bool verifyIntBuffer(const void *Actual, const int32_t *Expected,
                            size_t Count, bool Verbose) {
  const int32_t *ActualInts = static_cast<const int32_t *>(Actual);
  bool Success = true;
  for (size_t I = 0; I < Count; I++) {
    if (ActualInts[I] != Expected[I]) {
      hlsl_test::LogErrorFmt(L"Mismatch at index %zu: actual=%d, expected=%d",
                             I, ActualInts[I], Expected[I]);
      Success = false;
    } else if (Verbose) {
      hlsl_test::LogCommentFmt(L"  [%zu] actual=%d, expected=%d (OK)", I,
                               ActualInts[I], Expected[I]);
    }
  }
  return Success;
}

// ===========================================================================
// Test parameters
// ===========================================================================

struct MatrixParams {
  int CompType;
  int M;
  int N;
  int Use;
  int Scope;
  int Layout;
  int NumThreads;
  bool Enable16Bit;

  int strideBytes() const {
    int ElemSize = 4; // default F32/I32
    if (CompType == CT_F16 || CompType == CT_I16 || CompType == CT_U16)
      ElemSize = 2;
    else if (CompType == CT_F64 || CompType == CT_I64 || CompType == CT_U64)
      ElemSize = 8;
    if (Layout == ML_RowMajor)
      return N * ElemSize;
    else
      return M * ElemSize;
  }

  size_t totalElements() const { return static_cast<size_t>(M) * N; }

  size_t totalBytes() const {
    int ElemSize = 4;
    if (CompType == CT_F16 || CompType == CT_I16 || CompType == CT_U16)
      ElemSize = 2;
    else if (CompType == CT_F64 || CompType == CT_I64 || CompType == CT_U64)
      ElemSize = 8;
    return totalElements() * ElemSize;
  }
};

// ===========================================================================
// Test class
// ===========================================================================

class DxilConf_SM610_LinAlg {
public:
  BEGIN_TEST_CLASS(DxilConf_SM610_LinAlg)
  TEST_CLASS_PROPERTY(
      "Kits.TestName",
      "D3D12 - Shader Model 6.10 - LinAlg Matrix Operations")
  TEST_CLASS_PROPERTY("Kits.TestId",
                      "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
  TEST_CLASS_PROPERTY(
      "Kits.Description",
      "Validates SM 6.10 linear algebra matrix operations execute correctly")
  TEST_CLASS_PROPERTY(
      "Kits.Specification",
      "Device.Graphics.D3D12.DXILCore.ShaderModel610.CoreRequirement")
  TEST_METHOD_PROPERTY(L"Priority", L"0")
  END_TEST_CLASS()

  TEST_CLASS_SETUP(setupClass);
  TEST_METHOD_SETUP(setupMethod);

  TEST_METHOD(LoadStoreRoundtrip_Wave_F32);
  TEST_METHOD(LoadStoreRoundtrip_Wave_I32);
  TEST_METHOD(SplatStore_Wave_F32);
  TEST_METHOD(SplatStore_Wave_I32);

  // Element access
  TEST_METHOD(ElementAccess_Thread_F32);
  TEST_METHOD(ElementAccess_Thread_I32);
  TEST_METHOD(SetElement_Thread_F32);
  TEST_METHOD(SetElement_Thread_I32);

  // Cast
  TEST_METHOD(CopyConvert_Thread_F32);

  // Matrix arithmetic
  TEST_METHOD(MatMul_Wave_F32);
  TEST_METHOD(MatMulAccum_Wave_F32);
  TEST_METHOD(MatAccumulate_Wave_F32);

  // Thread vector ops
  TEST_METHOD(MatVecMul_Thread_F32);
  TEST_METHOD(MatVecMulAdd_Thread_F32);
  TEST_METHOD(OuterProduct_Thread_F32);

  // Groupshared
  TEST_METHOD(GroupsharedLoadStore_F32);
  TEST_METHOD(GroupsharedAccum_F32);

  // Descriptor accumulate + query
  TEST_METHOD(AccumToDescriptor_Wave_F32);
  TEST_METHOD(QueryAccumLayout);

private:
  CComPtr<ID3D12Device> D3DDevice;
  dxc::SpecificDllLoader DxcSupport;
  bool VerboseLogging = false;
  bool Initialized = false;
  std::optional<D3D12SDKSelector> D3D12SDK;
};

// ===========================================================================
// Class setup
// ===========================================================================

bool DxilConf_SM610_LinAlg::setupClass() {
  WEX::TestExecution::SetVerifyOutput VerifySettings(
      WEX::TestExecution::VerifyOutputSettings::LogOnlyFailures);

  if (!Initialized) {
    Initialized = true;

    // Always initialize DXC compiler — needed for shader compilation checks.
    VERIFY_SUCCEEDED(
        DxcSupport.InitializeForDll(dxc::kDxCompilerLib, "DxcCreateInstance"));

    D3D12SDK = D3D12SDKSelector();

    WEX::TestExecution::RuntimeParameters::TryGetValue(L"VerboseLogging",
                                                       VerboseLogging);

    bool FailIfRequirementsNotMet = false;
#ifdef _HLK_CONF
    FailIfRequirementsNotMet = true;
#endif
    WEX::TestExecution::RuntimeParameters::TryGetValue(
        L"FailIfRequirementsNotMet", FailIfRequirementsNotMet);

    // Try to create a device. In HLK mode, fail if unavailable.
    // In dev mode, D3DDevice stays null and tests will compile shaders
    // then skip GPU execution.
    if (!D3D12SDK->createDevice(&D3DDevice, D3D_SHADER_MODEL_6_10,
                                /*SkipUnsupported=*/false)) {
      if (FailIfRequirementsNotMet) {
        hlsl_test::LogErrorFmt(
            L"Device creation failed for SM 6.10, and "
            L"FailIfRequirementsNotMet is set.");
        return false;
      }
      // No device — tests will compile shaders and skip execution.
    }
  }

  return true;
}

bool DxilConf_SM610_LinAlg::setupMethod() {
  // Re-create device if it was lost. If we never had one, that's fine —
  // tests compile shaders and skip GPU execution.
  if (D3DDevice && D3DDevice->GetDeviceRemovedReason() != S_OK) {
    hlsl_test::LogCommentFmt(L"Device was lost!");
    D3DDevice.Release();
    D3D12SDK->createDevice(&D3DDevice, D3D_SHADER_MODEL_6_10,
                           /*SkipUnsupported=*/false);
  }
  return true;
}

// ===========================================================================
// Load/Store roundtrip
// ===========================================================================

static const char LoadStoreShader[] = R"(
  RWByteAddressBuffer Input : register(u0);
  RWByteAddressBuffer Output : register(u1);

  [numthreads(NUMTHREADS, 1, 1)]
  void main() {
    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, M_DIM, N_DIM, USE, SCOPE)]]
      Mat;
    __builtin_LinAlg_MatrixLoadFromDescriptor(
      Mat, Input, 0, STRIDE, LAYOUT);
    __builtin_LinAlg_MatrixStoreToDescriptor(
      Mat, Output, 0, STRIDE, LAYOUT);
  }
)";

static void runLoadStoreRoundtrip(ID3D12Device *Device,
                                  dxc::SpecificDllLoader &DxcSupport,
                                  const MatrixParams &Params, bool Verbose) {
  const size_t NumElements = Params.totalElements();
  const size_t BufferSize = Params.totalBytes();
  const int Stride = Params.strideBytes();

  std::string Args =
      buildCompilerArgs(Params.CompType, Params.M, Params.N, Params.Use,
                        Params.Scope, Stride, Params.Layout,
                        Params.NumThreads, Params.Enable16Bit);

  // Always verify the shader compiles.
  compileShader(DxcSupport, LoadStoreShader, "cs_6_10", Args);

  // Skip GPU execution if no device.
  if (!Device) {
    hlsl_test::LogCommentFmt(
        L"Shader compiled OK; skipping execution (no SM 6.10 device)");
    WEX::Logging::Log::Result(WEX::Logging::TestResults::Skipped);
    return;
  }

  // Build expected data.
  std::vector<float> ExpectedFloats(NumElements);
  std::vector<int32_t> ExpectedInts(NumElements);
  for (size_t I = 0; I < NumElements; I++) {
    ExpectedFloats[I] = static_cast<float>(I + 1);
    ExpectedInts[I] = static_cast<int32_t>(I + 1);
  }

  // Construct the ShaderOp: two UAV buffers, load from one, store to other.
  auto Op = createComputeOp(LoadStoreShader, "cs_6_10", "UAV(u0), UAV(u1)",
                            Args.c_str());
  addUAVBuffer(Op.get(), "Input", BufferSize, false, "byname");
  addUAVBuffer(Op.get(), "Output", BufferSize, true);
  addRootUAV(Op.get(), 0, "Input");
  addRootUAV(Op.get(), 1, "Output");

  auto Result = runShaderOp(
      Device, DxcSupport, std::move(Op),
      [&](LPCSTR Name, std::vector<BYTE> &Data, st::ShaderOp * /*pOp*/) {
        if (_stricmp(Name, "Input") != 0)
          return;
        if (Params.CompType == CT_F32) {
          float *Ptr = reinterpret_cast<float *>(Data.data());
          for (size_t I = 0; I < NumElements; I++)
            Ptr[I] = static_cast<float>(I + 1);
        } else if (Params.CompType == CT_I32) {
          int32_t *Ptr = reinterpret_cast<int32_t *>(Data.data());
          for (size_t I = 0; I < NumElements; I++)
            Ptr[I] = static_cast<int32_t>(I + 1);
        }
      });

  MappedData OutData;
  Result->Test->GetReadBackData("Output", &OutData);

  if (Params.CompType == CT_F32) {
    VERIFY_IS_TRUE(verifyFloatBuffer(OutData.data(), ExpectedFloats.data(),
                                     NumElements, Verbose));
  } else if (Params.CompType == CT_I32) {
    VERIFY_IS_TRUE(verifyIntBuffer(OutData.data(), ExpectedInts.data(),
                                   NumElements, Verbose));
  }
}

void DxilConf_SM610_LinAlg::LoadStoreRoundtrip_Wave_F32() {
  MatrixParams Params = {};
  Params.CompType = CT_F32;
  Params.M = 8;
  Params.N = 8;
  Params.Use = MU_A;
  Params.Scope = MS_Wave;
  Params.Layout = ML_RowMajor;
  Params.NumThreads = 64;
  Params.Enable16Bit = false;
  runLoadStoreRoundtrip(D3DDevice, DxcSupport, Params, VerboseLogging);
}

void DxilConf_SM610_LinAlg::LoadStoreRoundtrip_Wave_I32() {
  MatrixParams Params = {};
  Params.CompType = CT_I32;
  Params.M = 8;
  Params.N = 8;
  Params.Use = MU_A;
  Params.Scope = MS_Wave;
  Params.Layout = ML_RowMajor;
  Params.NumThreads = 64;
  Params.Enable16Bit = false;
  runLoadStoreRoundtrip(D3DDevice, DxcSupport, Params, VerboseLogging);
}

// ===========================================================================
// Splat + Store
// ===========================================================================

static const char SplatStoreShader[] = R"(
  RWByteAddressBuffer Output : register(u0);

  [numthreads(NUMTHREADS, 1, 1)]
  void main() {
    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, M_DIM, N_DIM, USE, SCOPE)]]
      Mat;
    __builtin_LinAlg_FillMatrix(Mat, FILL_VALUE);
    __builtin_LinAlg_MatrixStoreToDescriptor(
      Mat, Output, 0, STRIDE, LAYOUT);
  }
)";

static void runSplatStore(ID3D12Device *Device,
                          dxc::SpecificDllLoader &DxcSupport,
                          const MatrixParams &Params, float FillValue,
                          bool Verbose) {
  const size_t NumElements = Params.totalElements();
  const size_t BufferSize = Params.totalBytes();
  const int Stride = Params.strideBytes();

  std::stringstream ExtraDefs;
  ExtraDefs << "-DFILL_VALUE=" << FillValue;

  std::string Args = buildCompilerArgs(
      Params.CompType, Params.M, Params.N, Params.Use, Params.Scope, Stride,
      Params.Layout, Params.NumThreads, Params.Enable16Bit,
      ExtraDefs.str().c_str());

  // Always verify the shader compiles.
  compileShader(DxcSupport, SplatStoreShader, "cs_6_10", Args);

  // Skip GPU execution if no device.
  if (!Device) {
    hlsl_test::LogCommentFmt(
        L"Shader compiled OK; skipping execution (no SM 6.10 device)");
    WEX::Logging::Log::Result(WEX::Logging::TestResults::Skipped);
    return;
  }

  std::vector<float> ExpectedFloats(NumElements, FillValue);
  std::vector<int32_t> ExpectedInts(NumElements,
                                    static_cast<int32_t>(FillValue));

  auto Op =
      createComputeOp(SplatStoreShader, "cs_6_10", "UAV(u0)", Args.c_str());
  addUAVBuffer(Op.get(), "Output", BufferSize, true);
  addRootUAV(Op.get(), 0, "Output");

  auto Result = runShaderOp(Device, DxcSupport, std::move(Op));

  MappedData OutData;
  Result->Test->GetReadBackData("Output", &OutData);

  if (Params.CompType == CT_F32) {
    VERIFY_IS_TRUE(verifyFloatBuffer(OutData.data(), ExpectedFloats.data(),
                                     NumElements, Verbose));
  } else if (Params.CompType == CT_I32) {
    VERIFY_IS_TRUE(verifyIntBuffer(OutData.data(), ExpectedInts.data(),
                                   NumElements, Verbose));
  }
}

void DxilConf_SM610_LinAlg::SplatStore_Wave_F32() {
  MatrixParams Params = {};
  Params.CompType = CT_F32;
  Params.M = 8;
  Params.N = 8;
  Params.Use = MU_Accumulator;
  Params.Scope = MS_Wave;
  Params.Layout = ML_RowMajor;
  Params.NumThreads = 64;
  Params.Enable16Bit = false;
  runSplatStore(D3DDevice, DxcSupport, Params, 42.0f, VerboseLogging);
}

void DxilConf_SM610_LinAlg::SplatStore_Wave_I32() {
  MatrixParams Params = {};
  Params.CompType = CT_I32;
  Params.M = 8;
  Params.N = 8;
  Params.Use = MU_Accumulator;
  Params.Scope = MS_Wave;
  Params.Layout = ML_RowMajor;
  Params.NumThreads = 64;
  Params.Enable16Bit = false;
  runSplatStore(D3DDevice, DxcSupport, Params, 7.0f, VerboseLogging);
}

// ===========================================================================
// Element access: Length, GetCoordinate, GetElement
// ===========================================================================

static const char ElementAccessShader[] = R"(
  RWByteAddressBuffer Input : register(u0);
  RWByteAddressBuffer Output : register(u1);

  [numthreads(1, 1, 1)]
  void main() {
    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, M_DIM, N_DIM, USE, SCOPE)]]
      Mat;
    __builtin_LinAlg_MatrixLoadFromDescriptor(
      Mat, Input, 0, STRIDE, LAYOUT);

    // Length at offset 0.
    uint Len = __builtin_LinAlg_MatrixLength(Mat);
    Output.Store(0, Len);

    // Each element starting at offset 4.
    uint Ofs = 4;
#if COMP_TYPE == 9
    [unroll] for (uint I = 0; I < M_DIM * N_DIM; I++) {
      float Elem;
      __builtin_LinAlg_MatrixGetElement(Elem, Mat, I);
      Output.Store(Ofs, asuint(Elem));
      Ofs += 4;
    }
#else
    [unroll] for (uint I = 0; I < M_DIM * N_DIM; I++) {
      uint Elem;
      __builtin_LinAlg_MatrixGetElement(Elem, Mat, I);
      Output.Store(Ofs, Elem);
      Ofs += 4;
    }
#endif

    // GetCoordinate for index 0.
    uint2 Coord = __builtin_LinAlg_MatrixGetCoordinate(Mat, 0);
    Output.Store(Ofs, Coord.x);
    Output.Store(Ofs + 4, Coord.y);
  }
)";

static void runElementAccess(ID3D12Device *Device,
                             dxc::SpecificDllLoader &DxcSupport,
                             const MatrixParams &Params, bool Verbose) {
  const size_t NumElements = Params.totalElements();
  const size_t InputSize = Params.totalBytes();
  // Output: 4 (length) + NumElements*4 (elements) + 8 (coordinate).
  const size_t OutputSize = 4 + NumElements * 4 + 8;
  const int Stride = Params.strideBytes();

  std::string Args =
      buildCompilerArgs(Params.CompType, Params.M, Params.N, Params.Use,
                        Params.Scope, Stride, Params.Layout,
                        Params.NumThreads, Params.Enable16Bit);

  compileShader(DxcSupport, ElementAccessShader, "cs_6_10", Args);

  if (!Device) {
    hlsl_test::LogCommentFmt(
        L"Shader compiled OK; skipping execution (no SM 6.10 device)");
    WEX::Logging::Log::Result(WEX::Logging::TestResults::Skipped);
    return;
  }

  auto Op = createComputeOp(ElementAccessShader, "cs_6_10",
                            "UAV(u0), UAV(u1)", Args.c_str());
  addUAVBuffer(Op.get(), "Input", InputSize, false, "byname");
  addUAVBuffer(Op.get(), "Output", OutputSize, true);
  addRootUAV(Op.get(), 0, "Input");
  addRootUAV(Op.get(), 1, "Output");

  auto Result = runShaderOp(
      Device, DxcSupport, std::move(Op),
      [&](LPCSTR Name, std::vector<BYTE> &Data, st::ShaderOp *) {
        if (_stricmp(Name, "Input") != 0)
          return;
        if (Params.CompType == CT_F32) {
          float *Ptr = reinterpret_cast<float *>(Data.data());
          for (size_t I = 0; I < NumElements; I++)
            Ptr[I] = static_cast<float>(I + 1);
        } else if (Params.CompType == CT_I32) {
          int32_t *Ptr = reinterpret_cast<int32_t *>(Data.data());
          for (size_t I = 0; I < NumElements; I++)
            Ptr[I] = static_cast<int32_t>(I + 1);
        }
      });

  MappedData OutData;
  Result->Test->GetReadBackData("Output", &OutData);
  const uint32_t *Out = static_cast<const uint32_t *>(OutData.data());

  // Verify length equals M * N for Thread-scope matrix.
  VERIFY_ARE_EQUAL(Out[0], static_cast<uint32_t>(NumElements));

  // Verify element values match input data.
  for (size_t I = 0; I < NumElements; I++) {
    if (Params.CompType == CT_F32) {
      float Actual;
      memcpy(&Actual, &Out[1 + I], sizeof(float));
      VERIFY_ARE_EQUAL(Actual, static_cast<float>(I + 1));
    } else {
      VERIFY_ARE_EQUAL(static_cast<int32_t>(Out[1 + I]),
                       static_cast<int32_t>(I + 1));
    }
  }

  if (Verbose) {
    hlsl_test::LogCommentFmt(L"GetCoordinate(0) = (%u, %u)",
                             Out[1 + NumElements], Out[2 + NumElements]);
  }
}

void DxilConf_SM610_LinAlg::ElementAccess_Thread_F32() {
  MatrixParams Params = {};
  Params.CompType = CT_F32;
  Params.M = 4;
  Params.N = 4;
  Params.Use = MU_Accumulator;
  Params.Scope = MS_Thread;
  Params.Layout = ML_RowMajor;
  Params.NumThreads = 1;
  runElementAccess(D3DDevice, DxcSupport, Params, VerboseLogging);
}

void DxilConf_SM610_LinAlg::ElementAccess_Thread_I32() {
  MatrixParams Params = {};
  Params.CompType = CT_I32;
  Params.M = 4;
  Params.N = 4;
  Params.Use = MU_Accumulator;
  Params.Scope = MS_Thread;
  Params.Layout = ML_RowMajor;
  Params.NumThreads = 1;
  runElementAccess(D3DDevice, DxcSupport, Params, VerboseLogging);
}

// ===========================================================================
// SetElement
// ===========================================================================

static const char SetElementShader[] = R"(
  RWByteAddressBuffer Input : register(u0);
  RWByteAddressBuffer Output : register(u1);

  [numthreads(1, 1, 1)]
  void main() {
    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, M_DIM, N_DIM, USE, SCOPE)]]
      Mat;
    __builtin_LinAlg_MatrixLoadFromDescriptor(
      Mat, Input, 0, STRIDE, LAYOUT);

    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, M_DIM, N_DIM, USE, SCOPE)]]
      MatOut;
#if COMP_TYPE == 9
    __builtin_LinAlg_MatrixSetElement(MatOut, Mat, SET_IDX, (float)SET_VAL);
#else
    __builtin_LinAlg_MatrixSetElement(MatOut, Mat, SET_IDX, (int)SET_VAL);
#endif

    __builtin_LinAlg_MatrixStoreToDescriptor(
      MatOut, Output, 0, STRIDE, LAYOUT);
  }
)";

static void runSetElement(ID3D12Device *Device,
                          dxc::SpecificDllLoader &DxcSupport,
                          const MatrixParams &Params, uint32_t SetIdx,
                          int32_t SetVal, bool Verbose) {
  const size_t NumElements = Params.totalElements();
  const size_t BufferSize = Params.totalBytes();
  const int Stride = Params.strideBytes();

  std::stringstream ExtraDefs;
  ExtraDefs << "-DSET_IDX=" << SetIdx << " -DSET_VAL=" << SetVal;

  std::string Args = buildCompilerArgs(
      Params.CompType, Params.M, Params.N, Params.Use, Params.Scope, Stride,
      Params.Layout, Params.NumThreads, Params.Enable16Bit,
      ExtraDefs.str().c_str());

  compileShader(DxcSupport, SetElementShader, "cs_6_10", Args);

  if (!Device) {
    hlsl_test::LogCommentFmt(
        L"Shader compiled OK; skipping execution (no SM 6.10 device)");
    WEX::Logging::Log::Result(WEX::Logging::TestResults::Skipped);
    return;
  }

  auto Op = createComputeOp(SetElementShader, "cs_6_10",
                            "UAV(u0), UAV(u1)", Args.c_str());
  addUAVBuffer(Op.get(), "Input", BufferSize, false, "byname");
  addUAVBuffer(Op.get(), "Output", BufferSize, true);
  addRootUAV(Op.get(), 0, "Input");
  addRootUAV(Op.get(), 1, "Output");

  auto Result = runShaderOp(
      Device, DxcSupport, std::move(Op),
      [&](LPCSTR Name, std::vector<BYTE> &Data, st::ShaderOp *) {
        if (_stricmp(Name, "Input") != 0)
          return;
        if (Params.CompType == CT_F32) {
          float *Ptr = reinterpret_cast<float *>(Data.data());
          for (size_t I = 0; I < NumElements; I++)
            Ptr[I] = static_cast<float>(I + 1);
        } else if (Params.CompType == CT_I32) {
          int32_t *Ptr = reinterpret_cast<int32_t *>(Data.data());
          for (size_t I = 0; I < NumElements; I++)
            Ptr[I] = static_cast<int32_t>(I + 1);
        }
      });

  MappedData OutData;
  Result->Test->GetReadBackData("Output", &OutData);

  // Expected: same as input except element at SetIdx is replaced.
  std::vector<float> ExpectedFloats(NumElements);
  std::vector<int32_t> ExpectedInts(NumElements);
  for (size_t I = 0; I < NumElements; I++) {
    ExpectedFloats[I] = static_cast<float>(I + 1);
    ExpectedInts[I] = static_cast<int32_t>(I + 1);
  }
  ExpectedFloats[SetIdx] = static_cast<float>(SetVal);
  ExpectedInts[SetIdx] = SetVal;

  if (Params.CompType == CT_F32)
    VERIFY_IS_TRUE(verifyFloatBuffer(OutData.data(), ExpectedFloats.data(),
                                     NumElements, Verbose));
  else if (Params.CompType == CT_I32)
    VERIFY_IS_TRUE(verifyIntBuffer(OutData.data(), ExpectedInts.data(),
                                   NumElements, Verbose));
}

void DxilConf_SM610_LinAlg::SetElement_Thread_F32() {
  MatrixParams Params = {};
  Params.CompType = CT_F32;
  Params.M = 4;
  Params.N = 4;
  Params.Use = MU_Accumulator;
  Params.Scope = MS_Thread;
  Params.Layout = ML_RowMajor;
  Params.NumThreads = 1;
  runSetElement(D3DDevice, DxcSupport, Params, 2, 99, VerboseLogging);
}

void DxilConf_SM610_LinAlg::SetElement_Thread_I32() {
  MatrixParams Params = {};
  Params.CompType = CT_I32;
  Params.M = 4;
  Params.N = 4;
  Params.Use = MU_Accumulator;
  Params.Scope = MS_Thread;
  Params.Layout = ML_RowMajor;
  Params.NumThreads = 1;
  runSetElement(D3DDevice, DxcSupport, Params, 2, 99, VerboseLogging);
}

// ===========================================================================
// CopyConvert (Cast)
// ===========================================================================

static const char CopyConvertShader[] = R"(
  RWByteAddressBuffer Input : register(u0);
  RWByteAddressBuffer Output : register(u1);

  [numthreads(1, 1, 1)]
  void main() {
    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(SRC_COMP, M_DIM, N_DIM, SRC_USE, SCOPE)]]
      Src;
    __builtin_LinAlg_MatrixLoadFromDescriptor(
      Src, Input, 0, STRIDE, LAYOUT);

    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(DST_COMP, M_DIM, N_DIM, DST_USE, SCOPE)]]
      Dst;
    __builtin_LinAlg_CopyConvertMatrix(Dst, Src, TRANSPOSE);

    __builtin_LinAlg_MatrixStoreToDescriptor(
      Dst, Output, 0, STRIDE, LAYOUT);
  }
)";

static void runCopyConvert(ID3D12Device *Device,
                           dxc::SpecificDllLoader &DxcSupport,
                           int SrcComp, int DstComp, int SrcUse, int DstUse,
                           int M, int N, int Scope, int Layout, int Stride,
                           bool Transpose, int NumThreads, bool Verbose) {
  const size_t NumElements = static_cast<size_t>(M) * N;
  const size_t BufferSize = NumElements * 4;

  std::stringstream SS;
  SS << "-HV 202x";
  SS << " -DSRC_COMP=" << SrcComp;
  SS << " -DDST_COMP=" << DstComp;
  SS << " -DSRC_USE=" << SrcUse;
  SS << " -DDST_USE=" << DstUse;
  SS << " -DM_DIM=" << M;
  SS << " -DN_DIM=" << N;
  SS << " -DSCOPE=" << Scope;
  SS << " -DSTRIDE=" << Stride;
  SS << " -DLAYOUT=" << Layout;
  SS << " -DTRANSPOSE=" << (Transpose ? "true" : "false");
  SS << " -DNUMTHREADS=" << NumThreads;
  std::string Args = SS.str();

  compileShader(DxcSupport, CopyConvertShader, "cs_6_10", Args);

  if (!Device) {
    hlsl_test::LogCommentFmt(
        L"Shader compiled OK; skipping execution (no SM 6.10 device)");
    WEX::Logging::Log::Result(WEX::Logging::TestResults::Skipped);
    return;
  }

  auto Op = createComputeOp(CopyConvertShader, "cs_6_10",
                            "UAV(u0), UAV(u1)", Args.c_str());
  addUAVBuffer(Op.get(), "Input", BufferSize, false, "byname");
  addUAVBuffer(Op.get(), "Output", BufferSize, true);
  addRootUAV(Op.get(), 0, "Input");
  addRootUAV(Op.get(), 1, "Output");

  auto Result = runShaderOp(
      Device, DxcSupport, std::move(Op),
      [&](LPCSTR Name, std::vector<BYTE> &Data, st::ShaderOp *) {
        if (_stricmp(Name, "Input") != 0)
          return;
        float *Ptr = reinterpret_cast<float *>(Data.data());
        for (size_t I = 0; I < NumElements; I++)
          Ptr[I] = static_cast<float>(I + 1);
      });

  MappedData OutData;
  Result->Test->GetReadBackData("Output", &OutData);

  // Without transpose: values should pass through unchanged.
  std::vector<float> Expected(NumElements);
  if (!Transpose) {
    for (size_t I = 0; I < NumElements; I++)
      Expected[I] = static_cast<float>(I + 1);
  } else {
    for (int R = 0; R < M; R++)
      for (int C = 0; C < N; C++)
        Expected[R * N + C] = static_cast<float>(C * M + R + 1);
  }
  VERIFY_IS_TRUE(
      verifyFloatBuffer(OutData.data(), Expected.data(), NumElements, Verbose));
}

void DxilConf_SM610_LinAlg::CopyConvert_Thread_F32() {
  // F32 → F32, same dimensions, no transpose.
  int Stride = 4 * 4; // N * sizeof(float)
  runCopyConvert(D3DDevice, DxcSupport, CT_F32, CT_F32, MU_A, MU_B,
                 4, 4, MS_Thread, ML_RowMajor, Stride, false, 1,
                 VerboseLogging);
}

// ===========================================================================
// Matrix × Matrix multiply
// ===========================================================================

static const char MatMulShader[] = R"(
  RWByteAddressBuffer Output : register(u0);

  [numthreads(NUMTHREADS, 1, 1)]
  void main() {
    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, M_DIM, K_DIM, 0, SCOPE)]]
      MatA;
    __builtin_LinAlg_FillMatrix(MatA, A_FILL);

    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, K_DIM, N_DIM, 1, SCOPE)]]
      MatB;
    __builtin_LinAlg_FillMatrix(MatB, B_FILL);

    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, M_DIM, N_DIM, 2, SCOPE)]]
      MatC;
    __builtin_LinAlg_MatrixMatrixMultiply(MatC, MatA, MatB);

    __builtin_LinAlg_MatrixStoreToDescriptor(
      MatC, Output, 0, STRIDE, LAYOUT);
  }
)";

static void runMatMul(ID3D12Device *Device,
                      dxc::SpecificDllLoader &DxcSupport,
                      const MatrixParams &Params, int K,
                      float AFill, float BFill, bool Verbose) {
  const size_t OutElements = static_cast<size_t>(Params.M) * Params.N;
  const size_t BufferSize = OutElements * 4;
  const int Stride = Params.strideBytes();

  std::stringstream ExtraDefs;
  ExtraDefs << "-DK_DIM=" << K
            << " -DA_FILL=" << static_cast<int>(AFill)
            << " -DB_FILL=" << static_cast<int>(BFill);

  std::string Args = buildCompilerArgs(
      Params.CompType, Params.M, Params.N, Params.Use, Params.Scope, Stride,
      Params.Layout, Params.NumThreads, Params.Enable16Bit,
      ExtraDefs.str().c_str());

  compileShader(DxcSupport, MatMulShader, "cs_6_10", Args);

  if (!Device) {
    hlsl_test::LogCommentFmt(
        L"Shader compiled OK; skipping execution (no SM 6.10 device)");
    WEX::Logging::Log::Result(WEX::Logging::TestResults::Skipped);
    return;
  }

  // C[i][j] = sum_k(A[i][k] * B[k][j]) = AFill * BFill * K.
  float ExpectedVal = AFill * BFill * K;
  std::vector<float> Expected(OutElements, ExpectedVal);

  auto Op =
      createComputeOp(MatMulShader, "cs_6_10", "UAV(u0)", Args.c_str());
  addUAVBuffer(Op.get(), "Output", BufferSize, true);
  addRootUAV(Op.get(), 0, "Output");

  auto Result = runShaderOp(Device, DxcSupport, std::move(Op));

  MappedData OutData;
  Result->Test->GetReadBackData("Output", &OutData);
  VERIFY_IS_TRUE(
      verifyFloatBuffer(OutData.data(), Expected.data(), OutElements, Verbose));
}

void DxilConf_SM610_LinAlg::MatMul_Wave_F32() {
  MatrixParams Params = {};
  Params.CompType = CT_F32;
  Params.M = 4;
  Params.N = 4;
  Params.Use = MU_Accumulator;
  Params.Scope = MS_Wave;
  Params.Layout = ML_RowMajor;
  Params.NumThreads = 64;
  runMatMul(D3DDevice, DxcSupport, Params, 4, 2.0f, 3.0f, VerboseLogging);
}

// ===========================================================================
// Matrix × Matrix multiply + accumulate
// ===========================================================================

static const char MatMulAccumShader[] = R"(
  RWByteAddressBuffer Output : register(u0);

  [numthreads(NUMTHREADS, 1, 1)]
  void main() {
    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, M_DIM, K_DIM, 0, SCOPE)]]
      MatA;
    __builtin_LinAlg_FillMatrix(MatA, A_FILL);

    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, K_DIM, N_DIM, 1, SCOPE)]]
      MatB;
    __builtin_LinAlg_FillMatrix(MatB, B_FILL);

    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, M_DIM, N_DIM, 2, SCOPE)]]
      MatC;
    __builtin_LinAlg_FillMatrix(MatC, C_FILL);

    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, M_DIM, N_DIM, 2, SCOPE)]]
      MatR;
    __builtin_LinAlg_MatrixMatrixMultiplyAccumulate(MatR, MatA, MatB, MatC);

    __builtin_LinAlg_MatrixStoreToDescriptor(
      MatR, Output, 0, STRIDE, LAYOUT);
  }
)";

static void runMatMulAccum(ID3D12Device *Device,
                           dxc::SpecificDllLoader &DxcSupport,
                           const MatrixParams &Params, int K,
                           float AFill, float BFill, float CFill,
                           bool Verbose) {
  const size_t OutElements = static_cast<size_t>(Params.M) * Params.N;
  const size_t BufferSize = OutElements * 4;
  const int Stride = Params.strideBytes();

  std::stringstream ExtraDefs;
  ExtraDefs << "-DK_DIM=" << K
            << " -DA_FILL=" << static_cast<int>(AFill)
            << " -DB_FILL=" << static_cast<int>(BFill)
            << " -DC_FILL=" << static_cast<int>(CFill);

  std::string Args = buildCompilerArgs(
      Params.CompType, Params.M, Params.N, Params.Use, Params.Scope, Stride,
      Params.Layout, Params.NumThreads, Params.Enable16Bit,
      ExtraDefs.str().c_str());

  compileShader(DxcSupport, MatMulAccumShader, "cs_6_10", Args);

  if (!Device) {
    hlsl_test::LogCommentFmt(
        L"Shader compiled OK; skipping execution (no SM 6.10 device)");
    WEX::Logging::Log::Result(WEX::Logging::TestResults::Skipped);
    return;
  }

  // R = C + A * B. Each element = CFill + AFill * BFill * K.
  float ExpectedVal = CFill + AFill * BFill * K;
  std::vector<float> Expected(OutElements, ExpectedVal);

  auto Op =
      createComputeOp(MatMulAccumShader, "cs_6_10", "UAV(u0)", Args.c_str());
  addUAVBuffer(Op.get(), "Output", BufferSize, true);
  addRootUAV(Op.get(), 0, "Output");

  auto Result = runShaderOp(Device, DxcSupport, std::move(Op));

  MappedData OutData;
  Result->Test->GetReadBackData("Output", &OutData);
  VERIFY_IS_TRUE(
      verifyFloatBuffer(OutData.data(), Expected.data(), OutElements, Verbose));
}

void DxilConf_SM610_LinAlg::MatMulAccum_Wave_F32() {
  MatrixParams Params = {};
  Params.CompType = CT_F32;
  Params.M = 4;
  Params.N = 4;
  Params.Use = MU_Accumulator;
  Params.Scope = MS_Wave;
  Params.Layout = ML_RowMajor;
  Params.NumThreads = 64;
  runMatMulAccum(D3DDevice, DxcSupport, Params, 4, 2.0f, 3.0f, 1.0f,
                 VerboseLogging);
}

// ===========================================================================
// Matrix accumulate (element-wise add)
// ===========================================================================

static const char AccumulateShader[] = R"(
  RWByteAddressBuffer Output : register(u0);

  [numthreads(NUMTHREADS, 1, 1)]
  void main() {
    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, M_DIM, N_DIM, 2, SCOPE)]]
      MatLHS;
    __builtin_LinAlg_FillMatrix(MatLHS, LHS_FILL);

    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, M_DIM, N_DIM, 2, SCOPE)]]
      MatRHS;
    __builtin_LinAlg_FillMatrix(MatRHS, RHS_FILL);

    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, M_DIM, N_DIM, 2, SCOPE)]]
      MatC;
    __builtin_LinAlg_MatrixAccumulate(MatC, MatLHS, MatRHS);

    __builtin_LinAlg_MatrixStoreToDescriptor(
      MatC, Output, 0, STRIDE, LAYOUT);
  }
)";

static void runAccumulate(ID3D12Device *Device,
                          dxc::SpecificDllLoader &DxcSupport,
                          const MatrixParams &Params,
                          float LHSFill, float RHSFill, bool Verbose) {
  const size_t NumElements = Params.totalElements();
  const size_t BufferSize = Params.totalBytes();
  const int Stride = Params.strideBytes();

  std::stringstream ExtraDefs;
  ExtraDefs << "-DLHS_FILL=" << static_cast<int>(LHSFill)
            << " -DRHS_FILL=" << static_cast<int>(RHSFill);

  std::string Args = buildCompilerArgs(
      Params.CompType, Params.M, Params.N, Params.Use, Params.Scope, Stride,
      Params.Layout, Params.NumThreads, Params.Enable16Bit,
      ExtraDefs.str().c_str());

  compileShader(DxcSupport, AccumulateShader, "cs_6_10", Args);

  if (!Device) {
    hlsl_test::LogCommentFmt(
        L"Shader compiled OK; skipping execution (no SM 6.10 device)");
    WEX::Logging::Log::Result(WEX::Logging::TestResults::Skipped);
    return;
  }

  float ExpectedVal = LHSFill + RHSFill;
  std::vector<float> Expected(NumElements, ExpectedVal);

  auto Op =
      createComputeOp(AccumulateShader, "cs_6_10", "UAV(u0)", Args.c_str());
  addUAVBuffer(Op.get(), "Output", BufferSize, true);
  addRootUAV(Op.get(), 0, "Output");

  auto Result = runShaderOp(Device, DxcSupport, std::move(Op));

  MappedData OutData;
  Result->Test->GetReadBackData("Output", &OutData);
  VERIFY_IS_TRUE(verifyFloatBuffer(OutData.data(), Expected.data(),
                                   NumElements, Verbose));
}

void DxilConf_SM610_LinAlg::MatAccumulate_Wave_F32() {
  MatrixParams Params = {};
  Params.CompType = CT_F32;
  Params.M = 4;
  Params.N = 4;
  Params.Use = MU_Accumulator;
  Params.Scope = MS_Wave;
  Params.Layout = ML_RowMajor;
  Params.NumThreads = 64;
  runAccumulate(D3DDevice, DxcSupport, Params, 5.0f, 3.0f, VerboseLogging);
}

// ===========================================================================
// Matrix × Vector multiply
// ===========================================================================

static const char MatVecMulShader[] = R"(
  RWByteAddressBuffer VecIn : register(u0);
  RWByteAddressBuffer VecOut : register(u1);

  [numthreads(1, 1, 1)]
  void main() {
    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, 4, 4, USE, 0)]]
      Mat;
    __builtin_LinAlg_FillMatrix(Mat, MAT_FILL);

    float4 InVec = float4(
      asfloat(VecIn.Load(0)),
      asfloat(VecIn.Load(4)),
      asfloat(VecIn.Load(8)),
      asfloat(VecIn.Load(12)));

    float4 OutVec;
    __builtin_LinAlg_MatrixVectorMultiply(OutVec, Mat, InVec, INTERP);

    VecOut.Store(0, asuint(OutVec.x));
    VecOut.Store(4, asuint(OutVec.y));
    VecOut.Store(8, asuint(OutVec.z));
    VecOut.Store(12, asuint(OutVec.w));
  }
)";

static void runMatVecMul(ID3D12Device *Device,
                         dxc::SpecificDllLoader &DxcSupport,
                         int CompType, int Use, int Interp, float MatFill,
                         const float InVec[4], bool Verbose) {
  const size_t VecBytes = 4 * sizeof(float);

  std::stringstream SS;
  SS << "-HV 202x";
  SS << " -DCOMP_TYPE=" << CompType;
  SS << " -DUSE=" << Use;
  SS << " -DMAT_FILL=" << static_cast<int>(MatFill);
  SS << " -DINTERP=" << Interp;
  SS << " -DNUMTHREADS=1";
  std::string Args = SS.str();

  compileShader(DxcSupport, MatVecMulShader, "cs_6_10", Args);

  if (!Device) {
    hlsl_test::LogCommentFmt(
        L"Shader compiled OK; skipping execution (no SM 6.10 device)");
    WEX::Logging::Log::Result(WEX::Logging::TestResults::Skipped);
    return;
  }

  auto Op = createComputeOp(MatVecMulShader, "cs_6_10",
                            "UAV(u0), UAV(u1)", Args.c_str());
  addUAVBuffer(Op.get(), "VecIn", VecBytes, false, "byname");
  addUAVBuffer(Op.get(), "VecOut", VecBytes, true);
  addRootUAV(Op.get(), 0, "VecIn");
  addRootUAV(Op.get(), 1, "VecOut");

  auto Result = runShaderOp(
      Device, DxcSupport, std::move(Op),
      [&](LPCSTR Name, std::vector<BYTE> &Data, st::ShaderOp *) {
        if (_stricmp(Name, "VecIn") != 0)
          return;
        float *Ptr = reinterpret_cast<float *>(Data.data());
        for (int I = 0; I < 4; I++)
          Ptr[I] = InVec[I];
      });

  MappedData OutData;
  Result->Test->GetReadBackData("VecOut", &OutData);

  // Uniform-fill matrix: Out[i] = MatFill * sum(InVec).
  float Sum = InVec[0] + InVec[1] + InVec[2] + InVec[3];
  float ExpectedOut[4] = {MatFill * Sum, MatFill * Sum,
                          MatFill * Sum, MatFill * Sum};
  VERIFY_IS_TRUE(
      verifyFloatBuffer(OutData.data(), ExpectedOut, 4, Verbose));
}

void DxilConf_SM610_LinAlg::MatVecMul_Thread_F32() {
  float InVec[4] = {1.0f, 2.0f, 3.0f, 4.0f};
  runMatVecMul(D3DDevice, DxcSupport, CT_F32, MU_A, CT_F32,
               2.0f, InVec, VerboseLogging);
}

// ===========================================================================
// Matrix × Vector multiply + add
// ===========================================================================

static const char MatVecMulAddShader[] = R"(
  RWByteAddressBuffer VecIn : register(u0);
  RWByteAddressBuffer BiasIn : register(u1);
  RWByteAddressBuffer VecOut : register(u2);

  [numthreads(1, 1, 1)]
  void main() {
    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, 4, 4, USE, 0)]]
      Mat;
    __builtin_LinAlg_FillMatrix(Mat, MAT_FILL);

    float4 InVec = float4(
      asfloat(VecIn.Load(0)),
      asfloat(VecIn.Load(4)),
      asfloat(VecIn.Load(8)),
      asfloat(VecIn.Load(12)));

    float4 BiasVec = float4(
      asfloat(BiasIn.Load(0)),
      asfloat(BiasIn.Load(4)),
      asfloat(BiasIn.Load(8)),
      asfloat(BiasIn.Load(12)));

    float4 OutVec;
    __builtin_LinAlg_MatrixVectorMultiplyAdd(
      OutVec, Mat, InVec, INTERP, BiasVec, INTERP);

    VecOut.Store(0, asuint(OutVec.x));
    VecOut.Store(4, asuint(OutVec.y));
    VecOut.Store(8, asuint(OutVec.z));
    VecOut.Store(12, asuint(OutVec.w));
  }
)";

static void runMatVecMulAdd(ID3D12Device *Device,
                            dxc::SpecificDllLoader &DxcSupport,
                            int CompType, int Use, int Interp, float MatFill,
                            const float InVec[4], const float BiasVec[4],
                            bool Verbose) {
  const size_t VecBytes = 4 * sizeof(float);

  std::stringstream SS;
  SS << "-HV 202x";
  SS << " -DCOMP_TYPE=" << CompType;
  SS << " -DUSE=" << Use;
  SS << " -DMAT_FILL=" << static_cast<int>(MatFill);
  SS << " -DINTERP=" << Interp;
  SS << " -DNUMTHREADS=1";
  std::string Args = SS.str();

  compileShader(DxcSupport, MatVecMulAddShader, "cs_6_10", Args);

  if (!Device) {
    hlsl_test::LogCommentFmt(
        L"Shader compiled OK; skipping execution (no SM 6.10 device)");
    WEX::Logging::Log::Result(WEX::Logging::TestResults::Skipped);
    return;
  }

  auto Op = createComputeOp(MatVecMulAddShader, "cs_6_10",
                            "UAV(u0), UAV(u1), UAV(u2)", Args.c_str());
  addUAVBuffer(Op.get(), "VecIn", VecBytes, false, "byname");
  addUAVBuffer(Op.get(), "BiasIn", VecBytes, false, "byname");
  addUAVBuffer(Op.get(), "VecOut", VecBytes, true);
  addRootUAV(Op.get(), 0, "VecIn");
  addRootUAV(Op.get(), 1, "BiasIn");
  addRootUAV(Op.get(), 2, "VecOut");

  auto Result = runShaderOp(
      Device, DxcSupport, std::move(Op),
      [&](LPCSTR Name, std::vector<BYTE> &Data, st::ShaderOp *) {
        float *Ptr = reinterpret_cast<float *>(Data.data());
        if (_stricmp(Name, "VecIn") == 0) {
          for (int I = 0; I < 4; I++)
            Ptr[I] = InVec[I];
        } else if (_stricmp(Name, "BiasIn") == 0) {
          for (int I = 0; I < 4; I++)
            Ptr[I] = BiasVec[I];
        }
      });

  MappedData OutData;
  Result->Test->GetReadBackData("VecOut", &OutData);

  // Out[i] = MatFill * sum(InVec) + BiasVec[i].
  float Sum = InVec[0] + InVec[1] + InVec[2] + InVec[3];
  float MulPart = MatFill * Sum;
  float ExpectedOut[4] = {MulPart + BiasVec[0], MulPart + BiasVec[1],
                          MulPart + BiasVec[2], MulPart + BiasVec[3]};
  VERIFY_IS_TRUE(
      verifyFloatBuffer(OutData.data(), ExpectedOut, 4, Verbose));
}

void DxilConf_SM610_LinAlg::MatVecMulAdd_Thread_F32() {
  float InVec[4] = {1.0f, 2.0f, 3.0f, 4.0f};
  float BiasVec[4] = {10.0f, 20.0f, 30.0f, 40.0f};
  runMatVecMulAdd(D3DDevice, DxcSupport, CT_F32, MU_A, CT_F32,
                  2.0f, InVec, BiasVec, VerboseLogging);
}

// ===========================================================================
// Outer product
// ===========================================================================

static const char OuterProductShader[] = R"(
  RWByteAddressBuffer VecAIn : register(u0);
  RWByteAddressBuffer VecBIn : register(u1);
  RWByteAddressBuffer Output : register(u2);

  [numthreads(1, 1, 1)]
  void main() {
    float4 VecA = float4(
      asfloat(VecAIn.Load(0)),
      asfloat(VecAIn.Load(4)),
      asfloat(VecAIn.Load(8)),
      asfloat(VecAIn.Load(12)));

    float4 VecB = float4(
      asfloat(VecBIn.Load(0)),
      asfloat(VecBIn.Load(4)),
      asfloat(VecBIn.Load(8)),
      asfloat(VecBIn.Load(12)));

    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, 4, 4, 2, 0)]]
      Mat;
    __builtin_LinAlg_MatrixOuterProduct(Mat, VecA, VecB);

    __builtin_LinAlg_MatrixStoreToDescriptor(
      Mat, Output, 0, STRIDE, LAYOUT);
  }
)";

static void runOuterProduct(ID3D12Device *Device,
                            dxc::SpecificDllLoader &DxcSupport,
                            int CompType, int Layout, int Stride,
                            const float VecA[4], const float VecB[4],
                            bool Verbose) {
  const size_t MatBytes = 4 * 4 * sizeof(float);
  const size_t VecBytes = 4 * sizeof(float);

  std::stringstream SS;
  SS << "-HV 202x";
  SS << " -DCOMP_TYPE=" << CompType;
  SS << " -DSTRIDE=" << Stride;
  SS << " -DLAYOUT=" << Layout;
  SS << " -DNUMTHREADS=1";
  std::string Args = SS.str();

  compileShader(DxcSupport, OuterProductShader, "cs_6_10", Args);

  if (!Device) {
    hlsl_test::LogCommentFmt(
        L"Shader compiled OK; skipping execution (no SM 6.10 device)");
    WEX::Logging::Log::Result(WEX::Logging::TestResults::Skipped);
    return;
  }

  auto Op = createComputeOp(OuterProductShader, "cs_6_10",
                            "UAV(u0), UAV(u1), UAV(u2)", Args.c_str());
  addUAVBuffer(Op.get(), "VecAIn", VecBytes, false, "byname");
  addUAVBuffer(Op.get(), "VecBIn", VecBytes, false, "byname");
  addUAVBuffer(Op.get(), "Output", MatBytes, true);
  addRootUAV(Op.get(), 0, "VecAIn");
  addRootUAV(Op.get(), 1, "VecBIn");
  addRootUAV(Op.get(), 2, "Output");

  auto Result = runShaderOp(
      Device, DxcSupport, std::move(Op),
      [&](LPCSTR Name, std::vector<BYTE> &Data, st::ShaderOp *) {
        float *Ptr = reinterpret_cast<float *>(Data.data());
        if (_stricmp(Name, "VecAIn") == 0) {
          for (int I = 0; I < 4; I++)
            Ptr[I] = VecA[I];
        } else if (_stricmp(Name, "VecBIn") == 0) {
          for (int I = 0; I < 4; I++)
            Ptr[I] = VecB[I];
        }
      });

  MappedData OutData;
  Result->Test->GetReadBackData("Output", &OutData);

  // Expected: Mat[i][j] = VecA[i] * VecB[j] (row-major).
  float Expected[16];
  for (int R = 0; R < 4; R++)
    for (int C = 0; C < 4; C++)
      Expected[R * 4 + C] = VecA[R] * VecB[C];

  VERIFY_IS_TRUE(verifyFloatBuffer(OutData.data(), Expected, 16, Verbose));
}

void DxilConf_SM610_LinAlg::OuterProduct_Thread_F32() {
  float VecA[4] = {1.0f, 2.0f, 3.0f, 4.0f};
  float VecB[4] = {1.0f, 2.0f, 3.0f, 4.0f};
  int Stride = 4 * 4; // N * sizeof(float)
  runOuterProduct(D3DDevice, DxcSupport, CT_F32, ML_RowMajor, Stride,
                  VecA, VecB, VerboseLogging);
}

// ===========================================================================
// Groupshared Load/Store roundtrip
// ===========================================================================

static const char GroupsharedLoadStoreShader[] = R"(
  RWByteAddressBuffer Input : register(u0);
  RWByteAddressBuffer Output : register(u1);

  groupshared float SharedArr[M_DIM * N_DIM];

  [numthreads(NUMTHREADS, 1, 1)]
  void main(uint GI : SV_GroupIndex) {
    // Fill groupshared from input buffer.
    if (GI < M_DIM * N_DIM) {
      SharedArr[GI] = asfloat(Input.Load(GI * 4));
    }
    GroupMemoryBarrierWithGroupSync();

    // Load from groupshared into matrix.
    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, M_DIM, N_DIM, USE, 2)]]
      Mat;
    __builtin_LinAlg_MatrixLoadFromMemory(Mat, SharedArr, 0, STRIDE, LAYOUT);

    // Store to output buffer.
    __builtin_LinAlg_MatrixStoreToDescriptor(
      Mat, Output, 0, STRIDE, LAYOUT);
  }
)";

static void runGroupsharedLoadStore(ID3D12Device *Device,
                                    dxc::SpecificDllLoader &DxcSupport,
                                    const MatrixParams &Params, bool Verbose) {
  const size_t NumElements = Params.totalElements();
  const size_t BufferSize = Params.totalBytes();
  const int Stride = Params.strideBytes();

  std::string Args =
      buildCompilerArgs(Params.CompType, Params.M, Params.N, Params.Use,
                        Params.Scope, Stride, Params.Layout,
                        Params.NumThreads, Params.Enable16Bit);

  compileShader(DxcSupport, GroupsharedLoadStoreShader, "cs_6_10", Args);

  if (!Device) {
    hlsl_test::LogCommentFmt(
        L"Shader compiled OK; skipping execution (no SM 6.10 device)");
    WEX::Logging::Log::Result(WEX::Logging::TestResults::Skipped);
    return;
  }

  auto Op = createComputeOp(GroupsharedLoadStoreShader, "cs_6_10",
                            "UAV(u0), UAV(u1)", Args.c_str());
  addUAVBuffer(Op.get(), "Input", BufferSize, false, "byname");
  addUAVBuffer(Op.get(), "Output", BufferSize, true);
  addRootUAV(Op.get(), 0, "Input");
  addRootUAV(Op.get(), 1, "Output");

  std::vector<float> ExpectedFloats(NumElements);
  for (size_t I = 0; I < NumElements; I++)
    ExpectedFloats[I] = static_cast<float>(I + 1);

  auto Result = runShaderOp(
      Device, DxcSupport, std::move(Op),
      [&](LPCSTR Name, std::vector<BYTE> &Data, st::ShaderOp *) {
        if (_stricmp(Name, "Input") != 0)
          return;
        float *Ptr = reinterpret_cast<float *>(Data.data());
        for (size_t I = 0; I < NumElements; I++)
          Ptr[I] = static_cast<float>(I + 1);
      });

  MappedData OutData;
  Result->Test->GetReadBackData("Output", &OutData);
  VERIFY_IS_TRUE(verifyFloatBuffer(OutData.data(), ExpectedFloats.data(),
                                   NumElements, Verbose));
}

void DxilConf_SM610_LinAlg::GroupsharedLoadStore_F32() {
  MatrixParams Params = {};
  Params.CompType = CT_F32;
  Params.M = 4;
  Params.N = 4;
  Params.Use = MU_Accumulator;
  Params.Scope = MS_ThreadGroup;
  Params.Layout = ML_RowMajor;
  Params.NumThreads = 64;
  runGroupsharedLoadStore(D3DDevice, DxcSupport, Params, VerboseLogging);
}

// ===========================================================================
// Groupshared interlocked accumulate
// ===========================================================================

static const char GroupsharedAccumShader[] = R"(
  RWByteAddressBuffer Output : register(u0);

  groupshared float SharedArr[M_DIM * N_DIM];

  [numthreads(NUMTHREADS, 1, 1)]
  void main(uint GI : SV_GroupIndex) {
    // Zero out groupshared memory.
    if (GI < M_DIM * N_DIM) {
      SharedArr[GI] = 0.0f;
    }
    GroupMemoryBarrierWithGroupSync();

    // Each thread creates a matrix filled with 1 and accumulates.
    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, M_DIM, N_DIM, 2, 2)]]
      Mat;
    __builtin_LinAlg_FillMatrix(Mat, 1);
    __builtin_LinAlg_MatrixAccumulateToMemory(
      Mat, SharedArr, 0, STRIDE, LAYOUT);

    GroupMemoryBarrierWithGroupSync();

    // Thread 0 copies result to output.
    if (GI == 0) {
      [unroll] for (uint I = 0; I < M_DIM * N_DIM; I++) {
        Output.Store(I * 4, asuint(SharedArr[I]));
      }
    }
  }
)";

static void runGroupsharedAccum(ID3D12Device *Device,
                                dxc::SpecificDllLoader &DxcSupport,
                                const MatrixParams &Params, bool Verbose) {
  const size_t NumElements = Params.totalElements();
  const size_t BufferSize = NumElements * sizeof(float);
  const int Stride = Params.strideBytes();

  std::string Args =
      buildCompilerArgs(Params.CompType, Params.M, Params.N, Params.Use,
                        Params.Scope, Stride, Params.Layout,
                        Params.NumThreads, Params.Enable16Bit);

  compileShader(DxcSupport, GroupsharedAccumShader, "cs_6_10", Args);

  if (!Device) {
    hlsl_test::LogCommentFmt(
        L"Shader compiled OK; skipping execution (no SM 6.10 device)");
    WEX::Logging::Log::Result(WEX::Logging::TestResults::Skipped);
    return;
  }

  auto Op =
      createComputeOp(GroupsharedAccumShader, "cs_6_10", "UAV(u0)",
                      Args.c_str());
  addUAVBuffer(Op.get(), "Output", BufferSize, true);
  addRootUAV(Op.get(), 0, "Output");

  auto Result = runShaderOp(Device, DxcSupport, std::move(Op));

  MappedData OutData;
  Result->Test->GetReadBackData("Output", &OutData);

  // All NUMTHREADS threads accumulated 1.0 into each element.
  float ExpectedVal = static_cast<float>(Params.NumThreads);
  std::vector<float> Expected(NumElements, ExpectedVal);
  VERIFY_IS_TRUE(verifyFloatBuffer(OutData.data(), Expected.data(),
                                   NumElements, Verbose));
}

void DxilConf_SM610_LinAlg::GroupsharedAccum_F32() {
  MatrixParams Params = {};
  Params.CompType = CT_F32;
  Params.M = 4;
  Params.N = 4;
  Params.Use = MU_Accumulator;
  Params.Scope = MS_ThreadGroup;
  Params.Layout = ML_RowMajor;
  Params.NumThreads = 64;
  runGroupsharedAccum(D3DDevice, DxcSupport, Params, VerboseLogging);
}

// ===========================================================================
// Accumulate to descriptor (RWByteAddressBuffer)
// ===========================================================================

static const char AccumToDescriptorShader[] = R"(
  RWByteAddressBuffer Output : register(u0);

  [numthreads(NUMTHREADS, 1, 1)]
  void main() {
    __builtin_LinAlgMatrix
      [[__LinAlgMatrix_Attributes(COMP_TYPE, M_DIM, N_DIM, 2, SCOPE)]]
      Mat;
    __builtin_LinAlg_FillMatrix(Mat, FILL_VALUE);
    __builtin_LinAlg_MatrixAccumulateToDescriptor(
      Mat, Output, 0, STRIDE, LAYOUT);
  }
)";

static void runAccumToDescriptor(ID3D12Device *Device,
                                 dxc::SpecificDllLoader &DxcSupport,
                                 const MatrixParams &Params, float FillValue,
                                 bool Verbose) {
  const size_t NumElements = Params.totalElements();
  const size_t BufferSize = Params.totalBytes();
  const int Stride = Params.strideBytes();

  std::stringstream ExtraDefs;
  ExtraDefs << "-DFILL_VALUE=" << static_cast<int>(FillValue);

  std::string Args = buildCompilerArgs(
      Params.CompType, Params.M, Params.N, Params.Use, Params.Scope, Stride,
      Params.Layout, Params.NumThreads, Params.Enable16Bit,
      ExtraDefs.str().c_str());

  compileShader(DxcSupport, AccumToDescriptorShader, "cs_6_10", Args);

  if (!Device) {
    hlsl_test::LogCommentFmt(
        L"Shader compiled OK; skipping execution (no SM 6.10 device)");
    WEX::Logging::Log::Result(WEX::Logging::TestResults::Skipped);
    return;
  }

  auto Op = createComputeOp(AccumToDescriptorShader, "cs_6_10", "UAV(u0)",
                            Args.c_str());
  addUAVBuffer(Op.get(), "Output", BufferSize, true);
  addRootUAV(Op.get(), 0, "Output");

  auto Result = runShaderOp(Device, DxcSupport, std::move(Op));

  MappedData OutData;
  Result->Test->GetReadBackData("Output", &OutData);

  // Buffer was zero-initialized; one dispatch accumulated FillValue.
  std::vector<float> Expected(NumElements, FillValue);
  VERIFY_IS_TRUE(verifyFloatBuffer(OutData.data(), Expected.data(),
                                   NumElements, Verbose));
}

void DxilConf_SM610_LinAlg::AccumToDescriptor_Wave_F32() {
  MatrixParams Params = {};
  Params.CompType = CT_F32;
  Params.M = 4;
  Params.N = 4;
  Params.Use = MU_Accumulator;
  Params.Scope = MS_Wave;
  Params.Layout = ML_RowMajor;
  Params.NumThreads = 64;
  runAccumToDescriptor(D3DDevice, DxcSupport, Params, 7.0f, VerboseLogging);
}

// ===========================================================================
// Query accumulator layout
// ===========================================================================

static const char QueryAccumLayoutShader[] = R"(
  RWByteAddressBuffer Output : register(u0);

  [numthreads(1, 1, 1)]
  void main() {
    uint Layout = __builtin_LinAlg_MatrixQueryAccumulatorLayout();
    Output.Store(0, Layout);
  }
)";

static void runQueryAccumLayout(ID3D12Device *Device,
                                dxc::SpecificDllLoader &DxcSupport,
                                bool Verbose) {
  std::string Args = "-HV 202x";

  compileShader(DxcSupport, QueryAccumLayoutShader, "cs_6_10", Args);

  if (!Device) {
    hlsl_test::LogCommentFmt(
        L"Shader compiled OK; skipping execution (no SM 6.10 device)");
    WEX::Logging::Log::Result(WEX::Logging::TestResults::Skipped);
    return;
  }

  auto Op = createComputeOp(QueryAccumLayoutShader, "cs_6_10", "UAV(u0)",
                            Args.c_str());
  addUAVBuffer(Op.get(), "Output", sizeof(uint32_t), true);
  addRootUAV(Op.get(), 0, "Output");

  auto Result = runShaderOp(Device, DxcSupport, std::move(Op));

  MappedData OutData;
  Result->Test->GetReadBackData("Output", &OutData);
  const uint32_t *Out = static_cast<const uint32_t *>(OutData.data());

  // AccumulatorLayout should be 0 (A) or 1 (B).
  VERIFY_IS_TRUE(Out[0] <= 1);
  if (Verbose) {
    hlsl_test::LogCommentFmt(L"AccumulatorLayout = %u", Out[0]);
  }
}

void DxilConf_SM610_LinAlg::QueryAccumLayout() {
  runQueryAccumLayout(D3DDevice, DxcSupport, VerboseLogging);
}

} // namespace LinAlg
