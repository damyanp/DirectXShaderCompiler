# Expected symptom — #1306 "Validation for sync in varying flow control"

**Reported (2018-05-24):** FXC reports `error X3663: thread sync operation found in varying
flow control` for a `GroupMemoryBarrierWithGroupSync()` inside a thread-id-dependent `if`.
DXC does not. The issue is a request for DXC to perform the same analysis.

**Repro quality:** `complete` — the issue supplies a full compute shader.

**What we test:** compile the supplied shader as `cs_6_0`.

**Symptom is present if:** DXC produces no diagnostic mentioning varying flow control /
thread sync (i.e. the requested feature still does not exist).

**Symptom is absent if:** DXC emits an X3663-equivalent error or warning.

**Note:** this is an `enhancement`, not a regression. "Still repros" means "still not
implemented". Discussion on the issue (2018 and 2024) points at uniformity analysis in Clang
as the likely home for this, not DXC.
