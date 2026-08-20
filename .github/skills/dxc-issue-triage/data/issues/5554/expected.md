# Expected symptom — #5554

Title: "C++11 enums don't work as integer constants as expected". Repro quality:
**partial** — the issue body's own godbolt link (`1TdYh9E1a`) does not actually declare an
`enum class` at all (confirmed by a maintainer comment), so the real repro only appears later
in the thread, and it changes shape twice more after that. This is a **multi-ask** issue;
score each ask separately (SKILL.md step 4).

## Ask A — scoped enum used directly as an array index / integral expression (no cast)
Source (`godbolt.org/z/Pxd1zacr7`): `enum class KEK : uint {...}`, then
`partiboi[KEK::WAIT]` (array index, no cast) and `test<KEK::COUNT>` where the template
parameter is a plain `int sz` (template argument, no cast). Reporter's own next comment
(`godbolt.org/z/M6Kna6r7s`) inserts `(uint)` casts on **both** usages and reports it then
works. "Reproduces" for Ask A means: the uncast form is rejected by DXC AND real C++ would
also reject an implicit scoped-enum-to-int conversion in the same spot (i.e. DXC matches
C++ semantics rather than being a bug). If DXC's cast-free form compiles silently instead,
that is the actual bug this ask originally worried about.

## Ask B — `enum class` as a non-type template parameter's own type
Source (`godbolt.org/z/8hqrj1ezr`): `template<KEK sz> struct test { ... }`, i.e. the
template parameter itself is declared with type `KEK` (a scoped enum), not `int`.
"Reproduces" means this is rejected (or silently accepted incorrectly) where real C++ (a
scoped enum is a structural type and is a legal non-type template parameter type) would
accept it.

## Ask C — generic `integral_constant<T, T val>`-style template instantiated with an enum type
Source (`godbolt.org/z/EGaesxvE1`, filed directly on #5554): a **plain** (unscoped)
`enum Test` used as `integral_constant<Test, A>`; the comment claims this is "busted" too.
A near-duplicate issue, #6706 (closed as a duplicate of #5554), narrows this to exactly the
scoped-vs-unscoped contrast with two single-line-different godbolt links:
`hheGKo9vx` (`enum class ENUM` as `integral_constant<ENUM, ENUM::TRUE>`, reported broken) vs
`7rorK5qoW` (plain `enum ENUM`, reported to work). "Reproduces" for Ask C means the scoped
form fails while the unscoped form (same template, same pattern) succeeds — i.e. the gap is
specific to `enum class`, not to enums-as-template-arguments in general. #6706 is not itself
a fresh probe target — it is used here only for its precise minimal contrast and for the
maintainer statement recorded on it (see below).

## Maintainer position already on record
On the duplicate #6706, a maintainer (`damyanp`) wrote: *"While we'd consider accepting PR
that addresses this issue, we're not planning on investing in fixing this in DXC. This won't
be an issue in clang."* That is a **design/roadmap statement**, not a report that the bug is
already fixed — record it as such and do not read it as `does-not-repro`.

## Last thread event
The most recent comment (`llvm-beanz`, 2026-02-13): *"Oops... wrong window. Sorry for the
false hope."* — this is not a substantive update; note it in `notes.md` so a reader does not
mistake it for one.
