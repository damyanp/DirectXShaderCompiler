// #2633 -- both halves of "link libraries" in one file, because Compiler
// Explorer is single-file. `-DIMPORT_HALF=1` selects the half.
//
// This is a TRANSFORMATION of the two-file repro (lib-export.hlsl and
// repro.hlsl), so it is checked against them locally before being published:
// variant-ce-export-half-* and variant-ce-import-half-* must reproduce exactly
// what the separate files do.

#ifndef IMPORT_HALF

// ---- EXPORT half: the library that provides `foo`. ------------------------
// Compiles. Emits OpCapability Linkage + LinkageAttributes "foo" Export.

export float4 foo(float4 p) { return p * 0.5f; }

#else

// ---- IMPORT half: the module that wants to CALL `foo` from elsewhere. -----
// @s-perron's own case, from https://godbolt.org/z/4s8xaEdTK.
// Does not compile: there is no way to say "resolve this at link time".

struct vertexInfo {
  float4 position : POSITION;
};

struct v2p {
  float4 position : SV_POSITION;
};

float4 foo(float4 p);

[shader("vertex")] v2p vertexShader(vertexInfo input) {
  v2p output;
  output.position = foo(input.position);
  return output;
}

#endif
