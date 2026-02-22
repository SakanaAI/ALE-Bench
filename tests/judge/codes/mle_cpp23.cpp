#include <cstddef>
#include <cstdint>
#include <vector>

int main() {
    constexpr std::size_t allocBytes = 1056ULL * 1024ULL * 1024ULL;
    constexpr std::size_t pageSize = 4096;

    std::vector<std::uint8_t> buffer(allocBytes, 0);
    volatile std::uint8_t* touched = buffer.data();
    for (std::size_t i = 0; i < allocBytes; i += pageSize) {
        touched[i] = static_cast<std::uint8_t>(i);
    }
    return 0;
}
