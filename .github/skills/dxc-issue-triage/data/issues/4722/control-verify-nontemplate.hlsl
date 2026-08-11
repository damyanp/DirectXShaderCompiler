// Control for issue 4722's -verify measurement: the non-template half of the
// author's test case, on its own, carrying the author's own diagnostic
// directives.
//
// Expect NO MATCH under match-verify.json. Everything the author expects here
// happens: both matrix members compile and both non-matrix members are
// diagnosed, so -verify reports nothing. That is what makes the unexpected
// errors in issue-testcase.hlsl attributable to the template and not to the
// declarations themselves.

struct AlsoMatrices {
  row_major matrix<float, 4, 4> RowMajor;
  column_major matrix<float, 4, 4> ColumnMajor;

  row_major float NotAMatrix;        // expected-error {{'row_major' can only be used with a matrix type}}
  column_major float AlsoNotAMatrix; // expected-error {{'column_major' can only be used with a matrix type}}
};

void fn() {
  AlsoMatrices ShouldWork;
}
