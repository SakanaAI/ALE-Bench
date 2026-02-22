program main
  use, intrinsic :: iso_fortran_env
  implicit none
  integer(int8), allocatable, volatile :: blocks(:, :)
  integer :: i, j

  ! Allocate >1 GiB and touch pages to ensure RSS grows.
  allocate(blocks(16 * 1024 * 1024, 66))
  do j = 1, size(blocks, 2)
    do i = 1, size(blocks, 1), 4096
      blocks(i, j) = int(mod(i + j, 127), int8)
    end do
  end do
end program main
