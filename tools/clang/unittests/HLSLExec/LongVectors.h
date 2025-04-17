#pragma once

#include <array>
#include <limits>
#include <ostream>
#include <random>
#include <sstream>
#include <string>

#include <DirectXMath.h>
#include <DirectXPackedVector.h>

#include <Verify.h>

enum LongVectorOpType {
  LongVectorOpType_ScalarAdd,
  LongVectorOpType_ScalarMultiply,
  LongVectorOpType_Multiply,
  LongVectorOpType_Add,
  LongVectorOpType_Min,
  LongVectorOpType_Max,
  LongVectorOpType_Clamp,
  LongVectorOpType_Initialize,
  LongVectorOpType_UnInitialized
};

template <typename T, LongVectorOpType OpType>
struct LongVectorOpTestConfig; // Forward declaration

// LongVectorOp is used in ShaderOpArithTable.xml. The shaders for these
// tests use the struct defintion to read from the input global buffer.
template <typename T, std::size_t N> struct LongVectorOp {
  T ScalarInput;
  std::array<T, N> VecInput1;
  std::array<T, N> VecInput2;
  std::array<T, N> VecOutput;
};

// A helper struct because C++ bools are 1 byte and HLSL bools are 4 bytes.
// Take int32_t as a constuctor argument and convert it to bool when needed.
// Comparisons cast to a bool because we only care if the bool representation
// is true or false.
struct HLSLBool_t {
  HLSLBool_t() : val(0) {}
  HLSLBool_t(int32_t val) : val(val) {}
  HLSLBool_t(bool val) : val(val) {}
  HLSLBool_t(const HLSLBool_t &other) : val(other.val) {}

  bool operator==(const HLSLBool_t &other) const {
    return static_cast<bool>(val) == static_cast<bool>(other.val);
  }

  bool operator!=(const HLSLBool_t &other) const {
    return static_cast<bool>(val) != static_cast<bool>(other.val);
  }

  bool operator<(const HLSLBool_t &other) const { return val < other.val; }

  bool operator>(const HLSLBool_t &other) const { return val > other.val; }

  bool operator<=(const HLSLBool_t &other) const { return val <= other.val; }

  bool operator>=(const HLSLBool_t &other) const { return val >= other.val; }

  HLSLBool_t operator*(const HLSLBool_t &other) const {
    return HLSLBool_t(val * other.val);
  }

  HLSLBool_t operator+(const HLSLBool_t &other) const {
    return HLSLBool_t(val + other.val);
  }

  // So we can construct std::wstrings using std::wostream
  friend std::wostream &operator<<(std::wostream &os, const HLSLBool_t &obj) {
    os << static_cast<bool>(obj.val);
    return os;
  }

  // So we can construct std::strings using std::ostream
  friend std::ostream &operator<<(std::ostream &os, const HLSLBool_t &obj) {
    os << static_cast<bool>(obj.val);
    return os;
  }

  int32_t val = 0;
};

//  No native float16 type in C++ until C++23 . So we use uint16_t to
//  represent it. Simple little wrapping struct to help handle the right
//  behavior.
struct HLSLHalf_t {
  HLSLHalf_t() : val(0) {}
  HLSLHalf_t(DirectX::PackedVector::HALF val) : val(val) {}
  HLSLHalf_t(const HLSLHalf_t &other) : val(other.val) {}

  bool operator==(const HLSLHalf_t &other) const { return val == other.val; }

  bool operator<(const HLSLHalf_t &other) const {
    return DirectX::PackedVector::XMConvertHalfToFloat(val) <
           DirectX::PackedVector::XMConvertHalfToFloat(other.val);
  }

  bool operator>(const HLSLHalf_t &other) const {
    return DirectX::PackedVector::XMConvertHalfToFloat(val) >
           DirectX::PackedVector::XMConvertHalfToFloat(other.val);
  }

  // Used by tolerance checks in the tests.
  bool operator>(float d) const {
    float a = DirectX::PackedVector::XMConvertHalfToFloat(val);
    return a > d;
  }

  bool operator<=(const HLSLHalf_t &other) const {
    return DirectX::PackedVector::XMConvertHalfToFloat(val) <=
           DirectX::PackedVector::XMConvertHalfToFloat(other.val);
  }

