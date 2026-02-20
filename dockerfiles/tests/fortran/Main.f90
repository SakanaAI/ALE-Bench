include "acl/atcoder/union_find.f08"
program test_fortran_libs
  use, intrinsic :: iso_fortran_env
  use stdlib_sorting
  use stdlib_version
  use mod_union_find
  implicit none

  integer(int32) :: arr(5) = [5, 2, 4, 1, 3]
  type(union_find) :: uf

  call sort(arr)
  if (any(arr /= [1, 2, 3, 4, 5])) error stop "stdlib sorting check failed"

  uf = newuf(6)
  call unite(uf, 1, 2)
  if (.not. same(uf, 1, 2)) error stop "ac-library-fortran check failed"

  write(output_unit, '(a,1x,a)') "FORTRAN_OK", stdlib_version_string
end program test_fortran_libs
