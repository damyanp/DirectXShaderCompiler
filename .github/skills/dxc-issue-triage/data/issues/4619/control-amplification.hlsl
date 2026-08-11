// #4619 control -- sibling-stage control for ask A.
//
// An amplification shader with the same [numthreads(32, 2, 1)]. AS is the
// other stage that has a thread group but is not compute, and it was fixed in
// the same change as MS, so its behaviour dates the fix for the whole
// non-compute family rather than for mesh alone.
//
// Expected: no-match under match.json (the shader kind is Amplification, and
// the accessor reports 32,2,1 on current builds).

struct Payload {
  uint dummy;
};

groupshared Payload p;

[numthreads(32, 2, 1)]
void main(uint gtid : SV_GroupThreadID) {
  p.dummy = gtid;
  DispatchMesh(1, 1, 1, p);
}
