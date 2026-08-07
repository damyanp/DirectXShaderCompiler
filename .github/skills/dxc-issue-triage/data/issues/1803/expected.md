# Expected symptom - #1803 [RW]StructuredBuffer<matrix> ignores orientation

**Repro quality: complete.** Source, entry point (`main`) and construct are all given; only the
target profile is unstated and is freely derivable.

## What was reported (2018-12-21)

`RWStructuredBuffer<rmi22>` where `typedef row_major int2x2 rmi22`. The `row_major` attribute is
lost when the typedef is used as a template argument, because `Sema::CheckTemplateTypeArgument`
canonicalises the type and drops the attribute, so the specialisation is really
`RWStructuredBuffer<matrix<int,2,2>>`.

`buf[0] = int2x2(11, 12, 21, 22)` means m[0][0]=11, m[0][1]=12, m[1][0]=21, m[1][1]=22.

| storage | expected memory order |
| --- | --- |
| row_major (as declared) | 11, 12, 21, 22 |
| column_major (the bug)  | 11, 21, 12, 22 |

Reported DXC output stores `11, 21, 12, 22` - column-major, i.e. `row_major` ignored.
FXC stores `11, 12, 21, 22`.

## The symptom reproduces if

`dx.op.bufferStore.i32` receives the value operands in **column-major** order (11, 21, 12, 22)
despite the `row_major` typedef.

## Control (decides this, rather than merely matching a pattern)

Compile the identical shader with `column_major` substituted for `row_major`. If the two
produce **byte-identical** DXIL, the orientation attribute is provably ignored - far stronger
than matching one operand order. A fixed compiler must differ between the two.

## Not being tested

Whether row-major is the *correct* choice. The reporter notes FXC only honours the typedef form
and rejects `RWStructuredBuffer<row_major int2x2>` outright, so "what should happen" is partly a
language-design question. This triage tests only whether the attribute is honoured at all.
