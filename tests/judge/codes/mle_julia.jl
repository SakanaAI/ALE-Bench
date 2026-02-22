chunks = Vector{Vector{UInt8}}()
for i in 1:70
    chunk = fill(UInt8(i % 256), 16 * 1024 * 1024)
    for j in 1:4096:length(chunk)
        chunk[j] = UInt8((i + j) % 256)
    end
    push!(chunks, chunk)
end

if length(chunks) != 70
    error("allocation failed")
end
