# Expected symptom

Issue: #5681 "Segmentation fault/ICE when attempting a particular (invalid) code pattern"

Reporter's claim: compiling a shader that calls `InterlockedMax` (a global-scope atomic
intrinsic) directly on a field of the value returned by `RWByteAddressBuffer::Load<T>(0)`
(a templated/typed load) makes `dxc` crash internally (an ICE / "segmentation fault"),
instead of emitting an ordinary diagnostic rejecting the construct. The reporter explicitly
says the source **is invalid** — `InterlockedMax`'s first argument must be an lvalue backed by
groupshared/UAV storage, not the temporary returned by a templated `Load<T>()` — and the bug is
that DXC crashes rather than diagnoses that.

"This reproduces" means: compiling the repro with the ground-truth `dxc` produces an internal
failure (crash/assert/access-violation-class exit), not exit 0 and not an ordinary `error:`
diagnostic that gracefully rejects the construct.

Repro quality: **complete**. The issue body gives a minimal, direct snippet; a maintainer
(llvm-beanz) separately posted a Compiler Explorer link
(https://godbolt.org/z/5n31h354h) that wraps the exact same statements from the issue body in
a `[numthreads(1,1,1)] void main()` entry point, which is what turns the reporter's fragment
into compilable HLSL. That is the version this triage builds from.

Not compiler-verifiable aside: the reporter's closing question ("is there a way to express the
intent above with valid HLSL today?") is a language-capability question, not something a single
probe settles — the thread's own follow-up comments answer it with `RWByteAddressBuffer`'s
member `InterlockedMax(byteOffset, value, original)` plus manual `sizeof/offsetof` arithmetic
for the field offset. That is not this triage's compiler-behaviour question and is left to the
comment draft as context only.
