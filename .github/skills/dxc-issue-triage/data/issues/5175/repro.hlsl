// Verbatim from the issue's first comment (jeremyong, 2023-04-25).
//
// This is NOT run through dxc.exe: the symptom is an absence on the IDxcCursor COM interface
// (include/dxc/dxcisense.h), which dxc.exe does not expose a command line for. It is kept here
// as the exact input the reporter's AST dump (quoted in expected.md/notes.md) was produced
// from, and as a positive control that the source itself is valid HLSL (class templates with
// a type parameter and two non-type parameters compile and instantiate without diagnostics).
template <typename A, int B, uint C> class Foo {};
Foo<float, -2, 3> foo;
