import numpy as np


def main() -> None:
    arr = np.zeros((128, 1024, 1024), dtype=np.uint64)
    arr += 3


if __name__ == "__main__":
    main()