  bool operator>=(const HLSLHalf_t &other) const {
    return DirectX::PackedVector::XMConvertHalfToFloat(val) >=
           DirectX::PackedVector::XMConvertHalfToFloat(other.val);
  }

  bool operator!=(const HLSLHalf_t &other) const { return val != other.val; }

  HLSLHalf_t operator*(const HLSLHalf_t &other) const {
    float a = DirectX::PackedVector::XMConvertHalfToFloat(val);
    float b = DirectX::PackedVector::XMConvertHalfToFloat(other.val);
    return HLSLHalf_t(DirectX::PackedVector::XMConvertFloatToHalf(a * b));
  }

  HLSLHalf_t operator+(const HLSLHalf_t &other) const {
    float a = DirectX::PackedVector::XMConvertHalfToFloat(val);
    float b = DirectX::PackedVector::XMConvertHalfToFloat(other.val);
    return HLSLHalf_t(DirectX::PackedVector::XMConvertFloatToHalf(a + b));
  }

  HLSLHalf_t operator-(const HLSLHalf_t &other) const {
    float a = DirectX::PackedVector::XMConvertHalfToFloat(val);
    float b = DirectX::PackedVector::XMConvertHalfToFloat(other.val);
    return HLSLHalf_t(DirectX::PackedVector::XMConvertFloatToHalf(a - b));
  }

  // So we can construct std::wstrings using std::wostream
  friend std::wostream &operator<<(std::wostream &os, const HLSLHalf_t &obj) {
    os << DirectX::PackedVector::XMConvertHalfToFloat(obj.val);
    return os;
  }

  // So we can construct std::wstrings using std::wostream
  friend std::ostream &operator<<(std::ostream &os, const HLSLHalf_t &obj) {
    os << DirectX::PackedVector::XMConvertHalfToFloat(obj.val);
    return os;
  }

  // HALF is an alias to uint16_t
  DirectX::PackedVector::HALF val = 0;
};

template <typename T> struct LongVectorTestTraits {
  std::uniform_int_distribution<T> UD = std::uniform_int_distribution(
      std::numeric_limits<T>::min(), std::numeric_limits<T>::max());
};

template <> struct LongVectorTestTraits<HLSLHalf_t> {
  // Float values for this were taken from Microsoft online documentation for
  // the DirectX HALF data type. HALF is equivalent to IEEE 754 binary 16
  // format.
  std::uniform_int_distribution<DirectX::PackedVector::HALF> UD =
      std::uniform_int_distribution(
          DirectX::PackedVector::XMConvertFloatToHalf(float(6.10e-5f)),
          DirectX::PackedVector::XMConvertFloatToHalf(float(65504.0f)));
};

template <> struct LongVectorTestTraits<HLSLBool_t> {
  std::uniform_int_distribution<uint16_t> UD =
      std::uniform_int_distribution<uint16_t>(0u, 1u);
};

template <> struct LongVectorTestTraits<float> {
  //  The ranges for generation. A std::uniform_real_distribution can only
  //  have a range that is equal to the types largest value. This is due to
  //  precision issues. So instead we define some large values.
  std::uniform_real_distribution<float> UD =
      std::uniform_real_distribution(-1e20f, 1e20f);
};

template <> struct LongVectorTestTraits<double> {
  //  The ranges for generation. A std::uniform_real_distribution can only
  //  have a range that is equal to the types largest value. This is due to
  //  precision issues. So instead we define some large values.
  std::uniform_real_distribution<double> UD =
      std::uniform_real_distribution(-1e100, 1e100);
};

