// Issue 4721 -- probe-validity control for the release matrix.
//
// This shader contains nothing interesting on purpose. Its only job is to
// answer one question per build: does this dxc accept -HV 2021 and get as far
// as compiling a shader? A build that answers "Unknown HLSL version: 2021"
// never reaches Sema, so "it printed no fix-it hint" for the repro is a
// statement about argument parsing, not about fix-it rendering.
//
// It must NOT use any construct whose availability varies across releases --
// including the and()/select() intrinsics -- or a failure here would be
// ambiguous between "cannot express HLSL 2021" and "lacks that intrinsic".

float4 main() : SV_Target {
  return 0;
}
