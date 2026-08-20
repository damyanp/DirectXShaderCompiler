# Method notes for #5987 (do not promote cross-issue claims here into comment.md)

- **Same assert as #5338, different trigger shape -- flag for collation, do not assert.**
  #5987's Debug assert stack (`manual-case-assert-stack.txt`) is byte-for-byte the same
  `Error:`/`File:`/`Func:` triple as #5338's (`ScalarReplAggregatesHLSL.cpp(2630)`,
  `SROA_Helper::RewriteBitCast`, "expected struct bitcast to only be used by lifetime
  intrinsics"). The reporter of #5987 explicitly asked whether it might be a duplicate of
  #5338 but noted their repro has no explicit cast, unlike #5338's array-reinterpret cast.
  Per this skill's parallel-worker rule, "is this the same as #NNNN" is collation's call, so
  this is recorded here rather than in `comment.md`. If collation confirms the same root
  cause, note that the two issues' *repros* differ (whole-struct assign vs. explicit
  reinterpret-cast into an array) even though the assert is identical -- both are inputs the
  HLSL SROA pass's bitcast-rewrite does not expect, which suggests the underlying invariant
  the assert protects is too narrow for legitimate whole-struct-copy codegen, not that either
  repro is somehow invalid input.

- **`as_6_7` profile lets `bisect --linear` classify the whole pre-SM6.7 history as
  `invalid-probe` cleanly**, with no ambiguity: every release through v1.6.2112 answers the
  single, unambiguous `error: invalid profile as_6_7` and nothing else. No positive
  feature-presence control was needed beyond that literal diagnostic, unlike the trickier
  cases in the skill's own trap list (e.g. a release accepting a profile but lacking a
  *subsystem* within it). Confirmed anyway that v1.7.2207, the first release able to compile
  it at all, reproduces on the first try -- there is no ambiguous transition to chase.

- **Both of the reporter's own described workarounds make good `--expect no-match`
  controls verbatim**, with no reconstruction needed: "comment out the assignment" and
  "unwrap the struct" map directly to two `.hlsl` files. Both passed on the first run. This
  is a case where the issue text already supplies a complete control pair, so no further
  variant construction was needed to establish predicate specificity.
