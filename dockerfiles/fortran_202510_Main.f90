include "acl/atcoder/union_find.f08"
program test_stdlib
  use, intrinsic :: iso_fortran_env
  use stdlib_version
  use stdlib_sorting
  use mod_union_find
  implicit none
  integer(int32) :: arr(10) = [10, 2, 1, 5, 7, 8, 3, 9, 6, 4]
  type(union_find) :: uf
  write(output_unit, '(a)') stdlib_version_string
  call sort(arr)
  write(error_unit, '(*(i0, 1x))') arr(:)
  if (any(arr(:) /= [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])) &
      & error stop "Something error"
  uf = newuf(10)
  call unite(uf, 1, 2)
  write(error_unit, '(*(L, 1x))') same(uf, 1, 2), same(uf, 1, 3)
end program
