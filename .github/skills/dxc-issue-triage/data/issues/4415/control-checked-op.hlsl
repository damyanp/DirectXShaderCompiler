// #4415 control input: a trivially valid shader whose DXIL contains one
// resource-consuming op that ValidateHandleArgs *does* check (textureLoad).
//
// make-modules.py doctors this module's textureLoad handle operand to
// `undef` and to `zeroinitializer` -- the same two invalid handle values the
// subject modules put in `annotateHandle` -- so the pair of captures differs
// in the *opcode* alone. If the checked opcode is rejected and annotateHandle
// is accepted, the gap is in the opcode coverage, not in the handle value,
// not in the module, and not in the harness.
Texture2D<float4> T : register(t0);

float4 main() : SV_Target {
  return T.Load(int3(0, 0, 0));
}
