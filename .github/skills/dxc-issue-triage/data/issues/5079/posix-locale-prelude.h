// Force-included (`clang -include`) ahead of every translation unit in this
// issue's captures, purely to supply the POSIX `locale_t` family that
// `include/dxc/WinAdapter.h`'s `ScopedLocale` (line ~918) uses without
// including anything for it -- on real glibc these names arrive
// transitively; on this Windows host, with no Linux sysroot, they are not
// visible from any standard header at all.
//
// NOT part of the conflict under test (see expected.md / notes.md), and
// deliberately NOT a same-named header on the include path: this is a
// forced pre-include, so it cannot shadow a real `<locale.h>` that some
// other, unrelated header might legitimately include for ordinary C-locale
// functionality (`setlocale`, `LC_ALL`, ...). It only makes these five
// names already-declared by the time WinAdapter.h references them.
#pragma once

extern "C" {

typedef void *locale_t;

#define LC_CTYPE_MASK 2

locale_t newlocale(int category_mask, const char *locale, locale_t base);
locale_t uselocale(locale_t newloc);
void freelocale(locale_t locobj);

} // extern "C"
