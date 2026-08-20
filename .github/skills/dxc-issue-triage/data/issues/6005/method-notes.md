# Method notes — issue #6005

- `bisect --linear` warned that v1.4.1907 rejected `-Wno-c++11-extensions` ("An unrelated
  option can make a valid repro look unprobeable"). Per the skill's guidance to verify such a
  warning rather than accept the narrower range on faith, I re-ran v1.4.1907 with that flag
  (and its two `-Wno-*` siblings) dropped: it still rejects with `Unknown HLSL version: 202`
  (`variant-v1.4.1907-no-wno-flags.txt`). So the exclusion of v1.4.1907–v1.6.2112 from the
  bisectable range is legitimate — it is genuinely `-HV 202x` support that is missing, not an
  artifact of the unrelated warning flags — and the warning did not require widening the
  reported range. No change to the tool needed; recording this because the warning fired and
  the check it asks for is easy to skip.
- No other tooling defects or ambiguities encountered. `internal_failure` classification,
  `bisect`'s Release/NDEBUG warning, and the invalid-probe demotion for `-HV 202x` all worked
  exactly as documented.
