using Combinatorics
using DataStructures
using DelimitedFiles
using Distributions
using InvertedIndices
using IterTools
using OffsetArrays
using PrecompileTools
using Primes
using StaticArrays

# Combinatorics
perms = collect(permutations([1, 2, 3]))
@assert length(perms) == 6

# DataStructures
pq = PriorityQueue{String, Int}()
enqueue!(pq, "a", 3)
enqueue!(pq, "b", 1)
enqueue!(pq, "c", 2)
@assert dequeue!(pq) == "b"

# DelimitedFiles
buf = IOBuffer()
writedlm(buf, [1 2 3; 4 5 6])
seekstart(buf)
mat = readdlm(buf, '\t', Int)
@assert mat == [1 2 3; 4 5 6]

# Distributions
d = Normal(0.0, 1.0)
@assert abs(mean(d)) < 1e-10
@assert abs(std(d) - 1.0) < 1e-10

# InvertedIndices
arr = [10, 20, 30, 40, 50]
@assert arr[Not(3)] == [10, 20, 40, 50]

# IterTools
chained = collect(IterTools.chain([1, 2], [3, 4]))
@assert chained == [1, 2, 3, 4]

# OffsetArrays
oa = OffsetArray([10, 20, 30], 0:2)
@assert oa[0] == 10
@assert oa[2] == 30

# Primes
@assert isprime(17)
@assert !isprime(18)
@assert factor(Dict, 12) == Dict(2 => 2, 3 => 1)

# StaticArrays
sv = SVector(1.0, 2.0, 3.0)
@assert length(sv) == 3
@assert sum(sv) == 6.0

heavy_seconds = try
    parse(Int, get(ENV, "HEAVY_SECONDS", "2"))
catch
    throw(ArgumentError("invalid HEAVY_SECONDS"))
end
@assert heavy_seconds >= 1

deadline_ns = time_ns() + UInt64(heavy_seconds) * UInt64(1_000_000_000)
function run_heavy(deadline_ns::UInt64)
    acc = 1
    while time_ns() < deadline_ns
        for i in 1:100000
            acc = mod(acc * 1103515245 + i + 12345, 1000000007)
        end
    end
    return acc
end

acc = run_heavy(deadline_ns)

println("JULIA_OK")
println("JULIA_HEAVY_OK ", acc)
