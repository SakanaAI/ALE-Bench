program main
  use, intrinsic :: iso_fortran_env
  implicit none
  integer(int8), allocatable :: arr(:)
  integer :: i

  allocate(arr(1174405120))
  do i = 1, size(arr), 4096
    arr(i) = int(mod(i, 127), int8)
  end do
end program main