// Used to pass into LongVectorOpTestBase
template <typename T, LongVectorOpType OpType> struct LongVectorOpTestConfig {
  LongVectorOpTestConfig() {
    TargetString = "cs_6_9";

    switch (OpType) {
    case LongVectorOpType_ScalarAdd:
      OperatorString = "+";
      IsScalarOp = true;
      break;
    case LongVectorOpType_ScalarMultiply:
      OperatorString = "*";
      IsScalarOp = true;
      break;
    case LongVectorOpType_Multiply:
      OperatorString = "*";
      break;
    case LongVectorOpType_Add:
      OperatorString = "+";
      break;
    case LongVectorOpType_Min:
      OperatorString = ",";
      IntrinsicString = "min";
      break;
    case LongVectorOpType_Max:
      OperatorString = ",";
      IntrinsicString = "max";
      break;
    case LongVectorOpType_Clamp:
      IntrinsicString = "testClamp";
      IsBinaryOp = false;
      break;
    case LongVectorOpType_Initialize:
      IntrinsicString = "testInitialize";
      IsBinaryOp = false;
      break;
    default:
      VERIFY_FAIL("Invalid LongVectorOpType");
    }
  }

  // A helper to get the hlsl type as a string for a given C++ type.
  // Used in the long vector tests.
  static std::string GetHLSLTypeString() {
    if (std::is_same_v<T, HLSLBool_t>)
      return "bool";
    if (std::is_same_v<T, HLSLHalf_t>)
      return "half";
    if (std::is_same_v<T, float>)
      return "float";
    if (std::is_same_v<T, double>)
      return "double";
    if (std::is_same_v<T, int16_t>)
      return "int16_t";
    if (std::is_same_v<T, int32_t>)
      return "int";
    if (std::is_same_v<T, int64_t>)
      return "int64_t";
    if (std::is_same_v<T, uint16_t>)
      return "uint16_t";
    if (std::is_same_v<T, uint32_t>)
      return "uint32_t";
    if (std::is_same_v<T, uint64_t>)
      return "uint64_t";

    std::string errStr("GetHLSLTypeString() Unsupported type: ");
    errStr.append(typeid(T).name());
    VERIFY_IS_TRUE(false, errStr.c_str());
    return "UnknownType";
  }

  // To be used for the value of -DOPERATOR
  std::string OperatorString;
  // To be used for the value of -DFUNC
  std::string IntrinsicString;
  std::string TargetString;
  // Optional, can be used to override shader code.
  bool IsScalarOp = false;
  bool IsBinaryOp = true;
  float Tolerance = 0.0;
};

// A helper class to generate deterministic random numbers. For any given seed
// the generated sequence will always be the same. Each call to generate() will
// return the next number in the sequence.

template <typename T> class DeterministicNumberGenerator {
  // Mersenne Twister 'random' number generator. Generated numbers are based
  // on the seed value and are deterministic for any given seed.
  std::mt19937 Generator;

  LongVectorTestTraits<T> UD;

public:
  DeterministicNumberGenerator(unsigned SeedValue) : Generator(SeedValue) {}

  T generate() { return UD.UD(Generator); }
};

template <typename T> bool DoValuesMismatch(T A, T B, float Tolerance) {
  if (Tolerance == 0.0f)
    return A != B;

  T Diff = A > B ? A - B : B - A;
  return Diff > Tolerance;
}

inline bool DoValuesMismatch(HLSLBool_t A, HLSLBool_t B, float) { return A == B; }

template <typename T>
bool DoVectorsMatch(const std::vector<T> &VecInput,
                    const std::vector<T> &VecExpected, float Tolerance) {
  // Sanity check. Ensure both vectors have the same size
  if (VecInput.size() != VecExpected.size()) {
    VERIFY_FAIL(L"Vectors are different sizes!");
    return false;
  }

  // Stash mismatched indexes for easy failure logging later
  std::vector<size_t> MismatchedIndexes;
  for (size_t Index = 0; Index < VecInput.size(); ++Index) {
    if (!DoValuesMismatch(VecInput[Index], VecExpected[Index], Tolerance))
      MismatchedIndexes.push_back(Index);
  }

  if (MismatchedIndexes.empty())
    return true;

  if (!MismatchedIndexes.empty()) {
    for (size_t Index : MismatchedIndexes) {
      std::wstringstream Wss(L"");
      Wss << L"Mismatch at Index: " << Index;
      Wss << L" Actual Value:" << VecInput[Index] << ",";
      Wss << L" Expected Value:" << VecExpected[Index];
      WEX::Logging::Log::Error(Wss.str().c_str());
    }
  }

  return false;
}
