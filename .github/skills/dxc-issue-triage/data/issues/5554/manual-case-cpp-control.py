"""Corroborating control (not a dxc probe): confirms with a real C++ compiler (Compiler
Explorer's gcc) that (1) a scoped enum used directly as an array index without a cast is
rejected by standard C++ too (Ask A's array-index sub-claim is NOT a DXC bug), and (2) a
scoped enum used as an exactly-typed non-type template argument (matching the pattern DXC
rejects with "non-type template argument of type 'X' is not an integral constant
expression") is accepted by standard C++ (the underlying defect this issue's Ask B/C
describe is a genuine DXC/C++ divergence, not a design choice). Run with:
    python manual-case-cpp-control.py
Prints the exact HTTP request body and the compiler's response for both cases.
"""
import json
import urllib.request

CASES = [
    (
        "array-index-no-cast",
        "enum class KEK : unsigned { WAIT = 69 };\n"
        "int arr[128];\n"
        "int main(){ return arr[KEK::WAIT]; }\n",
    ),
    (
        "enum-as-exact-nontype-template-arg",
        "template<typename T, T val> struct integral_constant "
        "{ static const T value = val; };\n"
        "enum class ENUM : unsigned { TRUE_ = 0 };\n"
        "typedef integral_constant<ENUM, ENUM::TRUE_> test_t;\n"
        "int main(){ return (int)test_t::value; }\n",
    ),
]

URL = "https://godbolt.org/api/compiler/g132/compile"

for label, source in CASES:
    body = json.dumps(
        {"source": source, "options": {"userArguments": "-std=c++17",
                                        "compilerOptions": {}, "filters": {}}}
    ).encode("utf-8")
    print(f"=== {label} ===")
    print(f"$ POST {URL}")
    print(f"source:\n{source}")
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        print("--- response ---")
        print(resp.read().decode("utf-8"))
    print()
