# Expected behaviour — #5115

Repro quality: **complete**. The issue body gives the exact HLSL program, the exact `dxc`
diagnostic, a contrasting variation, and a public Compiler Explorer permalink
(https://godbolt.org/z/K5rWWj4c3) for the failing case plus a second link comparing against
gcc12's C++ overload resolution on the equivalent code
(https://godbolt.org/z/h4s4bx566).

## The two programs

**Program A** (`repro.hlsl`) — calls `f(1)`, an ordinary `int` literal:

```hlsl
void f(unsigned int){}
void f(int){}

float4 PSMain() : SV_TARGET
{
    f(1);
    return (float4)0;
}
```

Reported: DXC errors with

```
<source>:6:5: error: call to 'f' is ambiguous
    f(1);
    ^
<source>:1:6: note: candidate function
void f(unsigned int){}
     ^
<source>:2:6: note: candidate function
void f(int){}
     ^
```

**Program B** (`control-unsigned-literal.hlsl`) — identical except the call site is `f(1u)`
(an explicitly-`unsigned` literal): reported to compile with **no diagnostic at all**.

## What "reproduces" means

The reporter's claim is not merely "this errors" — it is that DXC's overload resolution is
**inconsistent with the language it copies (C++)**: an ordinary `int` literal argument should
resolve unambiguously to the exact-match `f(int)` overload (as gcc12 does, per the second
godbolt link, which the reporter used as the comparison baseline), not report ambiguity. The
`f(1u)` variant compiling silently is offered as evidence that DXC *is* able to pick a single
overload when the argument's type unambiguously matches one candidate — it just fails to do
so for a plain (signed) integer literal against `int`/`unsigned int` overloads.

So the symptom under test is: **compiling Program A produces the "call to 'f' is ambiguous"
diagnostic naming both candidates**, where the reporter (and the maintainer response) hold
that a correctly-implemented overload resolution would pick `f(int)` without complaint.

A maintainer (llvm-beanz, COLLABORATOR) commented same-day (2023-06-30) that this is
acknowledged, current DXC behaviour: "This is caused by broken behavior in DXC's overload
resolution... [a planned HLSL 202x feature] is effectively going to result in us adopting
C++ overload rules completely for HLSL, which should solve this and related issues." No PR,
commit, or later comment references a fix for this specific case; the issue carries `bug` and
`hlsl-next` and has never been closed.

Given that framing, `repros` means: Program A still emits the ambiguous-call diagnostic
(DXC still uses its own, not-C++-compatible overload resolution). `does-not-repro` would mean
Program A now compiles silently (or resolves unambiguously to one candidate) instead. There is
no realistic "changed-behavior" shape here short of the diagnostic wording changing while the
overload set still being rejected as ambiguous, which would still count as `repros` for this
issue's purposes (the reported design problem — ambiguity is reported where C++ would not
report it — would remain).

The control (`f(1u)`) is expected to keep compiling cleanly (`--expect no-match` against the
same predicate) on every compiler tested, as a sanity check that the predicate does not simply
fire on every use of `f`.
