chunks = []
for i in range(70):
    chunk = bytearray(16 * 1024 * 1024)
    for j in range(0, len(chunk), 4096):
        chunk[j] = (i + j) & 255
    chunks.append(chunk)

if len(chunks) != 70:
    raise RuntimeError("allocation failed")
