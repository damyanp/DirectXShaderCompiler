# Expected symptom — #1627 "force include file"

**Reported (2018-10-24):** there is no way to force a header to be included from the command
line; the reporter expected an `-include <filename>` flag. Re-requested by a second user in
2025-07, which is evidence of live demand.

**Repro quality:** `prose-only` in the issue — repro is **agent-constructed**: a shader that
references a macro defined only in a separate header, compiled with `-include forced.h`.

**What we test:** `dxc -T ps_6_0 -E main -include forced.h repro.hlsl`.

**Symptom is present if:** dxc rejects `-include` as an unknown argument.

**Symptom is absent if:** dxc accepts the flag and the shader compiles, proving the header
was force-included.

**Note:** this is an `enhancement` labelled `low-hanging-fruit`. "Still repros" means "still
not implemented".
