///////////////////////////////////////////////////////////////////////////////
//                                                                           //
// DxcTestUtils.h                                                            //
// Copyright (C) Microsoft Corporation. All rights reserved.                 //
// Licensed under the MIT license. See COPYRIGHT in the project root for     //
// full license information.                                                 //
//                                                                           //
// This file provides utility functions for testing dxc APIs.                //
//                                                                           //
///////////////////////////////////////////////////////////////////////////////

#include <string>
#include <vector>
#include "dxc/dxcapi.h"
#include "dxc/Support/dxcapi.use.h"

namespace hlsl {
namespace options {
class DxcOpts;
class MainArgs;
}
}

/// Use this class to run a FileCheck invocation in memory.
class FileCheckForTest {
public:
  FileCheckForTest();

  std::string CheckFilename;
  /// File to check (defaults to stdin)
  std::string InputFilename;
  /// Prefix to use from check file (defaults to 'CHECK')
  std::vector<std::string> CheckPrefixes;
  /// Do not treat all horizontal whitespace as equivalent
  bool NoCanonicalizeWhiteSpace;
  /// Add an implicit negative check with this pattern to every
  /// positive check. This can be used to ensure that no instances of
  /// this pattern occur which are not matched by a positive pattern
  std::vector<std::string> ImplicitCheckNot;
  /// Allow the input file to be empty. This is useful when making
  /// checks that some error message does not occur, for example.
  bool AllowEmptyInput;

  /// String to read in place of standard input.
  std::string InputForStdin;
  /// Output stream.
  std::string test_outs;
  /// Output stream.
  std::string test_errs;

  int Run();
};

class FileRunCommandPart {
private:
  void RunFileChecker(const FileRunCommandPart *Prior);
  void RunStdErrChecker(const FileRunCommandPart *Prior);
  void RunDxc(const FileRunCommandPart *Prior);
  void RunDxv(const FileRunCommandPart *Prior);
  void RunOpt(const FileRunCommandPart *Prior);
  void RunTee(const FileRunCommandPart *Prior);
public:
  FileRunCommandPart(const FileRunCommandPart&) = default;
  FileRunCommandPart(const std::string &command, const std::string &arguments, LPCWSTR commandFileName);
  FileRunCommandPart(FileRunCommandPart && other);
  
  void Run(const FileRunCommandPart *Prior);
  
  void ReadOptsForDxc(hlsl::options::MainArgs &argStrings, hlsl::options::DxcOpts &Opts);

  std::string Command;      // Command to run, eg %dxc
  std::string Arguments;    // Arguments to command
  LPCWSTR CommandFileName;  // File name replacement for %s

  dxc::DxcDllSupport *DllSupport; // DLL support to use for Run().

  // These fields are set after an invocation to Run().
  CComPtr<IDxcOperationResult> OpResult;  // The operation result, if any.
  int RunResult;                          // The exit code for the operation.
  std::string StdOut;                     // Standard output text.
  std::string StdErr;                     // Standard error text.
};

void ParseCommandParts(LPCSTR commands, LPCWSTR fileName, std::vector<FileRunCommandPart> &parts);
void ParseCommandPartsFromFile(LPCWSTR fileName, std::vector<FileRunCommandPart> &parts);

class FileRunTestResult {
public:
  std::string ErrorMessage;
  int RunResult;
  static FileRunTestResult RunFromFileCommands(LPCWSTR fileName);
  static FileRunTestResult RunFromFileCommands(LPCWSTR fileName, dxc::DxcDllSupport &dllSupport);
};

inline std::string BlobToUtf8(_In_ IDxcBlob *pBlob) {
  if (pBlob == nullptr)
    return std::string();
  return std::string((char *)pBlob->GetBufferPointer(), pBlob->GetBufferSize());
}

std::wstring BlobToUtf16(_In_ IDxcBlob *pBlob);
void CheckOperationSucceeded(IDxcOperationResult *pResult, IDxcBlob **ppBlob);
std::string DisassembleProgram(dxc::DxcDllSupport &dllSupport, IDxcBlob *pProgram);
void Utf8ToBlob(dxc::DxcDllSupport &dllSupport, const std::string &val, _Outptr_ IDxcBlob **ppBlob);
void Utf8ToBlob(dxc::DxcDllSupport &dllSupport, const std::string &val, _Outptr_ IDxcBlobEncoding **ppBlob);
void Utf8ToBlob(dxc::DxcDllSupport &dllSupport, const char *pVal, _Outptr_ IDxcBlobEncoding **ppBlob);
void Utf16ToBlob(dxc::DxcDllSupport &dllSupport, const std::wstring &val, _Outptr_ IDxcBlob **ppBlob);
void Utf16ToBlob(dxc::DxcDllSupport &dllSupport, const std::wstring &val, _Outptr_ IDxcBlobEncoding **ppBlob);
