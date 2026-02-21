include "acl/atcoder/union_find.f08"
program test_fortran_libs
  use, intrinsic :: iso_fortran_env
  use stdlib_sorting
  use stdlib_version
  use mod_union_find
  implicit none

  integer(int32) :: arr(5) = [5, 2, 4, 1, 3]
  type(union_find) :: uf
  integer :: heavy_seconds, ios, i, clk_start, clk_now, clk_rate
  real(real64) :: elapsed_seconds
  integer(int64) :: acc
  character(len=32) :: heavy_raw

  call sort(arr)
  if (any(arr /= [1, 2, 3, 4, 5])) error stop "stdlib sorting check failed"

  uf = newuf(6)
  call unite(uf, 1, 2)
  if (.not. same(uf, 1, 2)) error stop "ac-library-fortran check failed"

  heavy_seconds = 2
  heavy_raw = ""
  call get_environment_variable("HEAVY_SECONDS", heavy_raw, status=ios)
  if (ios == 0 .and. len_trim(heavy_raw) > 0) then
    read(heavy_raw, *, iostat=ios) heavy_seconds
    if (ios /= 0) error stop "invalid HEAVY_SECONDS"
  else if (ios > 1) then
    error stop "failed to read HEAVY_SECONDS"
  end if
  if (heavy_seconds < 1) error stop "invalid HEAVY_SECONDS"

  acc = 1_int64
  call system_clock(clk_start, clk_rate)
  do
    do i = 1, 100000
      acc = mod(acc * 1103515245_int64 + int(i, int64) + 12345_int64, 1000000007_int64)
    end do
    call system_clock(clk_now)
    elapsed_seconds = real(clk_now - clk_start, real64) / real(clk_rate, real64)
    if (elapsed_seconds >= real(heavy_seconds, real64)) exit
  end do

  write(output_unit, '(a,1x,a)') "FORTRAN_OK", stdlib_version_string
  write(output_unit, '(a,1x,i0)') "FORTRAN_HEAVY_OK", acc
end program test_fortran_libs
