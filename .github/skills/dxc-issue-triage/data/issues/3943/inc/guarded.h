#ifndef INC_GUARDED_H
#define INC_GUARDED_H

// Same content as common.h, but protected by a traditional include guard rather
// than `#pragma once`. A guard is keyed on a macro name, not on file identity,
// so it cannot be confused by two spellings of the same path. This is the
// workaround the issue thread already uses.
float CommonValue() { return 1.0f; }

#endif // INC_GUARDED_H
