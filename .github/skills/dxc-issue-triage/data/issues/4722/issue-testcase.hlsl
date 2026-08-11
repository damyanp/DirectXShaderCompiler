// Issue 4722's own test case, run through dxc's -verify mode.
//
// Reproduced verbatim from the issue body with exactly two deviations, both
// forced and both recorded in expected.md:
//
//   1. The second member of each struct is named `ColumnMajor`. The issue body
//      names it `RowMajor` in both structs, which is a redefinition and cannot
//      compile; the intent is obvious from the qualifier.
//   2. The RUN line is `%clang_cc1 -HV 2021 -fsyntax-only -ffreestanding -verify`.
//      dxc has -verify but needs a target profile and an entry point, so it is
//      driven as `-T ps_6_0 -E fn -HV 2021 -verify`.
//
// The diagnostic directives below are the author's, unchanged. -verify therefore
// reports exactly the difference between what the author said should happen and
// what dxc does.

template <typename T, int X, int Y>
struct Matrices {
  row_major matrix<T, X, Y> RowMajor;
  column_major matrix<T, X, Y> ColumnMajor;

  row_major T NotAMatrix;        // expected-error {{'row_major' can only be used with a matrix type}}
  column_major T AlsoNotAMatrix; // expected-error {{'column_major' can only be used with a matrix type}}
};

struct AlsoMatrices {
  row_major matrix<float, 4, 4> RowMajor;
  column_major matrix<float, 4, 4> ColumnMajor;

  row_major float NotAMatrix;        // expected-error {{'row_major' can only be used with a matrix type}}
  column_major float AlsoNotAMatrix; // expected-error {{'column_major' can only be used with a matrix type}}
};

void fn() {
  Matrices<float, 4, 4> ShouldWork;
}
